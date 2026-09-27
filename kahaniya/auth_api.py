import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth_delivery import send_otp, send_password_reset
from .auth_schemas import (
    AuthResponse,
    DevelopmentCodeResponse,
    ForgotPasswordRequest,
    OTPVerifyRequest,
    PasswordLoginRequest,
    PhoneRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from .database import get_db
from .models import AuthChallenge, AuthSession, User, utc_now
from .security import (
    ACCESS_TOKEN_MINUTES,
    DEVELOPMENT_CODES,
    REFRESH_TOKEN_DAYS,
    DUMMY_PASSWORD_HASH,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_secret,
    new_refresh_token,
    verify_password,
    verify_secret,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
ACCESS_COOKIE = "kahaniya_access"
REFRESH_COOKIE = "kahaniya_refresh"
COOKIE_SECURE = os.getenv("APP_ENV", "development").lower() == "production"


def _set_session_cookies(response: Response, user: User, session: AuthSession, refresh_token: str) -> None:
    response.set_cookie(ACCESS_COOKIE, create_access_token(user.id, session.id), max_age=ACCESS_TOKEN_MINUTES * 60, httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/")
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=REFRESH_TOKEN_DAYS * 86400, httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/")


def _create_session(db: Session, user: User, response: Response) -> None:
    refresh_token = new_refresh_token()
    session = AuthSession(user_id=user.id, refresh_token_hash=hash_secret(refresh_token), expires_at=utc_now() + timedelta(days=REFRESH_TOKEN_DAYS))
    db.add(session)
    db.commit()
    db.refresh(session)
    _set_session_cookies(response, user, session, refresh_token)


def _access_token(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return request.cookies.get(ACCESS_COOKIE)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    token = _access_token(request, credentials)
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="Please sign in", headers={"WWW-Authenticate": "Bearer"})
    session = db.get(AuthSession, UUID(payload["sid"]))
    if not session or session.revoked_at or session.expires_at <= utc_now() or str(session.user_id) != payload["sub"]:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    return user


def _issue_challenge(db: Session, purpose: str, subject: str, secret: str, expires: timedelta) -> AuthChallenge:
    challenge = AuthChallenge(purpose=purpose, subject=subject, secret_hash=hash_secret(secret), expires_at=utc_now() + expires)
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge


def _verify_challenge(db: Session, challenge: AuthChallenge | None, secret: str) -> bool:
    if not challenge or challenge.consumed_at or challenge.expires_at <= utc_now() or challenge.attempts >= 5:
        return False
    challenge.attempts += 1
    valid = verify_secret(secret, challenge.secret_hash)
    if valid:
        challenge.consumed_at = utc_now()
    db.commit()
    return valid


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    user = User(name=payload.name, email=str(payload.email).lower(), username=payload.username.lower(), phone_number=payload.phone_number, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        _create_session(db, user, response)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email, username, or phone number is already registered") from exc
    return AuthResponse(user=UserResponse.model_validate(user), message="Your कHaniya account is ready")


@router.post("/login", response_model=AuthResponse)
def password_login(payload: PasswordLoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    identifier = payload.identifier.strip().lower()
    user = db.scalar(select(User).where(or_(User.email == identifier, User.username == identifier)))
    hashed = user.password_hash if user else DUMMY_PASSWORD_HASH
    valid_password = verify_password(payload.password, hashed)
    if not user or not valid_password:
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 10:
                user.failed_login_attempts = 0
                user.locked_until = utc_now() + timedelta(minutes=15)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid email/username or password")
    if user.locked_until and user.locked_until > utc_now():
        raise HTTPException(status_code=401, detail="Invalid email/username or password")
    if user.locked_until or user.failed_login_attempts:
        user.locked_until = None
        user.failed_login_attempts = 0
        db.commit()
    _create_session(db, user, response)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/send-otp", response_model=DevelopmentCodeResponse)
def send_phone_otp(payload: PhoneRequest, db: Session = Depends(get_db)) -> DevelopmentCodeResponse:
    now = utc_now()
    recent = db.scalar(select(AuthChallenge).where(AuthChallenge.purpose == "phone_login", AuthChallenge.subject == payload.phone_number, AuthChallenge.created_at > now - timedelta(seconds=60)).order_by(AuthChallenge.created_at.desc()))
    if recent:
        raise HTTPException(status_code=429, detail="Please wait before requesting another code")
    code = f"{secrets.randbelow(1_000_000):06d}"
    send_otp(payload.phone_number, code)
    _issue_challenge(db, "phone_login", payload.phone_number, code, timedelta(minutes=10))
    return DevelopmentCodeResponse(message="If this number can sign in, a code has been sent", development_code=code if DEVELOPMENT_CODES else None)


@router.post("/verify-otp", response_model=AuthResponse)
def verify_phone_otp(payload: OTPVerifyRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.purpose == "phone_login", AuthChallenge.subject == payload.phone_number, AuthChallenge.consumed_at.is_(None)).order_by(AuthChallenge.created_at.desc()))
    if not _verify_challenge(db, challenge, payload.otp):
        raise HTTPException(status_code=400, detail="The code is invalid or expired")
    user = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if not user:
        raise HTTPException(status_code=401, detail="No account is linked to this phone number")
    user.is_verified = True
    user.updated_at = utc_now()
    db.commit()
    _create_session(db, user, response)
    return AuthResponse(user=UserResponse.model_validate(user), message="Phone verified. Welcome back")


@router.post("/forgot-password", response_model=DevelopmentCodeResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)) -> DevelopmentCodeResponse:
    identifier = payload.identifier.strip().lower()
    user = db.scalar(select(User).where(or_(User.email == identifier, User.username == identifier)))
    response = DevelopmentCodeResponse(message="If an account matches, reset instructions will be sent")
    if not user:
        return response
    recent_reset = db.scalar(select(AuthChallenge).where(AuthChallenge.purpose == "password_reset", AuthChallenge.subject == str(user.id), AuthChallenge.created_at > utc_now() - timedelta(minutes=1)))
    if recent_reset:
        return response
    secret = secrets.token_urlsafe(32)
    challenge = _issue_challenge(db, "password_reset", str(user.id), secret, timedelta(minutes=30))
    reset_token = f"{challenge.id}.{secret}"
    base_url = os.getenv("FRONTEND_BASE_URL", str(request.base_url).rstrip("/"))
    reset_url = f"{base_url}/?reset_token={reset_token}"
    try:
        delivered = send_password_reset(user.email, reset_url)
    except Exception:
        logging.getLogger(__name__).exception("Password reset email delivery failed")
        delivered = False
    if DEVELOPMENT_CODES and not delivered:
        response.development_reset_token = reset_token
    return response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        challenge_id, secret = payload.reset_token.split(".", 1)
        challenge = db.get(AuthChallenge, UUID(challenge_id))
    except (ValueError, AttributeError):
        challenge, secret = None, ""
    if not challenge or challenge.purpose != "password_reset" or not _verify_challenge(db, challenge, secret):
        raise HTTPException(status_code=400, detail="The reset link is invalid or expired")
    user = db.get(User, UUID(challenge.subject))
    if not user:
        raise HTTPException(status_code=400, detail="The reset link is invalid or expired")
    user.password_hash = hash_password(payload.new_password)
    user.updated_at = utc_now()
    for session in user.sessions:
        session.revoked_at = utc_now()
    db.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    return {"message": "Password updated. Please sign in"}


@router.post("/refresh", response_model=AuthResponse)
def refresh_session(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again")
    session = db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == hash_secret(refresh_token)))
    if not session or session.revoked_at or session.expires_at <= utc_now():
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    next_refresh_token = new_refresh_token()
    session.refresh_token_hash = hash_secret(next_refresh_token)
    session.expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_DAYS)
    db.commit()
    _set_session_cookies(response, user, session, next_refresh_token)
    return AuthResponse(user=UserResponse.model_validate(user), message="Session restored")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Response:
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    token = _access_token(request, credentials)
    payload = decode_access_token(token) if token else None
    sessions_to_revoke = []
    if payload:
        access_session = db.get(AuthSession, UUID(payload["sid"]))
        if access_session:
            sessions_to_revoke.append(access_session)
    if refresh_token:
        refresh_session = db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == hash_secret(refresh_token)))
        if refresh_session:
            sessions_to_revoke.append(refresh_session)
    if sessions_to_revoke:
        for session in sessions_to_revoke:
            if not session.revoked_at:
                session.revoked_at = utc_now()
        db.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response