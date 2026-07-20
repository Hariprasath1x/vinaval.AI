from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.space import LearningSpace
from app.models.message import ChatMessage
from app.models.note import SpaceNote


class SpaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Learning Spaces ────────────────────────────────────────────────────────

    async def create_space(self, user_id: int, exam_id: str, subject: str) -> LearningSpace:
        space = LearningSpace(
            user_id=user_id,
            exam_id=exam_id,
            subject=subject,
            title=f"{subject} Space",
        )
        self.db.add(space)
        await self.db.commit()
        await self.db.refresh(space)
        return space

    async def get_space_by_id(self, space_id: int, user_id: int) -> Optional[LearningSpace]:
        """Get a space only if it belongs to the given user (security check)."""
        result = await self.db.execute(
            select(LearningSpace)
            .options(selectinload(LearningSpace.messages))
            .where(LearningSpace.id == space_id, LearningSpace.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_spaces(self, user_id: int) -> List[LearningSpace]:
        result = await self.db.execute(
            select(LearningSpace)
            .where(LearningSpace.user_id == user_id)
            .order_by(LearningSpace.updated_at.desc())
        )
        return list(result.scalars().all())

    async def find_existing_space(self, user_id: int, exam_id: str, subject: str) -> Optional[LearningSpace]:
        """Return an existing space for this (user, exam, subject) combo if present."""
        result = await self.db.execute(
            select(LearningSpace).where(
                LearningSpace.user_id == user_id,
                LearningSpace.exam_id == exam_id,
                LearningSpace.subject == subject,
            )
        )
        # Use first() instead of scalar_one_or_none() to handle any duplicate
        # rows that may exist in the database without crashing.
        return result.scalars().first()


    # ── Chat Messages ──────────────────────────────────────────────────────────

    async def add_message(self, space_id: int, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(space_id=space_id, role=role, content=content)
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_messages(self, space_id: int) -> List[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.space_id == space_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars().all())

    # ── Notes ──────────────────────────────────────────────────────────────────

    async def get_note(self, space_id: int) -> Optional[SpaceNote]:
        result = await self.db.execute(
            select(SpaceNote).where(SpaceNote.space_id == space_id)
        )
        return result.scalar_one_or_none()

    async def upsert_note(self, space_id: int, content: str) -> SpaceNote:
        note = await self.get_note(space_id)
        if note:
            note.content = content
        else:
            note = SpaceNote(space_id=space_id, content=content)
            self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note
