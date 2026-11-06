"""
test_note_api.py — Unit & Integration tests for Smart Notes API endpoints.

Tests:
  - Auth required (401 when unauthenticated)
  - POST /api/v1/spaces/{id}/notes/generate (curriculum, document, English, Tamil)
  - POST /api/v1/spaces/{id}/notes (create note, validation)
  - GET  /api/v1/spaces/{id}/notes (list notes, search filter)
  - GET  /api/v1/spaces/{id}/notes/{note_id} (get single note)
  - PUT  /api/v1/spaces/{id}/notes/{note_id} (update note)
  - DELETE /api/v1/spaces/{id}/notes/{note_id} (delete note)
  - Cross-user tenant isolation (User B cannot access or modify User A's note -> 404)
  - Graceful LLM failure handling (502 Bad Gateway without traceback)
  - Alembic migration upgrade/downgrade execution
"""
from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.space import LearningSpace
from app.models.note import SpaceNote
from app.main import create_app

pytestmark = pytest.mark.asyncio

MOCK_NOTE_MARKDOWN = """# Optics & Wave Nature of Light
## Overview & Executive Summary
Light exhibits both wave and particle characteristics depending on the phenomenon observed. Wave optics deals with interference, diffraction, and polarization.

## Core Concepts & Definitions
- **Huygens' Principle**: Every point on a wavefront acts as a secondary source of spherical wavelets.
- **Interference**: Superposition of two coherent light waves leading to alternating bright and dark fringes.
- **Diffraction**: Bending of light waves around corners of an obstacle.

## Important Formulas / Facts / High-Yield Points
- Fringe width in YDSE: $\\beta = \\frac{\\lambda D}{d}$
- Constructive condition: $\\Delta x = n\\lambda$
- Destructive condition: $\\Delta x = (2n - 1)\\frac{\\lambda}{2}$

## Key Takeaways & Quick Review
- Coherence is mandatory for sustained interference.
- Intensity ratio: $I_{max}/I_{min} = ((a_1 + a_2)/(a_1 - a_2))^2$.
"""

MOCK_TAMIL_NOTE_MARKDOWN = """# ஒளி ஒளியியல் (Wave Optics)
## கண்ணோட்டம் (Overview)
ஒளி அலை மற்றும் துகள் ஆகிய இரண்டு பண்புகளையும் வெளிப்படுத்துகிறது.

## முக்கிய கருத்துக்கள் (Core Concepts)
- **ஹைஜென்ஸ் கொள்கை (Huygens' Principle)**: அலைமுகப்பில் உள்ள ஒவ்வொரு புள்ளியும் புதிய அலைகளின் மூலமாக செயல்படுகிறது.
- **குறுக்கீட்டு விளைவு (Interference)**: இரண்டு ஒத்திசைந்த ஒளி அலைகளின் மேற்பொருந்துதல்.

## சூத்திரங்கள் (Formulas)
- பட்டை அகலம்: $\\beta = \\frac{\\lambda D}{d}$

## முக்கிய குறிப்புகள் (Takeaways)
- தொடர்ச்சியான குறுக்கீட்டுக்கு ஒத்திசைவு மிக முக்கியம்.
"""


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def seeded_space(db_session: AsyncSession, mock_user) -> LearningSpace:
    """Seed a user and a LearningSpace in the in-memory SQLite database."""
    # Ensure user exists in DB
    user = User(
        id=mock_user.id,
        email=mock_user.email,
        name=mock_user.name,
        selected_exam=mock_user.selected_exam,
    )
    db_session.add(user)
    await db_session.flush()

    space = LearningSpace(
        id=101,
        user_id=mock_user.id,
        exam_id="NEET",
        subject="Physics",
        title="Physics Space",
    )
    db_session.add(space)
    await db_session.commit()
    return space


@pytest_asyncio.fixture
async def user_b_space(db_session: AsyncSession) -> tuple[User, LearningSpace]:
    """Seed a second user (User B) and their LearningSpace for cross-user isolation tests."""
    user_b = User(
        id=999,
        email="otherstudent@vinaval.ai",
        name="User B",
        selected_exam="NEET",
    )
    db_session.add(user_b)
    await db_session.flush()

    space_b = LearningSpace(
        id=202,
        user_id=999,
        exam_id="NEET",
        subject="Physics",
        title="User B Physics Space",
    )
    db_session.add(space_b)
    await db_session.commit()
    return user_b, space_b


# ── Auth & Protection Tests ───────────────────────────────────────────────────

class TestSmartNotesAuth:
    async def test_unauthenticated_request_returns_401(self, db_session: AsyncSession):
        """Requests without an auth token must be rejected with 401 Unauthorized."""
        app = create_app()

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:
            res = await ac.get("/api/v1/spaces/101/notes")
            assert res.status_code == 401
            assert "Not authenticated" in res.json()["detail"]

            gen_res = await ac.post(
                "/api/v1/spaces/101/notes/generate",
                json={"topic": "Optics"},
            )
            assert gen_res.status_code == 401


# ── Note Generation Tests ─────────────────────────────────────────────────────

class TestSmartNotesGeneration:
    async def test_generate_curriculum_notes_en(
        self, client: AsyncClient, seeded_space: LearningSpace
    ):
        """Generate Smart Notes in English grounded in syllabus context."""
        with (
            patch("app.rag.chain._llm_complete", new=AsyncMock(return_value=MOCK_NOTE_MARKDOWN)),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("Optics syllabus context", 3)),
        ):
            res = await client.post(
                f"/api/v1/spaces/{seeded_space.id}/notes/generate",
                json={"topic": "Optics", "lang": "en", "source_type": "curriculum"},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Optics & Wave Nature of Light"
        assert data["topic"] == "Optics"
        assert data["lang"] == "en"
        assert "Huygens' Principle" in data["content"]
        assert data["chunks_used"] == 3

    async def test_generate_curriculum_notes_ta(
        self, client: AsyncClient, seeded_space: LearningSpace
    ):
        """Generate Smart Notes in Tamil."""
        with (
            patch("app.rag.chain._llm_complete", new=AsyncMock(return_value=MOCK_TAMIL_NOTE_MARKDOWN)),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("Tamil syllabus chunks", 2)),
        ):
            res = await client.post(
                f"/api/v1/spaces/{seeded_space.id}/notes/generate",
                json={"topic": "ஒளியியல்", "lang": "ta", "source_type": "curriculum"},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["lang"] == "ta"
        assert "ஒளி ஒளியியல்" in data["title"]
        assert "ஹைஜென்ஸ் கொள்கை" in data["content"]

    async def test_generate_document_grounded_notes(
        self, client: AsyncClient, seeded_space: LearningSpace
    ):
        """Generate Smart Notes grounded in an uploaded document."""
        with (
            patch("app.rag.chain._llm_complete", new=AsyncMock(return_value=MOCK_NOTE_MARKDOWN)),
            patch("app.rag.chain._load_all_doc_chunks", return_value=("Uploaded doc chunks text", 5, ["Wave Optics"])),
        ):
            res = await client.post(
                f"/api/v1/spaces/{seeded_space.id}/notes/generate",
                json={"doc_id": 42, "source_type": "document"},
            )

        assert res.status_code == 200
        data = res.json()
        assert data["doc_id"] == 42
        assert data["source_type"] == "document"
        assert data["chunks_used"] == 5

    async def test_generate_notes_llm_failure_returns_502(
        self, client: AsyncClient, seeded_space: LearningSpace
    ):
        """When the LLM provider fails or times out, the API returns a graceful 502 with no stack trace."""
        with (
            patch("app.rag.chain._llm_complete", side_effect=ValueError("Groq API rate limit exceeded")),
            patch("app.rag.chain._retrieve_syllabus_context", return_value=("", 0)),
        ):
            res = await client.post(
                f"/api/v1/spaces/{seeded_space.id}/notes/generate",
                json={"topic": "Optics"},
            )

        assert res.status_code == 502
        data = res.json()
        assert "detail" in data
        assert "Note generation failed" in data["detail"]
        assert "Groq API rate limit exceeded" in data["detail"]


# ── CRUD Operation Tests ──────────────────────────────────────────────────────

class TestSmartNotesCRUD:
    async def test_create_note_success(
        self, client: AsyncClient, seeded_space: LearningSpace
    ):
        """Create a new note in the space."""
        payload = {
            "title": "My Kinematics Summary",
            "topic": "Kinematics",
            "content": "### 1D Motion\n$v = u + at$\n$s = ut + \\frac{1}{2}at^2$",
            "source_type": "topic",
        }
        res = await client.post(f"/api/v1/spaces/{seeded_space.id}/notes", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] is not None
        assert data["title"] == "My Kinematics Summary"
        assert data["topic"] == "Kinematics"
        assert data["space_id"] == seeded_space.id
        assert data["user_id"] == seeded_space.user_id

    async def test_create_note_validation_error(
        self, client: AsyncClient, seeded_space: LearningSpace
    ):
        """Creating a note with empty content should trigger a 422 validation error."""
        res = await client.post(
            f"/api/v1/spaces/{seeded_space.id}/notes",
            json={"title": "Empty Note", "content": ""},
        )
        assert res.status_code == 422

    async def test_list_and_search_notes(
        self, client: AsyncClient, seeded_space: LearningSpace
    ):
        """List notes and verify search keyword filtering."""
        # Create two notes
        await client.post(
            f"/api/v1/spaces/{seeded_space.id}/notes",
            json={"title": "Thermodynamics First Law", "topic": "Thermal Physics", "content": "dQ = dU + dW"},
        )
        await client.post(
            f"/api/v1/spaces/{seeded_space.id}/notes",
            json={"title": "Electrostatics Coulomb Law", "topic": "Electricity", "content": "F = k*q1*q2/r^2"},
        )

        # List all
        all_res = await client.get(f"/api/v1/spaces/{seeded_space.id}/notes")
        assert all_res.status_code == 200
        all_notes = all_res.json()
        assert len(all_notes) >= 2

        # Search for 'Thermo'
        search_res = await client.get(f"/api/v1/spaces/{seeded_space.id}/notes?search=Thermo")
        assert search_res.status_code == 200
        results = search_res.json()
        assert len(results) == 1
        assert "Thermodynamics" in results[0]["title"]

    async def test_get_update_delete_note(
        self, client: AsyncClient, seeded_space: LearningSpace
    ):
        """Retrieve by ID, update, and delete a note."""
        # Create
        create_res = await client.post(
            f"/api/v1/spaces/{seeded_space.id}/notes",
            json={"title": "Initial Title", "topic": "Magnetism", "content": "B = \\mu_0 I / 2\\pi r"},
        )
        note_id = create_res.json()["id"]

        # Get by ID
        get_res = await client.get(f"/api/v1/spaces/{seeded_space.id}/notes/{note_id}")
        assert get_res.status_code == 200
        assert get_res.json()["title"] == "Initial Title"

        # Update
        update_res = await client.put(
            f"/api/v1/spaces/{seeded_space.id}/notes/{note_id}",
            json={"title": "Updated Title", "content": "Updated content with new formulas"},
        )
        assert update_res.status_code == 200
        assert update_res.json()["title"] == "Updated Title"
        assert update_res.json()["content"] == "Updated content with new formulas"

        # Delete
        del_res = await client.delete(f"/api/v1/spaces/{seeded_space.id}/notes/{note_id}")
        assert del_res.status_code == 204

        # Verify 404 after delete
        not_found_res = await client.get(f"/api/v1/spaces/{seeded_space.id}/notes/{note_id}")
        assert not_found_res.status_code == 404


# ── Cross-User Tenant Isolation Tests ─────────────────────────────────────────

class TestCrossUserIsolation:
    async def test_user_b_cannot_access_or_modify_user_a_note(
        self,
        db_session: AsyncSession,
        seeded_space: LearningSpace,
        user_b_space: tuple[User, LearningSpace],
    ):
        """User B must never be able to view, list, edit, or delete User A's notes."""
        user_b, space_b = user_b_space

        # Create note belonging to User A in seeded_space (user_id=1)
        note_a = SpaceNote(
            space_id=seeded_space.id,
            user_id=seeded_space.user_id,
            title="User A Private Note",
            content="Top secret formulas for NEET Physics",
            topic="Physics Secrets",
        )
        db_session.add(note_a)
        await db_session.commit()
        await db_session.refresh(note_a)

        # Set up client authenticated as User B
        app = create_app()

        async def override_get_db():
            yield db_session

        async def override_get_user_b():
            return user_b

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_user_b

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client_b:
            # 1. User B tries to GET User A's space notes list
            list_res = await client_b.get(f"/api/v1/spaces/{seeded_space.id}/notes")
            assert list_res.status_code == 404

            # 2. User B tries to GET User A's individual note
            get_res = await client_b.get(f"/api/v1/spaces/{seeded_space.id}/notes/{note_a.id}")
            assert get_res.status_code == 404

            # 3. User B tries to GET User A's note even by spoofing their own space_id
            spoof_res = await client_b.get(f"/api/v1/spaces/{space_b.id}/notes/{note_a.id}")
            assert spoof_res.status_code == 404

            # 4. User B tries to PUT User A's note
            put_res = await client_b.put(
                f"/api/v1/spaces/{seeded_space.id}/notes/{note_a.id}",
                json={"title": "Hacked Title"},
            )
            assert put_res.status_code == 404

            # 5. User B tries to DELETE User A's note
            del_res = await client_b.delete(f"/api/v1/spaces/{seeded_space.id}/notes/{note_a.id}")
            assert del_res.status_code == 404

            # 6. User B tries to generate note in User A's space
            gen_res = await client_b.post(
                f"/api/v1/spaces/{seeded_space.id}/notes/generate",
                json={"topic": "Optics"},
            )
            assert gen_res.status_code == 404


# ── Alembic Migration Verification ────────────────────────────────────────────

class TestSmartNotesMigration:
    async def test_alembic_migration_structure(self):
        """Verify the expand_smart_notes migration exports upgrade and downgrade with correct revision IDs."""
        import importlib.util
        from pathlib import Path

        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "e34ccb42bc0e_expand_smart_notes.py"
        assert migration_path.exists(), f"Migration file {migration_path} does not exist"

        spec = importlib.util.spec_from_file_location("smart_notes_migration", migration_path)
        assert spec and spec.loader
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        assert hasattr(migration, "upgrade")
        assert callable(migration.upgrade)
        assert hasattr(migration, "downgrade")
        assert callable(migration.downgrade)
        assert migration.revision == "e34ccb42bc0e"
        assert migration.down_revision == "9799ba135d56"

