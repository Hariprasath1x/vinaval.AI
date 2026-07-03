from typing import List, Optional
from pydantic import BaseModel


class SubjectSchema(BaseModel):
    name: str
    icon: str
    color: str


class ExamSchema(BaseModel):
    id: str
    name: str
    tag: str
    description: str
    subjects: List[SubjectSchema]


class ExamSelectionRequest(BaseModel):
    exam_id: str  # Must be "NEET" or "TNPSC"


class ExamSelectionResponse(BaseModel):
    selected_exam: Optional[str]
    message: str
