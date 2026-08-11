from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


# ── Space ──────────────────────────────────────────────────────────────────────

class SpaceCreate(BaseModel):
    exam_id: str
    subject: str


class SpaceOut(BaseModel):
    id: int
    exam_id: str
    subject: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Chat Sessions ──────────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    name: str = "New Chat"


class ChatSessionRename(BaseModel):
    name: str


class ChatSessionOut(BaseModel):
    id: int
    space_id: int
    name: str
    ai_suggested_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Chat Messages ──────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str
    lang: Optional[str] = "auto"
    active_doc_id: Optional[int] = None           # doc_id of the active uploaded file
    active_doc_filename: Optional[str] = None     # filename for display in system prompt
    chat_session_id: Optional[int] = None         # scoped chat session


class MessageOut(BaseModel):
    id: int
    space_id: int
    session_id: Optional[int] = None
    role: str        # "user" or "assistant"
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Space Detail (with messages) ───────────────────────────────────────────────

class SpaceDetail(SpaceOut):
    messages: List[MessageOut] = []


# ── Notes ──────────────────────────────────────────────────────────────────────

class NoteOut(BaseModel):
    space_id: int
    content: str
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NoteUpdate(BaseModel):
    content: str
