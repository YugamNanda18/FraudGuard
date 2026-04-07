"""Tests for the async SQLite database layer.

Tests use a temporary in-memory database (`:memory:`) so no file I/O
is needed and each test is fully isolated.
"""

from __future__ import annotations

import pytest

from fraudai.core.database import Database

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db():
    """Yield an initialized in-memory database, closed after the test."""
    database = Database(db_path=":memory:")
    await database.initialize()
    yield database
    await database.close()


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


class TestSessionCRUD:
    """Create, read, update, delete operations on the sessions table."""

    async def test_create_and_get_session(self, db: Database) -> None:
        await db.create_session("s1", "tenant-a", "enterprise")
        session = await db.get_session("s1")
        assert session is not None
        assert session["session_id"] == "s1"
        assert session["tenant_id"] == "tenant-a"
        assert session["tier"] == "enterprise"
        assert session["turn_count"] == 0
        assert session["agent_history"] == []
        assert session["uploaded_files"] == []

    async def test_get_nonexistent_session_returns_none(self, db: Database) -> None:
        result = await db.get_session("does-not-exist")
        assert result is None

    async def test_delete_session_returns_true(self, db: Database) -> None:
        await db.create_session("s2", "tenant-b", "free")
        deleted = await db.delete_session("s2")
        assert deleted is True

    async def test_delete_nonexistent_session_returns_false(self, db: Database) -> None:
        deleted = await db.delete_session("ghost")
        assert deleted is False

    async def test_deleted_session_not_retrievable(self, db: Database) -> None:
        await db.create_session("s3", "tenant-c", "free")
        await db.delete_session("s3")
        assert await db.get_session("s3") is None

    async def test_record_turn_increments_count(self, db: Database) -> None:
        await db.create_session("s4", "tenant-d", "pro")
        await db.record_turn("s4", "harvey")
        await db.record_turn("s4", "louis")
        session = await db.get_session("s4")
        assert session is not None
        assert session["turn_count"] == 2
        assert session["agent_history"] == ["harvey", "louis"]

    async def test_record_turn_nonexistent_session_no_error(self, db: Database) -> None:
        # Should log a warning but not raise
        await db.record_turn("nonexistent", "harvey")

    async def test_record_upload_appends_filename(self, db: Database) -> None:
        await db.create_session("s5", "tenant-e", "free")
        await db.record_upload("s5", "report.csv")
        await db.record_upload("s5", "data.json")
        session = await db.get_session("s5")
        assert session is not None
        assert session["uploaded_files"] == ["report.csv", "data.json"]

    async def test_record_upload_nonexistent_session_no_error(self, db: Database) -> None:
        await db.record_upload("ghost", "file.txt")

    async def test_created_at_is_set(self, db: Database) -> None:
        await db.create_session("s6", "tenant-f", "free")
        session = await db.get_session("s6")
        assert session is not None
        assert session["created_at"] is not None
        assert len(session["created_at"]) > 10  # ISO format timestamp


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


class TestFeedbackCRUD:
    """Tests for feedback persistence."""

    async def test_save_feedback_no_error(self, db: Database) -> None:
        await db.save_feedback(
            session_id="s1",
            message_id="msg-1",
            user_id="user-1",
            rating=5,
            comment="Great analysis!",
        )
        # Verify it was written
        conn = db._ensure_connected()
        cursor = await conn.execute("SELECT * FROM feedback WHERE session_id = 's1'")
        rows = await cursor.fetchall()
        assert len(rows) == 1

    async def test_save_multiple_feedback(self, db: Database) -> None:
        for i in range(3):
            await db.save_feedback(
                session_id="s2",
                message_id=f"msg-{i}",
                user_id="user-2",
                rating=i + 1,
                comment=f"Comment {i}",
            )
        conn = db._ensure_connected()
        cursor = await conn.execute("SELECT COUNT(*) FROM feedback WHERE session_id = 's2'")
        row = await cursor.fetchone()
        assert row[0] == 3


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestDatabaseLifecycle:
    """Tests for database initialization and shutdown."""

    async def test_close_sets_db_to_none(self) -> None:
        database = Database(db_path=":memory:")
        await database.initialize()
        assert database._db is not None
        await database.close()
        assert database._db is None

    async def test_ensure_connected_raises_before_init(self) -> None:
        database = Database(db_path=":memory:")
        with pytest.raises(RuntimeError, match="not initialized"):
            database._ensure_connected()

    async def test_double_initialize_is_safe(self) -> None:
        """Calling initialize twice should not raise or corrupt data."""
        database = Database(db_path=":memory:")
        await database.initialize()
        await database.create_session("s1", "t1", "free")
        # Re-initialize (e.g. reconnect scenario) -- uses a new in-memory db
        # so data is lost, but the point is it should not raise
        await database.initialize()
        await database.close()
