"""
ChromaDB client and collection management for Vinaval AI RAG pipeline.
Uses a persistent local store so embeddings survive server restarts.

Multilingual Support
--------------------
Embedding model: paraphrase-multilingual-MiniLM-L12-v2
  - Supports 50+ languages including Tamil and English.
  - Produces semantically aligned embeddings across both languages,
    meaning a Tamil query will surface relevant English chunks and vice-versa.
  - Still lightweight (12-layer MiniLM) and CPU-friendly.

Collection naming convention:
  (exam, subject)          → "{exam}_{subject}"          e.g. "neet_physics"
  (exam, subject, lang)    → "{exam}_{subject}_{lang}"   e.g. "neet_physics_ta"

Books are seeded with an explicit --lang flag (e.g. "en" or "ta").
Both collections are queried at retrieval time for maximum coverage.
"""
from __future__ import annotations
from typing import Optional, List, Any
import logging
import os

logger = logging.getLogger(__name__)

from app.core.config import get_settings as _get_settings
_settings = _get_settings()

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False
    chromadb = None
    Settings = None
    embedding_functions = None

# ChromaDB persistence directory: configurable via CHROMA_PERSIST_DIR env var.
# Default resolves to <backend_root>/chroma_db where the pre-built RAG data lives.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_configured_dir = _settings.CHROMA_PERSIST_DIR
CHROMA_PATH = (
    _configured_dir
    if os.path.isabs(_configured_dir)
    else os.path.join(_BACKEND_DIR, _configured_dir.lstrip("./\\"))
)

# ── Multilingual Embedding Model ───────────────────────────────────────────────
# paraphrase-multilingual-MiniLM-L12-v2:
#   • Supports Tamil (ta), English (en), and 50+ other languages.
#   • Semantic similarity is cross-lingual: Tamil query ↔ English document works.
#   • ~120 MB download on first use; cached locally after that.
_embedding_function: Optional[Any] = None

def get_embedding_function():
    global _embedding_function
    if not HAS_CHROMA:
        return None
    if _embedding_function is None:
        logger.info("[STARTUP] Initializing embedding model...")
        try:
            _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(  # type: ignore
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
            logger.info("ChromaDB: using multilingual embedding model (paraphrase-multilingual-MiniLM-L12-v2)")
        except Exception as e:
            logger.warning("Failed to load multilingual model, falling back to MiniLM-L6: %s", e)
            _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(  # type: ignore
                model_name="all-MiniLM-L6-v2"
            )
    return _embedding_function

_client: Optional[Any] = None


# ── Client ─────────────────────────────────────────────────────────────────────

def get_chroma_client():
    if not HAS_CHROMA:
        raise RuntimeError(
            "ChromaDB is not installed. RAG features are unavailable. "
            "Run: pip install chromadb"
        )
    global _client
    if _client is None:
        logger.info("[STARTUP] Initializing ChromaDB PersistentClient...")
        _client = chromadb.PersistentClient(  # type: ignore
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),  # type: ignore
        )
    return _client


# ── Collection helpers ─────────────────────────────────────────────────────────

def _collection_name(exam: str, subject: str, lang: str | None = None) -> str:
    """
    Build a safe ChromaDB collection name.

    Examples:
        ("NEET", "Physics")        → "neet_physics"
        ("NEET", "Physics", "en")  → "neet_physics_en"
        ("NEET", "Physics", "ta")  → "neet_physics_ta"
    """
    base = f"{exam}_{subject}".lower().replace(" ", "_").replace("-", "_")
    if lang:
        return f"{base}_{lang.lower().strip()}"
    return base


def get_collection(exam: str, subject: str, lang: str | None = None):
    """
    Retrieve or create a ChromaDB collection.

    Args:
        exam:    e.g. "NEET" or "TNPSC"
        subject: e.g. "Physics" or "History"
        lang:    Optional language code — "en", "ta", or None (language-agnostic).
                 Pass None to get the legacy / mixed collection.
    """
    client = get_chroma_client()
    name = _collection_name(exam, subject, lang)
    return client.get_or_create_collection(
        name=name,
        embedding_function=get_embedding_function(),
    )


def list_all_collections() -> List[str]:
    """Return a list of all existing collection names."""
    client = get_chroma_client()
    return [col.name for col in client.list_collections()]


def get_collections_for_subject(exam: str, subject: str) -> list:
    """
    Return all existing collections that match a given exam+subject across all
    languages. Used during retrieval to search English and Tamil books together.

    Returns a list of chromadb.Collection objects (may be empty).
    """
    client = get_chroma_client()
    prefix = _collection_name(exam, subject)  # e.g. "neet_physics"
    all_names = [col.name for col in client.list_collections()]
    matched = [n for n in all_names if n == prefix or n.startswith(prefix + "_")]
    collections = []
    for name in matched:
        try:
            col = client.get_collection(name=name, embedding_function=get_embedding_function())
            if col.count() > 0:
                collections.append(col)
        except Exception as exc:
            logger.warning("Could not open collection %s: %s", name, exc)
    return collections


# ── Deletion helper ────────────────────────────────────────────────────────────

def delete_document_chunks(exam: str, subject: str, doc_id: int, lang: str | None = None) -> int:
    """
    Remove all ChromaDB chunks that were indexed for a specific document.
    Chunks are stored with metadata key 'doc_id'.

    If lang is provided, only the specific language collection is searched.
    If lang is None (default), all language-variant collections for this
    exam+subject are searched — needed for user uploads which are indexed
    into language-specific collections based on auto-detection.

    Returns the number of chunks deleted.
    """
    try:
        if lang is not None:
            # Target a specific collection (e.g. when seeding/deleting a known-language book)
            collections_to_search = [get_collection(exam, subject, lang)]
        else:
            # Search all language variants — covers en, ta, and legacy mixed
            collections_to_search = get_collections_for_subject(exam, subject)
            # Also include the legacy mixed collection in case it has chunks
            try:
                legacy = get_collection(exam, subject, None)
                if legacy.count() > 0 and legacy not in collections_to_search:
                    collections_to_search.append(legacy)
            except Exception:
                pass

        total_deleted = 0
        for collection in collections_to_search:
            try:
                results = collection.get(where={"doc_id": doc_id})
                ids = results.get("ids", [])
                if ids:
                    collection.delete(ids=ids)
                    total_deleted += len(ids)
            except Exception:
                pass
        return total_deleted
    except Exception:
        return 0
