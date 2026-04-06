# =============================================================================
# FraudAI Agent -- Production Dockerfile (multi-stage)
#
# Build:  docker build -t fraudai-agent:latest .
# Run:    docker run -p 8000:8000 --env-file .env fraudai-agent:latest
#
# Target image size: < 500 MB (python:3.11-slim base ~150 MB)
# Reference: ADR-006
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder -- install dependencies with uv
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for building Python packages (numpy, scikit-learn, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency specification + source (needed for package install)
COPY pyproject.toml ./
COPY src/ ./src/

# Install production dependencies (no dev extras)
RUN uv pip install --system --no-cache . && \
    rm -rf /root/.cache

# ---------------------------------------------------------------------------
# Stage 2: Runtime -- minimal image with only what's needed
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps (curl for Docker healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy application source only (no tests, docs, notebooks, etc.)
COPY --from=builder /app/src ./src

# Non-root user for security
RUN useradd -m -s /bin/bash -u 1000 fraudai
USER fraudai

EXPOSE 8000

# Healthcheck against the FastAPI /api/v1/health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production server: uvicorn with app factory
# Workers controlled via FRAUDAI_WORKERS env var (default 1 in CMD, override in compose)
CMD ["python", "-m", "uvicorn", "fraudai.api.app:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
