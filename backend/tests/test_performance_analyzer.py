import pytest
from app.services.performance_analyzer import PerformanceAnalyzer
from app.models.quiz import QuizSession, QuizAttempt, QuizQuestion

def test_performance_analyzer_high_performer():
    analyzer = PerformanceAnalyzer()
    
    session = QuizSession(id=1, space_id=1, topic="Biology", total_questions=5)
    
    questions = [
        QuizQuestion(id=1, topic="Cell Biology", correct_option="a"),
        QuizQuestion(id=2, topic="Cell Biology", correct_option="a"),
        QuizQuestion(id=3, topic="Cell Biology", correct_option="a"),
        QuizQuestion(id=4, topic="Genetics", correct_option="a"),
        QuizQuestion(id=5, topic="Genetics", correct_option="a"),
    ]
    
    attempts = [
        QuizAttempt(question_id=1, user_answer="a", is_correct=True),
        QuizAttempt(question_id=2, user_answer="a", is_correct=True),
        QuizAttempt(question_id=3, user_answer="a", is_correct=True),
        QuizAttempt(question_id=4, user_answer="a", is_correct=True),
        QuizAttempt(question_id=5, user_answer="a", is_correct=True),
    ]
    
    metrics = analyzer.compute(session, attempts, questions)
    
    assert metrics["performance_level"] == "excellent"
    assert metrics["score_pct"] == 100.0
    
    # Cell Biology has 3 questions and 100% accuracy -> strong
    # Genetics has 2 questions (less than 3) -> uncertain
    
    assert any(t["name"] == "Cell Biology" for t in metrics["strong_areas"])
    assert not any(t["name"] == "Genetics" for t in metrics["strong_areas"]) 
    
    topics = {t["name"]: t for t in metrics["topic_insights"]}
    assert topics["Genetics"]["level"] == "uncertain"
    
    # Recommendations should include a "Maintain" recommendation for Cell Biology
    assert any(r["action"] == "Maintain" and r["topic"] == "Cell Biology" for r in metrics["recommendations"])


def test_performance_analyzer_low_performer():
    analyzer = PerformanceAnalyzer()
    
    session = QuizSession(id=1, space_id=1, topic="Biology", total_questions=4)
    
    questions = [
        QuizQuestion(id=1, topic="Ecology", correct_option="a"),
        QuizQuestion(id=2, topic="Ecology", correct_option="a"),
        QuizQuestion(id=3, topic="Ecology", correct_option="a"),
        QuizQuestion(id=4, topic="Ecology", correct_option="a"),
    ]
    
    attempts = [
        QuizAttempt(question_id=1, user_answer="a", is_correct=True),
        QuizAttempt(question_id=2, user_answer="b", is_correct=False),
        QuizAttempt(question_id=3, user_answer="b", is_correct=False),
        QuizAttempt(question_id=4, user_answer="b", is_correct=False),
    ]
    
    metrics = analyzer.compute(session, attempts, questions)
    
    assert metrics["performance_level"] == "needs_work"
    assert metrics["score_pct"] == 25.0
    
    assert any(t["name"] == "Ecology" for t in metrics["priority_areas"])
    assert any(r["action"] == "Revise" and r["topic"] == "Ecology" for r in metrics["recommendations"])
    
    # Mistake patterns should identify conceptual gaps
    assert any(m["type"] == "conceptual_gaps" for m in metrics["mistake_patterns"])


def test_performance_analyzer_skipped():
    analyzer = PerformanceAnalyzer()
    
    session = QuizSession(id=1, space_id=1, topic="Biology", total_questions=3)
    
    questions = [
        QuizQuestion(id=1, topic="Evolution", correct_option="a"),
        QuizQuestion(id=2, topic="Evolution", correct_option="a"),
        QuizQuestion(id=3, topic="Evolution", correct_option="a"),
    ]
    
    attempts = [
        QuizAttempt(question_id=1, user_answer=None, is_correct=False), # Skipped explicitly
        QuizAttempt(question_id=2, user_answer="", is_correct=False),   # Skipped implicitly
        # Question 3 not attempted at all
    ]
    
    metrics = analyzer.compute(session, attempts, questions)
    
    assert metrics["skipped_count"] == 3
    assert metrics["score_pct"] == 0.0
    
    # Mistake patterns should identify time management
    assert any(m["type"] == "time_management" for m in metrics["mistake_patterns"])
