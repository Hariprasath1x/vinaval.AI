import pytest
from unittest.mock import patch, MagicMock

from app.core import vector_store
from app.core.config import Settings

@pytest.fixture
def mock_pinecone():
    with patch("app.core.vector_store.Pinecone") as mock_pc_class:
        mock_pc_instance = MagicMock()
        mock_pc_class.return_value = mock_pc_instance
        yield mock_pc_instance

@pytest.fixture
def clean_vector_store():
    # Reset singleton before and after test
    vector_store._store = None
    yield
    vector_store._store = None

def test_provider_selection_chroma(clean_vector_store):
    with patch("app.core.vector_store.get_settings") as mock_settings:
        mock_s = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db", SECRET_KEY="test", GROQ_API_KEY="test")
        mock_s.VECTOR_STORE_PROVIDER = "chroma"
        mock_settings.return_value = mock_s

        store = vector_store.get_vector_store()
        assert isinstance(store, vector_store.ChromaVectorStore)

def test_provider_selection_pinecone(clean_vector_store, mock_pinecone):
    with patch("app.core.vector_store.get_settings") as mock_settings:
        mock_s = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db", SECRET_KEY="test", GROQ_API_KEY="test")
        mock_s.VECTOR_STORE_PROVIDER = "pinecone"
        mock_s.PINECONE_API_KEY = "test_key"
        mock_s.PINECONE_INDEX_NAME = "test_index"
        mock_settings.return_value = mock_s

        mock_index = MagicMock()
        mock_index.name = "test_index"
        mock_pinecone.list_indexes.return_value = [mock_index]

        store = vector_store.get_vector_store()
        assert isinstance(store, vector_store.PineconeVectorStore)

def test_missing_pinecone_api_key(clean_vector_store):
    with patch("app.core.vector_store.get_settings") as mock_settings:
        mock_s = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db", SECRET_KEY="test", GROQ_API_KEY="test")
        mock_s.VECTOR_STORE_PROVIDER = "pinecone"
        mock_s.PINECONE_API_KEY = None
        mock_s.PINECONE_INDEX_NAME = "test_index"
        mock_settings.return_value = mock_s

        with pytest.raises(ValueError, match="Pinecone configuration is missing"):
            vector_store.get_vector_store()

def test_missing_pinecone_index_configuration(clean_vector_store):
    with patch("app.core.vector_store.get_settings") as mock_settings:
        mock_s = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db", SECRET_KEY="test", GROQ_API_KEY="test")
        mock_s.VECTOR_STORE_PROVIDER = "pinecone"
        mock_s.PINECONE_API_KEY = "test_key"
        mock_s.PINECONE_INDEX_NAME = None
        mock_settings.return_value = mock_s

        with pytest.raises(ValueError, match="Pinecone configuration is missing"):
            vector_store.get_vector_store()

def test_pinecone_index_does_not_exist_in_cloud(clean_vector_store, mock_pinecone):
    with patch("app.core.vector_store.get_settings") as mock_settings:
        mock_s = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db", SECRET_KEY="test", GROQ_API_KEY="test")
        mock_s.VECTOR_STORE_PROVIDER = "pinecone"
        mock_s.PINECONE_API_KEY = "test_key"
        mock_s.PINECONE_INDEX_NAME = "my_new_index"
        mock_settings.return_value = mock_s

        # Simulate empty list of indexes
        mock_pinecone.list_indexes.return_value = []

        with pytest.raises(ValueError, match="Pinecone index 'my_new_index' does not exist"):
            vector_store.get_vector_store()

def test_namespace_mapping(clean_vector_store, mock_pinecone):
    with patch("app.core.vector_store.get_settings") as mock_settings:
        mock_s = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db", SECRET_KEY="test", GROQ_API_KEY="test")
        mock_s.VECTOR_STORE_PROVIDER = "pinecone"
        mock_s.PINECONE_API_KEY = "test_key"
        mock_s.PINECONE_INDEX_NAME = "test_index"
        mock_settings.return_value = mock_s

        mock_index = MagicMock()
        mock_index.name = "test_index"
        mock_pinecone.list_indexes.return_value = [mock_index]

        store = vector_store.get_vector_store()
        col = store.get_collection("neet", "physics", "en")
        assert col.name == "neet_physics_en"

        col = store.get_collection_by_name("tnpsc_history")
        assert col.name == "tnpsc_history"

def test_query_request_mapping():
    mock_index = MagicMock()
    col = vector_store.PineconeVectorCollection(mock_index, "neet_physics_en")

    with patch("app.core.chroma.get_embedding_function") as mock_get_emb:
        mock_emb_fn = MagicMock()
        mock_emb_fn.return_value = [[0.1, 0.2, 0.3]]
        mock_get_emb.return_value = mock_emb_fn

        mock_match = MagicMock()
        mock_match.metadata = {"text": "dummy text", "doc_id": 123}
        mock_match.score = 0.95

        mock_response = MagicMock()
        mock_response.matches = [mock_match]
        mock_index.query.return_value = mock_response

        res = col.query(["test query"], n_results=5, where={"lang": "en"})

        mock_index.query.assert_called_once_with(
            namespace="neet_physics_en",
            vector=[0.1, 0.2, 0.3],
            top_k=5,
            filter={"lang": "en"},
            include_metadata=True,
            include_values=False
        )

        assert res == {
            "documents": [["dummy text"]],
            "metadatas": [[{"doc_id": 123}]],
            "distances": [[0.95]]
        }

def test_upsert_payload_construction():
    mock_index = MagicMock()
    col = vector_store.PineconeVectorCollection(mock_index, "neet_physics_en")

    with patch("app.core.chroma.get_embedding_function") as mock_get_emb:
        mock_emb_fn = MagicMock()
        mock_emb_fn.return_value = [[0.1], [0.2]]
        mock_get_emb.return_value = mock_emb_fn

        col.upsert(
            documents=["doc1", "doc2"],
            metadatas=[{"doc_id": 1}, {"doc_id": 2}],
            ids=["id1", "id2"]
        )

        mock_index.upsert.assert_called_once()
        call_args = mock_index.upsert.call_args[1]
        assert call_args["namespace"] == "neet_physics_en"
        vectors = call_args["vectors"]
        assert len(vectors) == 2
        assert vectors[0] == ("id1", [0.1], {"doc_id": 1, "text": "doc1"})
        assert vectors[1] == ("id2", [0.2], {"doc_id": 2, "text": "doc2"})

def test_delete_by_id_mapping():
    mock_index = MagicMock()
    col = vector_store.PineconeVectorCollection(mock_index, "neet_physics_en")

    col.delete(ids=["id1", "id2"])

    mock_index.delete.assert_called_once_with(ids=["id1", "id2"], namespace="neet_physics_en")

def test_delete_by_where_mapping():
    mock_index = MagicMock()
    col = vector_store.PineconeVectorCollection(mock_index, "neet_physics_en")

    col.delete(where={"doc_id": 123})

    mock_index.delete.assert_called_once_with(filter={"doc_id": 123}, namespace="neet_physics_en")

def test_chroma_delete_mapping():
    mock_chroma_col = MagicMock()
    col = vector_store.ChromaVectorCollection(mock_chroma_col)

    col.delete(ids=["id1"], where={"doc_id": 123})
    mock_chroma_col.delete.assert_called_once_with(ids=["id1"], where={"doc_id": 123})

def test_count_mapping():
    mock_index = MagicMock()
    mock_index.describe_index_stats.return_value = {
        "namespaces": {
            "neet_physics_en": {"vector_count": 42}
        }
    }
    col = vector_store.PineconeVectorCollection(mock_index, "neet_physics_en")

    count = col.count()
    assert count == 42

    # Missing namespace should return 0
    col2 = vector_store.PineconeVectorCollection(mock_index, "missing_ns")
    assert col2.count() == 0

def test_collection_discovery(clean_vector_store, mock_pinecone):
    with patch("app.core.vector_store.get_settings") as mock_settings:
        mock_s = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db", SECRET_KEY="test", GROQ_API_KEY="test")
        mock_s.VECTOR_STORE_PROVIDER = "pinecone"
        mock_s.PINECONE_API_KEY = "test_key"
        mock_s.PINECONE_INDEX_NAME = "test_index"
        mock_settings.return_value = mock_s

        mock_index = MagicMock()
        mock_index.name = "test_index"
        mock_pinecone.list_indexes.return_value = [mock_index]

        store = vector_store.get_vector_store()

        # We need to patch the internal _index to mock describe_index_stats
        mock_idx = MagicMock()
        mock_idx.describe_index_stats.return_value = {
            "namespaces": {
                "neet_physics_en": {"vector_count": 10},
                "neet_physics_ta": {"vector_count": 5},
                "tnpsc_history_en": {"vector_count": 1}
            }
        }
        store._index = mock_idx

        # Test list_collections
        cols = store.list_collections()
        assert set(cols) == {"neet_physics_en", "neet_physics_ta", "tnpsc_history_en"}

        # Test get_collections_for_subject
        physics_cols = store.get_collections_for_subject("neet", "physics")
        assert len(physics_cols) == 2
        names = {c.name for c in physics_cols}
        assert names == {"neet_physics_en", "neet_physics_ta"}
