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


# ── Chat Messages ──────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: int
    space_id: int
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
