import pytest
from app.services.quiz_service import QuizService

@pytest.mark.asyncio
async def test_quiz_service_init(db_session):
    # Basic skeleton test for quiz service
    service = QuizService(db_session)
    assert service is not None
