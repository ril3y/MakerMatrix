"""
Startup step abstraction for the application lifespan handler.

A StartupStep is a named, awaitable unit of work with a `required` flag:
- Required steps: failures abort startup (re-raise).
- Optional steps: failures are logged with full traceback and execution continues.

This replaces ~170 lines of inline lifespan code with a small declarative list
that's trivial to read, reorder, and unit-test.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StartupStep:
    """
    A single piece of work run during application startup.

    Attributes:
        name: Human-readable description used in logs ("Initialize rate limiter").
        run: Async callable returning None or any value. Result is logged but
            otherwise ignored.
        required: If True, raising from `run` aborts startup. If False, the
            exception is logged via `logger.exception` and the remaining steps
            still execute.
    """

    name: str
    run: Callable[[], Awaitable[Optional[object]]]
    required: bool = False


async def run_startup_steps(
    steps: Iterable[StartupStep],
    logger_: Optional[logging.Logger] = None,
) -> List[str]:
    """
    Execute startup steps in order, honoring the `required` flag.

    Args:
        steps: The steps to run, in declaration order.
        logger_: Optional logger override (default: module logger).

    Returns:
        List of step names that completed successfully. Useful for tests and
        smoke checks.

    Raises:
        Whatever a required step raises (after logging the failure).
    """
    log = logger_ or logger
    completed: List[str] = []
    for step in steps:
        log.info("Startup step: %s", step.name)
        try:
            await step.run()
        except Exception:
            if step.required:
                log.exception("Required startup step failed: %s", step.name)
                raise
            log.exception("Optional startup step failed, continuing: %s", step.name)
            continue
        completed.append(step.name)
    return completed
