import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(16), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    user: Mapped[User] = relationship(back_populates="sessions")


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purpose: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    author: Mapped[str] = mapped_column(String(300), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    genres: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    themes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    moods: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    intents: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    complexity: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    pace: Mapped[str] = mapped_column(String(40), nullable=False, default="Steady")
    description: Mapped[str] = mapped_column(String(600), nullable=False, default="")
    tone: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    year: Mapped[int | None] = mapped_column(Integer)
    badge: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    color: Mapped[str] = mapped_column(String(10), nullable=False, default="#487d68")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)