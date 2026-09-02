"""
conftest.py — Shared pytest fixtures for Vinaval AI backend tests.

IMPORTANT: We mock out chromadb and sentence_transformers BEFORE any app
modules are imported. This prevents the SentenceTransformer model (~120 MB)
from loading during tests, keeping the test suite fast and offline.
"""
from __future__ import annotations

import sys
import types
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

# ── Block heavy imports BEFORE any app code is loaded ─────────────────────────
# Intercept chromadb and sentence_transformers at the module level so the
# SentenceTransformer model is never downloaded or instantiated.
_mock_chroma = MagicMock()
_mock_st = MagicMock()
sys.modules.setdefault("chromadb", _mock_chroma)
sys.modules.setdefault("chromadb.config", _mock_chroma.config)
sys.modules.setdefault("chromadb.utils", _mock_chroma.utils)
sys.modules.setdefault("chromadb.utils.embedding_functions", _mock_chroma.utils.embedding_functions)
sys.modules.setdefault("sentence_transformers", _mock_st)

# Also mock firebase_admin, google.generativeai, and pinecone
_mock_firebase = MagicMock()
sys.modules.setdefault("firebase_admin", _mock_firebase)
sys.modules.setdefault("firebase_admin.credentials", _mock_firebase.credentials)
sys.modules.setdefault("firebase_admin.auth", _mock_firebase.auth)

_mock_genai = MagicMock()
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.generativeai", _mock_genai)

_mock_pinecone = MagicMock()
sys.modules.setdefault("pinecone", _mock_pinecone)

import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-testing-min-32-chars-long")
os.environ.setdefault("GROQ_API_KEY", "test-groq-api-key")

# ── Now it is safe to import app modules ──────────────────────────────────────
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base, get_db
from app.core.dependencies import get_current_user
from app.main import create_app


# ── In-memory SQLite engine ────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a shared in-memory async SQLite engine for the whole test session."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ── DB session (per test, rolled back after each test) ────────────────────────

@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a per-test async session that is completely isolated.
    Uses nested transactions (SAVEPOINTs) so that even if a test calls commit(),
    the outer transaction is rolled back at the end of the test.
    """
    async with engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()
        TestSessionLocal = async_sessionmaker(
            bind=conn, class_=AsyncSession, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with TestSessionLocal() as session:
            yield session
        await conn.rollback()


# ── Mock authenticated user ────────────────────────────────────────────────────

@pytest.fixture
def mock_user():
    """
    Synthetic user object for injection as the current authenticated user.
    Uses SimpleNamespace to avoid SQLAlchemy ORM descriptor issues.
    """
    return types.SimpleNamespace(
        id=1,
        email="testuser@vinaval.ai",
        name="Test Student",
        hashed_password=None,
        google_id=None,
        selected_exam="NEET",
    )


# ── Mock Learning Space ────────────────────────────────────────────────────────

@pytest.fixture
def mock_space():
    """
    Synthetic learning space for testing quiz endpoints.
    Uses SimpleNamespace to avoid SQLAlchemy ORM descriptor issues.
    """
    return types.SimpleNamespace(
        id=1,
        user_id=1,
        exam_id="NEET",
        subject="Physics",
        title="Physics Space",
    )


# ── FastAPI async test client ──────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, mock_user) -> AsyncGenerator[AsyncClient, None]:
    """
    Yield an httpx.AsyncClient pointed at the FastAPI app.

    Dependency overrides:
    - `get_db`           → yields the isolated in-memory test session
    - `get_current_user` → returns mock_user (bypasses JWT validation)
    """
    app = create_app()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Mock Embedding Readiness ───────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def mock_embedding_readiness():
    """Ensure embedding readiness state is initialized and set for tests, bypassing real background initialization."""
    from app.core.chroma import init_embedding_readiness_state
    import app.core.chroma as chroma
    init_embedding_readiness_state()
    if chroma._embedding_ready_event:
        chroma._embedding_ready_event.set()
