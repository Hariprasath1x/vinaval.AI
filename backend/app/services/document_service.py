"""
document_service.py — User Document Processing for Vinaval AI
=============================================================

Phase 1 — Text Extraction (PDF via PyMuPDF, TXT direct)
Phase 2 — Topic/Heading Extraction (heuristic — no LLM call needed)
Phase 3 — Semantic Chunking: split on topic boundaries, carry rich metadata
Phase 4 — Index enriched chunks into ChromaDB (language-aware collection)
Phase 5 — Persist extracted topics + chunk count to SpaceDocument SQL row
"""
from __future__ import annotations

import os
import re
import uuid
from typing import List, Dict, Any

import fitz  # PyMuPDF

from app.core.chroma import get_collection

# ── Tamil language heuristic (mirrors the one in chain.py) ───────────────────
_TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")


def _detect_lang(text: str) -> str:
    """Return 'ta' if >5% of characters are Tamil Unicode, else 'en'."""
    if not text:
        return "en"
    ratio = len(_TAMIL_RE.findall(text)) / max(len(text), 1)
    return "ta" if ratio > 0.05 else "en"


# ── Topic / Heading Extractor ─────────────────────────────────────────────────

def _extract_topics(text: str) -> List[str]:
    """
    Heuristic heading detector — works on plain text and simple PDFs.

    A line is considered a heading/topic if ALL of the following are true:
      - Length between 3 and 80 characters
      - Does not end with a period (not a sentence)
      - Not purely numeric
      - Preceded OR followed by a blank line (or is at start/end of file)
      - Not an obvious metadata line (Page, Copyright, www, http)

    Returns a deduplicated ordered list of detected topic strings.
    """
    lines = text.splitlines()
    n = len(lines)
    topics: List[str] = []
    seen: set = set()

    skip_patterns = re.compile(
        r"^(page\s*\d+|www\.|http|copyright|©|\d+\s*$)",
        re.IGNORECASE,
    )

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) < 3 or len(stripped) > 80:
            continue
        if stripped.endswith("."):
            continue
        if re.fullmatch(r"[\d\s\.\-,]+", stripped):
            continue
        if skip_patterns.match(stripped):
            continue

        prev_blank = (i == 0) or (lines[i - 1].strip() == "")
        next_blank = (i == n - 1) or (lines[i + 1].strip() == "")

        if prev_blank or next_blank:
            key = stripped.lower()
            if key not in seen:
                seen.add(key)
                topics.append(stripped)

    return topics


# ── Semantic Chunker ──────────────────────────────────────────────────────────

def _semantic_chunks(
    text: str,
    topics: List[str],
    chunk_size: int = 2500,
    chunk_overlap: int = 400,
) -> List[Dict[str, Any]]:
    """
    Split text into semantic chunks:
      1. Try to split on topic/heading boundaries first.
      2. Fall back to paragraph-aware fixed-size chunks if no boundaries found.

    Each chunk dict contains:
      text       : the chunk content
      topic      : nearest detected heading (or "" if unknown)
      chunk_index: position within document
    """
    # Build regex from detected topics to find section boundaries
    topic_pattern = None
    if topics:
        escaped = [re.escape(t) for t in topics]
        topic_pattern = re.compile(
            r"(?:^|\n)\s*(?:" + "|".join(escaped) + r")\s*(?:\n|$)",
            re.IGNORECASE,
        )

    raw_chunks: List[Dict[str, Any]] = []

    if topic_pattern and topic_pattern.search(text):
        # Split on detected headings
        parts = topic_pattern.split(text)
        headings = topic_pattern.findall(text)
        # parts[0] is preamble; parts[1..] correspond to headings
        if parts[0].strip():
            raw_chunks.append({"text": parts[0].strip(), "topic": ""})
        for heading, part in zip(headings, parts[1:]):
            topic_label = heading.strip()
            if part.strip():
                raw_chunks.append({"text": part.strip(), "topic": topic_label})
    else:
        # No headings detected — fall back to paragraph-aware fixed-size chunks
        raw_chunks = _fallback_chunks(text, chunk_size, chunk_overlap)

    # Now further split any chunk that exceeds chunk_size
    final: List[Dict[str, Any]] = []
    for raw in raw_chunks:
        content = raw["text"]
        if len(content) <= chunk_size:
            final.append(raw)
        else:
            # Sub-split large sections
            sub = _fallback_chunks(content, chunk_size, chunk_overlap)
            for s in sub:
                s["topic"] = raw["topic"]
                final.append(s)

    # Assign sequential indices
    for idx, chunk in enumerate(final):
        chunk["chunk_index"] = idx

    return final


def _fallback_chunks(
    text: str, chunk_size: int = 2500, chunk_overlap: int = 400
) -> List[Dict[str, Any]]:
    """Fixed-size paragraph-aware chunker — identical to original logic."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        bp = text.rfind("\n", start, end)
        if bp == -1 or bp <= start + chunk_size // 2:
            bp = text.rfind(". ", start, end)
        if bp == -1 or bp <= start + chunk_size // 2:
            bp = end
        else:
            bp += 1
        chunks.append(text[start:bp].strip())
        start = bp - chunk_overlap
        if start < 0:
            start = 0
        if len(chunks) > 1 and start <= (end - chunk_size):
            start = bp
    return [{"text": c, "topic": ""} for c in chunks if c]


# ── Main Service ──────────────────────────────────────────────────────────────

class DocumentService:
    def __init__(self):
        pass

    async def process_and_index_document(
        self,
        file_path: str,
        exam: str,
        subject: str,
        doc_id: int,
    ) -> Dict[str, Any]:
        """
        Full pipeline:
          1. Extract text from PDF or TXT.
          2. Extract topic/heading list.
          3. Create semantic chunks with rich metadata.
          4. Index into ChromaDB (language-aware collection).
          5. Return stats: { pages, chunk_count, topics, lang }.

        The caller (document.py router) is responsible for persisting
        topics and chunk_count into the SpaceDocument SQL row.
        """
        text = ""
        pages = 0
        ext = os.path.splitext(file_path)[1].lower()

        # ── Text extraction ───────────────────────────────────────────────────
        if ext == ".pdf":
            try:
                doc = fitz.open(file_path)
                pages = len(doc)
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()
            except Exception as e:
                raise ValueError(f"Failed to read PDF: {e}")

        elif ext == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except Exception as e:
                raise ValueError(f"Failed to read TXT: {e}")
            pages = text.count("\n\n") + 1  # rough estimate for TXT
        else:
            raise ValueError("Unsupported file type")

        if not text.strip():
            raise ValueError("Extracted text is empty")

        # ── Language detection ────────────────────────────────────────────────
        lang = _detect_lang(text)

        # ── Topic extraction ──────────────────────────────────────────────────
        topics = _extract_topics(text)

        # ── Semantic chunking ─────────────────────────────────────────────────
        chunk_dicts = _semantic_chunks(text, topics)
        if not chunk_dicts:
            raise ValueError("No chunks created from text")

        filename = os.path.basename(file_path)

        # ── Index into ChromaDB ───────────────────────────────────────────────
        collection = get_collection(exam, subject, lang)

        ids = [f"{doc_id}_{c['chunk_index']}_{uuid.uuid4().hex[:8]}" for c in chunk_dicts]
        metadatas = [
            {
                "source":      "user_upload",
                "exam":        exam,
                "subject":     subject,
                "lang":        lang,
                "book_title":  filename,
                "doc_id":      doc_id,
                "chunk_index": c["chunk_index"],
                "topic":       c.get("topic", ""),
            }
            for c in chunk_dicts
        ]
        documents = [c["text"] for c in chunk_dicts]

        batch_size = 100
        for i in range(0, len(documents), batch_size):
            collection.add(
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
                ids=ids[i : i + batch_size],
            )

        return {
            "pages":       pages,
            "chunk_count": len(chunk_dicts),
            "topics":      topics,
            "lang":        lang,
        }
