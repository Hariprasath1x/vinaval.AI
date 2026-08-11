from typing import List, Dict, Any, Tuple
from app.models.quiz import QuizSession, QuizAttempt, QuizQuestion
from app.schemas.performance_analysis import (
    TopicInsight, MistakePattern, Recommendation, PerformanceAnalysisOut
)

class PerformanceAnalyzer:
    """Deterministic calculation engine for computing test performance."""
    
    def compute(self, session: QuizSession, attempts: List[QuizAttempt], questions: List[QuizQuestion]) -> Dict[str, Any]:
        """
        Computes structured metrics for a quiz session.
        Returns a dictionary that can be unpacked into a PerformanceAnalysis model.
        """
        questions_by_id = {q.id: q for q in questions}
        
        # 1. Aggregate per-topic stats
        topic_stats = {}
        for q in questions:
            if q.topic not in topic_stats:
                topic_stats[q.topic] = {
                    "questions": 0, "correct": 0, "incorrect": 0, "skipped": 0,
                    "attempts": []
                }
            topic_stats[q.topic]["questions"] += 1
            
        total_questions = len(questions)
        correct_count = 0
        incorrect_count = 0
        skipped_count = 0
        
        # Process attempts
        answered_question_ids = set()
        for attempt in attempts:
            answered_question_ids.add(attempt.question_id)
            q = questions_by_id[attempt.question_id]
            topic_stats[q.topic]["attempts"].append(attempt)
            
            if attempt.user_answer is None or attempt.user_answer == "" or attempt.user_answer == "null":
                topic_stats[q.topic]["skipped"] += 1
                skipped_count += 1
            elif attempt.is_correct:
                topic_stats[q.topic]["correct"] += 1
                correct_count += 1
            else:
                topic_stats[q.topic]["incorrect"] += 1
                incorrect_count += 1
                
        # Handle skipped/unanswered questions
        for q in questions:
            if q.id not in answered_question_ids:
                topic_stats[q.topic]["skipped"] += 1
                skipped_count += 1
                
        score_pct = (correct_count / total_questions * 100) if total_questions > 0 else 0
        overall_accuracy = (correct_count / (correct_count + incorrect_count)) if (correct_count + incorrect_count) > 0 else 0
        
        # 2. Classify each topic
        strong_areas = []
        developing_areas = []
        needs_work_areas = []
        all_insights = []
        
        for topic, stats in topic_stats.items():
            total_q = stats["questions"]
            if total_q == 0:
                continue
                
            correct = stats["correct"]
            incorrect = stats["incorrect"]
            attempted = correct + incorrect
            
            base_accuracy = (correct / attempted) if attempted > 0 else 0.0
            weight = min(1.0, total_q / 5.0)
            
            if total_q < 3:
                level = "uncertain"
            elif base_accuracy >= 0.80 and weight >= 0.6:
                level = "strong"
            elif base_accuracy >= 0.55 or (weight < 0.4 and base_accuracy >= 0.65):
                level = "developing"
            else:
                level = "needs_work"
                
            insight = TopicInsight(
                name=topic,
                questions=total_q,
                correct=correct,
                incorrect=incorrect,
                skipped=stats["skipped"],
                accuracy=base_accuracy * 100,
                level=level,
                key_subtopics=[]
            )
            
            all_insights.append(insight)
            if level == "strong":
                strong_areas.append(insight)
            elif level == "developing":
                developing_areas.append(insight)
            elif level == "needs_work":
                needs_work_areas.append(insight)
                
        # 3. Identify mistake patterns
        mistake_patterns = self._identify_mistake_patterns(all_insights)
        
        # 4. Rank topics by improvement priority
        priority_areas = sorted(
            needs_work_areas + developing_areas, 
            key=lambda x: (x.accuracy, -x.questions)
        )
        
        recommendations = self._build_recommendations(priority_areas, strong_areas)
        
        # Overall performance level
        if score_pct >= 85:
            perf_level = "excellent"
        elif score_pct >= 70:
            perf_level = "good"
        elif score_pct >= 50:
            perf_level = "developing"
        else:
            perf_level = "needs_work"
            
        return {
            "performance_level": perf_level,
            "total_questions": total_questions,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "skipped_count": skipped_count,
            "score_pct": score_pct,
            "strong_areas": [a.model_dump() for a in strong_areas],
            "developing_areas": [a.model_dump() for a in developing_areas],
            "priority_areas": [a.model_dump() for a in priority_areas[:3]], # Top 3 priorities
            "topic_insights": [a.model_dump() for a in all_insights],
            "mistake_patterns": [p.model_dump() for p in mistake_patterns],
            "recommendations": [r.model_dump() for r in recommendations],
        }
        
    def _identify_mistake_patterns(self, insights: List[TopicInsight]) -> List[MistakePattern]:
        patterns = []
        high_skip_topics = [i.name for i in insights if i.skipped > 0 and (i.skipped / i.questions) > 0.4]
        if high_skip_topics:
            patterns.append(MistakePattern(
                type="time_management",
                description="High number of skipped questions suggests running out of time or uncertainty.",
                affected_topics=high_skip_topics
            ))
            
        low_acc_topics = [i.name for i in insights if i.accuracy < 30 and i.questions >= 3]
        if low_acc_topics:
            patterns.append(MistakePattern(
                type="conceptual_gaps",
                description="Consistently incorrect answers in these topics point to fundamental misunderstandings.",
                affected_topics=low_acc_topics
            ))
            
        return patterns
        
    def _build_recommendations(self, priority: List[TopicInsight], strong: List[TopicInsight]) -> List[Recommendation]:
        recs = []
        count = 1
        for topic in priority[:2]:
            recs.append(Recommendation(
                priority="High",
                action="Revise",
                topic=topic.name,
                detail=f"Focus on fundamental concepts, as accuracy is currently {topic.accuracy:.0f}%."
            ))
            count += 1
            
        for topic in strong[:1]:
            recs.append(Recommendation(
                priority="Low",
                action="Maintain",
                topic=topic.name,
                detail=f"Good performance ({topic.accuracy:.0f}%). Practice mixed questions to keep it fresh."
            ))
            
        return recs

performance_analyzer = PerformanceAnalyzer()
