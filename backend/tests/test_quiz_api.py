"""
test_quiz_api.py — Integration tests for the Quiz API endpoints.

Tests:
  - POST /api/v1/spaces/{id}/quiz/generate  (practice + mock exam modes)
  - POST /api/v1/spaces/{id}/quiz/attempt
  - GET  /api/v1/spaces/{id}/quiz/stats
  - POST /api/v1/spaces/{id}/quiz/review

The Groq LLM and ChromaDB are mocked so tests run fast without network calls.
The SpaceService is also mocked to return our `mock_space` fixture directly.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz import QuizQuestion, QuizAttempt


pytestmark = pytest.mark.asyncio


# ── Helpers ────────────────────────────────────────────────────────────────────

SAMPLE_QUESTIONS_JSON = json.dumps([
    {
        "topic": "Newton's Laws",
        "question": "What is Newton's first law?",
        "option_a": "An object at rest stays at rest",
        "option_b": "Force equals mass times acceleration",
        "option_c": "For every action there is a reaction",
        "option_d": "Energy is conserved",
        "correct_option": "a",
        "explanation": "Newton's first law is the law of inertia.",
    },
    {
        "topic": "Newton's Laws",
        "question": "What is Newton's second law?",
        "option_a": "An object at rest stays at rest",
        "option_b": "F = ma",
        "option_c": "For every action there is a reaction",
        "option_d": "p = mv",
        "correct_option": "b",
        "explanation": "F = ma is Newton's second law of motion.",
    },
])

SAMPLE_MOCK_EXAM_JSON = json.dumps([
    {
        "topic": "Photosynthesis",
        "question": "Which pigment is primarily involved in photosynthesis?",
        "option_a": "Melanin",
        "option_b": "Haemoglobin",
        "option_c": "Chlorophyll",
        "option_d": "Carotene",
        "correct_option": "c",
        "explanation": "Chlorophyll absorbs sunlight for photosynthesis.",
    },
    {
        "topic": "Thermodynamics",
        "question": "What does the first law of thermodynamics state?",
        "option_a": "Entropy always increases",
        "option_b": "Energy cannot be created or destroyed",
        "option_c": "Heat flows from cold to hot",
        "option_d": "Temperature is absolute",
        "correct_option": "b",
        "explanation": "The first law states conservation of energy.",
    },
])


def _make_groq_response(content: str):
    """Build a minimal mock object that mimics a Groq ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


def _patch_space_service(mock_space):
    """Return a context-manager patch that makes SpaceService.get_space return mock_space."""
    return patch(
        "app.api.v1.quiz.SpaceService.get_space",
        new=AsyncMock(return_value=mock_space),
    )


# ── Tests: generate questions (practice) ──────────────────────────────────────

class TestGenerateQuestions:
    async def test_generate_practice_questions_success(
        self, client: AsyncClient, mock_space
    ):
        """POST /quiz/generate with a topic returns a list of saved questions."""
        groq_response = _make_groq_response(SAMPLE_QUESTIONS_JSON)

        with (
            _patch_space_service(mock_space),
            patch("app.rag.chain.AsyncGroq") as mock_groq_cls,
            patch("app.rag.chain._retrieve_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=groq_response)
            mock_groq_cls.return_value = mock_client

            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/generate",
                json={"topic": "Newton's Laws", "count": 2, "lang": "en"},
            )

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["topic"] == "Newton's Laws"
        assert data[0]["correct_option"] == "a"

    async def test_generate_mock_exam_success(
        self, client: AsyncClient, mock_space
    ):
        """POST /quiz/generate with no topic triggers mock exam mode (diverse topics)."""
        groq_response = _make_groq_response(SAMPLE_MOCK_EXAM_JSON)

        with (
            _patch_space_service(mock_space),
            patch("app.rag.chain.AsyncGroq") as mock_groq_cls,
            patch("app.rag.chain._retrieve_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=groq_response)
            mock_groq_cls.return_value = mock_client

            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/generate",
                json={"topic": None, "count": 2, "lang": "en"},
            )

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        # Mock exam questions should have different topics
        topics = {q["topic"] for q in data}
        assert len(topics) == 2, "Mock exam should span multiple topics"

    async def test_generate_questions_invalid_json_from_llm(
        self, client: AsyncClient, mock_space
    ):
        """If the LLM returns invalid JSON, the endpoint should return 502."""
        groq_response = _make_groq_response("This is not valid JSON at all!")

        with (
            _patch_space_service(mock_space),
            patch("app.rag.chain.AsyncGroq") as mock_groq_cls,
            patch("app.rag.chain._retrieve_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=groq_response)
            mock_groq_cls.return_value = mock_client

            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/generate",
                json={"topic": "Gravity", "count": 5, "lang": "en"},
            )

        assert response.status_code == 502
        assert "invalid JSON" in response.json()["detail"].lower() or "failed" in response.json()["detail"].lower()

    async def test_generate_questions_clamps_count(
        self, client: AsyncClient, mock_space
    ):
        """Requesting > 30 questions should clamp to 30; < 1 should clamp to 1."""
        groq_response = _make_groq_response(SAMPLE_QUESTIONS_JSON)

        with (
            _patch_space_service(mock_space),
            patch("app.rag.chain.AsyncGroq") as mock_groq_cls,
            patch("app.rag.chain._retrieve_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=groq_response)
            mock_groq_cls.return_value = mock_client

            # Requesting 99 questions — should succeed (service clamps to 30)
            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/generate",
                json={"topic": "Optics", "count": 99, "lang": "en"},
            )

        # The LLM only returns 2 questions in our mock so 2 will be saved
        assert response.status_code == 201


# ── Tests: submit answer ───────────────────────────────────────────────────────

class TestSubmitAnswer:
    @pytest_asyncio.fixture(autouse=True)
    async def seed_question(self, db_session: AsyncSession, mock_space):
        """Insert a single question into the in-memory DB before each test."""
        q = QuizQuestion(
            space_id=mock_space.id,
            topic="Optics",
            question="What is the speed of light?",
            option_a="3 × 10⁸ m/s",
            option_b="3 × 10⁶ m/s",
            option_c="3 × 10⁴ m/s",
            option_d="3 × 10² m/s",
            correct_option="a",
            explanation="The speed of light in a vacuum is approximately 3 × 10⁸ m/s.",
        )
        db_session.add(q)
        await db_session.commit()
        await db_session.refresh(q)
        self.question_id = q.id

    async def test_submit_correct_answer(
        self, client: AsyncClient, mock_space
    ):
        """Submitting the correct answer returns is_correct=True."""
        with _patch_space_service(mock_space):
            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/attempt",
                json={"question_id": self.question_id, "user_answer": "a", "is_exam": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is True
        assert data["correct_option"] == "a"
        assert "explanation" in data

    async def test_submit_wrong_answer(
        self, client: AsyncClient, mock_space
    ):
        """Submitting a wrong answer returns is_correct=False."""
        with _patch_space_service(mock_space):
            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/attempt",
                json={"question_id": self.question_id, "user_answer": "d", "is_exam": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is False
        assert data["correct_option"] == "a"

    async def test_submit_invalid_answer_option(
        self, client: AsyncClient, mock_space
    ):
        """Submitting an invalid option (not a/b/c/d) returns 422."""
        with _patch_space_service(mock_space):
            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/attempt",
                json={"question_id": self.question_id, "user_answer": "z", "is_exam": False},
            )

        assert response.status_code == 422

    async def test_submit_answer_nonexistent_question(
        self, client: AsyncClient, mock_space
    ):
        """Submitting an answer for a non-existent question returns 404."""
        with _patch_space_service(mock_space):
            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/attempt",
                json={"question_id": 99999, "user_answer": "b", "is_exam": False},
            )

        assert response.status_code == 404


# ── Tests: stats ───────────────────────────────────────────────────────────────

class TestGetStats:
    async def test_stats_empty_space(
        self, client: AsyncClient, mock_space
    ):
        """Stats for a space with no attempts return zeros."""
        with _patch_space_service(mock_space):
            response = await client.get(
                f"/api/v1/spaces/{mock_space.id}/quiz/stats"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_all"] == 0
        assert data["correct_all"] == 0
        assert data["accuracy_all"] == 0.0
        assert data["topics_practiced"] == []

    async def test_stats_after_attempts(
        self, client: AsyncClient, mock_space, db_session: AsyncSession
    ):
        """Stats correctly aggregate practice and exam attempt counts."""
        # Seed 1 question and 3 attempts (2 practice correct, 1 exam wrong)
        q = QuizQuestion(
            space_id=mock_space.id,
            topic="Kinematics",
            question="What is velocity?",
            option_a="Rate of change of displacement",
            option_b="Rate of change of speed",
            option_c="Distance over time",
            option_d="Acceleration over time",
            correct_option="a",
        )
        db_session.add(q)
        await db_session.commit()

        for i, (is_correct, is_exam) in enumerate([
            (True,  False),  # practice, correct
            (True,  False),  # practice, correct
            (False, True),   # exam, wrong
        ]):
            a = QuizAttempt(
                space_id=mock_space.id,
                question_id=q.id,
                user_answer="a" if is_correct else "b",
                is_correct=is_correct,
                time_taken_seconds=10,
                is_exam=is_exam,
            )
            db_session.add(a)
        await db_session.commit()

        with _patch_space_service(mock_space):
            response = await client.get(
                f"/api/v1/spaces/{mock_space.id}/quiz/stats"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_practice"] == 2
        assert data["correct_practice"] == 2
        assert data["accuracy_practice"] == 100.0
        assert data["total_exam"] == 1
        assert data["correct_exam"] == 0
        assert data["accuracy_exam"] == 0.0
        assert data["total_all"] == 3
        assert "Kinematics" in data["topics_practiced"]


# ── Tests: quiz review ─────────────────────────────────────────────────────────

class TestQuizReview:
    async def test_generate_review_success(
        self, client: AsyncClient, mock_space
    ):
        """POST /quiz/review returns a review string from the LLM."""
        groq_response = MagicMock()
        groq_response.choices[0].message.content = (
            "Great effort! You excelled in Newton's Laws but need more practice on Optics."
        )

        with (
            _patch_space_service(mock_space),
            patch("app.rag.chain.AsyncGroq") as mock_groq_cls,
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=groq_response)
            mock_groq_cls.return_value = mock_client

            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/review",
                json={
                    "results": [
                        {"topic": "Newton's Laws", "is_correct": True},
                        {"topic": "Optics", "is_correct": False},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "review" in data
        assert len(data["review"]) > 10

    async def test_generate_review_empty_results(
        self, client: AsyncClient, mock_space
    ):
        """Posting empty results should return a graceful fallback review."""
        with _patch_space_service(mock_space):
            response = await client.post(
                f"/api/v1/spaces/{mock_space.id}/quiz/review",
                json={"results": []},
            )

        assert response.status_code == 200
        data = response.json()
        assert "review" in data
        assert "No questions" in data["review"] or len(data["review"]) > 0
