"""FastAPI application factory for FraudAI Agent.

Creates and configures the ASGI app with CORS, middleware, routes,
and lifespan events. Entry point for both development and production:

    Development:  uv run uvicorn fraudai.api.app:create_app --factory --reload
    Production:   Dockerfile CMD (ADR-006)

Reference: BR-006, ADR-006.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fraudai.api.middleware import MetricsMiddleware
from fraudai.api.routes import router as api_router
from fraudai.api.session_manager import SessionManager
from fraudai.core.config import settings
from fraudai.core.tracing import setup_tracing

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan: startup and shutdown hooks.

    Startup:
    - Initialize QdrantStore (create collections if missing)
    - Compile LangGraph orchestration graph
    - Create SessionManager
    - Store all on app.state for route access

    Shutdown:
    - Log cleanup (graceful shutdown)
    """
    # --- Startup ---
    from fraudai.agents.graph import build_fraud_ai_graph
    from fraudai.rag.qdrant_store import QdrantStore

    logger.info("Starting FraudAI Agent API (environment=%s)", settings.environment)

    # Qdrant vector store
    store = QdrantStore(host=settings.qdrant_host, port=settings.qdrant_port)
    try:
        await store.initialize()
        logger.info("QdrantStore initialized successfully")
    except Exception:
        logger.exception("QdrantStore initialization failed -- continuing in degraded mode")

    # RAG retriever + tool registry (Bug #4 fix: wire ToolRegistry into runtime)
    from fraudai.agents.tool_registry import ToolRegistry
    from fraudai.ingestion.embeddings import EmbeddingGenerator
    from fraudai.rag.retriever import LegalRetriever

    try:
        embedder = EmbeddingGenerator(device="cpu")
        retriever = LegalRetriever(store=store, embedder=embedder)
        tool_registry = ToolRegistry(retriever=retriever)
        logger.info("ToolRegistry initialized with LegalRetriever")
    except Exception:
        logger.exception("ToolRegistry initialization failed — tools will use stubs")
        tool_registry = None  # type: ignore[assignment]
        retriever = None  # type: ignore[assignment]

    # LangGraph compiled graph
    graph = build_fraud_ai_graph()
    logger.info("LangGraph orchestration graph compiled")

    # Session manager (in-memory MVP)
    session_manager = SessionManager()

    # Feedback store (in-memory MVP -- list of deque for bounded memory, Bug #14)
    from collections import deque
    feedback_store: deque[dict[str, Any]] = deque(maxlen=10_000)

    # Publish system info to Prometheus
    from fraudai.core.metrics import SYSTEM_INFO

    SYSTEM_INFO.info(
        {
            "version": "0.1.0",
            "environment": settings.environment,
        }
    )

    # Attach to app.state for route access
    app.state.graph = graph
    app.state.store = store
    app.state.session_manager = session_manager
    app.state.feedback_store = feedback_store
    app.state.tool_registry = tool_registry
    app.state.retriever = retriever

    yield

    # --- Shutdown ---
    logger.info("Shutting down FraudAI Agent API")


def create_app() -> FastAPI:
    """Create and configure the FraudAI Agent FastAPI application."""

    app = FastAPI(
        title="FraudAI Agent API",
        description=(
            "AI agentic platform for banking fraud detection and AI red teaming. "
            "Multi-agent system with RAG over Spanish/EU financial regulation (BOE). "
            "Agents: Donna (router), Harvey (fraud), Louis (compliance), "
            "Jessica (intelligence), Mike (red teaming), Rachel (data engineering)."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Structured logging with correlation IDs ---
    # Disabled during uvicorn dev: correlation_id format conflicts with
    # uvicorn's root logger handlers. Tracing works in production via
    # the MetricsMiddleware which sets correlation IDs independently.
    # setup_tracing()

    # --- CORS ---
    # Permissive in development; lock down in production via env config.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Prometheus metrics + correlation ID middleware ---
    app.add_middleware(MetricsMiddleware)

    # --- Routes ---
    app.include_router(api_router, prefix="/api/v1")

    return app
