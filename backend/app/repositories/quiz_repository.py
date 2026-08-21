from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.quiz import QuizQuestion, QuizAttempt, QuizSession


class QuizRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Questions ──────────────────────────────────────────────────────────────

    async def bulk_save_questions(self, questions: List[QuizQuestion]) -> List[QuizQuestion]:
        self.db.add_all(questions)
        await self.db.commit()
        for q in questions:
            await self.db.refresh(q)
        return questions

    async def get_questions_for_space(self, space_id: int, topic: Optional[str] = None) -> List[QuizQuestion]:
        stmt = select(QuizQuestion).where(QuizQuestion.space_id == space_id)
        if topic:
            stmt = stmt.where(QuizQuestion.topic == topic)
        stmt = stmt.order_by(QuizQuestion.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_question(self, question_id: int, space_id: int) -> Optional[QuizQuestion]:
        result = await self.db.execute(
            select(QuizQuestion).where(
                QuizQuestion.id == question_id,
                QuizQuestion.space_id == space_id,
            )
        )
        return result.scalar_one_or_none()

    # ── Sessions ───────────────────────────────────────────────────────────────

    async def create_session(self, space_id: int, topic: Optional[str], total_questions: int, is_exam: bool, lang: str, source_type: str = "curriculum") -> "QuizSession":
        from app.models.quiz import QuizSession
        session = QuizSession(
            space_id=space_id,
            topic=topic,
            total_questions=total_questions,
            is_exam=is_exam,
            lang=lang,
            source_type=source_type,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: int) -> Optional["QuizSession"]:
        from app.models.quiz import QuizSession
        result = await self.db.execute(select(QuizSession).where(QuizSession.id == session_id))
        return result.scalar_one_or_none()

    async def update_session(self, session: "QuizSession") -> "QuizSession":
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_sessions_for_space(self, space_id: int, limit: int = 20) -> List["QuizSession"]:
        from app.models.quiz import QuizSession
        stmt = select(QuizSession).where(QuizSession.space_id == space_id).order_by(QuizSession.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_global_sessions_for_user(self, user_id: int, limit: int = 50) -> List["QuizSession"]:
        from app.models.quiz import QuizSession
        from app.models.space import LearningSpace
        stmt = (
            select(QuizSession)
            .join(LearningSpace, QuizSession.space_id == LearningSpace.id)
            .where(LearningSpace.user_id == user_id)
            .order_by(QuizSession.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Attempts ───────────────────────────────────────────────────────────────

    async def save_attempt(
        self,
        space_id: int,
        question_id: int,
        user_answer: str,
        is_correct: bool,
        time_taken_seconds: Optional[int],
        is_exam: bool,
        session_id: Optional[int] = None,
    ) -> QuizAttempt:
        attempt = QuizAttempt(
            space_id=space_id,
            session_id=session_id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct,
            time_taken_seconds=time_taken_seconds,
            is_exam=is_exam,
        )
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def get_stats(self, space_id: int) -> dict:
        """Aggregate attempt stats for a space."""
        # Fetch all attempts for this space
        result = await self.db.execute(
            select(QuizAttempt.is_exam, QuizAttempt.is_correct)
            .where(QuizAttempt.space_id == space_id)
        )
        rows = result.fetchall()

        practice_total = practice_correct = exam_total = exam_correct = 0
        for row in rows:
            if row.is_exam:
                exam_total += 1
                if row.is_correct:
                    exam_correct += 1
            else:
                practice_total += 1
                if row.is_correct:
                    practice_correct += 1

        # Topics practiced (distinct topics from questions that have attempts)
        topics_result = await self.db.execute(
            select(QuizQuestion.topic)
            .join(QuizAttempt, QuizAttempt.question_id == QuizQuestion.id)
            .where(QuizAttempt.space_id == space_id)
            .distinct()
        )
        topics = [r[0] for r in topics_result.fetchall()]

        return {
            "practice": (practice_total, practice_correct),
            "exam": (exam_total, exam_correct),
            "topics": topics,
        }

    async def get_batch_stats(self, space_ids: List[int]) -> dict:
        """Aggregate attempt stats for multiple spaces in a single query."""
        if not space_ids:
            return {}
            
        result = await self.db.execute(
            select(QuizAttempt.space_id, QuizAttempt.is_exam, QuizAttempt.is_correct)
            .where(QuizAttempt.space_id.in_(space_ids))
        )
        rows = result.fetchall()
        
        stats_map = {sid: {"practice_total": 0, "practice_correct": 0, "exam_total": 0, "exam_correct": 0, "topics": set()} for sid in space_ids}
        
        for row in rows:
            sid = row.space_id
            if row.is_exam:
                stats_map[sid]["exam_total"] += 1
                if row.is_correct:
                    stats_map[sid]["exam_correct"] += 1
            else:
                stats_map[sid]["practice_total"] += 1
                if row.is_correct:
                    stats_map[sid]["practice_correct"] += 1
                    
        # Topics practiced
        topics_result = await self.db.execute(
            select(QuizAttempt.space_id, QuizQuestion.topic)
            .join(QuizAttempt, QuizAttempt.question_id == QuizQuestion.id)
            .where(QuizAttempt.space_id.in_(space_ids))
            .distinct()
        )
        for sid, topic in topics_result.fetchall():
            if sid in stats_map:
                stats_map[sid]["topics"].add(topic)
                
        return {
            sid: {
                "practice": (s["practice_total"], s["practice_correct"]),
                "exam": (s["exam_total"], s["exam_correct"]),
                "topics": list(s["topics"])
            } for sid, s in stats_map.items()
        }

    # ── Performance Analysis ───────────────────────────────────────────────────────────────

    async def get_attempts_for_session(self, session_id: int) -> List[QuizAttempt]:
        """Load all attempts for a given session."""
        stmt = select(QuizAttempt).where(QuizAttempt.session_id == session_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def save_analysis(self, analysis) -> "PerformanceAnalysis":
        """Save a new performance analysis record."""
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        return analysis

    async def get_analysis_for_session(self, session_id: int):
        """Get the performance analysis for a session."""
        from app.models.quiz import PerformanceAnalysis
        stmt = select(PerformanceAnalysis).where(PerformanceAnalysis.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_analyses_for_space(self, space_id: int, limit: int = 20):
        """Get past performance analyses for a space."""
        from app.models.quiz import PerformanceAnalysis
        stmt = select(PerformanceAnalysis).where(PerformanceAnalysis.space_id == space_id).order_by(PerformanceAnalysis.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
