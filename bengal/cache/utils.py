"""Cache management utilities for Bengal."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.utils.logger import BengalLogger


def clear_build_cache(site_root_path: str | Path, logger: BengalLogger | None = None) -> bool:
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


def clear_output_directory(output_dir_path: str | Path, logger: BengalLogger | None = None) -> bool:
    """
    Clear the output directory (public/) to force complete regeneration.

    This is necessary when build artifacts may contain stale values
    that won't be updated by incremental builds (e.g., baseurl baked
    into HTML meta tags).

    Args:
        output_dir_path: Path to output directory (e.g., site/public)
        logger: Optional logger for debug output

    Returns:
        True if directory was cleared, False if didn't exist or error occurred
    """
    import shutil

    output_dir = Path(output_dir_path)

    if not output_dir.exists():
        return False

    try:
        # Remove entire directory and its contents
        shutil.rmtree(output_dir)
        if logger:
            logger.debug("output_directory_cleared", output_dir=str(output_dir))
        return True
    except Exception as e:
        if logger:
            logger.warning("output_clear_failed", error=str(e), output_dir=str(output_dir))
        return False
