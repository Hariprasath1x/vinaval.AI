from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.space_service import SpaceService
from app.services.quiz_service import QuizService
from app.schemas.quiz import (
    GenerateQuestionsRequest,
    QuestionOut,
    SubmitAnswerRequest,
    AnswerResult,
    SpaceStats,
    QuizReviewRequest,
    QuizReviewResponse,
)

router = APIRouter(prefix="/spaces", tags=["Quiz"])


@router.post("/{space_id}/quiz/generate", response_model=List[QuestionOut], status_code=status.HTTP_201_CREATED)
async def generate_questions(
    space_id: int,
    body: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered MCQs for a topic within this Learning Space."""
    space_svc = SpaceService(db)
    space = await space_svc.get_space(space_id, current_user.id)
    quiz_svc = QuizService(db)
    return await quiz_svc.generate_questions(space, body)


@router.get("/{space_id}/quiz/questions", response_model=List[QuestionOut])
async def list_questions(
    space_id: int,
    topic: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List previously generated questions for this space (optionally filtered by topic)."""
    space_svc = SpaceService(db)
    await space_svc.get_space(space_id, current_user.id)
    quiz_svc = QuizService(db)
    return await quiz_svc.get_questions(space_id, topic)


@router.post("/{space_id}/quiz/attempt", response_model=AnswerResult)
async def submit_answer(
    space_id: int,
    body: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer for a quiz question. Returns whether it was correct plus explanation."""
    space_svc = SpaceService(db)
    space = await space_svc.get_space(space_id, current_user.id)
    quiz_svc = QuizService(db)
    return await quiz_svc.submit_answer(space, body)


@router.get("/{space_id}/quiz/stats", response_model=SpaceStats)
async def get_stats(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return practice and exam performance statistics for this space."""
    space_svc = SpaceService(db)
    await space_svc.get_space(space_id, current_user.id)
    quiz_svc = QuizService(db)
    return await quiz_svc.get_stats(space_id)


@router.post("/{space_id}/quiz/review", response_model=QuizReviewResponse)
async def get_quiz_review(
    space_id: int,
    body: QuizReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI-powered performance review based on recent quiz results."""
    space_svc = SpaceService(db)
    space = await space_svc.get_space(space_id, current_user.id)
    quiz_svc = QuizService(db)
    return await quiz_svc.generate_review(space, body)
