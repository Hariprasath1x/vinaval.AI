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
from typing import Optional, List, Any, Dict
import logging
import os
import time
import threading
import asyncio

logger = logging.getLogger(__name__)

from app.core.config import get_settings as _get_settings
_settings = _get_settings()

logger.info("[RAG] Importing chromadb")
try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    HAS_CHROMA = True
    logger.info("[RAG] chromadb import completed")
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

# ── Exception classes ─────────────────────────────────────────────────────────

class EmbeddingNotReadyError(RuntimeError):
    """Raised when an embedding operation is requested before the model is ready."""
    pass


class EmbeddingTimeoutError(EmbeddingNotReadyError):
    """Raised when waiting for the embedding model to initialize exceeds the timeout."""
    pass


class EmbeddingInitializationError(EmbeddingNotReadyError):
    """Raised when the embedding model initialization encounters an unrecoverable error."""
    pass


# ── Multilingual Embedding Model ───────────────────────────────────────────────
# paraphrase-multilingual-MiniLM-L12-v2:
#   • Supports Tamil (ta), English (en), and 50+ other languages.
#   • Semantic similarity is cross-lingual: Tamil query ↔ English document works.
#   • Produces 384-dimensional dense vectors compatible with both Chroma and Pinecone.
#   • Initialized asynchronously in background with bounded timeout and retry safety.
_embedding_function: Optional[Any] = None
_embedding_status: str = "uninitialized"  # "uninitialized" | "loading" | "ready" | "error"
_embedding_error: Optional[str] = None
_embedding_ready_event: Optional[asyncio.Event] = None
_init_lock = threading.Lock()


def get_embedding_status() -> Dict[str, Any]:
    """Return lightweight, sanitized status of the embedding model."""
    return {
        "status": _embedding_status,
        "model": "paraphrase-multilingual-MiniLM-L12-v2",
        "error": _embedding_error,
    }


def reset_embedding_state():
    """Reset embedding state (used primarily in tests and recovery)."""
    global _embedding_function, _embedding_status, _embedding_error, _embedding_ready_event
    with _init_lock:
        _embedding_function = None
        _embedding_status = "uninitialized"
        _embedding_error = None
        _embedding_ready_event = None


def _load_embedding_model_sync():
    """
    Synchronously load the SentenceTransformer model with single-thread CPU constraints.
    """
    global _embedding_function, _embedding_status, _embedding_error

    _embedding_status = "loading"
    logger.info("[EMBED] Initializing embedding model model=paraphrase-multilingual-MiniLM-L12-v2")
    start = time.perf_counter()

    # Constrain PyTorch thread contention on memory/CPU-constrained environments (e.g. Render 0.15 CPU)
    try:
        import torch
        torch.set_num_threads(1)
    except Exception:
        pass

    try:
        if HAS_CHROMA and embedding_functions is not None:
            fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
        else:
            try:
                from sentence_transformers import SentenceTransformer
                st_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
                class _DirectSTEmbeddingFunction:
                    def __init__(self, model):
                        self._model = model
                    def __call__(self, input: list[str]) -> list[list[float]]:
                        embeddings = self._model.encode(list(input), normalize_embeddings=False)
                        return embeddings.tolist()
                fn = _DirectSTEmbeddingFunction(st_model)
            except ImportError as imp_err:
                raise RuntimeError("Neither chromadb nor sentence-transformers is available for embeddings.") from imp_err

        # Free transient buffers created during weight loading
        try:
            import gc
            gc.collect()
        except Exception:
            pass

        elapsed_ms = (time.perf_counter() - start) * 1000
        _embedding_status = "ready"
        _embedding_error = None
        _embedding_function = fn
        logger.info(f"[EMBED] Embedding model initialized successfully elapsed_ms={elapsed_ms:.2f}")
        return fn
    except Exception as e:
        _embedding_status = "error"
        _embedding_error = f"{type(e).__name__}: {str(e)}"
        logger.exception(f"[EMBED] Embedding model initialization FAILED exception_type={type(e).__name__} exception={str(e)}")
        raise


def get_embedding_function():
    """
    Return the shared embedding model function.
    Loads synchronously with double-checked thread lock if not yet initialized.
    """
    global _embedding_function
    if _embedding_function is not None:
        return _embedding_function

    with _init_lock:
        if _embedding_function is not None:
            return _embedding_function
        _embedding_function = _load_embedding_model_sync()
        return _embedding_function


def init_embedding_readiness_state():
    """Initialize the asyncio.Event used to coordinate background warm-up."""
    global _embedding_ready_event
    if _embedding_ready_event is None:
        _embedding_ready_event = asyncio.Event()
        if _embedding_status == "ready":
            _embedding_ready_event.set()


async def init_embedding_model_background(force_retry: bool = False):
    """
    Background warm-up task. Offloads synchronous model loading to a worker thread
    so FastAPI startup and the event loop are never blocked.
    """
    global _embedding_ready_event, _embedding_error, _embedding_status, _embedding_function

    init_embedding_readiness_state()

    if _embedding_status == "ready" and not force_retry:
        if _embedding_ready_event and not _embedding_ready_event.is_set():
            _embedding_ready_event.set()
        return

    if _embedding_status == "loading" and not force_retry:
        return

    _embedding_status = "loading"
    _embedding_error = None

    try:
        fn = await asyncio.to_thread(get_embedding_function)
        _embedding_function = fn
        _embedding_status = "ready"
        _embedding_error = None
        if _embedding_ready_event:
            _embedding_ready_event.set()
    except asyncio.CancelledError:
        logger.info("[EMBED] Background embedding warm-up was cancelled.")
        if _embedding_status != "ready":
            _embedding_status = "uninitialized"
        raise
    except Exception as e:
        _embedding_status = "error"
        _embedding_error = f"{type(e).__name__}: {str(e)}"
        if _embedding_ready_event:
            _embedding_ready_event.set()  # Unblock waiters so they receive the error instead of hanging


async def wait_for_embedding_model(timeout: float = 15.0, allow_retry: bool = True):
    """
    Wait for the embedding model to be ready with a bounded timeout.
    Prevents RAG requests from hanging indefinitely or silently using an uninitialized model.
    """
    global _embedding_ready_event, _embedding_status, _embedding_error

    if _embedding_status == "ready":
        return

    init_embedding_readiness_state()

    # If uninitialized or previous error with retry allowed, start warm-up task
    if _embedding_status == "uninitialized" or (_embedding_status == "error" and allow_retry):
        if _embedding_ready_event:
            _embedding_ready_event.clear()
        asyncio.create_task(init_embedding_model_background(force_retry=True))

    # Wait for the event with a bounded timeout
    try:
        await asyncio.wait_for(_embedding_ready_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        raise EmbeddingTimeoutError(
            f"Embedding model initialization timed out after {timeout:.1f}s. Please retry shortly."
        )

    if _embedding_status == "error" or _embedding_error is not None:
        raise EmbeddingInitializationError(
            f"Embedding model initialization failed: {_embedding_error}"
        )


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
        base_path = os.path.basename(CHROMA_PATH.rstrip("/\\"))

        try:
            import resource
            before_rss = f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.2f}"
        except ImportError:
            before_rss = "N/A"

        logger.info(f"[RAG] About to initialize Chroma PersistentClient path={base_path} rss_mb={before_rss}")
        start = time.perf_counter()
        try:
            _client = chromadb.PersistentClient(  # type: ignore
                path=CHROMA_PATH,
                settings=Settings(anonymized_telemetry=False),  # type: ignore
            )
        except Exception as e:
            logger.exception("[RAG] Chroma PersistentClient initialization failed")
            raise

        elapsed = (time.perf_counter() - start) * 1000
        try:
            import resource
            after_rss = f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.2f}"
        except ImportError:
            after_rss = "N/A"

        logger.info(f"[RAG] Chroma PersistentClient initialized successfully elapsed_ms={elapsed:.2f} rss_mb={after_rss}")
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
