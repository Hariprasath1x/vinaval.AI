"""
test_streaming_parser.py — Comprehensive unit & regression tests for the incremental JSON streaming parser.

Tests cover:
  1. Standard clean streaming of multiple JSON objects.
  2. Outer framing handling (Markdown code fences, outer array brackets, commas, whitespace).
  3. Braces inside quoted strings (both balanced and unmatched open/close braces).
  4. Escaped quotation marks (\\") and escaped backslashes (\\\\) inside strings.
  5. Arbitrary token chunk boundary fragmentation (token splits across escape sequences).
  6. Nested JSON objects and arrays within pedagogical items.
  7. Malformed JSON candidate recovery (logging warning, continuing to parse next object).
  8. Incomplete / truncated stream at EOF (depth > 0 warning, no crash).
  9. Integration verification with generate_mcqs_stream.
 10. Integration verification with generate_flashcards_stream.
"""
import pytest
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock

from app.rag.chain import (
    _parse_json_objects_stream,
    generate_mcqs_stream,
    generate_flashcards_stream,
)

pytestmark = pytest.mark.asyncio


async def _to_async_gen(chunks: list[str]) -> AsyncGenerator[str, None]:
    for chunk in chunks:
        yield chunk


class TestIncrementalJsonStreamParser:
    async def test_standard_clean_streaming_multiple_objects(self):
        """Parser extracts multiple JSON objects arriving in chunks."""
        chunks = [
            '[\n',
            '  {"question": "Q1", "option_a": "A", "correct_option": "a"},\n',
            '  {"question": "Q2", "option_a": "B", "correct_option": "b"}\n',
            ']'
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 2
        assert results[0]["question"] == "Q1"
        assert results[1]["question"] == "Q2"

    async def test_markdown_fences_and_outer_framing(self):
        """Parser ignores leading/trailing markdown code fences and array brackets."""
        chunks = [
            "```json\n[\n",
            '{"front": "Card 1", "back": "Answer 1"},\n',
            '{"front": "Card 2", "back": "Answer 2"}\n',
            "]\n```"
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 2
        assert results[0]["front"] == "Card 1"
        assert results[1]["front"] == "Card 2"

    async def test_braces_inside_strings_unmatched_close(self):
        """Unmatched closing braces inside strings must NOT prematurely terminate the object."""
        chunks = [
            '{"question": "Which emoticon has a closing brace? E.g. :}", "correct_option": "a"}\n',
            '{"question": "Standard question", "correct_option": "b"}'
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 2
        assert results[0]["question"] == "Which emoticon has a closing brace? E.g. :}"
        assert results[1]["question"] == "Standard question"

    async def test_braces_inside_strings_unmatched_open(self):
        """Unmatched opening braces inside strings must NOT corrupt subsequent object parsing."""
        chunks = [
            '{"question": "Which emoticon has an open brace? E.g. :{", "correct_option": "a"}\n',
            '{"question": "Next question", "correct_option": "b"}'
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 2
        assert results[0]["question"] == "Which emoticon has an open brace? E.g. :{"
        assert results[1]["question"] == "Next question"

    async def test_mathematical_set_and_latex_braces(self):
        """Mathematical formulas with braces in LaTeX or set notation must parse accurately."""
        chunks = [
            '{"question": "Let set S = \\\\{1, 2, 3\\\\}. Evaluate $\\\\frac{\\\\alpha}{\\\\beta}$", "option_a": "1"}'
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 1
        assert "S = \\{1, 2, 3\\}" in results[0]["question"]

    async def test_escaped_quotes_and_escaped_backslashes(self):
        """Escaped quotes (\\") must not exit strings; escaped backslashes (\\\\) must be preserved."""
        chunks = [
            '{"question": "He said \\"Physics is easy\\" to the class", "dir": "C:\\\\docs\\\\"}',
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 1
        assert results[0]["question"] == 'He said "Physics is easy" to the class'
        assert results[0]["dir"] == 'C:\\docs\\'

    async def test_nested_objects_and_arrays(self):
        """Nested dictionaries and arrays within items must parse with correct depth tracking."""
        chunks = [
            '{"question": "Q1", "metadata": {"difficulty": "hard", "tags": ["optics", "physics"]}, "ans": "a"}'
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 1
        assert results[0]["metadata"]["difficulty"] == "hard"
        assert results[0]["metadata"]["tags"] == ["optics", "physics"]

    async def test_chunk_fragmentation_across_escapes(self):
        """Token chunks split directly across escape sequences and syntax characters must parse."""
        chunks = [
            '{"question": "He said \\',
            '"hello\\',
            '" to me", "option',
            '_a": "A',
            '"}',
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 1
        assert results[0]["question"] == 'He said "hello" to me'
        assert results[0]["option_a"] == 'A'

    async def test_malformed_object_recovery(self, caplog):
        """Malformed JSON candidate logs an explicit warning and does not crash subsequent parsing."""
        chunks = [
            '{"question": incomplete_unquoted_value}\n',
            '{"question": "Valid Question", "correct_option": "c"}'
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 1
        assert results[0]["question"] == "Valid Question"
        assert any("[STREAM_PARSER] Failed to parse candidate JSON object" in r.message for r in caplog.records)

    async def test_incomplete_stream_at_eof_logging(self, caplog):
        """Stream terminating mid-object logs diagnostic warning with unclosed depth."""
        chunks = [
            '{"question": "Truncated at the very end'
        ]
        results = [obj async for obj in _parse_json_objects_stream(_to_async_gen(chunks))]
        assert len(results) == 0
        assert any("[STREAM_PARSER] Stream ended with unclosed JSON object (depth=1)" in r.message for r in caplog.records)


class TestStreamRoutesIntegration:
    async def test_generate_mcqs_stream_integration(self):
        """generate_mcqs_stream integrates seamlessly with _parse_json_objects_stream."""
        mock_chunks = [
            '[\n',
            '  {"question": "What is speed?", "option_a": "d/t", "option_b": "d*t", "option_c": "t/d", "option_d": "d+t", "correct_option": "a", "explanation": "v=d/t"}\n',
            ']'
        ]
        with patch("app.rag.chain._llm_complete_stream", return_value=_to_async_gen(mock_chunks)), \
             patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)):
            items = [q async for q in generate_mcqs_stream("NEET", "Physics", count=1)]
            assert len(items) == 1
            assert items[0]["question"] == "What is speed?"
            assert items[0]["correct_option"] == "a"

    async def test_generate_flashcards_stream_integration(self):
        """generate_flashcards_stream integrates seamlessly with _parse_json_objects_stream."""
        mock_chunks = [
            '[\n',
            '  {"front": "Formula for kinetic energy?", "back": "1/2 m v^2"}\n',
            ']'
        ]
        with patch("app.rag.chain._llm_complete_stream", return_value=_to_async_gen(mock_chunks)), \
             patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)):
            items = [c async for c in generate_flashcards_stream("NEET", "Physics", topic="Kinematics", count=1)]
            assert len(items) == 1
            assert items[0]["front"] == "Formula for kinetic energy?"
            assert items[0]["back"] == "1/2 m v^2"
