import json
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.flashcard_repository import FlashcardRepository
from app.models.flashcard import Flashcard
from app.models.space import LearningSpace
from app.schemas.flashcard import GenerateFlashcardsRequest
from app.rag.chain import generate_flashcards, generate_flashcards_stream


class FlashcardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FlashcardRepository(db)

    async def generate_stream(
        self, space: LearningSpace, req: GenerateFlashcardsRequest
    ):
        count = max(1, min(20, req.count))
        lang = getattr(req, "lang", "en")
        
        try:
            async for c in generate_flashcards_stream(
                exam=space.exam_id,
                subject=space.subject,
                topic=req.topic,
                count=count,
                lang=lang,
                source_type=getattr(req, "source_type", "curriculum"),
                space_id=space.id,
            ):
                if not all(k in c for k in ("front", "back")):
                    continue
                if not c["front"].strip() or not c["back"].strip():
                    continue
                
                card_obj = Flashcard(
                    space_id=space.id,
                    topic=req.topic,
                    front=c["front"].strip(),
                    back=c["back"].strip(),
                )
                
                # Save to DB individually
                saved_card = (await self.repo.bulk_save([card_obj]))[0]
                
                card_dict = {
                    "id": saved_card.id,
                    "front": saved_card.front,
                    "back": saved_card.back,
                    "topic": saved_card.topic
                }
                yield f"event: flashcard\ndata: {json.dumps(card_dict)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "event: complete\ndata: {}\n\n"

    async def get_by_space(
        self, space_id: int, topic: Optional[str] = None
    ) -> List[Flashcard]:
        return await self.repo.get_by_space(space_id, topic)

    async def get_topics(self, space_id: int) -> List[str]:
        return await self.repo.get_topics(space_id)

    async def delete_topic(self, space_id: int, topic: str) -> int:
        return await self.repo.delete_by_topic(space_id, topic)
