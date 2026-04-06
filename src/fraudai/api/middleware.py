"""FastAPI middleware for Prometheus metrics and request tracing.

Records per-request latency and counts in Prometheus histograms /
counters, and propagates a correlation ID via ``X-Correlation-ID``
header for log-based distributed tracing.

Reference: F2 spec section 5.1 -- SLA monitoring.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from fraudai.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from fraudai.core.tracing import new_correlation_id

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records Prometheus metrics for every request.

    For each incoming request this middleware:
    1. Generates a new correlation ID and stores it in the context.
    2. Measures wall-clock latency.
    3. Records ``fraudai_request_duration_seconds`` (histogram).
    4. Increments ``fraudai_requests_total`` (counter) with status code.
    5. Adds ``X-Correlation-ID`` to the response headers.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        cid = new_correlation_id()

        # Normalise path to avoid high-cardinality label explosion.
        # Use the route pattern (e.g. "/api/v1/chat") when available,
        # otherwise fall back to a sanitised version of the raw path.
        endpoint = request.url.path
        method = request.method

        start = time.monotonic()
        response: Response = await call_next(request)
        duration = time.monotonic() - start

        status_code = str(response.status_code)

        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()

        response.headers["X-Correlation-ID"] = cid

        return response
