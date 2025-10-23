"""Server utilities for development behavior."""

from __future__ import annotations

from typing import Protocol


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
    except Exception:
        # Best-effort only
        pass


def get_dev_config(site_config: dict, *keys: str, default=None):
    """Safely access nested dev config: get_dev_config(cfg, 'watch', 'backend', default='auto')."""
    try:
        node = site_config.get("dev", {})
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
        return node if node is not None else default
    except Exception:
        return default


def safe_int(value, default: int = 0) -> int:
    """Parse int with fallback; accepts numeric strings and ints, otherwise default."""
    try:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        return int(str(value))
    except (ValueError, TypeError):
        return default


def clear_build_cache(site_root_path, logger=None) -> bool:
    """
    Clear Bengal's build cache to force a clean rebuild.
    
    Useful when:
    - Config changes in ways that affect output (baseurl, theme, etc.)
    - Stale cache is suspected
    - Forcing a complete regeneration
    
    Args:
        site_root_path: Path to site root directory
        logger: Optional logger for debug output
        
    Returns:
        True if cache was cleared, False if no cache existed
    """
    from pathlib import Path
    
    cache_dir = Path(site_root_path) / ".bengal"
    cache_path = cache_dir / "cache.json"
    
    if not cache_path.exists():
        return False
    
    try:
        cache_path.unlink()
        if logger:
            logger.debug("build_cache_cleared", cache_path=str(cache_path))
        return True
    except Exception as e:
        if logger:
            logger.warning("cache_clear_failed", error=str(e), cache_path=str(cache_path))
        return False
