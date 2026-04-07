"""Async SQLite database for session and feedback persistence.

MVP implementation using aiosqlite. Provides CRUD operations for
sessions and feedback, replacing the in-memory dicts that are lost
on restart.

Production should migrate to PostgreSQL (ADR-003 note).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path("data/fraudai.db")


class Database:
    """Async SQLite database for session and feedback persistence."""

    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self._db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create database file (if missing) and ensure tables exist."""
        db_dir = Path(self._db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                tier TEXT NOT NULL DEFAULT 'free',
                created_at TEXT NOT NULL,
                agent_history TEXT NOT NULL DEFAULT '[]',
                uploaded_files TEXT NOT NULL DEFAULT '[]',
                turn_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_tenant ON sessions(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id);
            """
        )
        await self._db.commit()
        logger.info("Database initialized at %s", self._db_path)

    def _ensure_connected(self) -> aiosqlite.Connection:
        """Return the active connection or raise."""
        if self._db is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._db

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def create_session(
        self,
        session_id: str,
        tenant_id: str,
        tier: str,
    ) -> None:
        """Insert a new session row."""
        db = self._ensure_connected()
        now = datetime.now(UTC).isoformat()
        await db.execute(
            "INSERT INTO sessions"
            " (session_id, tenant_id, tier, created_at,"
            " agent_history, uploaded_files, turn_count)"
            " VALUES (?, ?, ?, ?, '[]', '[]', 0)",
            (session_id, tenant_id, tier, now),
        )
        await db.commit()

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Fetch a session by ID, or None if not found."""
        db = self._ensure_connected()
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_session_dict(row)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if a row was removed."""
        db = self._ensure_connected()
        cursor = await db.execute(
            "DELETE FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def record_turn(self, session_id: str, agent: str) -> None:
        """Append an agent name to the session history and bump turn_count."""
        db = self._ensure_connected()
        cursor = await db.execute(
            "SELECT agent_history, turn_count FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            logger.warning("record_turn: session %s not found in DB", session_id)
            return

        history: list[str] = json.loads(row[0])
        history.append(agent)
        new_count = row[1] + 1

        await db.execute(
            "UPDATE sessions SET agent_history = ?, turn_count = ? WHERE session_id = ?",
            (json.dumps(history), new_count, session_id),
        )
        await db.commit()

    async def record_upload(self, session_id: str, filename: str) -> None:
        """Append a filename to the session's uploaded_files list."""
        db = self._ensure_connected()
        cursor = await db.execute(
            "SELECT uploaded_files FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            logger.warning("record_upload: session %s not found in DB", session_id)
            return

        files: list[str] = json.loads(row[0])
        files.append(filename)

        await db.execute(
            "UPDATE sessions SET uploaded_files = ? WHERE session_id = ?",
            (json.dumps(files), session_id),
        )
        await db.commit()

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    async def save_feedback(
        self,
        session_id: str,
        message_id: str,
        user_id: str,
        rating: int,
        comment: str,
    ) -> None:
        """Insert a feedback record."""
        db = self._ensure_connected()
        now = datetime.now(UTC).isoformat()
        await db.execute(
            """
            INSERT INTO feedback (session_id, message_id, user_id, rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, message_id, user_id, rating, comment, now),
        )
        await db.commit()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
            logger.info("Database connection closed")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_session_dict(row: Any) -> dict[str, Any]:
        """Convert a Row to a plain dict with parsed JSON fields."""
        return {
            "session_id": row[0],
            "tenant_id": row[1],
            "tier": row[2],
            "created_at": row[3],
            "agent_history": json.loads(row[4]),
            "uploaded_files": json.loads(row[5]),
            "turn_count": row[6],
        }
