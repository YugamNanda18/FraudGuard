"""FastAPI router with all FraudAI Agent API endpoints.

Endpoint signatures and docstrings only -- no business logic.
All handlers raise ``NotImplementedError``; implementation in F4.

Reference architecture:
- ADR-003: LangGraph StateGraph orchestrates agents
- ADR-006: FastAPI app served via uvicorn
- F2 spec: SLA targets documented per operation
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile

from fraudai.api.auth import User, get_admin_user, get_current_user
from fraudai.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConfirmationRequest,
    FeedbackRequest,
    FileUploadResponse,
    HealthResponse,
    SessionInfo,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Chat (core interaction -- ADR-003 LangGraph graph invocation)
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
) -> ChatResponse:
    """Send a message to FraudAI. Routes via Donna to the appropriate agent.

    Flow: user message -> Donna (classification) -> sub-agent -> response.
    Supports ``agent_override`` to bypass Donna routing.

    SLA targets (F2):
    - Donna routing P95: < 1.5 s
    - First agent response P95: < 5 s
    - Full response P95: < 10 s (streaming recommended for perceived latency)
    """
    raise NotImplementedError


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user: User = Depends(get_current_user),
) -> None:
    """SSE streaming endpoint for real-time agent responses.

    Returns a ``text/event-stream`` response with incremental tokens
    as the agent generates its answer. Recommended for all client
    integrations to meet the < 2 s perceived latency target (F2 5.3).

    Event types:
    - ``token``: Incremental text token from the agent.
    - ``citation``: A normative citation from the RAG corpus.
    - ``tool_start``: A tool execution has begun.
    - ``tool_end``: A tool execution completed (includes ToolResult).
    - ``done``: Stream complete; includes full ResponseMetadata.
    - ``error``: An error occurred during processing.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# File Upload (UR-002, UR-012)
# ---------------------------------------------------------------------------


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile,
    session_id: str,
    user: User = Depends(get_current_user),
) -> FileUploadResponse:
    """Upload a document for session context.

    Accepted formats: CSV, JSON, PDF, TXT.
    Maximum file size: 100 MB (SR-008).

    The file is indexed into an ephemeral Qdrant collection scoped to the
    session (T-RAG-04). Indexing target: < 30 s (SR-007).
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Sessions (SR-009 tenant-isolated)
# ---------------------------------------------------------------------------


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
) -> SessionInfo:
    """Get session information and history.

    Returns metadata, agent interaction history, and uploaded file
    references. Scoped to the authenticated user's tenant (SR-009).
    """
    raise NotImplementedError


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
) -> None:
    """Delete a session and all associated data.

    Removes:
    - LangGraph checkpoint state (ADR-003)
    - Ephemeral Qdrant collection for uploaded files
    - Audit log entries are **retained** per SEC-004 (1-year retention)
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Red Teaming HITL Confirmation (SEC-006)
# ---------------------------------------------------------------------------


@router.post("/confirm", response_model=ChatResponse)
async def confirm_action(
    request: ConfirmationRequest,
    user: User = Depends(get_current_user),
) -> ChatResponse:
    """Approve or reject a pending red teaming action (Mike Ross HITL).

    When Mike Ross proposes an offensive action (adversarial evasion,
    prompt injection test, model extraction), the graph pauses via
    ``interrupt()`` (ADR-003) and waits for user confirmation.

    - ``approved=True``: Resumes the graph and executes the action.
    - ``approved=False``: Cancels the action and returns a summary.

    SEC-006: No offensive tool executes without explicit user approval.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Feedback (UR-014)
# ---------------------------------------------------------------------------


@router.post("/feedback", status_code=201)
async def submit_feedback(
    request: FeedbackRequest,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Submit feedback for an agent response.

    Rating scale: 1 (bad) to 5 (excellent).
    Feedback is stored for continuous evaluation and prompt tuning.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check for all FraudAI infrastructure components.

    Checks connectivity to:
    - Qdrant (vector DB)
    - Ollama (local LLM for Donna)
    - Anthropic Claude API (remote LLM for agents)

    Returns overall status: 'healthy', 'degraded', or 'unhealthy'.
    No authentication required -- used by load balancers and monitoring.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Admin (SR-012 observability)
# ---------------------------------------------------------------------------


@router.get("/admin/metrics")
async def metrics(
    user: User = Depends(get_admin_user),
) -> dict[str, object]:
    """Prometheus-compatible metrics endpoint.

    Exposes:
    - Request count and latency histograms per endpoint
    - Token consumption per agent and per tenant
    - Tool call counts and durations
    - RAG retrieval latency and cache hit rate
    - Active sessions and concurrent users

    Requires admin privileges.
    """
    raise NotImplementedError
