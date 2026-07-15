from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.flashcard_repository import FlashcardRepository
from app.models.flashcard import Flashcard
from app.models.space import LearningSpace
from app.schemas.flashcard import GenerateFlashcardsRequest, FlashcardOut, FlashcardSetOut
from app.rag.chain import generate_flashcards as ai_generate_flashcards


class FlashcardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FlashcardRepository(db)

    async def generate(
        self, space: LearningSpace, req: GenerateFlashcardsRequest
    ) -> List[Flashcard]:
        count = max(1, min(20, req.count))

        try:
            raw_cards = await ai_generate_flashcards(
                exam=space.exam_id,
                subject=space.subject,
                topic=req.topic,
                count=count,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI flashcard generation failed: {e}",
            )

        cards = []
        for c in raw_cards:
            if not all(k in c for k in ("front", "back")):
                continue
            if not c["front"].strip() or not c["back"].strip():
                continue
            cards.append(
                Flashcard(
                    space_id=space.id,
                    topic=req.topic,
                    front=c["front"].strip(),
                    back=c["back"].strip(),
                )
            )

        if not cards:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned no valid flashcards. Try a different topic.",
            )

        return await self.repo.bulk_save(cards)

    async def get_by_space(
        self, space_id: int, topic: Optional[str] = None
    ) -> List[Flashcard]:
        return await self.repo.get_by_space(space_id, topic)

    async def get_topics(self, space_id: int) -> List[str]:
        return await self.repo.get_topics(space_id)

    async def delete_topic(self, space_id: int, topic: str) -> int:
        return await self.repo.delete_by_topic(space_id, topic)
