"""
ASGI application for Bengal dev server.

Provides create_bengal_dev_app() for Pounce/ASGI backends. Handles SSE live
reload and static file serving (with HTML injection when wired).
"""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bengal.server.live_reload import run_sse_loop

# ASGI app type: async (scope, receive, send) -> None
ASGIApp = Callable[..., Any]


def create_bengal_dev_app(
    *,
    output_dir: Path,
    build_in_progress: Callable[[], bool],
    active_palette: str | None = None,
    sse_keepalive_interval: float | None = None,
) -> ASGIApp:
    """
    Create an ASGI app for Bengal dev server.

    Handles GET /__bengal_reload__ with SSE live reload stream. All other
    paths return 404 until static serving is wired (Phase 1.2).

    Args:
        output_dir: Directory for static file serving (used when wired)
        build_in_progress: Callable returning True when a build is active
        active_palette: Theme for rebuilding page styling (used when wired)
        sse_keepalive_interval: Seconds between SSE keepalives (default from env).
            Use 0.05 for fast tests.

    Returns:
        ASGI application callable
    """

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        if method == "GET" and path == "/__bengal_reload__":
            await _handle_sse(send, keepalive_interval=sse_keepalive_interval)
            return

        # All other paths: 404 until static serving is wired
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"Not Found",
            }
        )

    return app


async def _handle_sse(send: Any, *, keepalive_interval: float | None = None) -> None:
    """Handle GET /__bengal_reload__ with SSE stream via thread/queue bridge."""
    q: queue.Queue[bytes | None] = queue.Queue()
    client_disconnected = threading.Event()

    def write_fn(chunk: bytes) -> None:
        if client_disconnected.is_set():
            raise ConnectionResetError("Client disconnected")
        q.put(chunk)

    def run_sse_thread() -> None:
        try:
            run_sse_loop(write_fn, keepalive_interval=keepalive_interval)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            q.put(None)  # Sentinel: run_sse_loop finished

    thread = threading.Thread(target=run_sse_thread, daemon=True)
    thread.start()

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/event-stream"],
                [
                    b"cache-control",
                    b"no-store, no-cache, must-revalidate, max-age=0, private, no-transform",
                ],
                [b"connection", b"keep-alive"],
                [b"x-accel-buffering", b"no"],
                [b"access-control-allow-origin", b"*"],
            ],
        }
    )

    try:
        while True:
            try:
                chunk = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue
            if chunk is None:
                break
            await send(
                {
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                }
            )
    except (ConnectionResetError, BrokenPipeError, OSError):
        client_disconnected.set()
    finally:
        try:
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                }
            )
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
