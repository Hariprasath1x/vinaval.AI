from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.space_repository import SpaceRepository
from app.core.constants import is_valid_subject, EXAM_MAP
from app.models.space import LearningSpace
from app.models.message import ChatMessage
from app.models.note import SpaceNote
from app.schemas.space import SpaceCreate, NoteUpdate
from app.rag.chain import stream_chat


class SpaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SpaceRepository(db)

    # ── Spaces ─────────────────────────────────────────────────────────────────

    async def get_or_create_space(self, user_id: int, data: SpaceCreate) -> LearningSpace:
        """
        Return an existing space for (user, exam, subject) or create a new one.
        This ensures clicking the same subject card multiple times opens the same space.
        """
        if data.exam_id not in EXAM_MAP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown exam '{data.exam_id}'.",
            )
        if not is_valid_subject(data.exam_id, data.subject):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{data.subject}' is not a valid subject for {data.exam_id}.",
            )

        existing = await self.repo.find_existing_space(user_id, data.exam_id, data.subject)
        if existing:
            return existing
        return await self.repo.create_space(user_id, data.exam_id, data.subject)

    async def get_space(self, space_id: int, user_id: int) -> LearningSpace:
        space = await self.repo.get_space_by_id(space_id, user_id)
        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning Space not found.",
            )
        return space

    async def list_spaces(self, user_id: int) -> List[LearningSpace]:
        return await self.repo.list_spaces(user_id)

    async def delete_space(self, space_id: int, user_id: int) -> bool:
        """Delete a Learning Space. Raises 404 if not found or not owned by user."""
        deleted = await self.repo.delete_space(space_id, user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning Space not found.",
            )
        return True

    # ── Chat ───────────────────────────────────────────────────────────────────

    async def get_messages(self, space_id: int) -> List[ChatMessage]:
        return await self.repo.get_messages(space_id)

    async def save_user_message(self, space_id: int, content: str) -> ChatMessage:
        return await self.repo.add_message(space_id, "user", content)

    async def save_assistant_message(self, space_id: int, content: str) -> ChatMessage:
        return await self.repo.add_message(space_id, "assistant", content)

    async def stream_ai_response(self, space: LearningSpace, user_message: str, forced_lang: Optional[str] = None):
        """
        Generator: yields SSE-formatted chunks, then saves both messages to DB.
        """
        # Build history (last 20 messages to stay within context window)
        messages = await self.repo.get_messages(space.id)
        history = [{"role": m.role, "content": m.content} for m in messages[-20:]]

        # Save user message first
        await self.repo.add_message(space.id, "user", user_message)

        # Stream AI response
        full_response: list[str] = []
        async for chunk in stream_chat(space.exam_id, space.subject, history, user_message, forced_lang):
            full_response.append(chunk)
            yield chunk

        # Persist the complete assistant message
        await self.repo.add_message(space.id, "assistant", "".join(full_response))

    # ── Notes ──────────────────────────────────────────────────────────────────

    async def get_note(self, space_id: int) -> Optional[SpaceNote]:
        return await self.repo.get_note(space_id)

    async def upsert_note(self, space_id: int, data: NoteUpdate) -> SpaceNote:
        return await self.repo.upsert_note(space_id, data.content)
