"""
Block cache management for render orchestration.

Pre-warms and manages a cache of site-wide template blocks (Kida engine only).
Blocks that depend only on site context are rendered once and reused for all pages,
avoiding redundant rendering of nav, footer, etc.

Mixed into RenderOrchestrator via BlockCacheMixin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

logger = get_logger(__name__)


class BlockCacheMixin:
    """
    Mixin providing block cache management for RenderOrchestrator.

    Expects from host class:
        site: SiteLike instance
        _block_cache: BlockCache | None (initialized in __init__)
    """

    site: SiteLike
    _block_cache: Any

    def _warm_block_cache(self) -> None:
        """Pre-warm block cache with site-wide blocks (Kida only).

        Identifies blocks that only depend on site context and pre-renders
        them once. These cached blocks are reused for all pages, avoiding
        redundant rendering of nav, footer, etc.

        RFC: kida-template-introspection
        """
        try:
            from bengal.protocols import EngineCapability
            from bengal.rendering.block_cache import BlockCache
            from bengal.rendering.context import get_engine_globals
            from bengal.rendering.engines import create_engine

            engine = create_engine(self.site)

            if not engine.has_capability(EngineCapability.BLOCK_CACHING):
                return

            self._block_cache = BlockCache(enabled=True)

            site_context = get_engine_globals(self.site)

            templates_to_warm = ["base.html", "page.html", "single.html", "list.html"]
            total_cached = 0

            for template_name in templates_to_warm:
                try:
                    cached = self._block_cache.warm_site_blocks(engine, template_name, site_context)
                    total_cached += cached
                except Exception:
                    pass

            if total_cached > 0:
                logger.info(
                    "block_cache_ready",
                    total_blocks_cached=total_cached,
                    templates_analyzed=len(templates_to_warm),
                )

        except Exception as e:
            logger.debug("block_cache_warm_failed", error=str(e))

    def get_cached_block(self, template_name: str, block_name: str) -> str | None:
        """Get a cached block if available.

        Args:
            template_name: Template containing the block
            block_name: Block to retrieve

        Returns:
            Cached HTML string, or None if not cached
        """
        if self._block_cache is None:
            return None
        return self._block_cache.get(template_name, block_name)

    def get_block_cache_stats(self) -> dict | None:
        """Get block cache statistics.

        Returns:
            Dict with hits, misses, and cached block count, or None if no cache
        """
        if self._block_cache is None:
            return None
        return self._block_cache.get_stats()
