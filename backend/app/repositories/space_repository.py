from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.space import LearningSpace
from app.models.chat_session import ChatSession
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

    async def delete_space(self, space_id: int, user_id: int) -> bool:
        """Delete a learning space (only if it belongs to the given user). Returns True if deleted."""
        space = await self.get_space_by_id(space_id, user_id)
        if not space:
            return False
        await self.db.delete(space)
        await self.db.commit()
        return True


    # ── Chat Sessions ──────────────────────────────────────────────────────────

    async def create_chat_session(self, space_id: int, name: str = "New Chat") -> ChatSession:
        session = ChatSession(space_id=space_id, name=name)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_chat_session(self, session_id: int, space_id: int) -> Optional[ChatSession]:
        result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.space_id == space_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_chat_sessions(self, space_id: int) -> List[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.space_id == space_id)
            .order_by(ChatSession.created_at.asc())
        )
        return list(result.scalars().all())

    async def rename_chat_session(self, session_id: int, space_id: int, name: str) -> Optional[ChatSession]:
        session = await self.get_chat_session(session_id, space_id)
        if not session:
            return None
        session.name = name
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def set_ai_suggested_name(self, session_id: int, suggested_name: str) -> None:
        session = await self.db.get(ChatSession, session_id)
        if session:
            session.ai_suggested_name = suggested_name
            await self.db.commit()

    async def delete_chat_session(self, session_id: int, space_id: int) -> bool:
        session = await self.get_chat_session(session_id, space_id)
        if not session:
            return False
        await self.db.delete(session)
        await self.db.commit()
        return True


    # ── Chat Messages ──────────────────────────────────────────────────────────

    async def add_message(self, space_id: int, role: str, content: str,
                          session_id: Optional[int] = None) -> ChatMessage:
        msg = ChatMessage(space_id=space_id, role=role, content=content, session_id=session_id)
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_messages(self, space_id: int, limit: int = 50,
                           session_id: Optional[int] = None) -> List[ChatMessage]:
        """Return the most recent `limit` messages for a space (or a specific session)."""
        stmt = select(ChatMessage).where(ChatMessage.space_id == space_id)
        if session_id is not None:
            stmt = stmt.where(ChatMessage.session_id == session_id)
        stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())
        # Reverse so callers get chronological (oldest-first) order
        messages.reverse()
        return messages

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
