import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from app.core import chroma
from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None


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
        col = chroma.get_collection(exam, subject, lang)
        return ChromaVectorCollection(col)

    def get_collections_for_subject(self, exam: str, subject: str) -> List[VectorCollectionInterface]:
        cols = chroma.get_collections_for_subject(exam, subject)
        return [ChromaVectorCollection(col) for col in cols]

    def list_collections(self) -> List[str]:
        return chroma.list_all_collections()

    def get_collection_by_name(self, name: str) -> VectorCollectionInterface:
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
    def __init__(self, index, namespace: str):
        self._index = index
        self._namespace = namespace

    @property
    def name(self) -> str:
        return self._namespace

    def query(self, query_texts: List[str], n_results: int, where: Optional[Dict] = None) -> Dict[str, Any]:
        if not query_texts:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        embedding_function = chroma.get_embedding_function()
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

        embedding_function = chroma.get_embedding_function()
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
        name = chroma._collection_name(exam, subject, lang)
        return PineconeVectorCollection(self._index, name)

    def get_collections_for_subject(self, exam: str, subject: str) -> List[VectorCollectionInterface]:
        prefix = chroma._collection_name(exam, subject)
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
            logger.info("[VECTOR] Provider=chroma")
            _store = ChromaVectorStore()
    return _store
