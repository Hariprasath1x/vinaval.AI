import json
from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.space_service import SpaceService
from app.schemas.space import (
    SpaceCreate,
    SpaceOut,
    SpaceDetail,
    MessageCreate,
    MessageOut,
    NoteOut,
    NoteUpdate,
)

router = APIRouter(prefix="/spaces", tags=["Learning Spaces"])


# ── Spaces ──────────────────────────────────────────────────────────────────────

@router.post("", response_model=SpaceOut, status_code=status.HTTP_201_CREATED)
async def create_or_get_space(
    body: SpaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Learning Space for the given exam+subject.
    If one already exists for this user, returns it instead (idempotent).
    """
    service = SpaceService(db)
    space = await service.get_or_create_space(current_user.id, body)
    return space


@router.get("", response_model=List[SpaceOut])
async def list_spaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all Learning Spaces belonging to the current user."""
    service = SpaceService(db)
    return await service.list_spaces(current_user.id)


@router.get("/{space_id}", response_model=SpaceDetail)
async def get_space(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a single Learning Space with its full message history."""
    service = SpaceService(db)
    return await service.get_space(space_id, current_user.id)


@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a Learning Space and all its associated data."""
    service = SpaceService(db)
    await service.delete_space(space_id, current_user.id)

# ── Chat ────────────────────────────────────────────────────────────────────────

@router.post("/{space_id}/chat")
async def chat(
    space_id: int,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a user message and stream the AI response via Server-Sent Events.

    SSE format:
        data: <json-encoded chunk>\\n\\n
        data: [DONE]\\n\\n
    """
    service = SpaceService(db)
    space = await service.get_space(space_id, current_user.id)

    async def event_stream():
        try:
            async for chunk in service.stream_ai_response(
                space,
                body.content,
                body.lang,
                active_doc_id=body.active_doc_id,
                active_doc_filename=body.active_doc_filename,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",    # disable nginx buffering if used
        },
    )


@router.get("/{space_id}/messages", response_model=List[MessageOut])
async def get_messages(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the full chat history for a Learning Space."""
    service = SpaceService(db)
    # Ensure space belongs to user
    await service.get_space(space_id, current_user.id)
    return await service.get_messages(space_id)


# ── Notes ───────────────────────────────────────────────────────────────────────

@router.get("/{space_id}/note", response_model=NoteOut)
async def get_note(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the note for this Learning Space (empty string if none exists yet)."""
    service = SpaceService(db)
    await service.get_space(space_id, current_user.id)  # ownership check
    note = await service.get_note(space_id)
    if note is None:
        return NoteOut(space_id=space_id, content="")
    return note


@router.put("/{space_id}/note", response_model=NoteOut)
async def upsert_note(
    space_id: int,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update the note for this Learning Space."""
    service = SpaceService(db)
    await service.get_space(space_id, current_user.id)  # ownership check
    return await service.upsert_note(space_id, body)
