"""FastAPI router with all FraudAI Agent API endpoints.

Connects FastAPI to the LangGraph orchestration graph, QdrantStore,
and SessionManager. All endpoints are async.

Reference architecture:
- ADR-003: LangGraph StateGraph orchestrates agents
- ADR-006: FastAPI app served via uvicorn
- F2 spec: SLA targets documented per operation
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx as httpx_client
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from fraudai.api.auth import User, get_admin_user, get_current_user
from fraudai.api.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConfirmationRequest,
    FeedbackRequest,
    FileUploadResponse,
    HealthResponse,
    ResponseMetadata,
    SessionInfo,
    ToolResult,
)
from fraudai.core.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langgraph.graph.state import CompiledStateGraph

    from fraudai.api.session_manager import SessionManager
    from fraudai.rag.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".csv", ".json", ".pdf", ".txt"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def _get_graph(request: Request) -> CompiledStateGraph:
    """Extract the compiled graph from app state."""
    return request.app.state.graph


def _get_store(request: Request) -> QdrantStore:
    """Extract the QdrantStore from app state."""
    return request.app.state.store


def _get_session_manager(request: Request) -> SessionManager:
    """Extract the SessionManager from app state."""
    return request.app.state.session_manager


def _get_feedback_store(request: Request) -> list[dict[str, Any]]:
    """Extract the feedback store from app state."""
    return request.app.state.feedback_store


def _extract_citations(state: dict[str, Any]) -> list[Citation]:
    """Extract RAG citations from the graph state shared_context."""
    raw_citations = (state.get("shared_context") or {}).get("citations", [])
    citations: list[Citation] = []
    for c in raw_citations:
        try:
            citations.append(Citation(**c))
        except Exception:
            logger.warning("Skipping malformed citation: %s", c)
    return citations


def _extract_tool_results(state: dict[str, Any]) -> list[ToolResult]:
    """Extract tool results from the graph state."""
    raw_results = state.get("tool_results") or []
    results: list[ToolResult] = []
    for r in raw_results:
        try:
            results.append(ToolResult(**r))
        except Exception:
            logger.warning("Skipping malformed tool result: %s", r)
    return results


def _extract_response_text(state: dict[str, Any]) -> str:
    """Extract the final response text from the last AIMessage in state."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return "No response generated."


def _build_metadata(state: dict[str, Any], latency_ms: int) -> ResponseMetadata:
    """Build response metadata from graph state."""
    shared = state.get("shared_context") or {}
    return ResponseMetadata(
        routing_agent=state.get("current_agent") or "donna",
        routing_confidence=shared.get("routing_confidence", 0.0),
        tokens_used=shared.get("tokens_used", 0),
        latency_ms=latency_ms,
        corpus_version=shared.get("corpus_version", "unknown"),
    )


# ---------------------------------------------------------------------------
# Chat (core interaction -- ADR-003 LangGraph graph invocation)
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request_body: ChatRequest,
    request: Request,
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
    graph = _get_graph(request)
    session_mgr = _get_session_manager(request)
    start_time = time.monotonic()

    # Session management
    session_id = request_body.session_id
    if session_id is None:
        session_id = session_mgr.create_session(
            tenant_id=user.tenant_id, tier=user.tier
        )
    elif session_mgr.get_session(session_id) is None:
        # Session ID provided but not tracked -- register it
        from fraudai.api.session_manager import SessionData

        session_mgr._sessions[session_id] = SessionData(
            session_id=session_id,
            tenant_id=user.tenant_id,
            tier=user.tier,
        )

    # Build input state
    input_state: dict[str, Any] = {
        "messages": [HumanMessage(content=request_body.message)],
        "session_id": session_id,
        "tenant_id": user.tenant_id,
        "user_tier": user.tier,
        "language": request_body.language,
    }

    # Agent override: bypass Donna routing
    if request_body.agent_override is not None:
        input_state["current_agent"] = request_body.agent_override

    config = {"configurable": {"thread_id": session_id}}

    try:
        final_state = await graph.ainvoke(input_state, config=config)
    except Exception as exc:
        logger.exception("Graph invocation failed for session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent processing failed. Please try again.",
        ) from exc

    latency_ms = int((time.monotonic() - start_time) * 1000)

    # Extract results from final state
    agent = final_state.get("current_agent") or "donna"
    response_text = _extract_response_text(final_state)
    citations = _extract_citations(final_state)
    tool_results = _extract_tool_results(final_state)
    metadata = _build_metadata(final_state, latency_ms)

    # Record turn in session
    session_mgr.record_turn(session_id, agent)

    return ChatResponse(
        session_id=session_id,
        agent=agent,
        message=response_text,
        citations=citations,
        tool_results=tool_results,
        metadata=metadata,
    )


@router.post("/chat/stream")
async def chat_stream(
    request_body: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
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
    graph = _get_graph(request)
    session_mgr = _get_session_manager(request)

    # Session management
    session_id = request_body.session_id
    if session_id is None:
        session_id = session_mgr.create_session(
            tenant_id=user.tenant_id, tier=user.tier
        )

    input_state: dict[str, Any] = {
        "messages": [HumanMessage(content=request_body.message)],
        "session_id": session_id,
        "tenant_id": user.tenant_id,
        "user_tier": user.tier,
        "language": request_body.language,
    }

    if request_body.agent_override is not None:
        input_state["current_agent"] = request_body.agent_override

    config = {"configurable": {"thread_id": session_id}}

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in graph.astream_events(
                input_state, config=config, version="v2"
            ):
                event_type = event.get("event", "")

                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        payload = {"type": "token", "content": chunk.content}
                        yield f"data: {json.dumps(payload)}\n\n"

                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    payload = {"type": "tool_start", "tool_name": tool_name}
                    yield f"data: {json.dumps(payload)}\n\n"

                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    output = event.get("data", {}).get("output", "")
                    payload = {
                        "type": "tool_end",
                        "tool_name": tool_name,
                        "result": str(output),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            # Final done event
            done_payload = {"type": "done", "session_id": session_id}
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as exc:
            logger.exception("Stream error for session %s", session_id)
            error_payload = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# File Upload (UR-002, UR-012)
# ---------------------------------------------------------------------------


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile,
    session_id: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> FileUploadResponse:
    """Upload a document for session context.

    Accepted formats: CSV, JSON, PDF, TXT.
    Maximum file size: 100 MB (SR-008).

    The file is indexed into an ephemeral Qdrant collection scoped to the
    session (T-RAG-04). Indexing target: < 30 s (SR-007).
    """
    store = _get_store(request)
    session_mgr = _get_session_manager(request)

    # Validate file extension
    filename = file.filename or "unnamed"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # Read and validate file size
    content = await file.read()
    size_bytes = len(content)
    if size_bytes > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_bytes} bytes). Maximum: {MAX_FILE_SIZE} bytes (100 MB).",
        )

    # Save to temp directory (sanitize filename to prevent path traversal)
    file_id = str(uuid.uuid4())
    safe_filename = Path(filename).name  # Strip directory components
    tmp_dir = Path(tempfile.gettempdir()) / "fraudai_uploads" / session_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    file_path = tmp_dir / f"{file_id}_{safe_filename}"
    file_path.write_bytes(content)

    logger.info(
        "File saved: file_id=%s, filename=%s, size=%d, session=%s",
        file_id,
        filename,
        size_bytes,
        session_id,
    )

    # Index into Qdrant session collection
    chunks_generated = 0
    indexed = False
    try:
        collection_name = await store.create_session_collection(session_id)
        # Minimal chunking for MVP -- split by paragraphs
        text_content = content.decode("utf-8", errors="replace")
        chunks = _simple_chunk(text_content, file_id=file_id, filename=filename)
        if chunks:
            chunks_generated = await store.upsert_chunks(collection_name, chunks)
            indexed = True
        logger.info(
            "Indexed %d chunks for file %s in session %s",
            chunks_generated,
            file_id,
            session_id,
        )
    except Exception:
        logger.exception(
            "Failed to index file %s in session %s", file_id, session_id
        )

    # Record in session
    session_mgr.record_upload(session_id, file_id)

    return FileUploadResponse(
        file_id=file_id,
        filename=filename,
        size_bytes=size_bytes,
        indexed=indexed,
        chunks_generated=chunks_generated,
    )


def _simple_chunk(
    text: str,
    file_id: str,
    filename: str,
    max_chunk_size: int = 1000,
) -> list[dict[str, Any]]:
    """Split text into simple chunks for MVP indexing.

    Production should use RecursiveCharacterTextSplitter with overlap.
    """
    paragraphs = text.split("\n\n")
    chunks: list[dict[str, Any]] = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "dense_vector": [0.0] * 1024,  # Placeholder -- real embeddings in production
                "sparse_vector": None,
                "metadata": {
                    "file_id": file_id,
                    "filename": filename,
                    "chunk_index": len(chunks),
                },
            })
            current_chunk = para
        else:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para

    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "dense_vector": [0.0] * 1024,
            "sparse_vector": None,
            "metadata": {
                "file_id": file_id,
                "filename": filename,
                "chunk_index": len(chunks),
            },
        })

    return chunks


# ---------------------------------------------------------------------------
# Sessions (SR-009 tenant-isolated)
# ---------------------------------------------------------------------------


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> SessionInfo:
    """Get session information and history.

    Returns metadata, agent interaction history, and uploaded file
    references. Scoped to the authenticated user's tenant (SR-009).
    """
    session_mgr = _get_session_manager(request)
    session = session_mgr.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    # Tenant isolation check
    if session.tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: session belongs to a different tenant.",
        )

    return SessionInfo(
        session_id=session.session_id,
        created_at=session.created_at,
        agent_history=session.agent_history,
        uploaded_files=session.uploaded_files,
        turn_count=session.turn_count,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """Delete a session and all associated data.

    Removes:
    - Session metadata from SessionManager
    - Ephemeral Qdrant collection for uploaded files
    - Audit log entries are **retained** per SEC-004 (1-year retention)
    """
    session_mgr = _get_session_manager(request)
    store = _get_store(request)

    session = session_mgr.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    # Tenant isolation check
    if session.tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: session belongs to a different tenant.",
        )

    # Delete Qdrant session collection
    try:
        await store.delete_session_collection(session_id)
    except Exception:
        logger.warning(
            "Failed to delete Qdrant session collection for %s (may not exist)",
            session_id,
        )

    # Remove from session manager
    session_mgr.delete_session(session_id)

    logger.info("Session deleted: session_id=%s, user=%s", session_id, user.user_id)


# ---------------------------------------------------------------------------
# Red Teaming HITL Confirmation (SEC-006)
# ---------------------------------------------------------------------------


@router.post("/confirm", response_model=ChatResponse)
async def confirm_action(
    request_body: ConfirmationRequest,
    request: Request,
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
    graph = _get_graph(request)
    session_mgr = _get_session_manager(request)
    start_time = time.monotonic()

    session_id = request_body.session_id
    config = {"configurable": {"thread_id": session_id}}

    try:
        final_state = await graph.ainvoke(
            Command(resume={"approved": request_body.approved}),
            config=config,
        )
    except Exception as exc:
        logger.exception(
            "Confirmation resume failed for session %s", session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process confirmation. The session may not have a pending action.",
        ) from exc

    latency_ms = int((time.monotonic() - start_time) * 1000)

    agent = final_state.get("current_agent") or "mike"
    response_text = _extract_response_text(final_state)
    citations = _extract_citations(final_state)
    tool_results = _extract_tool_results(final_state)
    metadata = _build_metadata(final_state, latency_ms)

    session_mgr.record_turn(session_id, agent)

    return ChatResponse(
        session_id=session_id,
        agent=agent,
        message=response_text,
        citations=citations,
        tool_results=tool_results,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Feedback (UR-014)
# ---------------------------------------------------------------------------


@router.post("/feedback", status_code=201)
async def submit_feedback(
    request_body: FeedbackRequest,
    request: Request,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Submit feedback for an agent response.

    Rating scale: 1 (bad) to 5 (excellent).
    Feedback is stored for continuous evaluation and prompt tuning.
    """
    feedback_store = _get_feedback_store(request)

    entry = {
        "feedback_id": str(uuid.uuid4()),
        "session_id": request_body.session_id,
        "message_id": request_body.message_id,
        "rating": request_body.rating,
        "comment": request_body.comment,
        "user_id": user.user_id,
        "tenant_id": user.tenant_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    feedback_store.append(entry)

    logger.info(
        "Feedback recorded: feedback_id=%s, session=%s, rating=%d",
        entry["feedback_id"],
        request_body.session_id,
        request_body.rating,
    )

    return {"status": "accepted", "feedback_id": entry["feedback_id"]}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Health check for all FraudAI infrastructure components.

    Checks connectivity to:
    - Qdrant (vector DB)
    - Ollama (local LLM for Donna)
    - Anthropic Claude API (remote LLM for agents)

    Returns overall status: 'healthy', 'degraded', or 'unhealthy'.
    No authentication required -- used by load balancers and monitoring.
    """
    store = _get_store(request)

    # Check Qdrant
    qdrant_ok = False
    try:
        qdrant_ok = await store.health_check()
    except Exception:
        logger.warning("Qdrant health check failed")

    # Check Ollama
    ollama_ok = False
    try:
        async with httpx_client.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_host}/api/tags")
            ollama_ok = resp.status_code == 200
    except Exception:
        logger.warning("Ollama health check failed")

    # Check Claude API
    claude_ok = False
    try:
        if settings.anthropic_api_key:
            async with httpx_client.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                # 401/405 means API is reachable (auth works, method not allowed is fine)
                claude_ok = resp.status_code in (200, 401, 405)
        else:
            logger.warning("Claude API key not configured")
    except Exception:
        logger.warning("Claude API health check failed")

    # Get corpus version
    corpus_version: str | None = None
    try:
        corpus_version = await store.get_corpus_version()
    except Exception:
        logger.warning("Failed to retrieve corpus version")

    # Determine overall status
    checks = [qdrant_ok, ollama_ok, claude_ok]
    if all(checks):
        overall = "healthy"
    elif any(checks):
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        qdrant=qdrant_ok,
        ollama=ollama_ok,
        claude_api=claude_ok,
        corpus_version=corpus_version,
    )


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
    raise NotImplementedError(
        "Metrics endpoint not yet implemented. Scheduled for F7 monitoring phase."
    )
