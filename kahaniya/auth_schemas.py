from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    phone_number: str | None = Field(default=None, min_length=9, max_length=16, pattern=r"^\+[1-9][0-9]{7,14}$")
    password: str = Field(min_length=10, max_length=128)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()


class PasswordLoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class PhoneRequest(BaseModel):
    phone_number: str = Field(min_length=9, max_length=16, pattern=r"^\+[1-9][0-9]{7,14}$")


class OTPVerifyRequest(PhoneRequest):
    otp: str = Field(pattern=r"^[0-9]{6}$")


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    username: str
    phone_number: str | None
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    user: UserResponse
    message: str = "Signed in successfully"


class DevelopmentCodeResponse(BaseModel):
    message: str
    development_code: str | None = None
    development_reset_token: str | None = None