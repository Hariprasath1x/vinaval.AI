from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import httpx

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.auth_service import AuthService
from app.core.config import get_settings as _get_settings
from app.schemas.auth import (
    TokenResponse,
    UserResponse,
    SignupRequest,
    LoginRequest,
    ProfileUpdateRequest,
    ChangePasswordRequest,
    RefreshTokenRequest,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Firebase Web API key — public client-side key, safe to expose in source.
# Move to FIREBASE_WEB_API_KEY env var for easy rotation without code changes.
_FIREBASE_API_KEY = _get_settings().FIREBASE_WEB_API_KEY


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token.
    """
    try:
        service = AuthService(db)
        return await service.refresh_token(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {exc}",
        )


# ── Sign Up ───────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new account with name, email, and password.
    Returns a JWT token immediately — no separate login step needed.
    """
    try:
        service = AuthService(db)
        return await service.signup(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {exc}",
        )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email and password.
    Returns a JWT token on success.
    """
    try:
        service = AuthService(db)
        return await service.login(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {exc}",
        )


# ── Firebase (Google Sign-In) ─────────────────────────────────────────────────

class FirebaseLoginRequest(BaseModel):
    id_token: str


@router.post("/firebase", response_model=TokenResponse)
async def firebase_login(
    body: FirebaseLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accepts a Firebase ID token and returns a JWT for API access."""
    try:
        service = AuthService(db)
        return await service.login_with_firebase(body.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {exc}",
        )


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's profile (e.g. name)."""
    try:
        service = AuthService(db)
        return await service.update_profile(current_user.id, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {exc}",
        )


@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the user's password."""
    try:
        service = AuthService(db)
        await service.change_password(current_user.id, body.current_password, body.new_password)
        return {"message": "Password updated successfully."}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {exc}",
        )

# ── Forgot Password ───────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(body: ForgotPasswordRequest):
    """
    Send a Firebase password-reset email via the Firebase REST API.
    Called server-side so it works even inside Streamlit (no iframe origin issues).
    """
    url = (
        f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"
        f"?key={_FIREBASE_API_KEY}"
    )
    payload = {"requestType": "PASSWORD_RESET", "email": body.email}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
        data = resp.json()

        if resp.status_code == 200:
            return {"message": "Password reset email sent. Please check your inbox."}

        # Map Firebase error codes to friendly messages
        error_code = data.get("error", {}).get("message", "")
        if error_code == "EMAIL_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email address.",
            )
        if error_code == "INVALID_EMAIL":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email address.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not send reset email: {error_code}",
        )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach Firebase: {exc}",
        )
