import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None


def build_collection_name(exam: str, subject: str, lang: Optional[str] = None) -> str:
    """
    Build a standard collection/namespace name.
    Examples:
        ("NEET", "Physics")        → "neet_physics"
        ("NEET", "Physics", "en")  → "neet_physics_en"
        ("NEET", "Physics", "ta")  → "neet_physics_ta"
    """
    base = f"{exam}_{subject}".lower().replace(" ", "_").replace("-", "_")
    if lang:
        return f"{base}_{lang.lower().strip()}"
    return base


class HuggingFaceInferenceEmbedding:
    """
    Lightweight serverless embedding client for 384-dimensional
    paraphrase-multilingual-MiniLM-L12-v2 vectors without loading
    in-process PyTorch/SentenceTransformers (~50MB vs ~1.13GB).
    Preserves exact 384-dimensional semantic space for Tamil/English RAG.
    """
    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        token: Optional[str] = None,
    ):
        self.model_name = model_name
        self.token = token
        self._client = None

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import InferenceClient
            settings = get_settings()
            token = self.token or getattr(settings, "HF_TOKEN", None) or getattr(settings, "HUGGINGFACE_API_KEY", None)
            self._client = InferenceClient(token=token)
        return self._client

    def __call__(self, input_texts: List[str]) -> List[List[float]]:
        if not input_texts:
            return []
        client = self._get_client()
        embeddings = []
        for text in input_texts:
            cleaned = text.strip() if text else ""
            if not cleaned:
                embeddings.append([0.0] * 384)
                continue
            res = client.feature_extraction(cleaned, model=self.model_name)
            if hasattr(res, "tolist"):
                res = res.tolist()
            if isinstance(res, list) and len(res) > 0 and isinstance(res[0], list):
                embeddings.append(res[0])
            elif isinstance(res, list):
                embeddings.append(res)
            else:
                embeddings.append(list(res))
        return embeddings


class VectorCollectionInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def query(self, query_texts: List[str], n_results: int, where: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Query the collection.
        Expected return shape:
        {
            "documents": [[...]],
            "metadatas": [[...]],
            "distances": [[...]]
        }
        """
        pass

    @abstractmethod
    def get(self, where: Optional[Dict] = None, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Retrieve chunks matching metadata filters.
        Expected return shape:
        {
            "ids": [...],
            "documents": [...],
            "metadatas": [...]
        }
        """
        pass

    @abstractmethod
    def add(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> None:
        pass

    @abstractmethod
    def upsert(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> None:
        pass

    @abstractmethod
    def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    def count(self) -> int:
        pass


class VectorStoreInterface(ABC):
    @abstractmethod
    def get_collection(self, exam: str, subject: str, lang: Optional[str] = None) -> VectorCollectionInterface:
        pass

    @abstractmethod
    def get_collections_for_subject(self, exam: str, subject: str) -> List[VectorCollectionInterface]:
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        pass

    @abstractmethod
    def get_collection_by_name(self, name: str) -> VectorCollectionInterface:
        pass


class ChromaVectorCollection(VectorCollectionInterface):
    """
    Adapter for a chromadb.Collection.
    Delegates operations and preserves exact return structures.
    """
    def __init__(self, chroma_collection):
        self._collection = chroma_collection

    @property
    def name(self) -> str:
        return self._collection.name

    def query(self, query_texts: List[str], n_results: int, where: Optional[Dict] = None) -> Dict[str, Any]:
        kwargs = {"query_texts": query_texts, "n_results": n_results}
        if where is not None:
            kwargs["where"] = where
        return self._collection.query(**kwargs)

    def get(self, where: Optional[Dict] = None, include: Optional[List[str]] = None) -> Dict[str, Any]:
        kwargs = {}
        if where is not None:
            kwargs["where"] = where
        if include is not None:
            kwargs["include"] = include
        return self._collection.get(**kwargs)

    def add(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> None:
        self._collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def upsert(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> None:
        self._collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> None:
        kwargs = {}
        if ids is not None:
            kwargs["ids"] = ids
        if where is not None:
            kwargs["where"] = where
        if kwargs:
            self._collection.delete(**kwargs)

    def count(self) -> int:
        return self._collection.count()


class ChromaVectorStore(VectorStoreInterface):
    """
    Adapter mapping VectorStoreInterface to the existing chroma.py functionality.
    """
    def get_collection(self, exam: str, subject: str, lang: Optional[str] = None) -> VectorCollectionInterface:
        from app.core import chroma
        col = chroma.get_collection(exam, subject, lang)
        return ChromaVectorCollection(col)

    def get_collections_for_subject(self, exam: str, subject: str) -> List[VectorCollectionInterface]:
        from app.core import chroma
        cols = chroma.get_collections_for_subject(exam, subject)
        return [ChromaVectorCollection(col) for col in cols]

    def list_collections(self) -> List[str]:
        from app.core import chroma
        return chroma.list_all_collections()

    def get_collection_by_name(self, name: str) -> VectorCollectionInterface:
        from app.core import chroma
        client = chroma.get_chroma_client()
        # Retrieve the collection using the existing embedding function
        # so that implicit embedding behavior is preserved.
        col = client.get_collection(name=name, embedding_function=chroma.get_embedding_function())
        return ChromaVectorCollection(col)


class PineconeVectorCollection(VectorCollectionInterface):
    """
    Adapter for a Pinecone namespace.
    Delegates operations and maps Pinecone responses to Chroma-expected structures.
    """
    def __init__(self, index, namespace: str, embedding_function: Optional[Any] = None):
        self._index = index
        self._namespace = namespace
        self._embedding_function = embedding_function

    @property
    def name(self) -> str:
        return self._namespace

    def _get_embedding_function(self):
        if self._embedding_function is not None:
            return self._embedding_function

        # 1. If Chroma's embedding function was patched in tests or already initialized, respect it
        try:
            from app.core import chroma
            if getattr(chroma, "_embedding_function", None) is not None:
                return chroma._embedding_function
            from unittest.mock import Mock
            if isinstance(chroma.get_embedding_function, Mock):
                mock_fn = chroma.get_embedding_function()
                if mock_fn is not None:
                    return mock_fn
        except Exception:
            pass

        # 2. In Pinecone mode (e.g. Render 512MB free tier), use lightweight serverless client
        settings = get_settings()
        if getattr(settings, "VECTOR_STORE_PROVIDER", "chroma").lower() == "pinecone":
            return HuggingFaceInferenceEmbedding()

        # 3. Fallback for Chroma / local development
        from app.core import chroma
        return chroma.get_embedding_function()

    def query(self, query_texts: List[str], n_results: int, where: Optional[Dict] = None) -> Dict[str, Any]:
        if not query_texts:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        embedding_function = self._get_embedding_function()
        if embedding_function is None:
            raise RuntimeError("Embedding function is not available.")
        embeddings = embedding_function(query_texts)

        results_documents = []
        results_metadatas = []
        results_distances = []

        for emb in embeddings:
            kwargs = {
                "namespace": self._namespace,
                "vector": emb,
                "top_k": n_results,
                "include_metadata": True,
                "include_values": False
            }
            if where:
                kwargs["filter"] = where

            response = self._index.query(**kwargs)

            docs = []
            metas = []
            dists = []

            for match in response.matches:
                meta = match.metadata or {}
                # Pop text so it's not duplicated in metadata returned to caller
                doc = meta.pop("text", "")
                docs.append(doc)
                metas.append(meta)
                dists.append(match.score)

            results_documents.append(docs)
            results_metadatas.append(metas)
            results_distances.append(dists)

        return {
            "documents": results_documents,
            "metadatas": results_metadatas,
            "distances": results_distances
        }

    def get(self, where: Optional[Dict] = None, include: Optional[List[str]] = None) -> Dict[str, Any]:
        # Pinecone cannot get by filter without a vector. We use a dummy vector.
        dummy_vector = [1e-5] * 384

        kwargs = {
            "namespace": self._namespace,
            "vector": dummy_vector,
            "top_k": 10000,
            "include_metadata": True,
            "include_values": False
        }
        if where:
            kwargs["filter"] = where

        response = self._index.query(**kwargs)

        ids = []
        docs = []
        metas = []

        for match in response.matches:
            ids.append(match.id)
            meta = match.metadata or {}
            doc = meta.pop("text", "")
            docs.append(doc)
            metas.append(meta)

        return {
            "ids": ids,
            "documents": docs,
            "metadatas": metas
        }

    def add(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> None:
        self.upsert(documents, metadatas, ids)

    def upsert(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> None:
        if not ids:
            return

        embedding_function = self._get_embedding_function()
        if embedding_function is None:
            raise RuntimeError("Embedding function is not available.")
        embeddings = embedding_function(documents)

        vectors_to_upsert = []
        for i in range(len(ids)):
            meta = dict(metadatas[i]) if metadatas and i < len(metadatas) else {}
            meta["text"] = documents[i]
            vectors_to_upsert.append((ids[i], embeddings[i], meta))

        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i+batch_size]
            self._index.upsert(vectors=batch, namespace=self._namespace)

    def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> None:
        if ids is not None and ids:
            self._index.delete(ids=ids, namespace=self._namespace)
        if where is not None:
            self._index.delete(filter=where, namespace=self._namespace)

    def count(self) -> int:
        stats = self._index.describe_index_stats()
        namespaces = stats.get("namespaces", {})
        ns_stats = namespaces.get(self._namespace, {})
        return ns_stats.get("vector_count", 0)


class PineconeVectorStore(VectorStoreInterface):
    """
    Adapter mapping VectorStoreInterface to Pinecone Serverless.
    """
    def __init__(self):
        settings = get_settings()
        api_key = settings.PINECONE_API_KEY
        index_name = settings.PINECONE_INDEX_NAME

        if not api_key or not index_name:
            raise ValueError(
                "Pinecone configuration is missing. "
                "Set PINECONE_API_KEY and PINECONE_INDEX_NAME in environment."
            )

        if Pinecone is None:
            raise ImportError("pinecone-client is not installed.")

        logger.info(f"[VECTOR] Provider=pinecone Initializing connection to index '{index_name}'")
        self._pc = Pinecone(api_key=api_key)
        self._index_name = index_name

        try:
            indexes = [idx.name for idx in self._pc.list_indexes()]
            if index_name not in indexes:
                raise ValueError(
                    f"Pinecone index '{index_name}' does not exist. "
                    "The index must be created separately before use."
                )
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            logger.warning(f"Failed to list indexes: {e}")

        self._index = self._pc.Index(index_name)

    def get_collection(self, exam: str, subject: str, lang: Optional[str] = None) -> VectorCollectionInterface:
        name = build_collection_name(exam, subject, lang)
        return PineconeVectorCollection(self._index, name)

    def get_collections_for_subject(self, exam: str, subject: str) -> List[VectorCollectionInterface]:
        prefix = build_collection_name(exam, subject)
        collections = []
        for name in self.list_collections():
            if name == prefix or name.startswith(prefix + "_"):
                collections.append(PineconeVectorCollection(self._index, name))
        return collections

    def list_collections(self) -> List[str]:
        stats = self._index.describe_index_stats()
        return list(stats.get("namespaces", {}).keys())

    def get_collection_by_name(self, name: str) -> VectorCollectionInterface:
        return PineconeVectorCollection(self._index, name)


# Backward-compatibility alias
_collection_name = build_collection_name


# Singleton instance
_store = None

def get_vector_store() -> VectorStoreInterface:
    global _store
    if _store is None:
        settings = get_settings()
        provider = getattr(settings, "VECTOR_STORE_PROVIDER", "chroma").lower()
        if provider == "pinecone":
            _store = PineconeVectorStore()
        else:
            if getattr(settings, "APP_ENV", "development") == "production":
                raise ValueError(
                    "Production requires VECTOR_STORE_PROVIDER=pinecone. "
                    f"Invalid provider found: '{provider}'. "
                    "Cannot silently fall back to local Chroma."
                )
            logger.info("[VECTOR] Provider=chroma")
            _store = ChromaVectorStore()
    return _store
