"""
Cache utilities for reducing redundancy across cache modules.

This package provides reusable mixins, utilities, and cache management functions:

Mixins:
- PersistentCacheMixin: Standardized load/save with compression and versioning
- ValidityTrackingMixin: Entry validity tracking with invalidation
- ThreadSafeCacheMixin: Thread-safe operations with RLock

Functions:
- check_bidirectional_invariants: Verify forward/reverse index consistency
- compute_validity_stats: Compute cache entry statistics
- compute_index_stats: Compute index-specific statistics
- compute_taxonomy_stats: Compute taxonomy-specific statistics
- clear_build_cache: Clear the main build cache
- clear_template_cache: Clear template bytecode cache
- clear_output_directory: Clear the output directory

Usage:
    from bengal.cache.utils import (
        PersistentCacheMixin,
        ValidityTrackingMixin,
        ThreadSafeCacheMixin,
        check_bidirectional_invariants,
        clear_build_cache,
    )

    class MyCache(PersistentCacheMixin, ValidityTrackingMixin):
        VERSION = 1
        ...

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.cache.utils.bidirectional import check_bidirectional_invariants
from bengal.cache.utils.persistence import PersistentCacheMixin
from bengal.cache.utils.stats import (
    compute_index_stats,
    compute_taxonomy_stats,
    compute_validity_stats,
)
from bengal.cache.utils.thread_safety import ThreadSafeCacheMixin
from bengal.cache.utils.validity import ValidityTrackingMixin

if TYPE_CHECKING:
    from bengal.utils.observability.logger import BengalLogger

__all__ = [
    "PersistentCacheMixin",
    "ThreadSafeCacheMixin",
    "ValidityTrackingMixin",
    "check_bidirectional_invariants",
    "clear_build_cache",
    "clear_output_directory",
    "clear_template_cache",
    "compute_index_stats",
    "compute_taxonomy_stats",
    "compute_validity_stats",
]


# =============================================================================
# Cache Management Functions (moved from old utils.py)
# =============================================================================


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
    from bengal.cache.paths import BengalPaths

    paths = BengalPaths(Path(site_root_path))
    cache_path = paths.build_cache
    compressed_path = cache_path.with_suffix(".json.zst")

    cleared = False

    # Clear uncompressed
    if cache_path.exists():
        try:
            cache_path.unlink()
            cleared = True
            if logger:
                logger.debug("build_cache_cleared", cache_path=str(cache_path))
        except Exception as e:
            if logger:
                from bengal.errors import ErrorCode

                logger.warning(
                    "cache_clear_failed",
                    error=str(e),
                    cache_path=str(cache_path),
                    error_code=ErrorCode.A005.value,
                )

    # Clear compressed
    if compressed_path.exists():
        try:
            compressed_path.unlink()
            cleared = True
            if logger:
                logger.debug("compressed_cache_cleared", cache_path=str(compressed_path))
        except Exception as e:
            if logger:
                from bengal.errors import ErrorCode

                logger.warning(
                    "cache_clear_failed",
                    error=str(e),
                    cache_path=str(compressed_path),
                    error_code=ErrorCode.A005.value,
                )

    return cleared


def clear_template_cache(site_root_path: str | Path, logger: BengalLogger | None = None) -> bool:
    """
    Clear template bytecode cache.

    Useful when:
    - Template files change but bytecode cache is stale
    - Starting dev server (ensures fresh template compilation)
    - Switching themes

    Args:
        site_root_path: Path to site root directory
        logger: Optional logger for debug output

    Returns:
        True if cache was cleared, False if no cache existed or error occurred

    """
    import shutil

    from bengal.cache.paths import BengalPaths

    paths = BengalPaths(Path(site_root_path))
    cache_dir = paths.templates_dir

    if not cache_dir.exists():
        return False

    try:
        shutil.rmtree(cache_dir)
        if logger:
            logger.debug("template_cache_cleared", cache_dir=str(cache_dir))
        return True
    except Exception as e:
        if logger:
            from bengal.errors import ErrorCode

            logger.warning(
                "template_cache_clear_failed",
                error=str(e),
                cache_dir=str(cache_dir),
                error_code=ErrorCode.A005.value,
            )
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
        shutil.rmtree(output_dir)
        if logger:
            logger.debug("output_directory_cleared", output_dir=str(output_dir))
        return True
    except Exception as e:
        if logger:
            from bengal.errors import ErrorCode

            logger.warning(
                "output_clear_failed",
                error=str(e),
                output_dir=str(output_dir),
                error_code=ErrorCode.A005.value,
            )
        return False
