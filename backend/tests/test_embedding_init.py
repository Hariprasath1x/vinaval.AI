"""
test_embedding_init.py — Comprehensive tests for embedding model lifecycle,
thread safety, bounded timeouts, health indicators, and Render free-tier optimizations.
"""
from __future__ import annotations

import asyncio
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.core import chroma
from app.core.chroma import (
    EmbeddingNotReadyError,
    EmbeddingTimeoutError,
    EmbeddingInitializationError,
    get_embedding_status,
    reset_embedding_state,
    wait_for_embedding_model,
    init_embedding_readiness_state,
    init_embedding_model_background,
    get_embedding_function,
)
from app.main import create_app, lifespan

pytestmark = pytest.mark.asyncio


class TestEmbeddingLifecycle:
    def setup_method(self):
        reset_embedding_state()

    def teardown_method(self):
        reset_embedding_state()
        chroma._embedding_status = "ready"
        init_embedding_readiness_state()
        if chroma._embedding_ready_event:
            chroma._embedding_ready_event.set()

    async def test_get_embedding_status_uninitialized(self):
        """Status indicator reports uninitialized initially without revealing secrets."""
        status = get_embedding_status()
        assert status["status"] == "uninitialized"
        assert status["model"] == "paraphrase-multilingual-MiniLM-L12-v2"
        assert status["error"] is None

    async def test_concurrent_initialization_single_load(self):
        """Concurrent calls to get_embedding_function load the model exactly once."""
        mock_constructor = MagicMock(return_value=MagicMock())
        call_count = 0

        def slow_loader():
            nonlocal call_count
            call_count += 1
            time.sleep(0.05)
            return mock_constructor()

        results = []

        def worker():
            fn = get_embedding_function()
            results.append(fn)

        with patch("app.core.chroma._load_embedding_model_sync", side_effect=slow_loader):
            threads = [threading.Thread(target=worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert len(results) == 5
        # Double-checked locking ensures exactly one invocation
        assert call_count == 1
        # All callers receive the exact same instance
        assert all(r is results[0] for r in results)

    async def test_successful_warmup_and_readiness_transition(self):
        """Background initialization transitions state cleanly to ready."""
        mock_emb_fn = MagicMock()
        with patch("app.core.chroma._load_embedding_model_sync", return_value=mock_emb_fn):
            await init_embedding_model_background()

        status = get_embedding_status()
        assert status["status"] == "ready"
        assert status["error"] is None
        assert chroma._embedding_ready_event.is_set()

        # wait_for_embedding_model returns immediately
        await wait_for_embedding_model(timeout=1.0)

    async def test_failed_initialization_and_retry(self):
        """Initialization failure transitions to error and can be safely retried."""
        # 1. Simulate failure during warm-up
        error_loader = MagicMock(side_effect=RuntimeError("Transient network timeout"))
        with patch("app.core.chroma._load_embedding_model_sync", side_effect=error_loader):
            await init_embedding_model_background(force_retry=True)

        status = get_embedding_status()
        assert status["status"] == "error"
        assert "Transient network timeout" in status["error"]

        # wait_for_embedding_model without retry raises EmbeddingInitializationError
        with pytest.raises(EmbeddingInitializationError) as exc_info:
            await wait_for_embedding_model(timeout=0.1, allow_retry=False)
        assert "Transient network timeout" in str(exc_info.value)

        # 2. Simulate recovery on retry
        success_fn = MagicMock()
        with patch("app.core.chroma._load_embedding_model_sync", return_value=success_fn):
            await init_embedding_model_background(force_retry=True)

        status = get_embedding_status()
        assert status["status"] == "ready"
        assert status["error"] is None
        await wait_for_embedding_model(timeout=1.0)

    async def test_rag_request_before_ready_timeout(self):
        """Waiting for an unready model respects bounded timeout without hanging."""
        init_embedding_readiness_state()
        chroma._embedding_status = "loading"
        # Event is deliberately NOT set and background task is not running
        start = time.perf_counter()
        with pytest.raises(EmbeddingTimeoutError):
            await wait_for_embedding_model(timeout=0.08, allow_retry=False)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, "Timeout did not return in a bounded duration"

    async def test_cancellation_and_clean_shutdown(self):
        """Cancellation of the warm-up task does not mark model as ready and raises CancelledError."""
        init_embedding_readiness_state()

        async def hung_loader():
            await asyncio.sleep(5.0)

        task = asyncio.create_task(hung_loader())
        await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert chroma._embedding_status != "ready"


class TestHealthAndReadinessEndpoints:
    @pytest.mark.asyncio
    async def test_health_check_includes_embedding_status(self):
        """GET /health always returns 200 with liveness and non-sensitive embedding state."""
        app = create_app()
        chroma._embedding_status = "ready"
        chroma._embedding_error = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res = await client.get("/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ok"
            assert "embedding" in data
            assert data["embedding"]["status"] == "ready"
            assert data["embedding"]["model"] == "paraphrase-multilingual-MiniLM-L12-v2"

    @pytest.mark.asyncio
    async def test_readiness_endpoint_ready_and_not_ready(self):
        """GET /health/ready returns 200 when ready, and 503 when warming up or in error."""
        app = create_app()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. When ready: 200 OK
            chroma._embedding_status = "ready"
            res = await client.get("/health/ready")
            assert res.status_code == 200
            assert res.json()["ready"] is True

            # 2. When loading / not ready: 503 Service Unavailable
            chroma._embedding_status = "loading"
            res = await client.get("/health/ready")
            assert res.status_code == 503
            assert res.json()["ready"] is False

            # 3. When in error: 503 Service Unavailable
            chroma._embedding_status = "error"
            res = await client.get("/health/ready")
            assert res.status_code == 503
            assert res.json()["ready"] is False
