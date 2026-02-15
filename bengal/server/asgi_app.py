"""
ASGI application for Bengal dev server.

Provides create_bengal_dev_app() for Pounce/ASGI backends. Handles SSE live
reload, static file serving with HTML injection, and build-aware behavior.
"""

from __future__ import annotations

import asyncio
import contextlib
import queue
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bengal.server.live_reload import LIVE_RELOAD_SCRIPT, run_sse_loop
from bengal.server.responses import get_rebuilding_badge_script
from bengal.server.utils import find_html_injection_point, get_content_type

# ASGI app type: async (scope, receive, send) -> None
ASGIApp = Callable[..., Any]

# Type for request callback: (method, path, status, duration_ms) -> None
RequestCallback = Callable[[str, str, int, float], None]

# Getter for lazy callback resolution (set after backend creation)
RequestCallbackGetter = Callable[[], RequestCallback | None]


def create_bengal_dev_app(
    *,
    output_dir: Path,
    build_in_progress: Callable[[], bool],
    active_palette: Callable[[], str | None] | str | None = None,
    sse_keepalive_interval: float | None = None,
    request_callback: RequestCallbackGetter | None = None,
) -> ASGIApp:
    """
    Create an ASGI app for Bengal dev server.

    Handles GET /__bengal_reload__ with SSE live reload stream. All other
    GET paths are served as static files with HTML injection and build-aware
    behavior (rebuilding page during builds).

    Args:
        output_dir: Directory for static file serving
        build_in_progress: Callable returning True when a build is active
        active_palette: Callable returning current palette, or static value
        sse_keepalive_interval: Seconds between SSE keepalives (default from env).
            Use 0.05 for fast tests.
        request_callback: Optional getter returning (method, path, status, duration_ms)
            callback for request logging. Only invoked for document requests (not static
            assets). Getter allows callback to be set after backend creation.

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

        if method == "GET":
            await _serve_static(
                send,
                output_dir=output_dir,
                path=path,
                build_in_progress=build_in_progress,
                active_palette=active_palette,
            )
            return

        await _send_404(send, output_dir=output_dir)

    if request_callback is not None:
        return _request_logging_middleware(app, request_callback)
    return app


def _is_document_request(path: str) -> bool:
    """True if path is a document request worth logging (HTML, key JSON)."""
    if path.startswith(("/assets/", "/bengal/")):
        return False
    path_lower = path.lower()
    static_extensions = (
        ".woff2",
        ".woff",
        ".ttf",
        ".otf",
        ".eot",
        ".css",
        ".js",
        ".map",
        ".ico",
        ".webmanifest",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".avif",
    )
    return not any(path_lower.endswith(ext) for ext in static_extensions)


def _request_logging_middleware(
    app: ASGIApp,
    request_callback: RequestCallbackGetter,
) -> ASGIApp:
    """Wrap app to log document requests via callback on response complete."""

    async def wrapped(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "")
        start = time.perf_counter()
        status = 500

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status
            if message.get("type") == "http.response.start":
                status = message.get("status", 500)
            await send(message)

        try:
            await app(scope, receive, send_wrapper)
        finally:
            if _is_document_request(path):
                cb = request_callback()
                if cb is not None:
                    duration_ms = (time.perf_counter() - start) * 1000
                    with contextlib.suppress(Exception):
                        cb(method, path, status, duration_ms)

    return wrapped


def _inject_live_reload_into_html(content: bytes) -> bytes:
    """Inject live reload script into HTML body before </body> or </html>."""
    script_bytes = LIVE_RELOAD_SCRIPT.encode("utf-8")
    idx = find_html_injection_point(content)
    if idx != -1:
        return content[:idx] + script_bytes + content[idx:]
    return content + script_bytes


def _inject_rebuilding_badge_into_html(content: bytes) -> bytes:
    """Inject small rebuilding badge into HTML when build is in progress."""
    badge_bytes = get_rebuilding_badge_script().encode("utf-8")
    idx = find_html_injection_point(content)
    if idx != -1:
        return content[:idx] + badge_bytes + content[idx:]
    return content + badge_bytes


def _is_html_path(path: str) -> bool:
    """True if path looks like an HTML request (no extension, .html, .htm, or dir)."""
    stripped = path.rstrip("/").split("/")[-1] if "/" in path else path
    if "." not in stripped:
        return True
    ext = stripped.split(".")[-1].lower()
    return ext in ("html", "htm")


def _resolve_file_path(output_dir: Path, path: str) -> Path | None:
    """
    Resolve request path to filesystem path under output_dir.

    Handles / -> index.html, trailing slash -> index.html, path traversal.
    Returns None if path escapes output_dir or is invalid.
    """
    base = output_dir.resolve()
    raw = path.split("?")[0].lstrip("/")
    if not raw:
        raw = "index.html"
    elif raw.endswith("/"):
        raw = raw + "index.html"
    full = (base / raw).resolve()
    try:
        full.relative_to(base)
    except ValueError:
        return None
    return full


async def _serve_static(
    send: Any,
    *,
    output_dir: Path,
    path: str,
    build_in_progress: Callable[[], bool],
    active_palette: Callable[[], str | None] | str | None,
) -> None:
    """Serve static files with HTML injection and build-aware behavior.

    When a build is in progress, serves cached content (if available) with a
    small rebuilding badge injected. Missing files return 404 (with badge on
    404.html). Never replaces the page with a full rebuilding placeholder.
    """
    resolved = _resolve_file_path(output_dir, path)
    if resolved is None:
        await _send_404(send, output_dir=output_dir, build_in_progress=build_in_progress)
        return

    # Directory -> try index.html
    if resolved.is_dir():
        for name in ("index.html", "index.htm"):
            candidate = resolved / name
            if candidate.is_file():
                resolved = candidate
                break
        else:
            resolved = resolved / "index.html"  # Expected path for 404 case

    # File doesn't exist: always 404 (with badge when build in progress)
    if not resolved.is_file():
        await _send_404(send, output_dir=output_dir, build_in_progress=build_in_progress)
        return

    content = await asyncio.to_thread(resolved.read_bytes)
    content_type = get_content_type(str(resolved))

    # HTML: inject live reload script; add rebuilding badge when build in progress
    if content_type.startswith("text/html"):
        content = _inject_live_reload_into_html(content)
        if build_in_progress():
            content = _inject_rebuilding_badge_into_html(content)

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", content_type.encode()],
                [b"content-length", str(len(content)).encode()],
                [b"cache-control", b"no-store, no-cache, must-revalidate, max-age=0"],
            ],
        }
    )
    await send({"type": "http.response.body", "body": content})


async def _send_404(
    send: Any,
    *,
    output_dir: Path | None = None,
    build_in_progress: Callable[[], bool] | None = None,
) -> None:
    """Send 404. If output_dir has 404.html, serve it with injection."""
    body = b"Not Found"
    content_type = b"text/plain"
    if output_dir is not None:
        custom_404 = output_dir / "404.html"
        if custom_404.is_file():
            body = await asyncio.to_thread(custom_404.read_bytes)
            body = _inject_live_reload_into_html(body)
            if build_in_progress is not None and build_in_progress():
                body = _inject_rebuilding_badge_into_html(body)
            content_type = b"text/html; charset=utf-8"

    await send(
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [
                [b"content-type", content_type],
                [b"content-length", str(len(body)).encode()],
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


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
            chunk = await asyncio.to_thread(q.get)
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
        with contextlib.suppress(ConnectionResetError, BrokenPipeError, OSError):
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                }
            )
