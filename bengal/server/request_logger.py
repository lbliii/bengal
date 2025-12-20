"""
Request logging utilities for the dev server.

Provides beautiful, minimal logging for HTTP requests with color-coded output.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bengal.output import CLIOutput
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class RequestLogger:
    """
    Mixin class providing beautiful, minimal logging for HTTP requests.

    This class is designed to be mixed into an HTTP request handler.
    """

    def log_message(self, format: str, *args: Any) -> None:
        """
        Log an HTTP request with beautiful formatting.

        Args:
            format: Format string
            *args: Format arguments
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
        Suppress error logging - we handle everything in log_message.

        Args:
            format: Format string
            *args: Format arguments
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
