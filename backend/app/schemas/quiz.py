from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class QuestionOut(BaseModel):
    id: int
    space_id: int
    topic: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    explanation: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateQuestionsRequest(BaseModel):
    topic: Optional[str] = None
    count: int = 5
    lang: str = "en"
    source_type: str = "curriculum"
    material_type: Optional[str] = None  # "en" (English) or "ta" (Tamil)


class GenerateQuestionsResponse(BaseModel):
    session_id: Optional[int] = None
    questions: List[QuestionOut]


class SubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: Optional[str] = None  # None means skipped (e.g. timer ran out)
    time_taken_seconds: Optional[int] = None
    is_exam: bool = False
    session_id: Optional[int] = None

class QuizSessionOut(BaseModel):
    id: int
    topic: Optional[str] = None
    total_questions: int
    correct_answers: int
    score_pct: int
    is_exam: bool
    is_completed: bool
    source_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnswerResult(BaseModel):
    question_id: int
    user_answer: str
    correct_option: str
    is_correct: bool
    explanation: Optional[str] = None


class SpaceStats(BaseModel):
    total_practice: int
    correct_practice: int
    accuracy_practice: float       # 0.0 – 100.0
    total_exam: int
    correct_exam: int
    accuracy_exam: float
    total_all: int
    correct_all: int
    accuracy_all: float
    topics_practiced: List[str]


class QuizReviewItem(BaseModel):
    topic: str
    is_correct: bool


class QuizReviewRequest(BaseModel):
    results: List[QuizReviewItem]


class QuizReviewResponse(BaseModel):
    review: str
