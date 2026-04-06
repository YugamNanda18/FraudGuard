"""FastAPI application factory for FraudAI Agent.

Creates and configures the ASGI app with CORS, middleware, routes,
and lifespan events. Entry point for both development and production:

    Development:  uv run uvicorn fraudai.api.app:create_app --factory --reload
    Production:   Dockerfile CMD (ADR-006)

Reference: BR-006, ADR-006.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fraudai.api.routes import router as api_router
from fraudai.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan: startup and shutdown hooks.

    Startup:
    - Verify Qdrant connectivity
    - Verify Ollama availability (Donna model loaded)
    - Warm up embedding model (BGE-M3)
    - Initialize LangGraph checkpointer (MemorySaver in dev, PostgresSaver in prod)

    Shutdown:
    - Flush pending audit log entries (SEC-004)
    - Close database connections
    - Release GPU resources
    """
    # --- Startup ---
    # TODO (F4): Initialize services, verify connectivity, warm up models
    _ = settings  # Ensure settings are loaded early
    yield
    # --- Shutdown ---
    # TODO (F4): Graceful cleanup


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
