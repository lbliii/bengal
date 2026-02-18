"""
Utility functions for Bengal dev server.

Provides helper functions for common dev server operations including
HTTP header management, configuration access, type coercion, and
shared utilities for icons, timestamps, and content types.

Functions:
    apply_dev_no_cache_headers: Add cache-busting headers to HTTP responses
    get_dev_config: Safely access nested dev server configuration
    get_dev_server_config: Access dev_server section of config
    safe_int: Parse integers with fallback for invalid input
    get_icons: Get icon set based on terminal capabilities
    get_timestamp: Get formatted timestamp for log display
    get_content_type: Get MIME type for file extension
    find_html_injection_point: Find injection point for live reload script

Protocols:
HeaderSender: Protocol for objects that can send HTTP headers

Note:
Cache management functions have been moved to bengal.cache.utils.
Import from bengal.cache instead for clear_build_cache and
clear_output_directory.

Related:
- bengal/server/asgi_app.py: Uses cache headers in responses
- bengal/server/dev_server.py: Uses get_dev_config for configuration
- bengal/server/live_reload.py: Uses find_html_injection_point
- bengal/cache/utils.py: Cache management utilities

"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.output.icons import IconSet

logger = get_logger(__name__)


# Content type mapping for common file extensions
CONTENT_TYPES: dict[str, str] = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".xml": "application/xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}


@runtime_checkable
class HeaderSender(Protocol):
    """
    Protocol for objects that can send HTTP headers.

    Used to type-hint HTTP request handlers in a framework-agnostic way.
    Any object with a send_header(key, value) method satisfies this protocol.

    Example:
            >>> def add_headers(sender: HeaderSender) -> None:
            ...     sender.send_header("X-Custom", "value")

    """

    def send_header(self, key: str, value: str) -> None:
        """
        Send an HTTP header.

        Args:
            key: Header name (e.g., "Content-Type")
            value: Header value (e.g., "text/html")
        """
        ...


def apply_dev_no_cache_headers(sender: HeaderSender) -> None:
    """
    Apply cache-busting headers to prevent browser caching in dev mode.

    Adds aggressive no-cache headers to ensure browsers always fetch fresh
    content during development. This prevents stale CSS, JS, and HTML from
    being served after file changes.

    Args:
        sender: HTTP handler with send_header method (e.g., BaseHTTPRequestHandler)

    Note:
        Must be called before end_headers(). Failures are logged but do not
        raise exceptions to avoid breaking request handling.

    Example:
            >>> class MyHandler(BaseHTTPRequestHandler):
            ...     def do_GET(self):
            ...         self.send_response(200)
            ...         apply_dev_no_cache_headers(self)
            ...         self.end_headers()

    """
    try:
        sender.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        sender.send_header("Pragma", "no-cache")
    except Exception as e:
        # Best-effort only - don't break request handling
        logger.debug(
            "server_utils_cache_header_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="skipping_header",
        )


def get_dev_config(site_config: dict[str, Any], *keys: str, default: object = None) -> object:
    """
    Safely access nested dev server configuration values.

    Traverses the site config dictionary to access values nested under
    the "dev" key. Returns a default value if any key in the path is
    missing or if the intermediate value is not a dict.

    Args:
        site_config: Full site configuration dictionary
        *keys: Variable path of keys to traverse (e.g., 'watch', 'backend')
        default: Value to return if path doesn't exist (default: None)

    Returns:
        The configuration value at the specified path, or default if not found.

    Example:
            >>> config = {"dev": {"watch": {"backend": "watchfiles", "debounce": 300}}}
            >>> get_dev_config(config, "watch", "backend")
            'watchfiles'
            >>> get_dev_config(config, "watch", "debounce", default=500)
        300
            >>> get_dev_config(config, "watch", "missing", default="auto")
            'auto'

    """
    try:
        node = site_config.get("dev", {})
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
        return node if node is not None else default
    except Exception as e:
        logger.debug(
            "server_utils_dev_config_access_failed",
            keys=keys,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_default",
        )
        return default


def safe_int(value: object, default: int = 0) -> int:
    """
    Parse an integer value with fallback for invalid input.

    Accepts integers, numeric strings, or None. Returns the default value
    for any input that cannot be converted to an integer.

    Args:
        value: Value to parse (int, str, or None)
        default: Value to return if parsing fails (default: 0)

    Returns:
        Parsed integer value, or default if parsing fails.

    Example:
            >>> safe_int(42)
        42
            >>> safe_int("123")
        123
            >>> safe_int(None, default=10)
        10
            >>> safe_int("invalid")
        0

    """
    try:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        return int(str(value))
    except ValueError, TypeError:
        return default


# Cache management functions moved to bengal.cache.utils
# Import from bengal.cache instead:
#   from bengal.cache import clear_build_cache, clear_output_directory


def get_icons() -> IconSet:
    """
    Get icon set based on terminal capabilities.

    Convenience function that combines icon set retrieval with emoji detection,
    eliminating the need to import from two separate modules.

    Returns:
        IconSet configured for the current terminal's emoji support.

    Example:
            >>> icons = get_icons()
            >>> print(f"{icons.success} Operation completed")

    """
    from bengal.output.icons import get_icon_set
    from bengal.utils.observability.rich_console import should_use_emoji

    return get_icon_set(should_use_emoji())


def get_timestamp() -> str:
    """
    Get current time formatted for log display.

    Returns:
        Time string in HH:MM:SS format.

    Example:
            >>> timestamp = get_timestamp()
            >>> print(f"[{timestamp}] Event occurred")
        [14:32:05] Event occurred

    """
    return datetime.now().strftime("%H:%M:%S")


def get_content_type(path: str) -> str:
    """
    Get MIME type for file path based on extension.

    Uses a predefined mapping of common file extensions to MIME types.
    Falls back to application/octet-stream for unknown extensions.

    Args:
        path: File path or URL path to check

    Returns:
        MIME type string (e.g., "text/css; charset=utf-8")

    Example:
            >>> get_content_type("/assets/style.css")
        'text/css; charset=utf-8'
            >>> get_content_type("script.js")
        'application/javascript; charset=utf-8'
            >>> get_content_type("unknown.xyz")
        'application/octet-stream'

    """
    ext = Path(path).suffix.lower()
    return CONTENT_TYPES.get(ext, "application/octet-stream")


def find_html_injection_point(content: bytes) -> int:
    """
    Find the best injection point for live reload script in HTML content.

    Searches for closing tags in order of preference:
    1. </body> (preferred - script goes at end of body)
    2. </BODY> (uppercase variant)
    3. </html> (fallback)
    4. </HTML> (uppercase fallback)

    If no closing tag is found, returns -1 indicating the caller should
    append the script at the end of the content.

    Args:
        content: HTML content as bytes

    Returns:
        Index of the injection point, or -1 if no suitable tag found.

    Example:
            >>> html = b"<html><body>Hello</body></html>"
            >>> idx = find_html_injection_point(html)
            >>> idx
        18
            >>> html[:idx] + b"<script>...</script>" + html[idx:]
        b'<html><body>Hello<script>...</script></body></html>'

    """
    # Try </body> first (preferred injection point)
    for tag in (b"</body>", b"</BODY>"):
        idx = content.rfind(tag)
        if idx != -1:
            return idx

    # Fallback to </html>
    for tag in (b"</html>", b"</HTML>"):
        idx = content.rfind(tag)
        if idx != -1:
            return idx

    return -1


def get_dev_server_config(
    config: dict[str, Any] | Any,
    *keys: str,
    default: Any = None,
) -> Any:
    """
    Safely access nested dev_server configuration values.

    Traverses the config dictionary starting from the "dev_server" key
    to access nested values. Returns a default value if any key in the
    path is missing or if the intermediate value is not a dict.

    This is the preferred function for accessing dev server configuration
    (uses "dev_server" key, not "dev").

    Args:
        config: Site configuration dict or ConfigSection
        *keys: Variable path of keys to traverse (e.g., 'exclude_patterns')
        default: Value to return if path doesn't exist (default: None)

    Returns:
        The configuration value at the specified path, or default if not found.

    Example:
            >>> config = {"dev_server": {"exclude_patterns": ["*.pyc"], "debounce": 300}}
            >>> get_dev_server_config(config, "exclude_patterns")
        ['*.pyc']
            >>> get_dev_server_config(config, "debounce", default=500)
        300
            >>> get_dev_server_config(config, "missing", default="auto")
        'auto'

    """
    try:
        # Handle ConfigSection objects that have .get() method
        if hasattr(config, "get"):
            node = config.get("dev_server", {})
        else:
            return default

        for key in keys:
            if not isinstance(node, dict):
                # Try .get() for ConfigSection-like objects
                if hasattr(node, "get"):
                    node = node.get(key, default)
                else:
                    return default
            else:
                node = node.get(key, default)

        return node if node is not None else default
    except Exception as e:
        logger.debug(
            "server_utils_dev_server_config_access_failed",
            keys=keys,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_default",
        )
        return default
