"""
retrieval_log.py — Structured retrieval diagnostics for Vinaval AI
Writes one JSON line per chat request to backend/logs/retrieval.log
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_PATH = os.path.join(_LOG_DIR, "retrieval.log")

_file_logger = logging.getLogger("vinaval.retrieval")
_file_logger.setLevel(logging.INFO)
_file_logger.propagate = False  # don't pollute the root logger

if not _file_logger.handlers:
    fh = logging.FileHandler(_LOG_PATH, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(message)s"))
    _file_logger.addHandler(fh)


def log_retrieval(
    *,
    space_id: int,
    active_doc_id: int | None,
    intent: str,
    chunks_retrieved: int,
    topics_used: int,
    retrieval_ms: float,
    llm_started: bool = True,
) -> None:
    """Write one structured log line per query."""
    record = {
        "ts":              datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "space_id":        space_id,
        "active_doc_id":   active_doc_id,
        "intent":          intent,
        "chunks_retrieved": chunks_retrieved,
        "topics_used":     topics_used,
        "retrieval_ms":    round(retrieval_ms, 1),
        "llm_started":     llm_started,
    }
    _file_logger.info(json.dumps(record, ensure_ascii=False))
