"""Shared runtime error helpers for consistent observability and fail-policy handling."""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeErrorContext:
    subsystem: str
    critical: bool = False


def log_runtime_exception(logger: logging.Logger, exc: Exception, context: RuntimeErrorContext) -> None:
    """Emit structured error logs with traceback and subsystem metadata."""
    severity = "CRITICAL" if context.critical else "ERROR"
    logger.error(
        "[%s] subsystem=%s type=%s message=%s",
        severity,
        context.subsystem,
        type(exc).__name__,
        str(exc),
    )
    logger.debug("Traceback for subsystem=%s\n%s", context.subsystem, traceback.format_exc())
