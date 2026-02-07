"""
Cache checking and storage for the rendering pipeline.

This module handles checking and storing parsed/rendered content in cache
for incremental builds. Extracted from core.py per RFC: rfc-modularize-large-files.

Classes:
CacheChecker: Handles cache operations for the rendering pipeline.

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.rendering.pipeline.output import format_html, write_output
from bengal.rendering.pipeline.toc import extract_toc_structure
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.sentinel import is_missing

if TYPE_CHECKING:
    from bengal.protocols import PageLike
    from bengal.rendering.renderer import Renderer

logger = get_logger(__name__)


class CacheChecker:
    """
    Handles cache operations for the rendering pipeline.

    Manages both rendered output cache (final HTML) and parsed content cache
    (parsed AST before template rendering) for incremental builds.

    Attributes:
        dependency_tracker: DependencyTracker for dependency tracking (e.g. end_page())
        build_cache: BuildCache for direct cache access (resolved from build_cache or
            dependency_tracker.cache)
        site: Site instance for configuration
        renderer: Renderer for template rendering
        build_stats: Optional BuildStats for metrics
        output_collector: Optional collector for hot reload tracking

    Example:
            >>> checker = CacheChecker(
            ...     dependency_tracker=tracker,
            ...     site=site,
            ...     renderer=renderer,
            ...     build_stats=stats,
            ... )
            >>> if checker.try_rendered_cache(page, template):
            ...     return  # Cache hit, page already written

    """

    def __init__(
        self,
        dependency_tracker: Any,
        site: Any,
        renderer: Renderer,
        build_stats: Any = None,
        output_collector: Any = None,
        write_behind: Any = None,
        build_cache: Any = None,
    ):
        """
        Initialize the cache checker.

        Args:
            dependency_tracker: DependencyTracker for dependency tracking (e.g. end_page())
            site: Site instance for configuration
            renderer: Renderer for template rendering
            build_stats: Optional BuildStats for metrics collection
            output_collector: Optional output collector for hot reload tracking
            write_behind: Optional write-behind collector for async I/O
            build_cache: Optional BuildCache for direct cache access. If None,
                falls back to dependency_tracker.cache for backward compatibility.
        """
        self.dependency_tracker = dependency_tracker
        self.site = site
        self.renderer = renderer
        self.build_stats = build_stats
        self.output_collector = output_collector
        self.write_behind = write_behind

        # Direct cache access: prefer explicit build_cache, fall back to dependency_tracker.cache
        self.build_cache = build_cache or (
            getattr(dependency_tracker, "cache", None) if dependency_tracker else None
        )

    def try_rendered_cache(self, page: PageLike, template: str) -> bool:
        """
        Try to use rendered output cache.

        If the page's rendered HTML is cached and valid, writes it directly
        to output without re-rendering.

        Args:
            page: Page to check cache for
            template: Template name for cache validation

        Returns:
            True if cache hit (page written), False if cache miss
        """
        if not self.build_cache or page.metadata.get("_generated"):
            return False

        cache = self.build_cache

        # Pass output_dir for asset manifest validation
        output_dir = getattr(self.site, "output_dir", None)
        rendered_html = cache.get_rendered_output(
            page.source_path, template, page.metadata, output_dir=output_dir
        )
        if not rendered_html or is_missing(rendered_html):
            return False

        page.rendered_html = rendered_html

        if self.build_stats:
            if not hasattr(self.build_stats, "rendered_cache_hits"):
                self.build_stats.rendered_cache_hits = 0
            self.build_stats.rendered_cache_hits += 1

        # Ensure output_path is set before writing (required by write_output)
        if not page.output_path:
            from bengal.rendering.pipeline.output import determine_output_path

            page.output_path = determine_output_path(page, self.site)

        write_output(
            page,
            self.site,
            self.dependency_tracker,
            collector=self.output_collector,
            write_behind=self.write_behind,
            build_cache=self.build_cache,
        )

        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.end_page()

        return True

    def try_parsed_cache(self, page: PageLike, template: str, parser_version: str) -> bool:
        """
        Try to use parsed content cache.

        If the page's parsed AST is cached and valid, renders it through
        the template engine without re-parsing the source content.

        Args:
            page: Page to check cache for
            template: Template name for cache validation
            parser_version: Parser version for cache validation

        Returns:
            True if cache hit (page rendered and written), False if cache miss
        """
        if not self.build_cache or page.metadata.get("_generated"):
            return False

        cache = self.build_cache

        cached = cache.get_parsed_content(page.source_path, page.metadata, template, parser_version)
        if not cached or is_missing(cached):
            return False

        page.html_content = cached["html"]
        page.toc = cached["toc"]
        page._toc_items_cache = cached.get("toc_items", [])

        if cached.get("ast"):
            page._ast_cache = cached["ast"]

        if self.build_stats:
            if not hasattr(self.build_stats, "parsed_cache_hits"):
                self.build_stats.parsed_cache_hits = 0
            self.build_stats.parsed_cache_hits += 1

        parsed_content = cached["html"]

        # Validate cached content is not empty
        if not parsed_content:
            logger.warning(
                "parsed_cache_empty",
                page=str(page.source_path),
                template=template,
            )
            return False

        # Pre-compute plain_text cache
        _ = page.plain_text

        # Restore cached links if present; otherwise fall back to extraction.
        cached_links = cached.get("links")
        if isinstance(cached_links, list):
            try:
                page.links = [str(x) for x in cached_links]
            except Exception:
                page.links = []
        else:
            try:
                page.extract_links()
            except Exception as e:
                logger.debug(
                    "link_extraction_failed",
                    page=str(page.source_path),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        html_content = self.renderer.render_content(parsed_content)
        page.rendered_html = self.renderer.render_page(page, html_content)
        page.rendered_html = format_html(page.rendered_html, page, self.site)

        # Validate rendered HTML is not empty
        if not page.rendered_html:
            logger.warning(
                "rendered_html_empty_after_cache",
                page=str(page.source_path),
                template=template,
                parsed_content_length=len(parsed_content) if parsed_content else 0,
            )
            return False

        # Ensure output_path is set before writing (required by write_output)
        if not page.output_path:
            from bengal.rendering.pipeline.output import determine_output_path

            page.output_path = determine_output_path(page, self.site)

        write_output(
            page,
            self.site,
            self.dependency_tracker,
            collector=self.output_collector,
            write_behind=self.write_behind,
            build_cache=self.build_cache,
        )

        if self.dependency_tracker and not page.metadata.get("_generated"):
            self.dependency_tracker.end_page()

        return True

    def cache_parsed_content(self, page: PageLike, template: str, parser_version: str) -> None:
        """
        Store parsed content in cache for next build.

        Args:
            page: Page with parsed content
            template: Template name used
            parser_version: Parser version used
        """
        if not self.build_cache or page.metadata.get("_generated"):
            return

        cache = self.build_cache

        toc_items = extract_toc_structure(page.toc or "")
        md_cfg = self.site.config.get("markdown", {}) or {}
        ast_cache_cfg = md_cfg.get("ast_cache", {}) or {}
        persist_tokens = bool(ast_cache_cfg.get("persist_tokens", False))
        cached_ast = getattr(page, "_ast_cache", None) if persist_tokens else None
        cached_links = getattr(page, "links", None)

        cache.store_parsed_content(
            page.source_path,
            page.html_content,
            page.toc,
            toc_items,
            cached_links if isinstance(cached_links, list) else None,
            page.metadata,
            template,
            parser_version,
            ast=cached_ast,
        )

    def cache_rendered_output(self, page: PageLike, template: str) -> None:
        """
        Store rendered output in cache for next build.

        Args:
            page: Page with rendered HTML
            template: Template name used
        """
        if not self.build_cache or page.metadata.get("_generated"):
            return

        cache = self.build_cache

        page_key = str(page.source_path)
        deps = list(cache.dependencies.get(page_key, []))

        # Pass output_dir to capture asset manifest mtime for cache invalidation
        output_dir = getattr(self.site, "output_dir", None)
        cache.store_rendered_output(
            page.source_path,
            page.rendered_html,
            template,
            page.metadata,
            dependencies=deps,
            output_dir=output_dir,
        )

    def should_bypass_cache(self, page: PageLike, changed_sources: set[Path]) -> bool:
        """
        Determine if cache should be bypassed for this page.

        Args:
            page: Page to check
            changed_sources: Set of changed source paths

        Returns:
            True if cache should be bypassed
        """
        # Check if page was marked for rebuild due to cascade changes
        # This flag is set by the provenance filter when cascade sources change
        if getattr(page, "_cascade_invalidated", False):
            return True

        if not self.build_cache:
            return False

        return self.build_cache.should_bypass(page.source_path, changed_sources)
