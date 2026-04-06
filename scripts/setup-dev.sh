#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 1. Copy .env.example to .env if it doesn't exist
if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "[+] Created .env from .env.example — edit it with your API keys."
else
    echo "[=] .env already exists, skipping copy."
fi

# 2. Start services
echo "[+] Starting Docker Compose services..."
docker compose up -d

# 3. Wait for Qdrant to be healthy
echo "[~] Waiting for Qdrant to be healthy..."
MAX_RETRIES=30
RETRY_INTERVAL=2
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
        echo "[+] Qdrant is healthy."
        break
    fi
    if [[ $i -eq $MAX_RETRIES ]]; then
        echo "[!] Qdrant failed to become healthy after $((MAX_RETRIES * RETRY_INTERVAL))s."
        exit 1
    fi
    sleep $RETRY_INTERVAL
done

# 4. Wait for Ollama to be healthy
echo "[~] Waiting for Ollama to be healthy..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "[+] Ollama is healthy."
        break
    fi
    if [[ $i -eq $MAX_RETRIES ]]; then
        echo "[!] Ollama failed to become healthy after $((MAX_RETRIES * RETRY_INTERVAL))s."
        exit 1
    fi
    sleep $RETRY_INTERVAL
done

# 5. Pull the Llama 3.1 8B model
echo "[~] Pulling llama3.1:8b-instruct-q4_K_M (this may take a while)..."
docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M

# 6. Confirmation
echo ""
echo "============================================"
echo "  FraudAI Agent dev environment is ready!"
echo "  Qdrant REST : http://localhost:6333"
echo "  Qdrant gRPC : localhost:6334"
echo "  Ollama      : http://localhost:11434"
echo "  Model       : llama3.1:8b-instruct-q4_K_M"
echo "============================================"
