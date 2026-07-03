from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.exam_service import ExamService
from app.schemas.exam import ExamSchema, ExamSelectionRequest, ExamSelectionResponse
from app.models.user import User

router = APIRouter(prefix="/exams", tags=["Examinations"])


@router.get("", response_model=List[ExamSchema])
async def list_exams(db: AsyncSession = Depends(get_db)):
    """Return all supported exams with their subjects. No auth required."""
    service = ExamService(db)
    return service.list_exams()


@router.post("/select", response_model=ExamSelectionResponse)
async def select_exam(
    body: ExamSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save the authenticated user's exam choice (NEET or TNPSC)."""
    try:
        service = ExamService(db)
        return await service.select_exam(current_user, body.exam_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/me", response_model=ExamSelectionResponse)
async def get_my_exam(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's selected exam."""
    from app.services.exam_service import ExamService
    service = ExamService(None)  # no DB needed — data from user object
    return service.get_user_exam(current_user)
