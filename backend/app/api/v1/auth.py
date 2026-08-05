from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import requests

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.auth_service import AuthService
from app.schemas.auth import (
    TokenResponse,
    UserResponse,
    SignupRequest,
    LoginRequest,
    ProfileUpdateRequest,
    ChangePasswordRequest,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

_FIREBASE_API_KEY = "AIzaSyClUultgV7XpYjT1teKAbtchNGpRfqr04A"




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

from pydantic import BaseModel

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
        resp = requests.post(url, json=payload, timeout=10.0)
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

    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach Firebase: {exc}",
        )
