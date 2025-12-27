"""Block-level template cache for site-wide block caching.

Uses Kida's template introspection API to identify blocks that can be
cached site-wide (blocks that only depend on site-level context, not
page-specific data).

Architecture:
    ```
    BlockCache
    ├── _site_blocks: dict[str, str]      # Cached site-wide blocks
    ├── _page_blocks: dict[str, str]      # Cached page-level blocks (per build)
    └── _analyzed_templates: set[str]     # Templates we've analyzed
    ```

Usage:
    ```python
    cache = BlockCache()

    # During build startup, analyze templates
    cache.analyze_template(engine, "base.html")

    # Check if we have a cached block
    if html := cache.get("base.html", "nav"):
        # Use cached HTML
    else:
        # Render and cache
        html = render_block(...)
        cache.set("base.html", "nav", html, scope="site")
    ```

Thread-Safety:
    - Site-wide cache is populated once at build start
    - Read-only during parallel page rendering
    - Page-level cache is per-build (cleared between builds)

RFC: kida-template-introspection
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.rendering.engines.kida import KidaTemplateEngine

logger = get_logger(__name__)


class BlockCache:
    """Cache for rendered template blocks.

    Caches blocks based on their introspection-determined cache scope:
    - "site": Cached once per build, reused for all pages
    - "page": Cached per-page (cleared between pages)
    - "none"/"unknown": Not cached

    Attributes:
        _site_blocks: Site-wide cached blocks {template:block -> html}
        _cacheable_blocks: Analysis results {template -> {block -> scope}}
        _stats: Cache hit/miss statistics

    Thread-Safety:
        Site blocks are populated before parallel rendering starts.
        During rendering, only reads occur (thread-safe).
    """

    __slots__ = ("_site_blocks", "_cacheable_blocks", "_stats", "_enabled")

    def __init__(self, enabled: bool = True) -> None:
        """Initialize block cache.

        Args:
            enabled: Whether caching is enabled (default True)
        """
        self._enabled = enabled
        self._site_blocks: dict[str, str] = {}
        self._cacheable_blocks: dict[str, dict[str, str]] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "site_blocks_cached": 0,
            "total_render_time_ms": 0.0,
        }

    def analyze_template(
        self,
        engine: KidaTemplateEngine,
        template_name: str,
    ) -> dict[str, str]:
        """Analyze a template for cacheable blocks.

        Uses Kida's introspection API to determine which blocks can be
        cached and at what scope.

        Args:
            engine: KidaTemplateEngine instance
            template_name: Template to analyze

        Returns:
            Dict of block_name → cache_scope for cacheable blocks
        """
        if not self._enabled:
            return {}

        # Use cached analysis if available
        if template_name in self._cacheable_blocks:
            return self._cacheable_blocks[template_name]

        # Get cacheable blocks from introspection
        cacheable = engine.get_cacheable_blocks(template_name)

        if cacheable:
            logger.debug(
                "block_cache_analysis",
                template=template_name,
                cacheable_blocks=list(cacheable.keys()),
                scopes={k: v for k, v in cacheable.items()},
            )

        self._cacheable_blocks[template_name] = cacheable
        return cacheable

    def get(self, template_name: str, block_name: str) -> str | None:
        """Get cached block HTML.

        Args:
            template_name: Template containing the block
            block_name: Block to retrieve

        Returns:
            Cached HTML string, or None if not cached
        """
        if not self._enabled:
            return None

        key = f"{template_name}:{block_name}"

        if key in self._site_blocks:
            self._stats["hits"] += 1
            return self._site_blocks[key]

        self._stats["misses"] += 1
        return None

    def set(
        self,
        template_name: str,
        block_name: str,
        html: str,
        scope: Literal["site", "page"] = "site",
    ) -> None:
        """Cache rendered block HTML.

        Args:
            template_name: Template containing the block
            block_name: Block name
            html: Rendered HTML
            scope: Cache scope ("site" for cross-page, "page" for single page)
        """
        if not self._enabled:
            return

        if scope == "site":
            key = f"{template_name}:{block_name}"
            if key not in self._site_blocks:
                self._site_blocks[key] = html
                self._stats["site_blocks_cached"] += 1
                logger.debug(
                    "block_cache_set",
                    template=template_name,
                    block=block_name,
                    scope=scope,
                    size_bytes=len(html),
                )

    def warm_site_blocks(
        self,
        engine: KidaTemplateEngine,
        template_name: str,
        site_context: dict,
    ) -> int:
        """Pre-warm cache with site-wide blocks from a template.

        Renders and caches all blocks that have "site" scope (only depend
        on site-level context, not page-specific data).

        Args:
            engine: KidaTemplateEngine instance
            template_name: Template to cache blocks from
            site_context: Site-level context (site, config, etc.)

        Returns:
            Number of blocks cached

        Example:
            >>> cache.warm_site_blocks(engine, "base.html", {"site": site})
            3  # Cached nav, header, footer
        """
        if not self._enabled:
            return 0

        # Analyze template for cacheable blocks
        cacheable = self.analyze_template(engine, template_name)
        if not cacheable:
            return 0

        # Get the template
        try:
            template = engine.env.get_template(template_name)
        except Exception:
            return 0

        # Render and cache site-scoped blocks
        import time

        cached_count = 0
        for block_name, scope in cacheable.items():
            if scope != "site":
                continue

            # Check if already cached
            key = f"{template_name}:{block_name}"
            if key in self._site_blocks:
                continue

            # Render block
            try:
                start_time = time.perf_counter()
                html = template.render_block(block_name, site_context)
                duration = (time.perf_counter() - start_time) * 1000
                self._stats["total_render_time_ms"] += duration

                self.set(template_name, block_name, html, scope="site")
                cached_count += 1
            except Exception as e:
                logger.debug(
                    "block_cache_warm_failed",
                    template=template_name,
                    block=block_name,
                    error=str(e),
                )

        if cached_count > 0:
            logger.info(
                "block_cache_warmed",
                template=template_name,
                blocks_cached=cached_count,
            )

        return cached_count

    def clear(self) -> None:
        """Clear all cached blocks (call between builds)."""
        self._site_blocks.clear()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "site_blocks_cached": 0,
        }
        logger.debug("block_cache_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, and cached block count
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        # Estimate time saved (hits * avg render time of cached blocks)
        avg_render_time = 0.0
        if self._stats["site_blocks_cached"] > 0:
            avg_render_time = (
                self._stats["total_render_time_ms"] / self._stats["site_blocks_cached"]
            )

        time_saved_ms = self._stats["hits"] * avg_render_time

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "site_blocks_cached": self._stats["site_blocks_cached"],
            "hit_rate_pct": round(hit_rate, 1),
            "total_render_time_ms": self._stats["total_render_time_ms"],
            "time_saved_ms": time_saved_ms,
        }

    def is_cacheable(self, template_name: str, block_name: str) -> bool:
        """Check if a block is marked as cacheable.

        Args:
            template_name: Template name
            block_name: Block name

        Returns:
            True if block can be cached (has site or page scope)
        """
        if template_name not in self._cacheable_blocks:
            return False
        return block_name in self._cacheable_blocks[template_name]

    def get_scope(
        self,
        template_name: str,
        block_name: str,
    ) -> Literal["site", "page", "none", "unknown"]:
        """Get cache scope for a block.

        Args:
            template_name: Template name
            block_name: Block name

        Returns:
            Cache scope from introspection analysis
        """
        if template_name not in self._cacheable_blocks:
            return "unknown"
        return self._cacheable_blocks[template_name].get(block_name, "unknown")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<BlockCache site_blocks={stats['site_blocks_cached']} "
            f"hit_rate={stats['hit_rate_pct']:.1f}%>"
        )
