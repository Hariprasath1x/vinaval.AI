from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.quiz_repository import QuizRepository
from app.models.quiz import QuizQuestion
from app.models.space import LearningSpace
from app.schemas.quiz import (
    GenerateQuestionsRequest,
    SubmitAnswerRequest,
    AnswerResult,
    SpaceStats,
    QuizReviewRequest,
    QuizReviewResponse,
)
from app.rag.chain import generate_mcqs, generate_quiz_review


class QuizService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = QuizRepository(db)

    async def generate_questions(
        self, space: LearningSpace, req: GenerateQuestionsRequest
    ) -> dict:
        count = max(1, min(30, req.count))  # clamp 1–30 (exam mode can request up to 30)

        try:
            raw_questions = await generate_mcqs(
                exam=space.exam_id,
                subject=space.subject,
                topic=req.topic,
                count=count,
                lang=getattr(req, "lang", "en"),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI question generation failed: {e}",
            )

        valid_options = {"a", "b", "c", "d"}
        questions = []
        for q in raw_questions:
            # Validate the AI response structure
            if not all(k in q for k in ("question", "option_a", "option_b", "option_c", "option_d", "correct_option")):
                continue
            if q["correct_option"].lower() not in valid_options:
                continue
            questions.append(
                QuizQuestion(
                    space_id=space.id,
                    topic=q.get("topic", req.topic or "Mixed Topics"),
                    question=q["question"],
                    option_a=q["option_a"],
                    option_b=q["option_b"],
                    option_c=q["option_c"],
                    option_d=q["option_d"],
                    correct_option=q["correct_option"].lower(),
                    explanation=q.get("explanation"),
                )
            )

        if not questions:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned no valid questions. Try a different topic.",
            )

        saved_questions = await self.repo.bulk_save_questions(questions)

        lang = getattr(req, "lang", "en")
        session = await self.repo.create_session(
            space_id=space.id,
            topic=req.topic,
            total_questions=len(saved_questions),
            is_exam=(req.topic is None),
            lang=lang
        )

        return {
            "session_id": session.id,
            "questions": saved_questions
        }

    async def get_questions(
        self, space_id: int, topic: Optional[str] = None
    ) -> List[QuizQuestion]:
        return await self.repo.get_questions_for_space(space_id, topic)

    async def submit_answer(
        self, space: LearningSpace, req: SubmitAnswerRequest
    ) -> AnswerResult:
        question = await self.repo.get_question(req.question_id, space.id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found in this space.",
            )

        user_answer = req.user_answer.lower()
        if user_answer not in {"a", "b", "c", "d"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="user_answer must be 'a', 'b', 'c', or 'd'.",
            )

        is_correct = user_answer == question.correct_option
        await self.repo.save_attempt(
            space_id=space.id,
            question_id=question.id,
            user_answer=user_answer,
            is_correct=is_correct,
            time_taken_seconds=req.time_taken_seconds,
            is_exam=req.is_exam,
            session_id=req.session_id,
        )

        if req.session_id:
            session = await self.repo.get_session(req.session_id)
            if session:
                if is_correct:
                    session.correct_answers += 1
                session.score_pct = int(round((session.correct_answers / session.total_questions) * 100)) if session.total_questions > 0 else 0
                await self.repo.update_session(session)

        return AnswerResult(
            question_id=question.id,
            user_answer=user_answer,
            correct_option=question.correct_option,
            is_correct=is_correct,
            explanation=question.explanation,
        )

    async def get_stats(self, space_id: int) -> SpaceStats:
        data = await self.repo.get_stats(space_id)

        p_total, p_correct = data["practice"]
        e_total, e_correct = data["exam"]
        all_total = p_total + e_total
        all_correct = p_correct + e_correct

        def pct(correct: int, total: int) -> float:
            return round(correct / total * 100, 1) if total > 0 else 0.0

        return SpaceStats(
            total_practice=p_total,
            correct_practice=p_correct,
            accuracy_practice=pct(p_correct, p_total),
            total_exam=e_total,
            correct_exam=e_correct,
            accuracy_exam=pct(e_correct, e_total),
            total_all=all_total,
            correct_all=all_correct,
            accuracy_all=pct(all_correct, all_total),
            topics_practiced=data["topics"],
        )

    async def get_history(self, space_id: int) -> list:
        return await self.repo.get_sessions_for_space(space_id)

    async def generate_review(
        self, space: LearningSpace, req: QuizReviewRequest
    ) -> QuizReviewResponse:
        results_list = [{"topic": r.topic, "is_correct": r.is_correct} for r in req.results]
        try:
            review_text = await generate_quiz_review(
                exam=space.exam_id,
                subject=space.subject,
                results=results_list,
            )
        except Exception:
            review_text = "Good effort! Keep studying and practicing to improve your scores."

        return QuizReviewResponse(review=review_text)
