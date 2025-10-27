"""
Custom HTTP request handler for the dev server.

Provides beautiful logging, custom 404 pages, and live reload support.
"""

from __future__ import annotations

import http.server
import re
import threading
from http.client import HTTPMessage
from pathlib import Path
from typing import override

from bengal.server.component_preview import ComponentPreviewServer
from bengal.server.live_reload import LIVE_RELOAD_SCRIPT, LiveReloadMixin
from bengal.server.request_logger import RequestLogger
from bengal.utils.logger import get_logger, truncate_str

logger = get_logger(__name__)


class BengalRequestHandler(RequestLogger, LiveReloadMixin, http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler with beautiful logging, custom 404 page, and live reload support.

    This handler combines:
    - RequestLogger: Beautiful, minimal HTTP request logging
    - LiveReloadMixin: Server-Sent Events for hot reload
    - SimpleHTTPRequestHandler: Standard HTTP file serving
    """

    # Suppress default server version header
    server_version = "Bengal/1.0"
    sys_version = ""

    # Cached Site instance for component preview (avoids expensive reconstruction on every request)
    _cached_site = None
    _cached_site_root = None

    # Cache for injected HTML responses (avoids re-reading files on rapid navigation)
    # Key: (file_path, mtime), Value: (modified_content, headers)
    _html_cache = {}
    _html_cache_max_size = 50  # Keep last 50 pages in cache
    _html_cache_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        """
        Initialize the request handler.

        Pre-initializes headers and request_version to avoid AttributeError
        when tests bypass normal request parsing flow. The parent class will
        properly set these during normal HTTP request handling.
        """
        super().__init__(*args, **kwargs)
        # Initialize with empty HTTPMessage
        self.headers = HTTPMessage()
        self.request_version = "HTTP/1.1"

    # In dev, aggressively prevent browser caching to avoid stale assets
    def end_headers(self) -> None:  # type: ignore[override]
        try:
            # If cache headers not already set, add sensible dev defaults
            if not any(
                h.lower().startswith(b"cache-control:")
                for h in getattr(self, "_headers_buffer", [])
            ):
                from bengal.server.utils import apply_dev_no_cache_headers

                apply_dev_no_cache_headers(self)
        except Exception:
            pass
        super().end_headers()

    @override
    def handle(self) -> None:
        """Override handle to suppress BrokenPipeError tracebacks."""
        import contextlib

        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            # Client disconnected - don't print traceback
            super().handle()

    @override
    def do_GET(self) -> None:
        """
        Override GET to support SSE and safe HTML injection via mixin.

        Request flow:
        - Serve SSE endpoint at /__bengal_reload__ (long-lived connection)
        - Try to serve HTML with injected live-reload script
        - Fallback to default file serving for non-HTML
        """
        # Component preview routes
        if self.path.startswith("/__bengal_components__/") or self.path.startswith(
            "/__bengal_components__"
        ):
            self._handle_component_preview()
            return

        # Handle SSE endpoint first (long-lived stream)
        if self.path == "/__bengal_reload__":
            self.handle_sse()
            return

        # Try to serve HTML with injected live reload script
        # If not HTML or injection fails, fall back to normal file serving
        if not self.serve_html_with_live_reload():
            super().do_GET()

    def _handle_component_preview(self) -> None:
        try:
            # Site is bound at server creation via directory chdir; fetch from env on demand
            # Use cached Site instance to avoid expensive reconstruction on every request
            from bengal.core.site import Site

            site_root = Path(self.directory).parent  # output_dir -> site root

            # Cache the site object to avoid expensive reconstruction
            if (
                BengalRequestHandler._cached_site is None
                or BengalRequestHandler._cached_site_root != site_root
            ):
                logger.debug("component_preview_initializing_site", site_root=str(site_root))
                BengalRequestHandler._cached_site = Site.from_config(site_root)
                BengalRequestHandler._cached_site_root = site_root

            site = BengalRequestHandler._cached_site
            cps = ComponentPreviewServer(site)

            # Routing
            if self.path.startswith("/__bengal_components__/view"):
                from urllib.parse import parse_qs, urlparse

                q = parse_qs(urlparse(self.path).query)
                comp_id = (q.get("c") or [""])[0]
                variant_id = (q.get("v") or [None])[0]
                html = cps.view_page(comp_id, variant_id)
            else:
                html = cps.list_page()

            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            logger.error("component_preview_failed", error=str(e), error_type=type(e).__name__)
            self.send_response(500)
            e_str = truncate_str(str(e), 2000, "\n... (truncated for security)")
            msg = f"<h1>Component Preview Error</h1><pre>{e_str}</pre>".encode()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def _might_be_html(self, path: str) -> bool:
        """
        Quick check if request might return HTML.

        This is a fast pre-filter to avoid buffering responses that are
        definitely not HTML (like CSS, JS, images).

        Args:
            path: Request path

        Returns:
            True if request might return HTML, False if definitely not HTML
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
        Check if response is HTML by inspecting headers and content.

        Args:
            response_data: Complete HTTP response (headers + body)

        Returns:
            True if response is HTML, False otherwise
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

    def _inject_live_reload(self, response_data: bytes) -> bytes:
        """
        Inject live reload script into HTML response.

        Args:
            response_data: Complete HTTP response (headers + body)

        Returns:
            Modified HTTP response with injected script
        """
        try:
            # Split headers and body
            headers_end = response_data.index(b"\r\n\r\n")
            headers_bytes = response_data[: headers_end + 4]
            body = response_data[headers_end + 4 :]

            # Decode body as UTF-8 (with error handling)
            html = body.decode("utf-8", errors="replace")

            # Inject script before </body> (case-insensitive)
            html_lower = html.lower()

            if "</body>" in html_lower:
                # Find last occurrence of </body>
                idx = html_lower.rfind("</body>")
                # Get actual index in original (preserving case)
                html = html[:idx] + LIVE_RELOAD_SCRIPT + html[idx:]
            elif "</html>" in html_lower:
                # Fallback: inject before </html>
                idx = html_lower.rfind("</html>")
                html = html[:idx] + LIVE_RELOAD_SCRIPT + html[idx:]
            else:
                # Last resort: append at end
                html += LIVE_RELOAD_SCRIPT

            # Re-encode body
            new_body = html.encode("utf-8")

            # Update Content-Length header if present
            headers = headers_bytes.decode("latin-1", errors="ignore")

            if "Content-Length:" in headers:
                # Replace Content-Length with new value
                headers = re.sub(
                    r"Content-Length:\s*\d+",
                    f"Content-Length: {len(new_body)}",
                    headers,
                    flags=re.IGNORECASE,
                )

            new_headers = headers.encode("latin-1")

            logger.debug(
                "live_reload_injected",
                original_size=len(body),
                new_size=len(new_body),
                script_size=len(LIVE_RELOAD_SCRIPT),
            )

            return new_headers + new_body

        except Exception as e:
            # If injection fails, return original response
            logger.error("injection_failed", error=str(e), error_type=type(e).__name__)
            return response_data

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        """
        Override send_error to serve custom 404 page.

        Args:
            code: HTTP error code
            message: Error message
            explain: Detailed explanation
        """
        # If it's a 404 error, try to serve custom 404.html
        if code == 404:
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
                    pass

        # Fall back to default error handling for non-404 or if custom 404 failed
        super().send_error(code, message, explain)
