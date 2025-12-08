"""Server utilities for development behavior."""

from __future__ import annotations

from typing import Protocol

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


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


def get_dev_config(site_config: dict, *keys: str, default: object = None) -> object:
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
