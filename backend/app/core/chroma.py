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

# Store ChromaDB persistently in the backend root directory
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CHROMA_PATH = os.path.join(_BACKEND_DIR, "chroma_db")

# ── Multilingual Embedding Model ───────────────────────────────────────────────
# paraphrase-multilingual-MiniLM-L12-v2:
#   • Supports Tamil (ta), English (en), and 50+ other languages.
#   • Semantic similarity is cross-lingual: Tamil query ↔ English document works.
#   • ~120 MB download on first use; cached locally after that.
if HAS_CHROMA:
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
else:
    _embedding_function = None

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
        embedding_function=_embedding_function,
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
            col = client.get_collection(name=name, embedding_function=_embedding_function)
            if col.count() > 0:
                collections.append(col)
        except Exception as exc:
            logger.warning("Could not open collection %s: %s", name, exc)
    return collections


# ── Deletion helper ────────────────────────────────────────────────────────────

def delete_document_chunks(exam: str, subject: str, doc_id: int, lang: str | None = None) -> int:
    """
    Remove all ChromaDB chunks that were indexed for a specific document.
    Chunks are stored with metadata key 'document_id'.
    Returns the number of chunks deleted.
    """
    try:
        collection = get_collection(exam, subject, lang)
        results = collection.get(where={"doc_id": doc_id})
        ids = results.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0
