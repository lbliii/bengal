"""
Request logging utilities for the dev server.

Provides beautiful, minimal logging for HTTP requests with color-coded output.
"""

from datetime import datetime
from typing import Any

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

        # Skip these noisy requests
        skip_patterns = [
            "/.well-known/",
            "/favicon.ico",
            "/favicon.png",
        ]

        for pattern in skip_patterns:
            if pattern in path:
                return

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

        # Colorize status codes
        status_color = self._get_status_color(status_code)
        method_color = self._get_method_color(method)

        # Format path nicely
        display_path = request_path
        if len(request_path) > 60:
            display_path = request_path[:57] + "..."

        # Get timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Add emoji indicators for different types
        indicator = ""
        if not is_asset:
            if status_code.startswith("2"):
                indicator = "📄 "  # Page load
            elif status_code.startswith("4"):
                indicator = "❌ "  # Error

        # Beautiful output
        print(
            f"  {timestamp} │ {method_color}{method:6}{self._reset()} │ {status_color}{status_code:3}{self._reset()} │ {indicator}{display_path}"
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

    def _get_status_color(self, status: str) -> str:
        """Get ANSI color code for status code."""
        try:
            code = int(status)
            if 200 <= code < 300:
                return "\033[32m"  # Green
            elif code == 304:
                return "\033[90m"  # Gray
            elif 300 <= code < 400:
                return "\033[36m"  # Cyan
            elif 400 <= code < 500:
                return "\033[33m"  # Yellow
            else:
                return "\033[31m"  # Red
        except (ValueError, TypeError):
            return ""

    def _get_method_color(self, method: str) -> str:
        """Get ANSI color code for HTTP method."""
        colors = {
            "GET": "\033[36m",  # Cyan
            "POST": "\033[33m",  # Yellow
            "PUT": "\033[35m",  # Magenta
            "DELETE": "\033[31m",  # Red
            "PATCH": "\033[35m",  # Magenta
        }
        return colors.get(method, "\033[37m")  # Default white

    def _reset(self) -> str:
        """Get ANSI reset code."""
        return "\033[0m"
