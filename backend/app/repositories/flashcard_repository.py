from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flashcard import Flashcard


class FlashcardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_save(self, cards: List[Flashcard]) -> List[Flashcard]:
        self.db.add_all(cards)
        await self.db.commit()
        for card in cards:
            await self.db.refresh(card)
        return cards

    async def get_by_space(self, space_id: int, topic: Optional[str] = None) -> List[Flashcard]:
        stmt = select(Flashcard).where(Flashcard.space_id == space_id)
        if topic:
            stmt = stmt.where(Flashcard.topic == topic)
        stmt = stmt.order_by(Flashcard.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_topics(self, space_id: int) -> List[str]:
        """Return distinct topics that have flashcards in this space."""
        from sqlalchemy import distinct
        result = await self.db.execute(
            select(distinct(Flashcard.topic))
            .where(Flashcard.space_id == space_id)
            .order_by(Flashcard.topic)
        )
        return list(result.scalars().all())

    async def delete_by_topic(self, space_id: int, topic: str) -> int:
        result = await self.db.execute(
            delete(Flashcard)
            .where(Flashcard.space_id == space_id, Flashcard.topic == topic)
        )
        await self.db.commit()
        return result.rowcount
