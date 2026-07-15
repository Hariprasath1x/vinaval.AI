from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class GenerateFlashcardsRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    count: int = Field(default=8, ge=1, le=20)


class FlashcardOut(BaseModel):
    id: int
    space_id: int
    topic: str
    front: str
    back: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FlashcardSetOut(BaseModel):
    topic: str
    cards: List[FlashcardOut]
