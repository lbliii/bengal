"""
HTTP request handler for Bengal dev server.

Provides the main request handler that combines file serving, live reload
injection, and custom error pages.

Features:
- Automatic live reload script injection into HTML responses
- Custom 404.html page support (serves user's error page if present)
- Rebuild-aware directory listing (shows "rebuilding" page during builds)
- Build-aware CSS/JS caching (serves cached assets during builds)
- HTML response caching for rapid navigation
- Cache-busting headers for development

Classes:
BengalRequestHandler: Main HTTP handler combining all features

Architecture:
The handler uses multiple inheritance (mixins) to compose functionality:
- RequestLogger: Beautiful HTTP request logging
- LiveReloadMixin: SSE endpoint and script injection
- SimpleHTTPRequestHandler: Base file serving

Request flow:
1. SSE endpoint (/__bengal_reload__) → LiveReloadMixin.handle_sse()
2. HTML files → inject live reload script via mixin
3. Other files → default SimpleHTTPRequestHandler behavior

Related:
- bengal/server/live_reload.py: LiveReloadMixin implementation
- bengal/server/request_logger.py: RequestLogger mixin
- bengal/server/dev_server.py: Creates and manages this handler

"""

from __future__ import annotations

import http.server
import io
import os
import time
from collections.abc import Callable
from http.client import HTTPMessage
from pathlib import Path
from typing import Any, override

from bengal.server.build_state import build_state
from bengal.server.live_reload import LiveReloadMixin
from bengal.server.request_logger import RequestLogger
from bengal.server.responses import get_rebuilding_page_html
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class BengalRequestHandler(RequestLogger, LiveReloadMixin, http.server.SimpleHTTPRequestHandler):
    """
    HTTP request handler for Bengal dev server with live reload and error pages.

    Combines multiple mixins to provide a complete development experience:
    - RequestLogger: Beautiful, filtered HTTP request logging
    - LiveReloadMixin: SSE endpoint and automatic script injection
    - SimpleHTTPRequestHandler: Static file serving

    Features:
        - Live reload script auto-injection into HTML pages
        - Server-Sent Events endpoint at /__bengal_reload__
        - Custom 404.html page support
        - "Rebuilding" placeholder during active builds
        - HTML response caching (LRU, 50 pages)
        - Aggressive cache-busting headers

    Dashboard Integration (RFC: rfc-dashboard-api-integration):
        - on_request callback: Called for each HTTP request with method, path, status, and duration.
          Enables real-time request logging display in the dev server dashboard.

    Class Attributes:
        server_version: HTTP server version header ("Bengal/1.0")
        protocol_version: HTTP protocol version ("HTTP/1.1" for keep-alive)
        _html_cache: LRU cache for injected HTML (inherited from LiveReloadMixin)
        _build_in_progress: Flag indicating active rebuild
        _active_palette: Theme for rebuilding page styling
        _on_request: Optional callback for request logging (method, path, status_code, duration_ms)

    Thread Safety:
        - _html_cache is protected by _html_cache_lock (from LiveReloadMixin)
        - _build_in_progress is protected by _build_lock
        - Safe for use with ThreadingTCPServer

    Example:
            >>> from functools import partial
            >>> handler = partial(BengalRequestHandler, directory="/path/to/public")
            >>> server = TCPServer(("localhost", 5173), handler)

    """

    # Suppress default server version header
    server_version = "Bengal/1.0"
    sys_version = ""
    # Ensure HTTP/1.1 for proper keep-alive behavior on SSE
    protocol_version = "HTTP/1.1"

    # Note: _html_cache, _html_cache_max_size, _html_cache_lock are inherited from LiveReloadMixin
    # to avoid circular import. Access via BengalRequestHandler._html_cache still works.

    # Build state: shared via build_state module (BuildTrigger/dev_server write, handler reads)

    # Request logging callback for dashboard integration (RFC: rfc-dashboard-api-integration)
    # Signature: (method: str, path: str, status_code: int, duration_ms: float) -> None
    _on_request: Callable[[str, str, int, float], None] | None = None

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        """
        Initialize the request handler with optional directory override.

        Pre-initializes HTTP attributes (headers, request_version, etc.) to
        avoid AttributeError when tests bypass normal request parsing. The
        parent class sets these properly during real HTTP handling.

        Args:
            *args: Positional arguments passed to SimpleHTTPRequestHandler
            directory: Root directory for file serving. Avoids os.getcwd() call
                      which can fail if CWD is deleted during rebuilds.
            **kwargs: Additional keyword arguments for parent class
        """
        # Pass directory to parent to avoid os.getcwd() call (which fails if CWD is deleted during rebuilds)
        if directory is not None:
            super().__init__(*args, directory=directory, **kwargs)
        else:
            super().__init__(*args, **kwargs)
        # Initialize with empty HTTPMessage and default values for testing
        self.headers = HTTPMessage()
        self.request_version = "HTTP/1.1"
        self.requestline = ""
        self.command = ""  # HTTP command (GET, POST, etc.)

    # In dev, aggressively prevent browser caching to avoid stale assets
    def end_headers(self) -> None:
        try:
            # If cache headers not already set, add sensible dev defaults
            if (
                not any(
                    h.lower().startswith(b"cache-control:")
                    for h in getattr(self, "_headers_buffer", [])
                )
                and getattr(self, "path", "") != "/__bengal_reload__"
            ):
                from typing import cast

                from bengal.server.utils import HeaderSender, apply_dev_no_cache_headers

                apply_dev_no_cache_headers(cast(HeaderSender, self))
        except Exception as e:
            logger.debug(
                "dev_cache_header_application_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
        super().end_headers()

    @override
    def handle(self) -> None:
        """Override handle to suppress BrokenPipeError tracebacks."""
        import contextlib

        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            # Client disconnected - don't print traceback
            super().handle()

    @override
    def translate_path(self, path: str) -> str:
        """
        Override translate_path to ensure it never returns None.

        In Python 3.14, when self.directory is None and os.getcwd() fails,
        translate_path returns None. This causes crashes in the parent class's
        do_GET() -> send_head() -> os.path.isdir(path).

        We guard against this by falling back to the configured directory.
        """
        result = super().translate_path(path)
        if result is None:
            # Fallback to self.directory if translate_path fails
            # This can happen if os.getcwd() fails during rebuild
            if self.directory:
                return str(self.directory)
            # Last resort: return current file's directory
            return str(Path(__file__).parent)
        return result

    @override
    def do_GET(self) -> None:
        """
        Handle GET requests with live reload injection and special routes.

        Request routing (in priority order):
        1. /__bengal_reload__ → SSE endpoint (long-lived connection)
        2. *.html files → Inject live reload script, serve with cache
        3. CSS/JS assets → Build-aware caching (serves from cache during builds)
        4. Other files → Default SimpleHTTPRequestHandler behavior
        """
        request_start = time.time()
        status_code = 200  # Default, updated based on response

        try:
            # Handle SSE endpoint first (long-lived stream)
            # Skip request logging for SSE (it's long-lived)
            if self.path == "/__bengal_reload__":
                self.handle_sse()
                return

            # Try to serve HTML with injected live reload script
            # If not HTML or injection fails, fall back to normal file serving
            if not self.serve_html_with_live_reload():
                # Check build state for asset caching
                building = build_state.get_build_in_progress()

                # Try build-aware asset serving for CSS/JS
                # This ensures assets remain available during atomic file rewrites
                if not self.serve_asset_with_cache(building):
                    super().do_GET()
        except Exception:
            status_code = 500
            raise
        finally:
            # Capture actual status code from response if available
            # The _headers_buffer contains the status line after send_response()
            if hasattr(self, "_headers_buffer") and self._headers_buffer:
                try:
                    # First line is status line: "HTTP/1.1 200 OK\r\n"
                    first_line = self._headers_buffer[0]
                    if isinstance(first_line, bytes):
                        first_line = first_line.decode("latin-1")
                    parts = first_line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        status_code = int(parts[1])
                except (IndexError, ValueError, AttributeError):
                    pass  # Keep default status_code

            # Notify dashboard of request completion (RFC: rfc-dashboard-api-integration)
            # Skip SSE endpoint as it's long-lived
            if self.path != "/__bengal_reload__" and BengalRequestHandler._on_request is not None:
                duration_ms = (time.time() - request_start) * 1000
                try:
                    BengalRequestHandler._on_request("GET", self.path, status_code, duration_ms)
                except Exception as e:
                    logger.debug(
                        "request_callback_error",
                        path=self.path,
                        error=str(e),
                    )

    def _might_be_html(self, path: str) -> bool:
        """
        Fast pre-filter to check if a request path might return HTML.

        Used to avoid unnecessary response buffering for files that are
        definitely not HTML (CSS, JS, images, fonts, etc.).

        Args:
            path: URL path from request (e.g., "/blog/post" or "/assets/style.css")

        Returns:
            True if the path might return HTML (no extension, .html, .htm, or unknown).
            False if the path has a known non-HTML extension.
        """
        # Check if path has a non-HTML extension
        if "/" not in path:
            return True  # Root path

        last_segment = path.split("/")[-1]

        # If no dot in last segment, it's either a directory or no extension
        if "." not in last_segment:
            return True

        # Check extension
        extension = last_segment.split(".")[-1].lower()

        # Common non-HTML extensions
        non_html_extensions = {
            "css",
            "js",
            "json",
            "xml",
            "jpg",
            "jpeg",
            "png",
            "gif",
            "webp",
            "svg",
            "ico",
            "woff",
            "woff2",
            "ttf",
            "otf",
            "eot",
            "mp4",
            "webm",
            "mp3",
            "wav",
            "pdf",
            "zip",
            "tar",
            "gz",
            "txt",
            "md",
            "csv",
        }

        # Might be HTML (including .html, .htm, or unknown extensions)
        return extension not in non_html_extensions

    def _is_html_response(self, response_data: bytes) -> bool:
        """
        Determine if an HTTP response contains HTML content.

        Checks Content-Type header first (most reliable), then falls back
        to inspecting the response body for HTML markers.

        Args:
            response_data: Complete HTTP response bytes (headers + body)

        Returns:
            True if Content-Type is text/html or body contains HTML markers.
            False for non-HTML responses or malformed data.
        """
        try:
            # HTTP response format: headers\r\n\r\nbody
            if b"\r\n\r\n" not in response_data:
                return False

            headers_end = response_data.index(b"\r\n\r\n")
            headers_bytes = response_data[:headers_end]
            body = response_data[headers_end + 4 :]

            # Decode headers (HTTP headers are latin-1)
            headers = headers_bytes.decode("latin-1", errors="ignore")

            # Check Content-Type header (most reliable)
            for line in headers.split("\r\n"):
                if line.lower().startswith("content-type:"):
                    content_type = line.split(":", 1)[1].strip().lower()
                    # If Content-Type is present, trust it
                    return "text/html" in content_type

            # No Content-Type header - check body for HTML markers (fallback)
            body_lower = body.lower()
            return bool(b"<html" in body_lower or b"<!doctype html" in body_lower)

        except Exception as e:
            logger.debug("html_detection_failed", error=str(e), error_type=type(e).__name__)
            return False

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        """
        Override send_error to serve custom 404 page.

        Args:
            code: HTTP error code
            message: Error message
            explain: Detailed explanation
        """
        # If it's a 404 error, try to serve custom 404.html
        if code == 404 and self.directory is not None:
            custom_404_path = Path(self.directory) / "404.html"
            if custom_404_path.exists():
                try:
                    # Read custom 404 page
                    with open(custom_404_path, "rb") as f:
                        content = f.read()

                    # Send custom 404 response
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)

                    logger.debug(
                        "custom_404_served", path=self.path, custom_page_path=str(custom_404_path)
                    )
                    return
                except Exception as e:
                    # If custom 404 fails, fall back to default
                    logger.warning(
                        "custom_404_failed",
                        path=self.path,
                        custom_page_path=str(custom_404_path),
                        error=str(e),
                        error_type=type(e).__name__,
                        action="using_default_404",
                    )

        # Fall back to default error handling for non-404 or if custom 404 failed
        super().send_error(code, message, explain)

    @override
    def list_directory(self, path: str | os.PathLike[str]) -> io.BytesIO | None:
        """
        Show themed "rebuilding" page during builds instead of directory listing.

        When a build is in progress and index.html doesn't exist yet (common
        for autodoc pages being regenerated), displays a friendly placeholder
        instead of an ugly Apache-style directory listing.

        Rebuilding page features:
        - Bengal-themed styling with animated loading indicators
        - Auto-refresh every 2 seconds via meta refresh tag
        - Live reload connection for instant refresh when build completes
        - Displays requested path for user context

        Args:
            path: Filesystem path to the directory being listed

        Returns:
            BytesIO containing "rebuilding" HTML if build in progress.
            Delegates to parent's directory listing otherwise.

        Note:
            Only shows rebuilding page when _build_in_progress is True.
            Does NOT show rebuilding page for missing index.html when no
            build is active (prevents infinite refresh loops).
        """
        # Check if build is in progress
        building = build_state.get_build_in_progress()

        if building:
            # Show rebuilding page instead of directory listing
            request_path = getattr(self, "path", "/")
            html = get_rebuilding_page_html(request_path, build_state.get_active_palette())

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            # Prevent caching of rebuilding page
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()

            logger.debug(
                "rebuilding_page_served",
                path=request_path,
                reason="build_in_progress",
            )

            return io.BytesIO(html)

        # Fall back to default directory listing
        # Note: We intentionally DON'T show rebuilding page for missing index.html
        # when build is not in progress. This was causing infinite refresh loops
        # where the page would refresh forever waiting for a file that may never come.
        return super().list_directory(path)

    @classmethod
    def set_build_in_progress(cls, in_progress: bool) -> None:
        """
        Update the build-in-progress state flag.

        Delegates to shared build_state. Kept for backward compatibility.
        BuildTrigger and dev_server may use build_state directly.
        """
        build_state.set_build_in_progress(in_progress)
        logger.debug("build_state_changed", in_progress=in_progress)

    @classmethod
    def set_on_request(cls, callback: Callable[[str, str, int, float], None] | None) -> None:
        """
        Set the request logging callback for dashboard integration.

        Called for each HTTP request with method, path, status code, and duration.
        Enables real-time request logging display in the dev server dashboard.

        Args:
            callback: Function to call for each request, or None to disable.
                      Signature: (method: str, path: str, status_code: int, duration_ms: float) -> None

        Note:
            SSE endpoint requests (/__bengal_reload__) are not logged as they
            are long-lived connections.

        RFC: rfc-dashboard-api-integration
        """
        cls._on_request = callback
        logger.debug("request_callback_set", enabled=callback is not None)
