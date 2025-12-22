"""
Output handling utilities for the rendering pipeline.

This module provides the final stage of the rendering pipeline: determining
output paths, selecting templates, and writing rendered HTML to disk.

Key Functions:
    - determine_output_path(): Compute output file path for a page
    - determine_template(): Select template based on page type and metadata
    - write_output(): Write rendered HTML with atomic writes and caching
    - format_html(): Apply HTML minification or pretty-printing

Write Strategies:
    The module supports two write modes controlled by ``build.fast_writes``:

    - **Atomic writes (default)**: Crash-safe using temporary files and rename.
      Slightly slower but ensures output is never corrupted on interruption.

    - **Fast writes**: Direct file writes without atomicity. Used by dev server
      for maximum performance during rapid iteration.

Directory Caching:
    Uses thread-safe directory tracking to minimize syscalls during parallel
    builds. Once a directory is created, subsequent pages skip the exists check.

Related Modules:
    - bengal.rendering.pipeline.core: Main pipeline orchestration
    - bengal.rendering.pipeline.thread_local: Directory creation tracking
    - bengal.utils.url_strategy: URL and path computation
    - bengal.utils.atomic_write: Atomic file operations
    - bengal.postprocess.html_output: HTML formatting implementation
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.rendering.pipeline.thread_local import mark_dir_created
from bengal.utils.logger import get_logger
from bengal.utils.url_strategy import URLStrategy

if TYPE_CHECKING:
    from bengal.core.output import OutputCollector
    from bengal.core.page import Page

logger = get_logger(__name__)


def determine_output_path(page: Page, site: Any) -> Path:
    """
    Determine the output path for a page.

    Delegates path computation to centralized URLStrategy (i18n-aware).

    Args:
        page: Page to determine path for
        site: Site instance

    Returns:
        Output path
    """
    return URLStrategy.compute_regular_page_output_path(page, site)


def determine_template(page: Page) -> str:
    """
    Determine which template will be used for this page.

    Template resolution order:
    1. page.template attribute
    2. page.metadata['template']
    3. Default based on page type

    Args:
        page: Page object

    Returns:
        Template name (e.g., 'single.html', 'page.html')
    """
    # Check page-specific template first
    if hasattr(page, "template") and page.template:
        return page.template

    # Check metadata
    if "template" in page.metadata:
        return page.metadata["template"]

    # Default based on page type
    page_type = page.metadata.get("type", "page")

    match page_type:
        case "page":
            return "page.html"
        case "section":
            return "list.html"
        case _ if page.metadata.get("is_section"):
            return "list.html"
        case _:
            return "single.html"


def write_output(
    page: Page,
    site: Any,
    dependency_tracker: Any = None,
    collector: OutputCollector | None = None,
) -> None:
    """
    Write rendered page to output directory.

    Handles:
    - Directory creation with caching (reduces syscalls)
    - Atomic writes for crash safety (optional)
    - Fast writes for dev server performance
    - Source→output tracking for incremental cleanup
    - Output tracking for hot reload (when collector provided)

    Args:
        page: Page with rendered content
        site: Site instance for config
        dependency_tracker: Optional tracker for output mapping
        collector: Optional output collector for hot reload tracking
    """
    # Ensure output_path is set
    if page.output_path is None:
        return

    # Ensure parent directory exists (with caching to reduce syscalls)
    parent_dir = page.output_path.parent

    # Only create directory if not already done (thread-safe atomic check-and-add)
    if mark_dir_created(str(parent_dir)):
        parent_dir.mkdir(parents=True, exist_ok=True)

    # Write rendered HTML (atomic for safety, fast mode for performance)
    # Fast mode skips atomic writes for dev server (PERFORMANCE OPTIMIZATION)
    fast_writes = site.config.get("build", {}).get("fast_writes", False)

    try:
        if fast_writes:
            # Direct write (faster, but not crash-safe)
            page.output_path.write_text(page.rendered_html, encoding="utf-8")
        else:
            # Atomic write (crash-safe, slightly slower)
            from bengal.utils.atomic_write import atomic_write_text

            atomic_write_text(
                page.output_path,
                page.rendered_html,
                encoding="utf-8",
                ensure_parent=False,  # parent dir already ensured above (cached)
            )
    except FileNotFoundError:
        # Robustness fallback: if write fails due to missing parent directory
        # (can happen if output_dir was cleaned but our thread-safe cache is stale),
        # force directory creation and retry once.
        parent_dir.mkdir(parents=True, exist_ok=True)

        if fast_writes:
            page.output_path.write_text(page.rendered_html, encoding="utf-8")
        else:
            from bengal.utils.atomic_write import atomic_write_text

            atomic_write_text(
                page.output_path,
                page.rendered_html,
                encoding="utf-8",
                ensure_parent=False,
            )

    # Track source→output mapping for cleanup on deletion
    # (Skip generated and autodoc pages - they have virtual paths that don't exist on disk)
    if (
        dependency_tracker
        and not page.metadata.get("_generated")
        and not page.metadata.get("is_autodoc")
        and hasattr(dependency_tracker, "cache")
        and dependency_tracker.cache
    ):
        dependency_tracker.cache.track_output(page.source_path, page.output_path, site.output_dir)

    # Record output for hot reload tracking
    if collector and page.output_path:
        from bengal.core.output import OutputType

        collector.record(page.output_path, OutputType.HTML, phase="render")


def format_html(html: str, page: Page, site: Any) -> str:
    """
    Format HTML output (minify/pretty).

    Respects page-level and site-level configuration:
    - page.metadata.no_format: Skip formatting
    - site.config.html_output.mode: 'minify', 'pretty', or 'raw'
    - site.config.minify_html: Option

    Args:
        html: Rendered HTML content
        page: Page being rendered
        site: Site instance for config

    Returns:
        Formatted HTML
    """
    try:
        from bengal.postprocess.html_output import format_html_output

        # Resolve mode from config with backward compatibility
        # Priority: page.metadata.no_format → html_output.mode → minify_html
        if page.metadata.get("no_format") is True:
            mode = "raw"
            options = {}
        else:
            html_cfg = site.config.get("html_output", {}) or {}
            mode = html_cfg.get(
                "mode",
                "minify" if site.config.get("minify_html", True) else "pretty",
            )
            options = {
                "remove_comments": html_cfg.get("remove_comments", mode == "minify"),
                "collapse_blank_lines": html_cfg.get("collapse_blank_lines", True),
            }
        return format_html_output(html, mode=mode, options=options)
    except Exception as e:
        # Never fail the build on formatter errors; fall back to raw HTML
        logger.debug(
            "html_formatter_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="falling_back_to_raw_html",
        )
        return html
