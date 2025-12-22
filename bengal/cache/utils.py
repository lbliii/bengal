"""
Cache management utilities for clearing and resetting Bengal caches.

This module provides functions for clearing various caches when a clean rebuild
is needed, such as after configuration changes or suspected cache corruption.

Functions:
    clear_build_cache: Remove the main build cache (.bengal/cache.json.zst)
        to force file fingerprint recalculation on next build.

    clear_template_cache: Remove Jinja2 bytecode cache (.bengal/templates/)
        to force template recompilation.

    clear_output_directory: Remove the entire output directory (public/)
        to force complete regeneration of all output files.

When to Clear Caches:
    - Build cache: Config changes affecting output (baseurl, theme), stale cache
    - Template cache: Template file changes not being detected, theme switching
    - Output directory: Baseurl changes, orphaned files from deleted content

Usage:
    from bengal.cache.utils import clear_build_cache, clear_template_cache

    # Clear all caches for a site
    clear_build_cache(site.root_path, logger)
    clear_template_cache(site.root_path, logger)
    clear_output_directory(site.output_dir, logger)

Related:
    - bengal.cache.paths: BengalPaths for cache file locations
    - bengal.cli.commands: CLI commands using these utilities
"""

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
    from bengal.cache.paths import BengalPaths

    paths = BengalPaths(Path(site_root_path))
    cache_path = paths.build_cache

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


def clear_template_cache(site_root_path: str | Path, logger: BengalLogger | None = None) -> bool:
    """
    Clear Jinja2 bytecode template cache.

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
        # Remove all bytecode cache files
        shutil.rmtree(cache_dir)
        if logger:
            logger.debug("template_cache_cleared", cache_dir=str(cache_dir))
        return True
    except Exception as e:
        if logger:
            logger.warning("template_cache_clear_failed", error=str(e), cache_dir=str(cache_dir))
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
