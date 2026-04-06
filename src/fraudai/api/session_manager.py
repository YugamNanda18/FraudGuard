"""In-memory session management for FraudAI Agent API.

Tracks session metadata, turn history, and uploaded file references.
MVP implementation -- production should back this with Redis or PostgreSQL.

Reference: SR-009 (tenant isolation), ADR-003 (LangGraph thread_id mapping).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SessionData(BaseModel):
    """Metadata for a single chat session."""

    session_id: str
    tenant_id: str
    tier: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    agent_history: list[str] = Field(default_factory=list)
    uploaded_files: list[str] = Field(default_factory=list)
    turn_count: int = 0


class SessionManager:
    """Manages chat sessions with metadata tracking.

    Thread-safe for single-process async usage (no cross-process locking).
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}

    def create_session(self, tenant_id: str, tier: str) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = SessionData(
            session_id=session_id,
            tenant_id=tenant_id,
            tier=tier,
        )
        logger.info(
            "Session created: session_id=%s, tenant_id=%s, tier=%s",
            session_id,
            tenant_id,
            tier,
        )
        return session_id

    def get_session(self, session_id: str) -> SessionData | None:
        """Return session data or None if not found."""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        removed = self._sessions.pop(session_id, None)
        if removed:
            logger.info("Session deleted: session_id=%s", session_id)
            return True
        return False

    def record_turn(self, session_id: str, agent: str) -> None:
        """Record an agent turn in the session history."""
        session = self._sessions.get(session_id)
        if session is None:
            logger.warning(
                "record_turn called for unknown session: %s", session_id
            )
            return
        session.agent_history.append(agent)
        session.turn_count += 1

    def record_upload(self, session_id: str, filename: str) -> None:
        """Record a file upload in the session."""
        session = self._sessions.get(session_id)
        if session is None:
            logger.warning(
                "record_upload called for unknown session: %s", session_id
            )
            return
        session.uploaded_files.append(filename)

    def list_sessions(self, tenant_id: str | None = None) -> list[SessionData]:
        """List all sessions, optionally filtered by tenant."""
        if tenant_id is None:
            return list(self._sessions.values())
        return [
            s for s in self._sessions.values() if s.tenant_id == tenant_id
        ]
