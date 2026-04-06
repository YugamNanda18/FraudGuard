#!/usr/bin/env bash
# =============================================================================
# FraudAI Agent -- Production Deployment Script
#
# Usage: ./scripts/deploy.sh [--skip-sandbox] [--no-pull-model]
#
# Steps:
#   1. Validate prerequisites
#   2. Build sandbox image
#   3. Build app image
#   4. Start all services
#   5. Wait for health checks
#   6. Pull Ollama model
#   7. Run smoke test
#   8. Print endpoints
#
# Reference: ADR-006
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_DIR}/.env"

MAX_RETRIES=30
RETRY_INTERVAL=2

SKIP_SANDBOX=false
NO_PULL_MODEL=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

for arg in "$@"; do
    case $arg in
        --skip-sandbox) SKIP_SANDBOX=true ;;
        --no-pull-model) NO_PULL_MODEL=true ;;
        --help|-h)
            echo "Usage: $0 [--skip-sandbox] [--no-pull-model]"
            echo ""
            echo "Options:"
            echo "  --skip-sandbox    Skip building the sandbox Docker image"
            echo "  --no-pull-model   Skip pulling the Ollama model"
            exit 0
            ;;
        *)
            echo -e "${RED}[!] Unknown argument: $arg${NC}"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log_info()  { echo -e "${GREEN}[+]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[~]${NC} $*"; }
log_error() { echo -e "${RED}[!]${NC} $*"; }

wait_for_healthy() {
    local service_name="$1"
    local url="$2"
    local retries="${3:-$MAX_RETRIES}"

    log_warn "Waiting for ${service_name} to be healthy..."
    for i in $(seq 1 "$retries"); do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_info "${service_name} is healthy."
            return 0
        fi
        if [[ $i -eq $retries ]]; then
            log_error "${service_name} failed to become healthy after $((retries * RETRY_INTERVAL))s."
            return 1
        fi
        sleep "$RETRY_INTERVAL"
    done
}

# ---------------------------------------------------------------------------
# 0. Validate prerequisites
# ---------------------------------------------------------------------------

cd "$PROJECT_DIR"

log_info "Validating prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "docker is not installed. Aborting."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    log_error "docker compose plugin is not available. Aborting."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env file not found. Copy .env.example and configure it:"
    log_error "  cp .env.example .env"
    exit 1
fi

log_info "Prerequisites validated."

# ---------------------------------------------------------------------------
# 1. Build sandbox image
# ---------------------------------------------------------------------------

if [[ "$SKIP_SANDBOX" == "false" ]]; then
    log_info "Building sandbox image (fraudai-sandbox:latest)..."
    docker compose -f "$COMPOSE_FILE" --profile build build sandbox
    log_info "Sandbox image built."
else
    log_warn "Skipping sandbox image build (--skip-sandbox)."
fi

# ---------------------------------------------------------------------------
# 2. Build app image
# ---------------------------------------------------------------------------

log_info "Building FraudAI Agent image..."
docker compose -f "$COMPOSE_FILE" build fraudai
log_info "FraudAI Agent image built."

# ---------------------------------------------------------------------------
# 3. Tag current images for rollback
# ---------------------------------------------------------------------------

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
log_info "Tagging current images for rollback (tag: ${TIMESTAMP})..."

# Tag only if the image exists (first deploy won't have a previous image)
if docker image inspect fraudai-agent:latest &> /dev/null 2>&1; then
    docker tag fraudai-agent:latest "fraudai-agent:rollback-${TIMESTAMP}"
    log_info "Tagged fraudai-agent:rollback-${TIMESTAMP}"
fi

# ---------------------------------------------------------------------------
# 4. Start all services
# ---------------------------------------------------------------------------

log_info "Starting all services..."
docker compose -f "$COMPOSE_FILE" up -d
log_info "Services started."

# ---------------------------------------------------------------------------
# 5. Wait for health checks
# ---------------------------------------------------------------------------

wait_for_healthy "Qdrant" "http://localhost:6333/healthz" "$MAX_RETRIES"
wait_for_healthy "Ollama" "http://localhost:11434/api/tags" "$MAX_RETRIES"

# ---------------------------------------------------------------------------
# 6. Pull Ollama model
# ---------------------------------------------------------------------------

if [[ "$NO_PULL_MODEL" == "false" ]]; then
    OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b-instruct-q4_K_M}"
    log_warn "Pulling Ollama model: ${OLLAMA_MODEL} (this may take a while)..."
    docker compose -f "$COMPOSE_FILE" exec ollama ollama pull "$OLLAMA_MODEL"
    log_info "Model pulled: ${OLLAMA_MODEL}"
else
    log_warn "Skipping Ollama model pull (--no-pull-model)."
fi

# FraudAI needs Ollama + model ready before it can pass health fully
FRAUDAI_PORT="${FRAUDAI_PORT:-8000}"
wait_for_healthy "FraudAI Agent" "http://localhost:${FRAUDAI_PORT}/api/v1/health" 60

# ---------------------------------------------------------------------------
# 7. Smoke test
# ---------------------------------------------------------------------------

log_info "Running smoke test..."
HEALTH_RESPONSE=$(curl -sf "http://localhost:${FRAUDAI_PORT}/api/v1/health" 2>&1) || {
    log_error "Smoke test FAILED: /api/v1/health not reachable."
    log_error "Check logs: docker compose -f $COMPOSE_FILE logs fraudai"
    exit 1
}

log_info "Smoke test passed. Health response:"
echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"

# ---------------------------------------------------------------------------
# 8. Print endpoints
# ---------------------------------------------------------------------------

echo ""
echo "============================================"
echo "  FraudAI Agent -- Production Deployment"
echo "============================================"
echo "  API           : http://localhost:${FRAUDAI_PORT}/api/v1"
echo "  Health        : http://localhost:${FRAUDAI_PORT}/api/v1/health"
echo "  Docs (Swagger): http://localhost:${FRAUDAI_PORT}/docs"
echo "  Docs (ReDoc)  : http://localhost:${FRAUDAI_PORT}/redoc"
echo "  Qdrant REST   : http://localhost:6333"
echo "  Qdrant gRPC   : localhost:6334"
echo "  Ollama        : http://localhost:11434"
echo "============================================"
echo ""
echo "  Rollback tag: fraudai-agent:rollback-${TIMESTAMP}"
echo "  Rollback cmd: ./scripts/rollback.sh rollback-${TIMESTAMP}"
echo ""
