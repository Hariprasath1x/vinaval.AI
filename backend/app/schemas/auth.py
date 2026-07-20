from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    google_id: Optional[str] = None
    hashed_password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    selected_exam: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Email / Password Auth ─────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str   # plain-text, will be hashed server-side


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Google OAuth (kept for legacy / future use) ───────────────────────────────

class GoogleCallbackRequest(BaseModel):
    code: str
