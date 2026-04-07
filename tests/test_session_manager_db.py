"""Tests for SessionManager backed by Database persistence.

Verifies that SessionManager delegates to the Database correctly
while maintaining backward compatibility (no DB = pure in-memory).
"""

from __future__ import annotations

import asyncio

import pytest

from fraudai.api.session_manager import SessionManager
from fraudai.core.database import Database

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db():
    """Yield an initialized in-memory database."""
    database = Database(db_path=":memory:")
    await database.initialize()
    yield database
    await database.close()


@pytest.fixture
def mgr_no_db() -> SessionManager:
    """SessionManager without database (pure in-memory, backward compat)."""
    return SessionManager()


@pytest.fixture
def mgr_with_db(db: Database) -> SessionManager:
    """SessionManager backed by a Database."""
    return SessionManager(db=db)


# ---------------------------------------------------------------------------
# Backward compatibility (no DB)
# ---------------------------------------------------------------------------


class TestSessionManagerNoDB:
    """Verify that SessionManager works exactly as before when no DB is set."""

    def test_create_session_returns_uuid(self, mgr_no_db: SessionManager) -> None:
        sid = mgr_no_db.create_session("tenant-1", "free")
        assert len(sid) == 36  # UUID format

    def test_get_session_returns_data(self, mgr_no_db: SessionManager) -> None:
        sid = mgr_no_db.create_session("tenant-1", "enterprise")
        session = mgr_no_db.get_session(sid)
        assert session is not None
        assert session.tenant_id == "tenant-1"
        assert session.tier == "enterprise"

    def test_delete_session(self, mgr_no_db: SessionManager) -> None:
        sid = mgr_no_db.create_session("tenant-1", "free")
        assert mgr_no_db.delete_session(sid) is True
        assert mgr_no_db.get_session(sid) is None

    def test_record_turn(self, mgr_no_db: SessionManager) -> None:
        sid = mgr_no_db.create_session("tenant-1", "free")
        mgr_no_db.record_turn(sid, "harvey")
        session = mgr_no_db.get_session(sid)
        assert session is not None
        assert session.agent_history == ["harvey"]
        assert session.turn_count == 1

    def test_record_upload(self, mgr_no_db: SessionManager) -> None:
        sid = mgr_no_db.create_session("tenant-1", "free")
        mgr_no_db.record_upload(sid, "report.csv")
        session = mgr_no_db.get_session(sid)
        assert session is not None
        assert session.uploaded_files == ["report.csv"]

    def test_list_sessions(self, mgr_no_db: SessionManager) -> None:
        mgr_no_db.create_session("tenant-a", "free")
        mgr_no_db.create_session("tenant-b", "pro")
        mgr_no_db.create_session("tenant-a", "enterprise")
        assert len(mgr_no_db.list_sessions()) == 3
        assert len(mgr_no_db.list_sessions("tenant-a")) == 2


# ---------------------------------------------------------------------------
# With Database backing
# ---------------------------------------------------------------------------


class TestSessionManagerWithDB:
    """Verify that SessionManager persists operations to the DB."""

    async def test_create_session_persists_to_db(
        self,
        mgr_with_db: SessionManager,
        db: Database,
    ) -> None:
        sid = mgr_with_db.create_session("tenant-1", "pro")
        # Give the fire-and-forget task a chance to run
        await asyncio.sleep(0.05)
        row = await db.get_session(sid)
        assert row is not None
        assert row["tenant_id"] == "tenant-1"
        assert row["tier"] == "pro"

    async def test_delete_session_persists_to_db(
        self,
        mgr_with_db: SessionManager,
        db: Database,
    ) -> None:
        sid = mgr_with_db.create_session("tenant-1", "free")
        await asyncio.sleep(0.05)
        mgr_with_db.delete_session(sid)
        await asyncio.sleep(0.05)
        row = await db.get_session(sid)
        assert row is None

    async def test_record_turn_persists_to_db(
        self,
        mgr_with_db: SessionManager,
        db: Database,
    ) -> None:
        sid = mgr_with_db.create_session("tenant-1", "free")
        await asyncio.sleep(0.05)
        mgr_with_db.record_turn(sid, "jessica")
        await asyncio.sleep(0.05)
        row = await db.get_session(sid)
        assert row is not None
        assert row["agent_history"] == ["jessica"]
        assert row["turn_count"] == 1

    async def test_record_upload_persists_to_db(
        self,
        mgr_with_db: SessionManager,
        db: Database,
    ) -> None:
        sid = mgr_with_db.create_session("tenant-1", "free")
        await asyncio.sleep(0.05)
        mgr_with_db.record_upload(sid, "data.csv")
        await asyncio.sleep(0.05)
        row = await db.get_session(sid)
        assert row is not None
        assert row["uploaded_files"] == ["data.csv"]

    async def test_load_from_db_hydrates_cache(self, db: Database) -> None:
        """Sessions in the DB should be loaded into memory on startup."""
        # Seed the DB directly
        await db.create_session("persisted-1", "tenant-x", "enterprise")
        await db.create_session("persisted-2", "tenant-x", "free")
        await db.record_turn("persisted-1", "harvey")

        # Fresh SessionManager that loads from DB
        mgr = SessionManager(db=db)
        count = await mgr.load_from_db()
        assert count == 2

        s1 = mgr.get_session("persisted-1")
        assert s1 is not None
        assert s1.tenant_id == "tenant-x"
        assert s1.tier == "enterprise"
        assert s1.agent_history == ["harvey"]
        assert s1.turn_count == 1

        s2 = mgr.get_session("persisted-2")
        assert s2 is not None
        assert s2.tier == "free"

    async def test_load_from_db_returns_zero_when_no_db(self) -> None:
        mgr = SessionManager(db=None)
        count = await mgr.load_from_db()
        assert count == 0

    async def test_ensure_session_persists_to_db(
        self,
        mgr_with_db: SessionManager,
        db: Database,
    ) -> None:
        mgr_with_db.ensure_session("manual-id", "tenant-z", "pro")
        await asyncio.sleep(0.05)
        row = await db.get_session("manual-id")
        assert row is not None
        assert row["tenant_id"] == "tenant-z"
