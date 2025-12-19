"""
Custom HTTP request handler for the dev server.

Provides beautiful logging, custom 404 pages, and live reload support.
"""

from __future__ import annotations

import http.server
import io
import threading
from http.client import HTTPMessage
from pathlib import Path
from typing import Any, override

from bengal.server.component_preview import ComponentPreviewServer
from bengal.server.live_reload import LiveReloadMixin
from bengal.server.request_logger import RequestLogger
from bengal.utils.logger import get_logger, truncate_str

logger = get_logger(__name__)


# HTML template for "rebuilding" page shown during builds
# Uses CSS animation and auto-retry via meta refresh + live reload script
# Features Bengal branding with rosette logo and cat theme
# Placeholders: %PATH%, %ACCENT%, %ACCENT_RGB%, %BG_PRIMARY%, %BG_SECONDARY%
REBUILDING_PAGE_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="2">
    <title>Rebuilding... | Bengal</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(145deg, %BG_PRIMARY% 0%, %BG_SECONDARY% 50%, %BG_TERTIARY% 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e8e4de;
            overflow: hidden;
            position: relative;
        }
        /* Subtle pattern overlay */
        body::before {
            content: '';
            position: absolute;
            inset: 0;
            background-image: radial-gradient(circle at 20% 30%, rgba(%ACCENT_RGB%, 0.03) 0%, transparent 50%),
                              radial-gradient(circle at 80% 70%, rgba(%ACCENT_RGB%, 0.03) 0%, transparent 50%);
            pointer-events: none;
        }
        .container {
            text-align: center;
            padding: 2.5rem;
            position: relative;
            z-index: 1;
        }
        .logo-container {
            margin-bottom: 1.5rem;
            position: relative;
        }
        .logo {
            width: 72px;
            height: 72px;
            margin: 0 auto;
            color: %ACCENT%;
            animation: pulse 2s ease-in-out infinite;
        }
        .logo svg {
            width: 100%;
            height: 100%;
            filter: drop-shadow(0 0 12px rgba(%ACCENT_RGB%, 0.3));
        }
        @keyframes pulse {
            0%, 100% { 
                transform: scale(1);
                opacity: 1;
            }
            50% { 
                transform: scale(1.08);
                opacity: 0.85;
            }
        }
        /* Orbiting dots around logo */
        .orbit {
            position: absolute;
            width: 120px;
            height: 120px;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            animation: orbit 3s linear infinite;
        }
        .orbit::before, .orbit::after {
            content: '';
            position: absolute;
            width: 6px;
            height: 6px;
            background: %ACCENT%;
            border-radius: 50%;
        }
        .orbit::before { top: 0; left: 50%; transform: translateX(-50%); }
        .orbit::after { bottom: 0; left: 50%; transform: translateX(-50%); opacity: 0.5; }
        @keyframes orbit {
            from { transform: translate(-50%, -50%) rotate(0deg); }
            to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        .brand {
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: %ACCENT%;
            margin-bottom: 1.5rem;
            opacity: 0.9;
        }
        h1 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #f5f3ef;
            letter-spacing: -0.01em;
        }
        .subtitle {
            color: #9a9488;
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }
        .path {
            display: inline-block;
            padding: 0.5rem 1rem;
            background: rgba(%ACCENT_RGB%, 0.08);
            border: 1px solid rgba(%ACCENT_RGB%, 0.15);
            border-radius: 0.5rem;
            font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, monospace;
            font-size: 0.8rem;
            color: %ACCENT%;
        }
        .paw-prints {
            margin-top: 2rem;
            display: flex;
            justify-content: center;
            gap: 0.75rem;
        }
        .paw {
            width: 16px;
            height: 16px;
            opacity: 0;
            animation: fadeWalk 2s ease-in-out infinite;
        }
        .paw:nth-child(1) { animation-delay: 0s; }
        .paw:nth-child(2) { animation-delay: 0.4s; }
        .paw:nth-child(3) { animation-delay: 0.8s; }
        @keyframes fadeWalk {
            0%, 100% { opacity: 0; transform: translateY(0); }
            30%, 70% { opacity: 0.6; transform: translateY(-4px); }
        }
        .paw svg {
            width: 100%;
            height: 100%;
            fill: %ACCENT%;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-container">
            <div class="orbit"></div>
            <div class="logo">
                <!-- Bengal Rosette Logo -->
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <ellipse cx="12" cy="11" rx="5" ry="1.5" fill="currentColor" opacity="0.25"/>
                    <path d="M7 10 L7 11 A5 1.5 0 0 0 17 11 L17 10" fill="currentColor" opacity="0.35"/>
                    <ellipse cx="12" cy="10" rx="5" ry="4" stroke="currentColor" stroke-width="1.5"/>
                    <ellipse cx="12" cy="10" rx="2" ry="1.5" fill="currentColor"/>
                    <path d="M9 8 A3 2 0 0 1 14 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.4"/>
                    <ellipse cx="6.5" cy="17.5" rx="3" ry="0.8" fill="currentColor" opacity="0.2"/>
                    <path d="M3.5 17 L3.5 17.5 A3 0.8 0 0 0 9.5 17.5 L9.5 17" fill="currentColor" opacity="0.3"/>
                    <ellipse cx="6.5" cy="17" rx="3" ry="2.5" stroke="currentColor" stroke-width="1.5"/>
                    <ellipse cx="6.5" cy="17" rx="1.2" ry="0.9" fill="currentColor"/>
                    <ellipse cx="17.5" cy="16.5" rx="2.8" ry="0.7" fill="currentColor" opacity="0.2"/>
                    <path d="M14.7 16 L14.7 16.5 A2.8 0.7 0 0 0 20.3 16.5 L20.3 16" fill="currentColor" opacity="0.3"/>
                    <ellipse cx="17.5" cy="16" rx="2.8" ry="2.2" stroke="currentColor" stroke-width="1.5"/>
                    <ellipse cx="17.5" cy="16" rx="1" ry="0.7" fill="currentColor"/>
                </svg>
            </div>
        </div>
        <div class="brand">Bengal</div>
        <h1>Rebuilding site...</h1>
        <p class="subtitle">This page will refresh automatically when ready.</p>
        <div class="path">%PATH%</div>
        <div class="paw-prints">
            <div class="paw">
                <svg viewBox="0 0 24 24"><path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-4.5 2c-.83 0-1.5.67-1.5 1.5S6.67 15 7.5 15 9 14.33 9 13.5 8.33 12 7.5 12zm9 0c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zM12 16c-1.1 0-2 .45-2 1s.9 1 2 1 2-.45 2-1-.9-1-2-1zm-4 2c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1zm8 0c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/></svg>
            </div>
            <div class="paw">
                <svg viewBox="0 0 24 24"><path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-4.5 2c-.83 0-1.5.67-1.5 1.5S6.67 15 7.5 15 9 14.33 9 13.5 8.33 12 7.5 12zm9 0c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zM12 16c-1.1 0-2 .45-2 1s.9 1 2 1 2-.45 2-1-.9-1-2-1zm-4 2c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1zm8 0c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/></svg>
            </div>
            <div class="paw">
                <svg viewBox="0 0 24 24"><path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-4.5 2c-.83 0-1.5.67-1.5 1.5S6.67 15 7.5 15 9 14.33 9 13.5 8.33 12 7.5 12zm9 0c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zM12 16c-1.1 0-2 .45-2 1s.9 1 2 1 2-.45 2-1-.9-1-2-1zm-4 2c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1zm8 0c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/></svg>
            </div>
        </div>
    </div>
    <script>
        // Connect to live reload for faster refresh
        const es = new EventSource('/__bengal_reload__');
        es.onmessage = (e) => {
            if (e.data === 'reload' || e.data.includes('"action":"reload"')) {
                window.location.reload();
            }
        };
    </script>
</body>
</html>
"""

# Palette color schemes for the rebuilding page (dark mode colors)
# Each palette maps to: (accent_hex, accent_rgb, bg_primary, bg_secondary, bg_tertiary)
PALETTE_COLORS: dict[str, tuple[str, str, str, str, str]] = {
    # Snow Lynx - Icy teal
    "snow-lynx": ("#6EC4BC", "110, 196, 188", "#18191A", "#252729", "#333538"),
    # Silver Bengal - Pure silver (monochromatic)
    "silver-bengal": ("#D1D5DB", "209, 213, 219", "#000000", "#0F0F0F", "#1A1A1A"),
    # Charcoal Bengal - Golden glitter
    "charcoal-bengal": ("#C9A84D", "201, 168, 77", "#0C0B0A", "#14130F", "#1E1C18"),
    # Brown Bengal - Warm amber
    "brown-bengal": ("#FFAD3D", "255, 173, 61", "#1F1811", "#2D2218", "#3D3020"),
    # Blue Bengal - Powder blue
    "blue-bengal": ("#9DBDD9", "157, 189, 217", "#141B22", "#1B2430", "#243140"),
}

# Default palette colors (Snow Lynx - the default palette)
DEFAULT_PALETTE = "snow-lynx"


def get_rebuilding_page_html(path: str, palette: str | None = None) -> bytes:
    """
    Generate the rebuilding page HTML with the appropriate palette colors.

    Args:
        path: The URL path being rebuilt
        palette: The palette name (e.g., 'snow-lynx', 'charcoal-bengal')
                 If None, uses the default palette.

    Returns:
        Bytes containing the complete HTML with colors applied
    """
    # Get colors for the palette (or default)
    palette_key = palette or DEFAULT_PALETTE
    if palette_key not in PALETTE_COLORS:
        palette_key = DEFAULT_PALETTE

    accent, accent_rgb, bg_primary, bg_secondary, bg_tertiary = PALETTE_COLORS[palette_key]

    # Apply all replacements
    html = REBUILDING_PAGE_HTML
    html = html.replace(b"%PATH%", path.encode("utf-8"))
    html = html.replace(b"%ACCENT%", accent.encode("utf-8"))
    html = html.replace(b"%ACCENT_RGB%", accent_rgb.encode("utf-8"))
    html = html.replace(b"%BG_PRIMARY%", bg_primary.encode("utf-8"))
    html = html.replace(b"%BG_SECONDARY%", bg_secondary.encode("utf-8"))
    html = html.replace(b"%BG_TERTIARY%", bg_tertiary.encode("utf-8"))

    return html


class BengalRequestHandler(RequestLogger, LiveReloadMixin, http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler with beautiful logging, custom 404 page, and live reload support.

    This handler combines:
    - RequestLogger: Beautiful, minimal HTTP request logging
    - LiveReloadMixin: Server-Sent Events for hot reload
    - SimpleHTTPRequestHandler: Standard HTTP file serving

    Build resilience:
    - Shows "rebuilding" page instead of directory listing during builds
    - Auto-refreshes when build completes via live reload
    """

    # Suppress default server version header
    server_version = "Bengal/1.0"
    sys_version = ""
    # Ensure HTTP/1.1 for proper keep-alive behavior on SSE
    protocol_version = "HTTP/1.1"

    # Cached Site instance for component preview (avoids expensive reconstruction on every request)
    _cached_site = None
    _cached_site_root = None

    # Cache for injected HTML responses (avoids re-reading files on rapid navigation)
    # Key: (file_path_str, mtime), Value: modified_content bytes
    _html_cache: dict[tuple[str, float], bytes] = {}
    _html_cache_max_size = 50  # Keep last 50 pages in cache
    _html_cache_lock = threading.Lock()

    # Build state tracking - set by BuildHandler during rebuilds
    # When True, directory listings show "rebuilding" page instead
    _build_in_progress: bool = False
    _build_lock = threading.Lock()

    # Active theme palette for rebuilding page styling
    # Set by dev_server at startup based on site config
    _active_palette: str | None = None

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        """
        Initialize the request handler.

        Pre-initializes headers and request_version to avoid AttributeError
        when tests bypass normal request parsing flow. The parent class will
        properly set these during normal HTTP request handling.

        Args:
            directory: Directory to serve files from. If provided, passed to parent
                       to avoid os.getcwd() which can fail if CWD is deleted during rebuilds.
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
    def end_headers(self) -> None:  # type: ignore[override]
        try:
            # If cache headers not already set, add sensible dev defaults
            if (
                not any(
                    h.lower().startswith(b"cache-control:")
                    for h in getattr(self, "_headers_buffer", [])
                )
                and getattr(self, "path", "") != "/__bengal_reload__"
            ):
                from bengal.server.utils import apply_dev_no_cache_headers

                apply_dev_no_cache_headers(self)
        except Exception as e:
            logger.debug(
                "dev_cache_header_application_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
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
                variant_list = q.get("v") or []
                variant_id = variant_list[0] if variant_list else None
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

    @override
    def list_directory(self, path: str) -> io.BytesIO | None:
        """
        Override list_directory to show a "rebuilding" page during builds.

        When a build is in progress and the user navigates to a page whose
        index.html doesn't exist yet (e.g., autodoc pages being regenerated),
        show a friendly "rebuilding" page instead of an ugly directory listing.

        The rebuilding page:
        - Has a loading spinner
        - Auto-refreshes every 2 seconds via meta refresh
        - Also connects to live reload for faster refresh
        - Shows the requested path for context

        Args:
            path: Filesystem path to the directory

        Returns:
            BytesIO with HTML content, or None if not handled
        """
        # Check if build is in progress
        with BengalRequestHandler._build_lock:
            building = BengalRequestHandler._build_in_progress

        if building:
            # Show rebuilding page instead of directory listing
            request_path = getattr(self, "path", "/")
            html = get_rebuilding_page_html(request_path, BengalRequestHandler._active_palette)

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

        # Not building - check if this directory should have an index.html
        # If so, show rebuilding page as the file might be coming soon
        dir_path = Path(path)
        index_path = dir_path / "index.html"

        # For API/autodoc paths, if index.html is missing, likely a build artifact
        # that hasn't been written yet - show rebuilding page
        request_path = getattr(self, "path", "/")
        is_api_path = request_path.startswith("/api/")

        if is_api_path and not index_path.exists():
            html = get_rebuilding_page_html(request_path, BengalRequestHandler._active_palette)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()

            logger.debug(
                "rebuilding_page_served",
                path=request_path,
                reason="api_index_missing",
            )

            return io.BytesIO(html)

        # Fall back to default directory listing for other cases
        return super().list_directory(path)

    @classmethod
    def set_build_in_progress(cls, in_progress: bool) -> None:
        """
        Set the build-in-progress state.

        Called by BuildHandler at the start and end of rebuilds.

        Args:
            in_progress: True when build starts, False when build ends
        """
        with cls._build_lock:
            cls._build_in_progress = in_progress
        logger.debug("build_state_changed", in_progress=in_progress)
