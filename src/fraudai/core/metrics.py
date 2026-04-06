"""Prometheus metrics registry for FraudAI Agent.

Centralises all application metrics in one module so that instrumented
components import metric objects directly rather than constructing their
own.  The registry uses the default ``prometheus_client`` global
registry.

Bucket boundaries are aligned with the F2 specification SLAs:
- Donna routing P95 < 1.5 s
- RAG retrieval P95 < 200 ms
- Agent first response P95 < 5 s
- Sandbox execution P95 < 300 s (100 MB dataset)

Reference: F2 spec section 5.1 (SLAs por operacion).
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# ---------------------------------------------------------------------------
# Request metrics
# ---------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "fraudai_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "fraudai_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# ---------------------------------------------------------------------------
# Agent metrics
# ---------------------------------------------------------------------------

AGENT_INVOCATIONS = Counter(
    "fraudai_agent_invocations_total",
    "Agent invocations",
    ["agent_name"],
)

AGENT_LATENCY = Histogram(
    "fraudai_agent_duration_seconds",
    "Agent response time",
    ["agent_name"],
    buckets=[1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

ROUTING_ACCURACY = Counter(
    "fraudai_routing_total",
    "Donna routing decisions",
    ["target_agent", "confidence_bucket"],  # confidence_bucket: high/medium/low
)

# ---------------------------------------------------------------------------
# RAG metrics
# ---------------------------------------------------------------------------

RETRIEVAL_LATENCY = Histogram(
    "fraudai_retrieval_duration_seconds",
    "RAG retrieval latency",
    ["collection"],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0],
)

RETRIEVAL_RESULTS = Histogram(
    "fraudai_retrieval_results_count",
    "Number of results returned by retrieval",
    ["collection"],
    buckets=[0, 1, 5, 10, 20],
)

# ---------------------------------------------------------------------------
# Tool metrics
# ---------------------------------------------------------------------------

TOOL_CALLS = Counter(
    "fraudai_tool_calls_total",
    "Tool invocations",
    ["tool_name", "status"],  # status: success/error
)

TOOL_LATENCY = Histogram(
    "fraudai_tool_duration_seconds",
    "Tool execution time",
    ["tool_name"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# ---------------------------------------------------------------------------
# Sandbox metrics
# ---------------------------------------------------------------------------

SANDBOX_EXECUTIONS = Counter(
    "fraudai_sandbox_executions_total",
    "Sandbox container executions",
    ["status"],  # success/error/timeout
)

SANDBOX_DURATION = Histogram(
    "fraudai_sandbox_duration_seconds",
    "Sandbox execution time",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

# ---------------------------------------------------------------------------
# Token metrics
# ---------------------------------------------------------------------------

TOKENS_USED = Counter(
    "fraudai_tokens_total",
    "LLM tokens consumed",
    ["agent_name", "direction"],  # direction: input/output
)

TOKEN_COST_ESTIMATED = Counter(
    "fraudai_token_cost_usd_total",
    "Estimated token cost in USD",
    ["agent_name"],
)

# ---------------------------------------------------------------------------
# Session metrics
# ---------------------------------------------------------------------------

ACTIVE_SESSIONS = Gauge(
    "fraudai_active_sessions",
    "Currently active sessions",
)

# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------

SYSTEM_INFO = Info(
    "fraudai",
    "FraudAI Agent system information",
)
