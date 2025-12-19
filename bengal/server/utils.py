"""Server utilities for development behavior."""

from __future__ import annotations

import os
from typing import Any, Protocol

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def is_process_isolation_enabled(config: dict[str, Any] | None = None) -> bool:
    """
    Check if process-isolated builds are enabled.

    Process isolation runs builds in a subprocess for resilience - a crashed
    build won't take down the dev server.

    Configuration precedence:
    1. BENGAL_DEV_SERVER_V2 env var: "1" enables, "0" disables
    2. Config: dev_server.process_isolation = true/false
    3. Default: False (conservative, process isolation is opt-in)

    Args:
        config: Site configuration dict (optional)

    Returns:
        True if process-isolated builds should be used
    """
    # Environment variable takes precedence
    env_val = os.environ.get("BENGAL_DEV_SERVER_V2", "").lower()
    if env_val == "1":
        return True
    if env_val == "0":
        return False

    # Check config
    if config:
        dev_server = config.get("dev_server", {})
        if isinstance(dev_server, dict):
            return bool(dev_server.get("process_isolation", False))

    # Default: disabled (conservative)
    return False


class HeaderSender(Protocol):
    def send_header(self, key: str, value: str) -> None: ...


def apply_dev_no_cache_headers(sender: HeaderSender) -> None:
    """
    Apply consistent dev no-cache headers to an HTTP response.

    Intended to be called before end_headers().
    """
    try:
        sender.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        sender.send_header("Pragma", "no-cache")
    except Exception as e:
        # Best-effort only
        logger.debug(
            "server_utils_cache_header_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="skipping_header",
        )
        pass


def get_dev_config(site_config: dict[str, Any], *keys: str, default: object = None) -> object:
    """Safely access nested dev config: get_dev_config(cfg, 'watch', 'backend', default='auto')."""
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
    """Parse int with fallback; accepts numeric strings and ints, otherwise default."""
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
