"""
test_rag_chain.py — Unit tests for app.rag.chain functions.

Tests:
  - generate_mcqs        : correct JSON parsing, mock exam mode, error handling
  - generate_flashcards  : correct parsing, invalid JSON handling
  - generate_quiz_review : correct review text generation, empty results edge case
  - _detect_lang         : language detection heuristic
  - _retrieve_syllabus_context    : graceful fallback when ChromaDB is unavailable
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
)



# ── Helper ─────────────────────────────────────────────────────────────────────

def _mock_groq_response(content: str):
    """Create a minimal mock that looks like a Groq ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ══════════════════════════════════════════════════════════════════════════════
#  Language Detection
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectLang:
    def test_english_text_returns_en(self):
        assert _detect_lang("What is Newton's first law?") == "en"

    def test_tamil_text_returns_ta(self):
        # Tamil Unicode block: U+0B80–U+0BFF
        tamil = "நியூட்டனின் முதல் விதி என்ன?"
        assert _detect_lang(tamil) == "ta"

    def test_empty_string_returns_en(self):
        assert _detect_lang("") == "en"

    def test_mixed_mostly_english_returns_en(self):
        # This string has a ratio of Tamil chars well below the 3% threshold
        # (0 Tamil chars in a pure English string) — should remain 'en'
        assert _detect_lang("Hello world English only") == "en"


# ══════════════════════════════════════════════════════════════════════════════
#  ChromaDB Retrieval Fallback
# ══════════════════════════════════════════════════════════════════════════════

class TestRetrieveContext:
    def test_returns_empty_when_chromadb_raises(self):
        """If get_collections_for_subject raises an exception, _retrieve_syllabus_context returns empty."""
        with patch(
            "app.core.chroma.get_collections_for_subject",
            side_effect=Exception("ChromaDB not running"),
        ):
            context, n = _retrieve_syllabus_context("NEET", "Physics", "gravity", n_results=4)
        # Should gracefully return empty context
        assert context == ""
        assert n == 0

    def test_returns_empty_when_no_collections(self):
        """If no collections are found for exam+subject, return empty context."""
        with patch(
            "app.core.chroma.get_collections_for_subject",
            return_value=[],
        ):
            context, n = _retrieve_syllabus_context("NEET", "Botany", "cell division", n_results=4)
        assert context == ""
        assert n == 0


# ══════════════════════════════════════════════════════════════════════════════
#  MCQ Generation
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
        "option_b": "F = kq₁q₂/r²",
        "option_c": "F = mv",
        "option_d": "F = qE",
        "correct_option": "b",
        "explanation": "Coulomb's law defines the electrostatic force between two charges.",
    },
])


class TestGenerateMCQs:
    async def test_generate_practice_questions(self):
        """generate_mcqs with a topic returns correctly parsed question dicts."""
        mock_resp = _mock_groq_response(VALID_MCQ_JSON)

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            questions = await generate_mcqs(
                exam="NEET",
                subject="Physics",
                topic="Newton's Laws",
                count=1,
                lang="en",
            )

        assert isinstance(questions, list)
        assert len(questions) == 1
        q = questions[0]
        assert q["topic"] == "Newton's Laws"
        assert q["correct_option"] == "a"
        assert "explanation" in q

    async def test_generate_mock_exam_no_topic(self):
        """generate_mcqs with topic=None triggers mock exam, spanning multiple topics."""
        mock_resp = _mock_groq_response(VALID_MOCK_EXAM_JSON)

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            questions = await generate_mcqs(
                exam="NEET",
                subject="Physics",
                topic=None,
                count=2,
                lang="en",
            )

        assert len(questions) == 2
        topics = {q["topic"] for q in questions}
        assert "Thermodynamics" in topics
        assert "Electrostatics" in topics

    async def test_generate_mcqs_strips_markdown_code_fences(self):
        """generate_mcqs should correctly strip ```json ... ``` fences from LLM output."""
        wrapped = f"```json\n{VALID_MCQ_JSON}\n```"
        mock_resp = _mock_groq_response(wrapped)

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic="Inertia", count=1, lang="en"
            )

        assert len(questions) == 1

    async def test_generate_mcqs_raises_on_invalid_json(self):
        """generate_mcqs should raise ValueError when LLM returns non-JSON."""
        mock_resp = _mock_groq_response("Sorry, I cannot generate questions right now.")

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            with pytest.raises(ValueError, match="invalid JSON"):
                await generate_mcqs(
                    exam="NEET", subject="Physics", topic="Gravity", count=1, lang="en"
                )

    async def test_generate_mcqs_raises_when_not_a_list(self):
        """generate_mcqs should raise ValueError when LLM returns a JSON object, not array."""
        mock_resp = _mock_groq_response('{"error": "no questions"}')

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            with pytest.raises(ValueError, match="JSON array"):
                await generate_mcqs(
                    exam="NEET", subject="Physics", topic="Gravity", count=1, lang="en"
                )

    async def test_generate_mcqs_tamil_language(self):
        """generate_mcqs with lang='ta' passes Tamil instruction to the LLM."""
        tamil_json = json.dumps([{
            "topic": "ஒளியியல் (Optics)",
            "question": "ஒளியின் வேகம் என்ன?",
            "option_a": "3 × 10⁸ m/s",
            "option_b": "3 × 10⁶ m/s",
            "option_c": "3 × 10⁴ m/s",
            "option_d": "1 × 10⁸ m/s",
            "correct_option": "a",
            "explanation": "ஒளியின் வேகம் வெற்றிடத்தில் 3 × 10⁸ m/s ஆகும்.",
        }])
        mock_resp = _mock_groq_response(tamil_json)

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            questions = await generate_mcqs(
                exam="NEET", subject="Physics", topic="Optics", count=1, lang="ta"
            )

        assert len(questions) == 1
        # Verify the prompt contained Tamil instruction by checking call args
        call_args = mock_client.chat.completions.create.call_args
        prompt_content = call_args[1]["messages"][0]["content"]
        assert "Tamil" in prompt_content


# ══════════════════════════════════════════════════════════════════════════════
#  Flashcard Generation
# ══════════════════════════════════════════════════════════════════════════════

VALID_FLASHCARD_JSON = json.dumps([
    {"front": "What is photosynthesis?", "back": "The process by which plants convert sunlight into glucose."},
    {"front": "What is ATP?", "back": "Adenosine triphosphate — the energy currency of the cell."},
])


class TestGenerateFlashcards:
    async def test_generate_flashcards_success(self):
        """generate_flashcards returns correctly parsed front/back pairs."""
        mock_resp = _mock_groq_response(VALID_FLASHCARD_JSON)

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            cards = await generate_flashcards(
                exam="NEET", subject="Botany", topic="Photosynthesis", count=2, lang="en"
            )

        assert isinstance(cards, list)
        assert len(cards) == 2
        assert "front" in cards[0]
        assert "back" in cards[0]

    async def test_generate_flashcards_strips_code_fences(self):
        """generate_flashcards strips markdown fences from LLM output."""
        wrapped = f"```\n{VALID_FLASHCARD_JSON}\n```"
        mock_resp = _mock_groq_response(wrapped)

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            cards = await generate_flashcards(
                exam="NEET", subject="Botany", topic="Photosynthesis", count=2, lang="en"
            )

        assert len(cards) == 2

    async def test_generate_flashcards_raises_on_invalid_json(self):
        """generate_flashcards raises ValueError for non-JSON LLM output."""
        mock_resp = _mock_groq_response("Here are your flashcards: ...")

        with (
            patch("app.rag.chain.AsyncGroq") as mock_cls,
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            with pytest.raises(ValueError, match="invalid JSON"):
                await generate_flashcards(
                    exam="NEET", subject="Botany", topic="Photosynthesis", count=2, lang="en"
                )


# ══════════════════════════════════════════════════════════════════════════════
#  Quiz Review Generation
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateQuizReview:
    async def test_generate_review_success(self):
        """generate_quiz_review returns the LLM-generated review string."""
        expected_review = "Great job! You did well on Newton's Laws but need work on Optics."
        mock_resp = _mock_groq_response(expected_review)

        with patch("app.rag.chain.AsyncGroq") as mock_cls:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            results = [
                {"topic": "Newton's Laws", "is_correct": True},
                {"topic": "Optics", "is_correct": False},
            ]
            review = await generate_quiz_review("NEET", "Physics", results)

        assert review == expected_review

    async def test_generate_review_empty_results(self):
        """generate_quiz_review returns a fallback message for empty result list."""
        review = await generate_quiz_review("NEET", "Physics", [])
        assert "No questions" in review

    async def test_generate_review_correct_score_calculation(self):
        """generate_quiz_review correctly calculates score/percentage in the prompt."""
        mock_resp = _mock_groq_response("Score: 2/3 (66.7%). Good effort!")

        with patch("app.rag.chain.AsyncGroq") as mock_cls:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            results = [
                {"topic": "A", "is_correct": True},
                {"topic": "B", "is_correct": True},
                {"topic": "C", "is_correct": False},
            ]
            review = await generate_quiz_review("TNPSC", "History", results)

        # Verify the prompt was built with the correct score
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "2/3" in prompt
        assert "66.7" in prompt
