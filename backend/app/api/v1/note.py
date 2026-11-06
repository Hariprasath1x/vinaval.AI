from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rate_limit import limiter

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.note_service import NoteService
from app.schemas.note import (
    NoteCreate,
    NoteUpdate,
    NoteOut,
    GenerateNotesRequest,
    GenerateNotesResponse,
)

router = APIRouter(prefix="/spaces", tags=["Smart Notes"])


@router.post("/{space_id}/notes/generate", response_model=GenerateNotesResponse)
@limiter.limit("5/minute")
async def generate_smart_notes_endpoint(
    request: Request,
    space_id: int,
    body: GenerateNotesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate structured, curriculum- or document-grounded Smart Notes in English or Tamil.
    Rate limited to 5 requests per minute.
    """
    note_svc = NoteService(db)
    return await note_svc.generate_note(space_id, current_user.id, body)


@router.post("/{space_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    space_id: int,
    body: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a new note in this Learning Space for the logged-in student."""
    note_svc = NoteService(db)
    return await note_svc.create_note(space_id, current_user.id, body)


@router.get("/{space_id}/notes", response_model=List[NoteOut])
async def list_notes(
    space_id: int,
    search: Optional[str] = Query(None, description="Search term for title, topic, or content"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all saved notes for this Learning Space and current user with optional search."""
    note_svc = NoteService(db)
    return await note_svc.list_notes(space_id, current_user.id, search=search)


@router.get("/{space_id}/notes/{note_id}", response_model=NoteOut)
async def get_note(
    space_id: int,
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single saved note by ID."""
    note_svc = NoteService(db)
    return await note_svc.get_note(space_id, note_id, current_user.id)


@router.put("/{space_id}/notes/{note_id}", response_model=NoteOut)
async def update_note(
    space_id: int,
    note_id: int,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update title, topic, or content of a saved note."""
    note_svc = NoteService(db)
    return await note_svc.update_note(space_id, note_id, current_user.id, body)


@router.delete("/{space_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    space_id: int,
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved note."""
    note_svc = NoteService(db)
    await note_svc.delete_note(space_id, note_id, current_user.id)

