"""
SSE event loop and reload state for live reload.

Provides run_sse_loop (sync, for LiveReloadMixin), wait_for_sse_event (for
async ASGI handler), ReloadState, and shutdown/reset helpers.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class ReloadState:
    """Encapsulates live reload SSE state (generation, action, condition)."""

    def __init__(self) -> None:
        self.generation: int = 0
        self.last_action: str = "reload"
        self.sent_count: int = 0
        self.condition = threading.Condition()
        self.shutdown_requested: bool = False


_state = ReloadState()


def _reload_events_disabled() -> bool:
    """Check if reload events are disabled via env."""
    try:
        val = (os.environ.get("BENGAL_DISABLE_RELOAD_EVENTS", "") or "").strip().lower()
        return val in ("1", "true", "yes", "on")
    except Exception:
        return False


def _get_keepalive_interval() -> float:
    """Get keepalive interval from env (default 15s, clamped 5-120)."""
    try:
        ka_env = os.environ.get("BENGAL_SSE_KEEPALIVE_SECS", "15").strip()
        return float(max(5, min(120, int(ka_env))))
    except Exception as e:
        logger.debug("keepalive_env_parse_failed", error=str(e))
        return 15.0


def get_current_generation() -> int:
    """Return the current reload generation (thread-safe snapshot)."""
    return _state.generation


def wait_for_sse_event(
    last_seen_generation: int,
    timeout: float,
) -> tuple[bytes, int] | None:
    """Block until an SSE event is available or timeout expires (keepalive).

    Designed to be called via ``asyncio.to_thread`` from the ASGI SSE handler.
    Each call performs a single ``Condition.wait`` and returns immediately with
    either the reload payload or a keepalive comment.

    Returns:
        ``(chunk_bytes, new_generation)`` on event/keepalive, or ``None`` on shutdown.
    """
    with _state.condition:
        if _state.shutdown_requested:
            return None
        _state.condition.wait(timeout=timeout)
        if _state.shutdown_requested:
            return None
        current_gen = _state.generation
        action = _state.last_action if current_gen != last_seen_generation else None

    if action is not None:
        return (f"data: {action}\n\n".encode(), current_gen)
    return (b": keepalive\n\n", last_seen_generation)


def run_sse_loop(
    write_fn: Callable[[bytes], None],
    *,
    keepalive_interval: float | None = None,
) -> tuple[int, int]:
    """
    Run the SSE event loop, yielding retry, connected, data events, and keepalives.

    Transport-agnostic: call write_fn with each chunk of bytes to send.
    Used by LiveReloadMixin (http.server path). The ASGI path uses
    wait_for_sse_event() instead.
    """
    interval = keepalive_interval if keepalive_interval is not None else _get_keepalive_interval()
    message_count = 0
    keepalive_count = 0

    write_fn(b"retry: 2000\n\n")
    write_fn(b": connected\n\n")

    last_seen_generation = _state.generation

    while True:
        with _state.condition:
            if _state.shutdown_requested:
                break
            _state.condition.wait(timeout=interval)
            if _state.shutdown_requested:
                break
            current_generation = _state.generation
            pending_action = (
                _state.last_action if current_generation != last_seen_generation else None
            )

        if pending_action is not None:
            write_fn(f"data: {pending_action}\n\n".encode())
            message_count += 1
            last_seen_generation = current_generation
        else:
            write_fn(b": keepalive\n\n")
            keepalive_count += 1

    return (message_count, keepalive_count)


def shutdown_sse_clients() -> None:
    """Signal all SSE handlers to exit gracefully."""
    with _state.condition:
        _state.shutdown_requested = True
        _state.condition.notify_all()
    logger.info("sse_shutdown_requested")


def reset_sse_shutdown() -> None:
    """Reset the shutdown flag for a fresh server start."""
    with _state.condition:
        _state.shutdown_requested = False
    logger.debug("sse_shutdown_reset")
