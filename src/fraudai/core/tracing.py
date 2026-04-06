"""Lightweight distributed tracing via correlation IDs.

Provides a ``contextvars``-based correlation ID that propagates through
async call chains and is injected into every log record by
:class:`CorrelationFilter`.  This is the MVP tracing strategy --
lightweight and dependency-free -- suitable for log-based observability
before adopting a full OpenTelemetry collector pipeline.

Usage::

    from fraudai.core.tracing import new_correlation_id, correlation_id

    cid = new_correlation_id()           # sets + returns "abc12345"
    logger.info("processing request")    # log includes correlation_id=abc12345

Reference: F2 spec section 5.3 -- monitoring and observability.
"""

from __future__ import annotations

import contextvars
import logging
import uuid

# ---------------------------------------------------------------------------
# Context variable -- propagates through async call chains
# ---------------------------------------------------------------------------

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id",
    default="",
)


# ---------------------------------------------------------------------------
# Logging filter
# ---------------------------------------------------------------------------


class CorrelationFilter(logging.Filter):
    """Injects ``correlation_id`` into every log record.

    Attach this filter to the root logger (or a handler) so that all
    formatters can reference ``%(correlation_id)s``.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get("")  # type: ignore[attr-defined]
        return True


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

_TRACING_FORMAT = (
    "%(asctime)s [%(levelname)s] [cid=%(correlation_id)s] "
    "%(name)s: %(message)s"
)


def setup_tracing(level: int = logging.INFO) -> None:
    """Configure structured logging with correlation IDs.

    Adds a :class:`CorrelationFilter` to the root logger so that every
    log record gets a ``correlation_id`` attribute.  Only sets the custom
    formatter on handlers that *we* create -- external handlers (e.g.
    pytest's capture handler) are left untouched to avoid format key
    errors in third-party formatters.

    Safe to call multiple times -- it checks for an existing filter first.
    """
    root = logging.getLogger()

    # Avoid adding the filter twice (idempotent setup).
    if any(isinstance(f, CorrelationFilter) for f in root.filters):
        return

    root.addFilter(CorrelationFilter())
    root.setLevel(level)

    # Only create and configure a handler if none exist.
    # We intentionally do NOT modify existing handlers' formatters
    # because external test/logging frameworks may not expect
    # %(correlation_id)s in their format strings.
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_TRACING_FORMAT))
        root.addHandler(handler)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def new_correlation_id() -> str:
    """Generate and set a new correlation ID for the current context.

    Returns:
        The 8-character hex correlation ID.
    """
    cid = uuid.uuid4().hex[:8]
    correlation_id.set(cid)
    return cid
