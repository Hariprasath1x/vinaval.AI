"""
test_pinecone_memory_isolation.py — Comprehensive tests verifying:
1. Pinecone mode does NOT initialize local Sentence Transformers/PyTorch/ChromaDB on startup.
2. Chroma mode continues to function normally with background warm-up.
3. Health and readiness endpoints accurately report provider-specific status and memory RSS.
4. Firebase authentication endpoint handles unconfigured/invalid states safely without 500 or secret leakage.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport

from app.core import chroma, vector_store
from app.core.config import Settings
from app.core.firebase import FirebaseNotConfiguredError
from app.main import create_app, lifespan

pytestmark = pytest.mark.asyncio


class TestPineconeIsolation:
    async def test_pinecone_mode_startup_does_not_initialize_chroma_model(self):
        """In Pinecone mode, application lifespan must not launch the heavy Chroma warm-up task."""
        mock_settings = Settings(
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
            SECRET_KEY="test_secret",
            VECTOR_STORE_PROVIDER="pinecone",
            PINECONE_API_KEY="test_key",
            PINECONE_INDEX_NAME="vinavalai-rag",
        )

        with patch("app.main.settings", mock_settings), \
             patch("app.core.config.get_settings", return_value=mock_settings), \
             patch("app.core.vector_store.get_settings", return_value=mock_settings), \
             patch("app.core.vector_store.Pinecone") as mock_pc_cls, \
             patch("app.core.chroma.init_embedding_model_background") as mock_warmup, \
             patch("app.core.chroma._load_embedding_model_sync") as mock_loader:

            # Mock Pinecone index existence
            mock_idx = MagicMock()
            mock_idx.name = "vinavalai-rag"
            mock_pc_inst = MagicMock()
            mock_pc_inst.list_indexes.return_value = [mock_idx]
            mock_pc_cls.return_value = mock_pc_inst

            vector_store._store = None
            app = create_app()

            async with lifespan(app):
                # Verify that Chroma's heavy warm-up task was NEVER invoked
                assert mock_warmup.call_count == 0, "Chroma warm-up should NOT be called in Pinecone mode"
                assert mock_loader.call_count == 0, "Chroma sync loader should NOT be called in Pinecone mode"

            vector_store._store = None

    async def test_chroma_mode_startup_launches_warmup(self):
        """In Chroma mode, application lifespan launches the background warm-up task."""
        mock_settings = Settings(
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
            SECRET_KEY="test_secret",
            VECTOR_STORE_PROVIDER="chroma",
        )

        with patch("app.main.settings", mock_settings), \
             patch("app.core.config.get_settings", return_value=mock_settings), \
             patch("app.core.chroma.init_embedding_model_background") as mock_warmup:

            # Make mock_warmup an async mock
            mock_warmup.return_value = asyncio.sleep(0)

            app = create_app()
            async with lifespan(app):
                assert mock_warmup.call_count == 1, "Chroma warm-up should be called when provider=chroma"

    async def test_pinecone_health_and_readiness_endpoints(self):
        """Health check returns provider=pinecone and readiness check returns 200 when configured."""
        mock_settings = Settings(
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
            SECRET_KEY="test_secret",
            VECTOR_STORE_PROVIDER="pinecone",
            PINECONE_API_KEY="test_api_key",
            PINECONE_INDEX_NAME="vinavalai-rag",
        )

        with patch("app.main.settings", mock_settings), \
             patch("app.core.config.get_settings", return_value=mock_settings):

            app = create_app()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                # /health endpoint
                health_res = await client.get("/health")
                assert health_res.status_code == 200
                data = health_res.json()
                assert data["status"] == "ok"
                assert data["provider"] == "pinecone"
                assert data["embedding"]["provider"] == "pinecone"
                assert data["embedding"]["status"] == "ready"
                assert data["embedding"]["index"] == "vinavalai-rag"
                assert data["embedding"]["dimension"] == 384
                assert "memory_rss_mb" in data

                # /health/ready endpoint
                ready_res = await client.get("/health/ready")
                assert ready_res.status_code == 200
                ready_data = ready_res.json()
                assert ready_data["ready"] is True
                assert ready_data["provider"] == "pinecone"

    async def test_pinecone_unconfigured_readiness_fails_with_503(self):
        """When Pinecone is selected but unconfigured, /health/ready must return 503 Service Unavailable."""
        mock_settings = Settings(
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
            SECRET_KEY="test_secret",
            VECTOR_STORE_PROVIDER="pinecone",
            PINECONE_API_KEY=None,
            PINECONE_INDEX_NAME=None,
        )

        with patch("app.main.settings", mock_settings), \
             patch("app.core.config.get_settings", return_value=mock_settings):

            app = create_app()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                ready_res = await client.get("/health/ready")
                assert ready_res.status_code == 503
                ready_data = ready_res.json()
                assert ready_data["ready"] is False
                assert ready_data["provider"] == "pinecone"
                assert ready_data["embedding"]["status"] == "unconfigured"


    async def test_pinecone_query_uses_lightweight_embedding_without_chroma(self):
        """In Pinecone mode, collection queries use the lightweight embedding client without loading Chroma or SentenceTransformer."""
        mock_settings = Settings(
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
            SECRET_KEY="test_secret",
            VECTOR_STORE_PROVIDER="pinecone",
            PINECONE_API_KEY="test_key",
            PINECONE_INDEX_NAME="vinavalai-rag",
        )

        mock_index = MagicMock()
        mock_match = MagicMock()
        mock_match.metadata = {"text": "Tamil Nadu Physics content", "doc_id": 1}
        mock_match.score = 0.98
        mock_response = MagicMock()
        mock_response.matches = [mock_match]
        mock_index.query.return_value = mock_response

        col = vector_store.PineconeVectorCollection(mock_index, "neet_physics_ta")

        # Mock the huggingface_hub client feature_extraction method
        mock_hf_client = MagicMock()
        mock_hf_client.feature_extraction.return_value = [0.05] * 384

        with patch("app.core.vector_store.get_settings", return_value=mock_settings), \
             patch("huggingface_hub.InferenceClient", return_value=mock_hf_client), \
             patch("app.core.chroma._load_embedding_model_sync") as mock_chroma_load:

            res = col.query(["நியூட்டனின் இரண்டாம் விதி"], n_results=3)

            assert mock_chroma_load.call_count == 0, "Chroma local model loader should NOT be called"
            assert mock_hf_client.feature_extraction.call_count == 1
            call_args = mock_hf_client.feature_extraction.call_args
            assert call_args[0][0] == "நியூட்டனின் இரண்டாம் விதி"
            assert call_args[1]["model"] == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

            assert len(res["documents"][0]) == 1
            assert res["documents"][0][0] == "Tamil Nadu Physics content"

    async def test_stream_chat_in_pinecone_mode_does_not_wait_for_chroma(self):
        """In Pinecone mode, stream_chat does not call wait_for_embedding_model."""
        from unittest.mock import AsyncMock

        mock_settings = Settings(
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
            SECRET_KEY="test_secret",
            VECTOR_STORE_PROVIDER="pinecone",
            GEMINI_API_KEY="dummy_gemini",
        )

        mock_chunk = MagicMock()
        mock_chunk.text = "Test response chunk"

        async def dummy_stream_gen():
            yield mock_chunk

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=dummy_stream_gen())

        with patch("app.rag.chain.settings", mock_settings), \
             patch("app.core.chroma.wait_for_embedding_model") as mock_wait, \
             patch("app.rag.chain._retrieve_syllabus_context", return_value=("Mock syllabus context", 1)), \
             patch("google.generativeai.GenerativeModel", return_value=mock_model):

            from app.rag.chain import stream_chat
            chunks = []
            async for chunk in stream_chat(
                exam="NEET",
                subject="Physics",
                history=[],
                user_message="What is velocity?",
            ):
                chunks.append(chunk)

            assert mock_wait.call_count == 0, "wait_for_embedding_model should NOT be called in Pinecone mode"
            assert "Test response chunk" in "".join(chunks)


class TestFirebaseAuthEndpointSafety:
    async def test_firebase_login_missing_token_returns_400(self):
        """Calling /api/v1/auth/firebase with empty token returns 400 Bad Request."""
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.post("/api/v1/auth/firebase", json={"id_token": "   "})
            assert res.status_code == 400
            assert "ID token is required" in res.json()["detail"]

    async def test_firebase_login_unconfigured_returns_503_not_500(self):
        """Calling /api/v1/auth/firebase when Firebase is unconfigured returns 503 Service Unavailable."""
        app = create_app()
        with patch("app.services.auth_service.verify_firebase_token", side_effect=FirebaseNotConfiguredError("Unconfigured")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                res = await client.post("/api/v1/auth/firebase", json={"id_token": "dummy_token_123"})
                assert res.status_code == 503
                assert "not configured" in res.json()["detail"]

    async def test_firebase_login_invalid_token_returns_401(self):
        """Calling /api/v1/auth/firebase with invalid token returns 401 Unauthorized without exposing tokens."""
        app = create_app()
        with patch("app.services.auth_service.verify_firebase_token", side_effect=ValueError("Invalid or expired Firebase token")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                res = await client.post("/api/v1/auth/firebase", json={"id_token": "expired_token_xyz"})
                assert res.status_code == 401
                assert "Invalid" in res.json()["detail"] or "expired" in res.json()["detail"]
                # Verify token itself is NOT in the response
                assert "expired_token_xyz" not in res.text

    async def test_firebase_login_missing_email_returns_401(self):
        """When Firebase token has no email associated, returns 401 with informative error."""
        app = create_app()
        with patch("app.services.auth_service.verify_firebase_token", return_value={"uid": "u123", "email": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                res = await client.post("/api/v1/auth/firebase", json={"id_token": "token_without_email"})
                assert res.status_code == 401
                assert "email" in res.text.lower()
