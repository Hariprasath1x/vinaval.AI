import json
import logging
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
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
    ChatSessionCreate,
    ChatSessionRename,
    ChatSessionOut,
)

router = APIRouter(prefix="/spaces", tags=["Learning Spaces"])
logger = logging.getLogger(__name__)

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


# ── Chat Sessions ────────────────────────────────────────────────────────────────

@router.get("/{space_id}/chat-sessions", response_model=List[ChatSessionOut])
async def list_chat_sessions(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all named chat conversations for this Learning Space."""
    service = SpaceService(db)
    await service.get_space(space_id, current_user.id)  # ownership check
    return await service.list_chat_sessions(space_id)


@router.post("/{space_id}/chat-sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    space_id: int,
    body: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new named chat session within this Learning Space."""
    service = SpaceService(db)
    await service.get_space(space_id, current_user.id)  # ownership check
    return await service.create_chat_session(space_id, body.name)


@router.put("/{space_id}/chat-sessions/{session_id}", response_model=ChatSessionOut)
async def rename_chat_session(
    space_id: int,
    session_id: int,
    body: ChatSessionRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a chat session (user's manual name takes priority over AI suggestion)."""
    service = SpaceService(db)
    await service.get_space(space_id, current_user.id)  # ownership check
    return await service.rename_chat_session(session_id, space_id, body.name)


@router.delete("/{space_id}/chat-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    space_id: int,
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    service = SpaceService(db)
    await service.get_space(space_id, current_user.id)  # ownership check
    await service.delete_chat_session(session_id, space_id)


# ── Chat ────────────────────────────────────────────────────────────────────────

@router.post("/{space_id}/chat")
@limiter.limit("5/minute")
async def chat(
    request: Request,
    space_id: int,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a user message and stream the AI response via Server-Sent Events.
    Pass chat_session_id to scope the conversation to a specific named session.

    SSE format:
        data: <json-encoded chunk>\n\n
        data: [DONE]\n\n
    """
    service = SpaceService(db)

    start_time = time.perf_counter()
    logger.info("[CHAT] Request received")
    logger.info(f"[CHAT] space_id={space_id}")
    logger.info(f"[CHAT] language={body.lang}")
    logger.info(f"[CHAT] active_doc_id={body.active_doc_id}")
    logger.info(f"[CHAT] chat_session_id={body.chat_session_id}")
    logger.info("[CHAT] User authenticated successfully")

    space = await service.get_space(space_id, current_user.id)
    logger.info("[CHAT] Learning space validated")

    async def event_stream():
        logger.info("[CHAT] SSE generator started")
        gen_start_time = time.perf_counter()
        first_chunk = True
        try:
            async for chunk in service.stream_ai_response(
                space,
                body.content,
                body.lang,
                active_doc_id=body.active_doc_id,
                active_doc_filename=body.active_doc_filename,
                chat_session_id=body.chat_session_id,
                is_continuation=body.is_continuation,
            ):
                if first_chunk:
                    elapsed = (time.perf_counter() - gen_start_time) * 1000
                    logger.info(f"[CHAT] First SSE chunk yielded elapsed_ms={elapsed:.2f}")
                    first_chunk = False
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as exc:
            logger.exception(f"[CHAT] SSE generator FAILED exception_type={type(exc).__name__} exception={str(exc)}")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            elapsed_total = (time.perf_counter() - start_time) * 1000
            logger.info(f"[CHAT] SSE stream completed elapsed_ms={elapsed_total:.2f}")
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{space_id}/messages", response_model=List[MessageOut])
async def get_messages(
    space_id: int,
    session_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return chat history. Pass ?session_id=X to scope to a specific chat session."""
    service = SpaceService(db)
    await service.get_space(space_id, current_user.id)
    return await service.get_messages(space_id, session_id=session_id)


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
