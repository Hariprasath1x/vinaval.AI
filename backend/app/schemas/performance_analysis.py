from typing import List, Optional, Dict
from pydantic import BaseModel


class TopicInsight(BaseModel):
    name: str
    questions: int
    correct: int
    incorrect: int
    skipped: int
    accuracy: float
    level: str
    key_subtopics: List[str] = []


class MistakePattern(BaseModel):
    type: str
    description: str
    affected_topics: List[str] = []


class Recommendation(BaseModel):
    priority: str
    action: str
    topic: str
    detail: str


class PerformanceAnalysisOut(BaseModel):
    session_id: int
    space_id: int
    
    # Deterministic fields
    performance_level: str
    total_questions: int
    correct_count: int
    incorrect_count: int
    skipped_count: int
    score_pct: float
    
    strong_areas: List[TopicInsight]
    developing_areas: List[TopicInsight]
    priority_areas: List[TopicInsight]
    topic_insights: List[TopicInsight]
    mistake_patterns: List[MistakePattern]
    recommendations: List[Recommendation]
    
    # AI-generated fields
    overall_summary: Optional[str] = None
    ai_narrative: Optional[str] = None
    ai_generated: bool
    
    model_config = {"from_attributes": True}
