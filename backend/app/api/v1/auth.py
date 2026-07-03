from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.auth_service import AuthService
from app.schemas.auth import TokenResponse, UserResponse
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class FirebaseLoginRequest(BaseModel):
    id_token: str  # Firebase ID token from the frontend


@router.post("/firebase", response_model=TokenResponse)
async def firebase_login(
    body: FirebaseLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a Firebase ID token from the frontend.
    Verifies it, upserts the user, and returns a JWT for API access.
    """
    try:
        service = AuthService(db)
        return await service.login_with_firebase(body.id_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {exc}",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
