#!/usr/bin/env bash
set -euo pipefail

echo "=== FraudAI Agent — Live Smoke Tests ==="
echo ""

# Check backend
if ! curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "ERROR: Backend not running on :8000"
    echo "Start it with: .venv/bin/python3 -m uvicorn fraudai.api.app:create_app --factory --host 0.0.0.0 --port 8000"
    exit 1
fi

echo "Backend healthy. Running tests..."
echo ""

.venv/bin/python3 -m pytest tests/test_smoke_live.py -v --tb=short "$@"
