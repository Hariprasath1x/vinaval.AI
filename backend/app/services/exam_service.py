from __future__ import annotations
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.constants import EXAM_DATA, VALID_EXAM_IDS
from app.schemas.exam import ExamSchema, SubjectSchema, ExamSelectionResponse
from app.repositories.user_repository import UserRepository
from app.models.user import User


class ExamService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.repo = UserRepository(db) if db is not None else None

    def list_exams(self) -> List[ExamSchema]:
        """Return all supported exams with their subjects."""
        return [
            ExamSchema(
                id=exam.id,
                name=exam.name,
                tag=exam.tag,
                description=exam.description,
                subjects=[
                    SubjectSchema(name=s.name, icon=s.icon, color=s.color)
                    for s in exam.subjects
                ],
            )
            for exam in EXAM_DATA
        ]

    async def select_exam(self, user: User, exam_id: str) -> ExamSelectionResponse:
        """Save the user's exam selection. Validates against known exam IDs."""
        normalized_exam_id = exam_id.upper().strip() if exam_id else ""
        if normalized_exam_id not in VALID_EXAM_IDS:
            raise ValueError(
                f"Invalid exam '{exam_id}'. Supported exams: {', '.join(VALID_EXAM_IDS)}"
            )
        if not self.repo:
            raise RuntimeError("Database session required to save exam selection.")
        await self.repo.update_selected_exam(user.id, normalized_exam_id)
        return ExamSelectionResponse(
            selected_exam=normalized_exam_id,
            message=f"Exam set to {normalized_exam_id} successfully.",
        )

    def get_user_exam(self, user: User) -> ExamSelectionResponse:
        """Return the user's currently selected exam."""
        return ExamSelectionResponse(
            selected_exam=user.selected_exam,
            message="OK",
        )

