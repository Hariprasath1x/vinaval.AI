from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from app.core import chroma

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
    def delete(self, ids: List[str]) -> None:
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

    def delete(self, ids: List[str]) -> None:
        self._collection.delete(ids=ids)

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


# Singleton instance
_store = ChromaVectorStore()

def get_vector_store() -> VectorStoreInterface:
    return _store
