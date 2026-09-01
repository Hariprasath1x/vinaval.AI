from typing import List, Optional, Dict
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
from app.rag.chain import generate_mcqs, generate_mcqs_stream, generate_quiz_review, generate_performance_analysis
from app.services.performance_analyzer import performance_analyzer
from app.models.quiz import PerformanceAnalysis
import json


class QuizService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = QuizRepository(db)

    
    async def generate_questions_stream(
        self, space: LearningSpace, req: GenerateQuestionsRequest
    ):
        count = max(1, min(30, req.count))
        lang = getattr(req, "lang", "en")
        source_type = getattr(req, "source_type", "curriculum")

        # Create session first so we can return its ID immediately
        session = await self.repo.create_session(
            space_id=space.id,
            topic=req.topic,
            total_questions=count, # Approximate, might be fewer
            is_exam=(req.topic is None),
            lang=lang,
            source_type=source_type,
        )

        # Yield the session ID first
        yield f"event: session\ndata: {json.dumps({'session_id': session.id})}\n\n"

        valid_options = {"a", "b", "c", "d"}
        
        try:
            async for q in generate_mcqs_stream(
                exam=space.exam_id,
                subject=space.subject,
                topic=req.topic,
                count=count,
                lang=lang,
                source_type=source_type,
                space_id=space.id,
            ):
                if not all(k in q for k in ("question", "option_a", "option_b", "option_c", "option_d", "correct_option")):
                    continue
                if q["correct_option"].lower() not in valid_options:
                    continue
                
                question_obj = QuizQuestion(
                    space_id=space.id,
                    topic=q.get("topic", req.topic or "Mixed Topics"),
                    question=q["question"],
                    option_a=q["option_a"],
                    option_b=q["option_b"],
                    option_c=q["option_c"],
                    option_d=q["option_d"],
                    correct_option=q["correct_option"].lower(),
                    explanation=q.get("explanation"),
                    source_type=source_type,
                )
                
                # Save to DB individually
                saved_q = (await self.repo.bulk_save_questions([question_obj]))[0]
                
                # Yield to frontend
                q_dict = {
                    "id": saved_q.id,
                    "question": saved_q.question,
                    "option_a": saved_q.option_a,
                    "option_b": saved_q.option_b,
                    "option_c": saved_q.option_c,
                    "option_d": saved_q.option_d,
                    "explanation": saved_q.explanation,
                    "topic": saved_q.topic
                }
                yield f"event: question\ndata: {json.dumps(q_dict)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "event: complete\ndata: {}\n\n"
            
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
                source_type=getattr(req, "source_type", "curriculum"),
                space_id=space.id,
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
                    source_type=getattr(req, "source_type", "curriculum"),
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
            lang=lang,
            source_type=getattr(req, "source_type", "curriculum"),
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

        # None means the question was skipped (e.g. timer expired)
        user_answer = req.user_answer
        is_skipped = user_answer is None

        if not is_skipped:
            user_answer = user_answer.lower()
            if user_answer not in {"a", "b", "c", "d"}:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="user_answer must be 'a', 'b', 'c', or 'd', or null to skip.",
                )

        is_correct = (not is_skipped) and (user_answer == question.correct_option)
        await self.repo.save_attempt(
            space_id=space.id,
            question_id=question.id,
            user_answer=user_answer or "skip",  # store "skip" for None in DB
            is_correct=is_correct,
            time_taken_seconds=req.time_taken_seconds,
            is_exam=req.is_exam,
            session_id=req.session_id,
        )

        if req.session_id and not is_skipped:
            session = await self.repo.get_session(req.session_id)
            if session:
                if is_correct:
                    session.correct_answers += 1
                session.score_pct = int(round((session.correct_answers / session.total_questions) * 100)) if session.total_questions > 0 else 0
                await self.repo.update_session(session)

        return AnswerResult(
            question_id=question.id,
            user_answer=user_answer or "skip",
            correct_option=question.correct_option,
            is_correct=is_correct,
            explanation=question.explanation if not is_skipped else None,
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

    async def get_batch_stats(self, space_ids: List[int]) -> Dict[int, SpaceStats]:
        batch_data = await self.repo.get_batch_stats(space_ids)
        result = {}
        
        def pct(correct: int, total: int) -> float:
            return round(correct / total * 100, 1) if total > 0 else 0.0
            
        for sid, data in batch_data.items():
            p_total, p_correct = data["practice"]
            e_total, e_correct = data["exam"]
            all_total = p_total + e_total
            all_correct = p_correct + e_correct
            
            result[sid] = SpaceStats(
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
        return result

    async def get_history(self, space_id: int) -> list:
        return await self.repo.get_sessions_for_space(space_id)

    async def get_global_history(self, user_id: int) -> list:
        return await self.repo.get_global_sessions_for_user(user_id)

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

    async def complete_session(self, session_id: int, space: LearningSpace, user_id: int):
        session = await self.repo.get_session(session_id)
        if not session or session.space_id != space.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
            
        session.is_completed = True
        session.user_id = int(user_id)
        await self.repo.update_session(session)
        
        attempts = await self.repo.get_attempts_for_session(session_id)
        questions = await self.repo.get_questions_for_space(space.id)
        
        structured_metrics = performance_analyzer.compute(session, attempts, questions)
        
        # AI call
        ai_narrative = None
        overall_summary = None
        ai_generated = False
        try:
            analysis_dict = await generate_performance_analysis(
                exam=space.exam_id,
                subject=space.subject,
                structured_metrics=structured_metrics
            )
            ai_narrative = analysis_dict.get("ai_narrative")
            overall_summary = analysis_dict.get("overall_summary")
            ai_generated = True
        except Exception:
            pass
            
        analysis = PerformanceAnalysis(
            session_id=session.id,
            space_id=space.id,
            user_id=int(user_id),
            performance_level=structured_metrics["performance_level"],
            total_questions=structured_metrics["total_questions"],
            correct_count=structured_metrics["correct_count"],
            incorrect_count=structured_metrics["incorrect_count"],
            skipped_count=structured_metrics["skipped_count"],
            score_pct=structured_metrics["score_pct"],
            strong_areas=json.dumps(structured_metrics["strong_areas"]),
            developing_areas=json.dumps(structured_metrics["developing_areas"]),
            priority_areas=json.dumps(structured_metrics["priority_areas"]),
            topic_insights=json.dumps(structured_metrics["topic_insights"]),
            mistake_patterns=json.dumps(structured_metrics["mistake_patterns"]),
            recommendations=json.dumps(structured_metrics["recommendations"]),
            overall_summary=overall_summary,
            ai_narrative=ai_narrative,
            ai_generated=ai_generated,
        )
        await self.repo.save_analysis(analysis)
        
        # Merge AI text into the return dict
        structured_metrics["ai_narrative"] = ai_narrative
        structured_metrics["overall_summary"] = overall_summary
        structured_metrics["ai_generated"] = ai_generated
        structured_metrics["session_id"] = session.id
        structured_metrics["space_id"] = space.id
        
        return {"session": session, "analysis": structured_metrics}

    async def get_session_analysis(self, session_id: int, space: LearningSpace, user_id: int):
        analysis = await self.repo.get_analysis_for_session(session_id)
        if not analysis or analysis.space_id != space.id or analysis.user_id != int(user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found or unauthorized")
            
        return {
            "session_id": analysis.session_id,
            "space_id": analysis.space_id,
            "performance_level": analysis.performance_level,
            "total_questions": analysis.total_questions,
            "correct_count": analysis.correct_count,
            "incorrect_count": analysis.incorrect_count,
            "skipped_count": analysis.skipped_count,
            "score_pct": analysis.score_pct,
            "strong_areas": json.loads(analysis.strong_areas) if analysis.strong_areas else [],
            "developing_areas": json.loads(analysis.developing_areas) if analysis.developing_areas else [],
            "priority_areas": json.loads(analysis.priority_areas) if analysis.priority_areas else [],
            "topic_insights": json.loads(analysis.topic_insights) if analysis.topic_insights else [],
            "mistake_patterns": json.loads(analysis.mistake_patterns) if analysis.mistake_patterns else [],
            "recommendations": json.loads(analysis.recommendations) if analysis.recommendations else [],
            "overall_summary": analysis.overall_summary,
            "ai_narrative": analysis.ai_narrative,
            "ai_generated": analysis.ai_generated,
        }
