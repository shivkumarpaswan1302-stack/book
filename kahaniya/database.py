import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

IS_VERCEL = os.getenv("VERCEL") == "1"
APP_ENV = os.getenv("APP_ENV", "production" if IS_VERCEL else "development").lower()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL and APP_ENV == "production":
    raise RuntimeError("DATABASE_URL must be configured in production")
DATABASE_URL = DATABASE_URL or "postgresql+psycopg://postgres:postgres@localhost:5432/kahaniya"
if DATABASE_URL.startswith(("postgres://", "postgresql://")):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()