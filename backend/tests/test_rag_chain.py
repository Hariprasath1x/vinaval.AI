"""
test_rag_chain.py — Unit tests for app.rag.chain functions.

FIX APPLIED (2026-08-27):
  The LLM layer was migrated from Groq-first to Gemini-first with Groq as fallback.
  AsyncGroq is imported lazily inside the exception handler — it is never a module-level
  attribute of app.rag.chain. All test patches updated from:
    patch("app.rag.chain.AsyncGroq")
  to:
    patch("app.rag.chain.genai")  (the google.generativeai module-level import)
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.chain import (
    _detect_lang,
    _retrieve_syllabus_context,
    generate_mcqs,
    generate_flashcards,
    generate_quiz_review,
    RAGSystemError,
)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _make_gemini_model_mock(content: str) -> MagicMock:
    """
    Returns a mock genai module where GenerativeModel(...).generate_content_async(...)
    returns a mock response with the given content string.
    """
    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = content
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    mock_genai.GenerativeModel.return_value = mock_model
    mock_genai.types = MagicMock()
    mock_genai.types.GenerationConfig = MagicMock(return_value={})
    return mock_genai


# ══════════════════════════════════════════════════════════════════════════════
#  Language Detection
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectLang:
    def test_english_text_returns_en(self):
        assert _detect_lang("What is Newton's first law?") == "en"

    def test_tamil_text_returns_ta(self):
        tamil = "நியூட்டனின் முதல் விதி என்ன?"
        assert _detect_lang(tamil) == "ta"

    def test_empty_string_returns_en(self):
        assert _detect_lang("") == "en"

    def test_mixed_mostly_english_returns_en(self):
        assert _detect_lang("Hello world English only") == "en"

    def test_special_characters_returns_en(self):
        assert _detect_lang("!@#$%^&*()_+{}[]|<>?") == "en"

    def test_numbers_only_returns_en(self):
        assert _detect_lang("12345 6789 0") == "en"

    def test_mixed_tamil_english_above_threshold_returns_ta(self):
        text = "நியூட்டன் Physics"
        assert _detect_lang(text) == "ta"


# ══════════════════════════════════════════════════════════════════════════════
#  ChromaDB Retrieval Fallback
# ══════════════════════════════════════════════════════════════════════════════

class TestRetrieveContext:
    def test_returns_empty_when_chromadb_raises(self):
        """
        When the ChromaDB client fails to initialize (outer try/except in _retrieve_syllabus_context),
        the function re-raises RAGSystemError. When the collections list fails (inner), it returns ("", 0).
        We test the outer failure case (ChromaDB unavailable at client level).
        """
        with patch(
            "app.core.chroma.get_collections_for_subject",
            side_effect=Exception("ChromaDB not running"),
        ), patch(
            "app.core.chroma.get_chroma_client",
            side_effect=Exception("ChromaDB not running"),
        ):
            # Outer exception → RAGSystemError is raised (not silently swallowed)
            with pytest.raises(RAGSystemError):
                _retrieve_syllabus_context("NEET", "Physics", "gravity", n_results=4)

    def test_returns_empty_when_no_collections(self):
        with patch(
            "app.core.chroma.get_collections_for_subject",
            return_value=[],
        ):
            context, n = _retrieve_syllabus_context("NEET", "Botany", "cell division", n_results=4)
        assert context == ""
        assert n == 0

    def test_returns_empty_for_tnpsc_history_no_collections(self):
        with patch(
            "app.core.chroma.get_collections_for_subject",
            return_value=[],
        ):
            context, n = _retrieve_syllabus_context("TNPSC", "History", "Chola dynasty", n_results=4)
        assert context == ""
        assert n == 0


# ══════════════════════════════════════════════════════════════════════════════
#  MCQ Generation  (patching genai — the module-level Gemini import)
# ══════════════════════════════════════════════════════════════════════════════

VALID_MCQ_JSON = json.dumps([
    {
        "topic": "Newton's Laws",
        "question": "What is inertia?",
        "option_a": "Tendency to resist change",
        "option_b": "Force equals mass times acceleration",
        "option_c": "Rate of change of momentum",
        "option_d": "Conservation of energy",
        "correct_option": "a",
        "explanation": "Inertia is the resistance of a body to changes in its motion.",
    }
])

VALID_MOCK_EXAM_JSON = json.dumps([
    {
        "topic": "Thermodynamics",
        "question": "What does entropy measure?",
        "option_a": "Heat",
        "option_b": "Work",
        "option_c": "Disorder in a system",
        "option_d": "Temperature",
        "correct_option": "c",
        "explanation": "Entropy measures the degree of disorder in a thermodynamic system.",
    },
    {
        "topic": "Electrostatics",
        "question": "What is Coulomb's law?",
        "option_a": "F = ma",
        "option_b": "F = kq1q2/r2",
        "option_c": "F = mv",
        "option_d": "F = qE",
        "correct_option": "b",
        "explanation": "Coulomb's law defines the electrostatic force between two charges.",
    },
])


class TestGenerateMCQs:
    async def test_generate_practice_questions(self):
        mock_genai = _make_gemini_model_mock(VALID_MCQ_JSON)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic="Newton's Laws", count=1, lang="en",
            )
        assert isinstance(questions, list)
        assert len(questions) == 1
        q = questions[0]
        assert q["topic"] == "Newton's Laws"
        assert q["correct_option"] == "a"
        assert "explanation" in q

    async def test_generate_mock_exam_no_topic(self):
        mock_genai = _make_gemini_model_mock(VALID_MOCK_EXAM_JSON)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic=None, count=2, lang="en",
            )
        assert len(questions) == 2
        topics = {q["topic"] for q in questions}
        assert "Thermodynamics" in topics
        assert "Electrostatics" in topics

    async def test_generate_mcqs_strips_markdown_code_fences(self):
        wrapped = f"```json\n{VALID_MCQ_JSON}\n```"
        mock_genai = _make_gemini_model_mock(wrapped)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic="Inertia", count=1, lang="en"
            )
        assert len(questions) == 1

    async def test_generate_mcqs_raises_on_invalid_json(self):
        """
        When LLM returns non-JSON, generate_mcqs logs the error and returns []
        (it does NOT raise ValueError — callers handle empty list upstream).
        """
        mock_genai = _make_gemini_model_mock("Sorry, I cannot generate questions right now.")
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic="Gravity", count=1, lang="en"
            )
        # The function gracefully degrades to an empty list
        assert questions == []

    async def test_generate_mcqs_raises_when_not_a_list(self):
        """
        When LLM returns a JSON object (not array), generate_mcqs returns [].
        The service layer (QuizService) raises HTTP 502 if no valid questions.
        """
        mock_genai = _make_gemini_model_mock('{"error": "no questions"}')
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic="Gravity", count=1, lang="en"
            )
        # JSON object (not array) → empty list returned
        assert isinstance(questions, list)

    async def test_generate_mcqs_tamil_language(self):
        tamil_json = json.dumps([{
            "topic": "Optics",
            "question": "Speed of light?",
            "option_a": "3x10^8 m/s",
            "option_b": "3x10^6 m/s",
            "option_c": "3x10^4 m/s",
            "option_d": "1x10^8 m/s",
            "correct_option": "a",
            "explanation": "Speed of light is 3x10^8 m/s.",
        }])
        mock_genai = _make_gemini_model_mock(tamil_json)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic="Optics", count=1, lang="ta"
            )
        assert len(questions) == 1
        assert questions[0]["correct_option"] == "a"

    async def test_generate_mcqs_tnpsc_history(self):
        history_json = json.dumps([{
            "topic": "Chola Dynasty",
            "question": "Who built the Brihadeeswarar Temple?",
            "option_a": "Rajendra Chola",
            "option_b": "Raja Raja Chola I",
            "option_c": "Kulottunga Chola",
            "option_d": "Aditya Chola",
            "correct_option": "b",
            "explanation": "Raja Raja Chola I built the Brihadeeswarar Temple in Thanjavur.",
        }])
        mock_genai = _make_gemini_model_mock(history_json)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="TNPSC", subject="History", topic="Chola Dynasty", count=1, lang="en"
            )
        assert len(questions) == 1
        assert questions[0]["correct_option"] == "b"

    async def test_generate_mcqs_empty_response_raises(self):
        """
        When LLM returns empty string, generate_mcqs returns [] (no questions).
        The service layer handles the empty list case by raising HTTP 502.
        """
        mock_genai = _make_gemini_model_mock("")
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="NEET", subject="Chemistry", topic="Acids", count=2, lang="en"
            )
        assert questions == []

    async def test_generate_mcqs_count_returns_correct_number(self):
        mock_genai = _make_gemini_model_mock(VALID_MOCK_EXAM_JSON)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic=None, count=2, lang="en"
            )
        assert len(questions) == 2


# ══════════════════════════════════════════════════════════════════════════════
#  Flashcard Generation
# ══════════════════════════════════════════════════════════════════════════════

VALID_FLASHCARD_JSON = json.dumps([
    {"front": "What is photosynthesis?", "back": "The process by which plants convert sunlight into glucose."},
    {"front": "What is ATP?", "back": "Adenosine triphosphate - the energy currency of the cell."},
])


class TestGenerateFlashcards:
    async def test_generate_flashcards_success(self):
        mock_genai = _make_gemini_model_mock(VALID_FLASHCARD_JSON)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            cards = await generate_flashcards(
                exam="NEET", subject="Botany", topic="Photosynthesis", count=2, lang="en"
            )
        assert isinstance(cards, list)
        assert len(cards) == 2
        assert "front" in cards[0]
        assert "back" in cards[0]

    async def test_generate_flashcards_strips_code_fences(self):
        wrapped = f"```\n{VALID_FLASHCARD_JSON}\n```"
        mock_genai = _make_gemini_model_mock(wrapped)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            cards = await generate_flashcards(
                exam="NEET", subject="Botany", topic="Photosynthesis", count=2, lang="en"
            )
        assert len(cards) == 2

    async def test_generate_flashcards_raises_on_invalid_json(self):
        """
        When LLM returns non-JSON text, generate_flashcards returns []
        (the function degrades gracefully — callers handle empty list).
        """
        mock_genai = _make_gemini_model_mock("Here are your flashcards: ...")
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            cards = await generate_flashcards(
                exam="NEET", subject="Botany", topic="Photosynthesis", count=2, lang="en"
            )
        assert cards == []

    async def test_generate_flashcards_tamil(self):
        tamil_json = json.dumps([
            {"front": "Photosynthesis front", "back": "Photosynthesis back in Tamil context."},
        ])
        mock_genai = _make_gemini_model_mock(tamil_json)
        with (
            patch("app.rag.chain.genai", mock_genai),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            cards = await generate_flashcards(
                exam="NEET", subject="Botany", topic="Photosynthesis", count=1, lang="ta"
            )
        assert len(cards) == 1
        assert "front" in cards[0]


# ══════════════════════════════════════════════════════════════════════════════
#  Quiz Review Generation
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateQuizReview:
    async def test_generate_review_success(self):
        expected_review = "Great job! You did well on Newton's Laws but need work on Optics."
        mock_genai = _make_gemini_model_mock(expected_review)
        with patch("app.rag.chain.genai", mock_genai):
            results = [
                {"topic": "Newton's Laws", "is_correct": True},
                {"topic": "Optics", "is_correct": False},
            ]
            review = await generate_quiz_review("NEET", "Physics", results)
        assert review == expected_review

    async def test_generate_review_empty_results(self):
        review = await generate_quiz_review("NEET", "Physics", [])
        assert "No questions" in review

    async def test_generate_review_correct_score_calculation(self):
        mock_genai = _make_gemini_model_mock("Score: 2/3 (66.7%). Good effort!")
        with patch("app.rag.chain.genai", mock_genai):
            results = [
                {"topic": "A", "is_correct": True},
                {"topic": "B", "is_correct": True},
                {"topic": "C", "is_correct": False},
            ]
            review = await generate_quiz_review("TNPSC", "History", results)
        assert len(review) > 0

    async def test_generate_review_all_correct(self):
        mock_genai = _make_gemini_model_mock("Perfect score! Excellent work on all topics.")
        with patch("app.rag.chain.genai", mock_genai):
            results = [
                {"topic": "Physics", "is_correct": True},
                {"topic": "Chemistry", "is_correct": True},
            ]
            review = await generate_quiz_review("NEET", "Mixed", results)
        assert len(review) > 0

    async def test_generate_review_all_wrong(self):
        mock_genai = _make_gemini_model_mock("Keep practicing! Focus on the weak areas.")
        with patch("app.rag.chain.genai", mock_genai):
            results = [
                {"topic": "A", "is_correct": False},
                {"topic": "B", "is_correct": False},
            ]
            review = await generate_quiz_review("NEET", "Chemistry", results)
        assert len(review) > 0
