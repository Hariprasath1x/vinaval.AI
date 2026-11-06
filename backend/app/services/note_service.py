import logging
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.space import LearningSpace
from app.models.note import SpaceNote
from app.schemas.note import NoteCreate, NoteUpdate, GenerateNotesRequest, GenerateNotesResponse
from app.repositories.note_repository import NoteRepository
from app.repositories.space_repository import SpaceRepository
from app.rag.chain import generate_smart_notes

logger = logging.getLogger(__name__)


class NoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.note_repo = NoteRepository(db)
        self.space_repo = SpaceRepository(db)

    async def _verify_space(self, space_id: int, user_id: int) -> LearningSpace:
        space = await self.space_repo.get_space_by_id(space_id, user_id)
        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning Space not found or access denied.",
            )
        return space

    async def generate_note(
        self,
        space_id: int,
        user_id: int,
        req: GenerateNotesRequest,
    ) -> GenerateNotesResponse:
        space = await self._verify_space(space_id, user_id)
        try:
            result = await generate_smart_notes(
                exam=space.exam_id,
                subject=space.subject,
                topic=req.topic,
                doc_id=req.doc_id,
                lang=req.lang,
                source_type=req.source_type,
                space_id=space.id,
            )
            return GenerateNotesResponse(
                title=result["title"],
                topic=result["topic"],
                content=result["content"],
                lang=req.lang,
                source_type=result["source_type"],
                doc_id=req.doc_id,
                chunks_used=result.get("chunks_used", 0),
            )
        except ValueError as e:
            logger.error(f"[NoteService] LLM generation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Note generation failed: {str(e)}",
            )
        except Exception as e:
            logger.error(f"[NoteService] Unexpected error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during note generation.",
            )

    async def create_note(
        self,
        space_id: int,
        user_id: int,
        data: NoteCreate,
    ) -> SpaceNote:
        await self._verify_space(space_id, user_id)
        return await self.note_repo.create_note(
            space_id=space_id,
            user_id=user_id,
            title=data.title,
            content=data.content,
            topic=data.topic,
            source_type=data.source_type,
        )

    async def list_notes(
        self,
        space_id: int,
        user_id: int,
        search: Optional[str] = None,
    ) -> List[SpaceNote]:
        await self._verify_space(space_id, user_id)
        return await self.note_repo.list_notes(space_id, user_id, search)

    async def get_note(
        self,
        space_id: int,
        note_id: int,
        user_id: int,
    ) -> SpaceNote:
        await self._verify_space(space_id, user_id)
        note = await self.note_repo.get_note_by_id(note_id, space_id, user_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found or access denied.",
            )
        return note

    async def update_note(
        self,
        space_id: int,
        note_id: int,
        user_id: int,
        data: NoteUpdate,
    ) -> SpaceNote:
        note = await self.get_note(space_id, note_id, user_id)
        return await self.note_repo.update_note(
            note=note,
            title=data.title,
            content=data.content,
            topic=data.topic,
        )

    async def delete_note(
        self,
        space_id: int,
        note_id: int,
        user_id: int,
    ) -> None:
        note = await self.get_note(space_id, note_id, user_id)
        await self.note_repo.delete_note(note)

