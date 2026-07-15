"""
ChromaDB client and collection management for Vinaval AI RAG pipeline.
Uses a persistent local store so embeddings survive server restarts.
"""
from __future__ import annotations
from typing import Optional
import os
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Store ChromaDB persistently in the backend root directory
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CHROMA_PATH = os.path.join(_BACKEND_DIR, "chroma_db")

# Lightweight CPU-friendly embedding model
_embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection(exam: str, subject: str) -> chromadb.Collection:
    """
    Retrieves or creates a ChromaDB collection keyed by exam+subject.
    Example: ("NEET", "Physics") → collection name "neet_physics".
    """
    client = get_chroma_client()
    safe_name = f"{exam}_{subject}".lower().replace(" ", "_").replace("-", "_")
    return client.get_or_create_collection(
        name=safe_name,
        embedding_function=_embedding_function,
    )


def delete_document_chunks(exam: str, subject: str, document_id: int) -> int:
    """
    Remove all ChromaDB chunks that were indexed for a specific document.
    Chunks are stored with metadata key 'document_id'.
    Returns the number of chunks deleted.
    """
    try:
        collection = get_collection(exam, subject)
        results = collection.get(where={"document_id": document_id})
        ids = results.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0
