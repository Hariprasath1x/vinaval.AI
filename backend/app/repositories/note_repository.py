from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import SpaceNote


class NoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_note(
        self,
        space_id: int,
        user_id: int,
        title: str,
        content: str,
        topic: Optional[str] = None,
        source_type: str = "manual",
    ) -> SpaceNote:
        note = SpaceNote(
            space_id=space_id,
            user_id=user_id,
            title=title,
            content=content,
            topic=topic,
            source_type=source_type,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def list_notes(
        self,
        space_id: int,
        user_id: int,
        search: Optional[str] = None,
    ) -> List[SpaceNote]:
        stmt = select(SpaceNote).where(
            SpaceNote.space_id == space_id,
            SpaceNote.user_id == user_id,
        )
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    SpaceNote.title.ilike(term),
                    SpaceNote.topic.ilike(term),
                    SpaceNote.content.ilike(term),
                )
            )
        stmt = stmt.order_by(SpaceNote.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_note_by_id(
        self,
        note_id: int,
        space_id: int,
        user_id: int,
    ) -> Optional[SpaceNote]:
        stmt = select(SpaceNote).where(
            SpaceNote.id == note_id,
            SpaceNote.space_id == space_id,
            SpaceNote.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_note(
        self,
        note: SpaceNote,
        title: Optional[str] = None,
        content: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> SpaceNote:
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if topic is not None:
            note.topic = topic
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def delete_note(self, note: SpaceNote) -> None:
        await self.db.delete(note)
        await self.db.commit()

