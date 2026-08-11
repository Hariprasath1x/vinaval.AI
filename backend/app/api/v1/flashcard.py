from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rate_limit import limiter

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.space_service import SpaceService
from app.services.flashcard_service import FlashcardService
from app.schemas.flashcard import (
    GenerateFlashcardsRequest,
    FlashcardOut,
)

router = APIRouter(prefix="/spaces", tags=["Flashcards"])


@router.post(
    "/{space_id}/flashcards/generate",
    response_model=List[FlashcardOut],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def generate_flashcards(
    request: Request,
    space_id: int,
    body: GenerateFlashcardsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered flashcards for a topic in this Learning Space."""
    space_svc = SpaceService(db)
    space = await space_svc.get_space(space_id, current_user.id)
    fc_svc = FlashcardService(db)
    return await fc_svc.generate(space, body)


@router.get("/{space_id}/flashcards", response_model=List[FlashcardOut])
async def list_flashcards(
    space_id: int,
    topic: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List flashcards for this space, optionally filtered by topic."""
    space_svc = SpaceService(db)
    await space_svc.get_space(space_id, current_user.id)
    fc_svc = FlashcardService(db)
    return await fc_svc.get_by_space(space_id, topic)


@router.get("/{space_id}/flashcards/topics", response_model=List[str])
async def list_flashcard_topics(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct topics that have flashcards in this space."""
    space_svc = SpaceService(db)
    await space_svc.get_space(space_id, current_user.id)
    fc_svc = FlashcardService(db)
    return await fc_svc.get_topics(space_id)


@router.delete("/{space_id}/flashcards/{topic}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flashcard_topic(
    space_id: int,
    topic: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all flashcards for a specific topic in this space."""
    space_svc = SpaceService(db)
    await space_svc.get_space(space_id, current_user.id)
    fc_svc = FlashcardService(db)
    await fc_svc.delete_topic(space_id, topic)
