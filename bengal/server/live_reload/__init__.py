"""
Server-Sent Events (SSE) live reload for Bengal dev server.

Public API re-exports. Import from bengal.server.live_reload for backward compatibility.
"""

from __future__ import annotations

from .injection import inject_live_reload_into_response
from .mixin import HTTPHandlerProtocol, LiveReloadMixin
from .notification import (
    LiveReloadNotifier,
    notify_clients_reload,
    send_build_error_payload,
    send_build_ok_payload,
    send_reload_payload,
    set_reload_action,
)
from .script import LIVE_RELOAD_SCRIPT
from .sse import (
    ReloadState,
    get_current_generation,
    reset_for_testing,
    reset_sse_shutdown,
    run_sse_loop,
    shutdown_sse_clients,
    wait_for_sse_event,
)

__all__ = [
    "LIVE_RELOAD_SCRIPT",
    "HTTPHandlerProtocol",
    "LiveReloadMixin",
    "LiveReloadNotifier",
    "ReloadState",
    "get_current_generation",
    "inject_live_reload_into_response",
    "notify_clients_reload",
    "reset_for_testing",
    "reset_sse_shutdown",
    "run_sse_loop",
    "send_build_error_payload",
    "send_build_ok_payload",
    "send_reload_payload",
    "set_reload_action",
    "shutdown_sse_clients",
    "wait_for_sse_event",
]


def __getattr__(name: str) -> object:
    """Backward compatibility: expose _state attributes for tests."""
    from . import sse

    if name == "_shutdown_requested":
        return sse._state.shutdown_requested
    if name == "_reload_generation":
        return sse._state.generation
    if name == "_last_action":
        return sse._state.last_action
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
