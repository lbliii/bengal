"""
ASGI application for Bengal dev server.

Provides create_bengal_dev_app() for Pounce/ASGI backends. Handles SSE live
reload, static file serving with HTML injection, and build-aware behavior.
"""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bengal.server.live_reload import LIVE_RELOAD_SCRIPT, run_sse_loop
from bengal.server.responses import get_rebuilding_page_html
from bengal.server.utils import find_html_injection_point, get_content_type

# ASGI app type: async (scope, receive, send) -> None
ASGIApp = Callable[..., Any]


def create_bengal_dev_app(
    *,
    output_dir: Path,
    build_in_progress: Callable[[], bool],
    active_palette: Callable[[], str | None] | str | None = None,
    sse_keepalive_interval: float | None = None,
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
    return app


def _inject_live_reload_into_html(content: bytes) -> bytes:
    """Inject live reload script into HTML body before </body> or </html>."""
    script_bytes = LIVE_RELOAD_SCRIPT.encode("utf-8")
    idx = find_html_injection_point(content)
    if idx != -1:
        return content[:idx] + script_bytes + content[idx:]
    return content + script_bytes


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
    if not str(full).startswith(str(base)):
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
    """Serve static files with HTML injection and build-aware rebuilding page."""
    # Build in progress + HTML path -> rebuilding page
    if build_in_progress() and _is_html_path(path):
        palette = (
            active_palette() if callable(active_palette) else active_palette
        )
        html = get_rebuilding_page_html(path, palette)
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"text/html; charset=utf-8"],
                    [b"content-length", str(len(html)).encode()],
                    [b"cache-control", b"no-store, no-cache, must-revalidate, max-age=0"],
                ],
            }
        )
        await send({"type": "http.response.body", "body": html})
        return

    resolved = _resolve_file_path(output_dir, path)
    if resolved is None:
        await _send_404(send, output_dir=output_dir)
        return

    # Directory -> try index.html
    if resolved.is_dir():
        for name in ("index.html", "index.htm"):
            candidate = resolved / name
            if candidate.is_file():
                resolved = candidate
                break
        else:
            await _send_404(send)
            return

    if not resolved.is_file():
        await _send_404(send, output_dir=output_dir)
        return

    content = resolved.read_bytes()
    content_type = get_content_type(str(resolved))

    # HTML: inject live reload script
    if content_type.startswith("text/html"):
        content = _inject_live_reload_into_html(content)

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


async def _send_404(send: Any, *, output_dir: Path | None = None) -> None:
    """Send 404. If output_dir has 404.html, serve it with injection."""
    body = b"Not Found"
    content_type = b"text/plain"
    if output_dir is not None:
        custom_404 = output_dir / "404.html"
        if custom_404.is_file():
            body = custom_404.read_bytes()
            body = _inject_live_reload_into_html(body)
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
