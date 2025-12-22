"""
Utility functions for Bengal dev server.

Provides helper functions for common dev server operations including
HTTP header management, configuration access, and type coercion.

Functions:
    apply_dev_no_cache_headers: Add cache-busting headers to HTTP responses
    get_dev_config: Safely access nested dev server configuration
    safe_int: Parse integers with fallback for invalid input

Protocols:
    HeaderSender: Protocol for objects that can send HTTP headers

Note:
    Cache management functions have been moved to bengal.cache.utils.
    Import from bengal.cache instead for clear_build_cache and
    clear_output_directory.

Related:
    - bengal/server/request_handler.py: Uses apply_dev_no_cache_headers
    - bengal/server/dev_server.py: Uses get_dev_config for configuration
    - bengal/cache/utils.py: Cache management utilities
"""

from __future__ import annotations

from typing import Any, Protocol

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


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
        pass


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
    except (ValueError, TypeError):
        return default


# Cache management functions moved to bengal.cache.utils
# Import from bengal.cache instead:
#   from bengal.cache import clear_build_cache, clear_output_directory
