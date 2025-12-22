"""
HTTP request logging for Bengal dev server.

Provides beautiful, minimal request logging with intelligent filtering
to reduce noise while highlighting important events (errors, page loads).

Features:
    - Color-coded output by status code (2xx green, 4xx yellow, 5xx red)
    - Automatic filtering of noisy requests (favicons, cache hits, assets)
    - Optional resource 404 suppression (expected when deps not installed)
    - Structured logging for machine-readable analysis
    - BrokenPipe/ConnectionReset suppression (normal client behavior)

Classes:
    RequestLogger: Mixin class for HTTP request handlers

Architecture:
    This module provides a mixin that overrides log_message() and log_error()
    from BaseHTTPRequestHandler. It should be mixed in before the handler class
    in the MRO to intercept logging calls.

Related:
    - bengal/server/request_handler.py: Uses RequestLogger mixin
    - bengal/output/cli.py: CLIOutput handles actual console formatting
    - bengal/utils/logger.py: Structured logging backend
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bengal.output import CLIOutput
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class RequestLogger:
    """
    Mixin providing beautiful, minimal HTTP request logging.

    Designed to be mixed into an HTTP request handler to override default
    logging behavior. Filters out noisy requests and provides color-coded
    output for easy scanning during development.

    Filtering Rules:
        - Skip: favicon requests, .well-known paths
        - Skip: 304 Not Modified (cache hits)
        - Skip: Successful asset loads (/assets/, /static/)
        - Skip: Optional resource 404s (search-index.json)
        - Show: All page loads, errors, and initial asset loads

    Example:
        >>> class MyHandler(RequestLogger, SimpleHTTPRequestHandler):
        ...     pass  # Logging is automatically enhanced
    """

    def log_message(self, format: str, *args: Any) -> None:
        """
        Log an HTTP request with beautiful, filtered formatting.

        Overrides BaseHTTPRequestHandler.log_message() to provide:
        - Color-coded status indicators
        - Intelligent request filtering
        - Both human-readable and structured log output

        Args:
            format: Printf-style format string (from BaseHTTPRequestHandler)
            *args: Format arguments: (request_line, status_code, size)
        """
        # Skip certain requests that clutter the logs
        path = args[0] if args else ""
        status_code = args[1] if len(args) > 1 else ""

        # Skip these noisy requests entirely
        skip_patterns = [
            "/.well-known/",
            "/favicon.ico",
            "/favicon.png",
        ]

        for pattern in skip_patterns:
            if pattern in path:
                return

        # Optional resources that are expected to 404 when not installed/configured
        # These are silently skipped to avoid log noise from expected behavior
        optional_resources = [
            "/search-index.json",  # Pre-built Lunr index (requires `pip install bengal[search]`)
        ]

        # Get request method and path
        parts = path.split()
        method = parts[0] if parts else "GET"
        request_path = parts[1] if len(parts) > 1 else "/"

        # Skip assets unless they're errors or initial loads
        is_asset = any(request_path.startswith(prefix) for prefix in ["/assets/", "/static/"])
        is_cached = status_code == "304"
        is_success = status_code.startswith("2")

        # Only show assets if they're errors, not cached successful loads
        if is_asset and (is_cached or is_success):
            return

        # Skip 304s entirely - they're just cache hits
        if is_cached:
            return

        # Skip 404s for optional resources - these are expected when dependencies not installed
        is_404 = status_code == "404"
        is_optional_resource = any(request_path == pattern for pattern in optional_resources)
        if is_404 and is_optional_resource:
            return

        # Structured logging for machine-readable analysis
        log_level = "info"
        if status_code.startswith("4"):
            log_level = "warning"
        elif status_code.startswith("5"):
            log_level = "error"

        getattr(logger, log_level)(
            "http_request",
            method=method,
            path=request_path,
            status=int(status_code) if status_code.isdigit() else 0,
            is_asset=is_asset,
            client_address=getattr(self, "client_address", ["unknown", 0])[0],
        )

        # Get timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Use CLIOutput for consistent formatting
        cli = CLIOutput()
        cli.http_request(
            timestamp=timestamp,
            method=method,
            status_code=status_code,
            path=request_path,
            is_asset=is_asset,
        )

    def log_error(self, format: str, *args: Any) -> None:
        """
        Suppress noisy error logging from BaseHTTPRequestHandler.

        Filters out expected errors (BrokenPipe, ConnectionReset) that occur
        during normal client behavior (closing tabs, navigating away). Other
        errors are handled via log_message with proper filtering.

        Args:
            format: Printf-style format string
            *args: Format arguments containing error details
        """
        # Suppress BrokenPipeError and ConnectionResetError - these are normal
        # when clients disconnect early (closing tabs, navigation, etc.)
        if args and len(args) > 0:
            error_msg = str(args[0]) if args else ""
            if "Broken pipe" in error_msg or "Connection reset" in error_msg:
                logger.debug(
                    "client_disconnected",
                    error_type="BrokenPipe" if "Broken pipe" in error_msg else "ConnectionReset",
                    client_address=getattr(self, "client_address", ["unknown", 0])[0],
                )
                return

        # All other error logging is handled in log_message with proper filtering
        # This prevents duplicate error messages
        pass
