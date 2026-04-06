#!/usr/bin/env bash
# =============================================================================
# FraudAI Agent -- Rollback Script
#
# Usage:
#   ./scripts/rollback.sh <image-tag>
#   ./scripts/rollback.sh rollback-20260406_143000
#   ./scripts/rollback.sh --list   # List available rollback tags
#
# Steps:
#   1. Validate the rollback tag exists
#   2. Stop current FraudAI Agent service
#   3. Re-tag the rollback image as :latest
#   4. Start services with the restored image
#   5. Verify health
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

MAX_RETRIES=30
RETRY_INTERVAL=2

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

usage() {
    echo "Usage: $0 <rollback-tag>"
    echo "       $0 --list"
    echo ""
    echo "Arguments:"
    echo "  <rollback-tag>  Docker image tag to restore (e.g., rollback-20260406_143000)"
    echo "  --list          List all available rollback tags"
    echo ""
    echo "Example:"
    echo "  $0 rollback-20260406_143000"
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

if [[ $# -lt 1 ]]; then
    log_error "Missing required argument: rollback tag."
    echo ""
    usage
    exit 1
fi

case "$1" in
    --list)
        echo "Available rollback tags for fraudai-agent:"
        echo ""
        docker images fraudai-agent --format "  {{.Tag}}\t{{.CreatedAt}}\t{{.Size}}" | grep "rollback-" || {
            echo "  (no rollback tags found)"
        }
        exit 0
        ;;
    --help|-h)
        usage
        exit 0
        ;;
    *)
        ROLLBACK_TAG="$1"
        ;;
esac

# ---------------------------------------------------------------------------
# 0. Validate
# ---------------------------------------------------------------------------

cd "$PROJECT_DIR"

FULL_IMAGE="fraudai-agent:${ROLLBACK_TAG}"

log_info "Validating rollback image: ${FULL_IMAGE}..."

if ! docker image inspect "$FULL_IMAGE" &> /dev/null 2>&1; then
    log_error "Image not found: ${FULL_IMAGE}"
    log_error "Available tags:"
    docker images fraudai-agent --format "  {{.Tag}}\t{{.CreatedAt}}" | head -10
    exit 1
fi

log_info "Rollback image found: ${FULL_IMAGE}"

# ---------------------------------------------------------------------------
# 1. Save current :latest tag as pre-rollback backup
# ---------------------------------------------------------------------------

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if docker image inspect fraudai-agent:latest &> /dev/null 2>&1; then
    docker tag fraudai-agent:latest "fraudai-agent:pre-rollback-${TIMESTAMP}"
    log_info "Current :latest backed up as fraudai-agent:pre-rollback-${TIMESTAMP}"
fi

# ---------------------------------------------------------------------------
# 2. Stop current FraudAI Agent service (keep infra services running)
# ---------------------------------------------------------------------------

log_info "Stopping FraudAI Agent service..."
docker compose -f "$COMPOSE_FILE" stop fraudai
docker compose -f "$COMPOSE_FILE" rm -f fraudai
log_info "FraudAI Agent stopped."

# ---------------------------------------------------------------------------
# 3. Re-tag the rollback image as :latest
# ---------------------------------------------------------------------------

log_info "Restoring image: ${FULL_IMAGE} -> fraudai-agent:latest"
docker tag "$FULL_IMAGE" fraudai-agent:latest
log_info "Image re-tagged."

# ---------------------------------------------------------------------------
# 4. Start services with restored image
# ---------------------------------------------------------------------------

log_info "Starting FraudAI Agent with restored image..."
docker compose -f "$COMPOSE_FILE" up -d fraudai
log_info "FraudAI Agent started."

# ---------------------------------------------------------------------------
# 5. Verify health
# ---------------------------------------------------------------------------

FRAUDAI_PORT="${FRAUDAI_PORT:-8000}"

# Infrastructure should already be running
wait_for_healthy "Qdrant" "http://localhost:6333/healthz" 10
wait_for_healthy "Ollama" "http://localhost:11434/api/tags" 10
wait_for_healthy "FraudAI Agent" "http://localhost:${FRAUDAI_PORT}/api/v1/health" "$MAX_RETRIES"

# Smoke test
HEALTH_RESPONSE=$(curl -sf "http://localhost:${FRAUDAI_PORT}/api/v1/health" 2>&1) || {
    log_error "Rollback verification FAILED. Health endpoint not reachable."
    log_error "Check logs: docker compose -f $COMPOSE_FILE logs fraudai"
    exit 1
}

echo ""
echo "============================================"
echo "  Rollback Complete"
echo "============================================"
echo "  Restored image : ${FULL_IMAGE}"
echo "  Pre-rollback   : fraudai-agent:pre-rollback-${TIMESTAMP}"
echo "  Health status  :"
echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
echo "============================================"
