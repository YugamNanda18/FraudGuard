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

from fraudai.api.routes import router as api_router
from fraudai.api.session_manager import SessionManager
from fraudai.core.config import settings

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

    # LangGraph compiled graph
    graph = build_fraud_ai_graph()
    logger.info("LangGraph orchestration graph compiled")

    # Session manager (in-memory MVP)
    session_manager = SessionManager()

    # Feedback store (in-memory MVP -- list of dicts)
    feedback_store: list[dict[str, Any]] = []

    # Attach to app.state for route access
    app.state.graph = graph
    app.state.store = store
    app.state.session_manager = session_manager
    app.state.feedback_store = feedback_store

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

    # --- CORS ---
    # Permissive in development; lock down in production via env config.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routes ---
    app.include_router(api_router, prefix="/api/v1")

    return app
