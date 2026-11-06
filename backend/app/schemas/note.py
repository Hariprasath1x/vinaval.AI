from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    title: str = Field(default="Untitled Note", min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    topic: Optional[str] = Field(default=None, max_length=255)
    source_type: str = Field(default="manual", max_length=50)


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = Field(default=None, min_length=1)
    topic: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    space_id: int
    user_id: Optional[int] = None
    title: str
    content: str
    topic: Optional[str] = None
    source_type: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GenerateNotesRequest(BaseModel):
    topic: Optional[str] = None
    doc_id: Optional[int] = None
    lang: str = Field(default="en", description="Output language: 'en' (English) or 'ta' (Tamil)")
    source_type: str = Field(default="curriculum", description="'curriculum', 'document', or 'user'")


class GenerateNotesResponse(BaseModel):
    title: str
    topic: Optional[str] = None
    content: str
    lang: str
    source_type: str
    doc_id: Optional[int] = None
    chunks_used: int = 0
