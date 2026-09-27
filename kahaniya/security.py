import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash


APP_ENV = os.getenv("APP_ENV", "development").lower()
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    if APP_ENV == "production":
        raise RuntimeError("JWT_SECRET must be configured in production")
    JWT_SECRET = "development-only-kahaniya-secret-change-before-deploy"
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 characters")
password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-user-password")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "14"))
DEVELOPMENT_CODES = APP_ENV != "production" and os.getenv("AUTH_EXPOSE_DEV_CODES", "true").lower() == "true"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def hash_secret(value: str) -> str:
    return hmac.new(JWT_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


def verify_secret(value: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_secret(value), expected_hash)


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: UUID, session_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], options={"require": ["sub", "sid", "exp"]})
        if payload.get("type") != "access":
            return None
        UUID(payload["sub"])
        UUID(payload["sid"])
        return payload
    except (jwt.InvalidTokenError, ValueError, KeyError):
        return None