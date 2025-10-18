"""
Query Index Registry - Manages all query indexes.

Coordinates:
- Index registration (built-in + custom)
- Index building (full + incremental)
- Index persistence
- Template access

Architecture:
- Lazy initialization (only load when needed)
- Automatic built-in registration
- Support for custom user indexes
- Incremental updates with dependency tracking
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.cache.query_index import QueryIndex
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class QueryIndexRegistry:
    """
    Registry for all query indexes.

    Manages the lifecycle of query indexes:
    - Registration (built-in + custom)
    - Building (full + incremental)
    - Persistence
    - Template access via site.indexes

    Example:
        registry = QueryIndexRegistry(site, cache_dir)
        registry.build_all(site.pages, build_cache)

        # Template access
        blog_posts = registry.get('section').get('blog')
    """

    def __init__(self, site: "Site", cache_dir: Path):
        """
        Initialize registry.

        Args:
            site: Site instance
            cache_dir: Directory for index cache files
        """
        self.site = site
        self.cache_dir = Path(cache_dir)
        self.indexes: dict[str, QueryIndex] = {}
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization - only register indexes when first accessed."""
        if self._initialized:
            return

        self._register_builtins()
        self._initialized = True

    def _register_builtins(self) -> None:
        """Register built-in indexes."""
        try:
            from bengal.cache.indexes.author_index import AuthorIndex
            from bengal.cache.indexes.category_index import CategoryIndex
            from bengal.cache.indexes.date_range_index import DateRangeIndex
            from bengal.cache.indexes.section_index import SectionIndex

            self.register("section", SectionIndex(self.cache_dir / "section_index.json"))
            self.register("author", AuthorIndex(self.cache_dir / "author_index.json"))
            self.register("category", CategoryIndex(self.cache_dir / "category_index.json"))
            self.register("date_range", DateRangeIndex(self.cache_dir / "date_range_index.json"))

            logger.debug("builtin_indexes_registered", count=len(self.indexes))
        except Exception as e:
            logger.warning("builtin_indexes_registration_failed", error=str(e))

    def register(self, name: str, index: "QueryIndex") -> None:
        """
        Register a query index.

        Args:
            name: Index name (e.g., 'section', 'author', 'status')
            index: QueryIndex instance
        """
        if name in self.indexes:
            logger.warning(
                "index_already_registered",
                name=name,
                action="overwriting",
            )

        self.indexes[name] = index
        logger.debug("index_registered", name=name)

    def build_all(
        self,
        pages: list["Page"],
        build_cache: "BuildCache",
        skip_generated: bool = True,
    ) -> None:
        """
        Build all indexes from scratch (full build).

        Args:
            pages: All site pages
            build_cache: Build cache for dependency tracking
            skip_generated: Skip generated pages (tag pages, etc.)
        """
        self._ensure_initialized()

        logger.info("building_all_indexes", indexes=len(self.indexes), pages=len(pages))

        for name, index in self.indexes.items():
            logger.debug("building_index", name=name)

            # Clear existing entries
            index.clear()

            # Build index from all pages
            for page in pages:
                if skip_generated and page.metadata.get("_generated"):
                    continue
                index.update_page(page, build_cache)

            # Save to disk
            index.save_to_disk()

            stats = index.stats()
            logger.info(
                "index_built",
                name=name,
                keys=stats["total_keys"],
                pages=stats["unique_pages"],
            )

    def update_incremental(
        self,
        changed_pages: list["Page"],
        build_cache: "BuildCache",
        skip_generated: bool = True,
    ) -> dict[str, set[str]]:
        """
        Update indexes incrementally for changed pages.

        Args:
            changed_pages: Pages that changed
            build_cache: Build cache for dependency tracking
            skip_generated: Skip generated pages

        Returns:
            Dict mapping index_name → affected_keys
        """
        self._ensure_initialized()

        affected_by_index: dict[str, set[str]] = {}

        logger.info(
            "updating_indexes_incremental",
            indexes=len(self.indexes),
            changed_pages=len(changed_pages),
        )

        for name, index in self.indexes.items():
            affected_keys: set[str] = set()

            for page in changed_pages:
                if skip_generated and page.metadata.get("_generated"):
                    continue

                keys = index.update_page(page, build_cache)
                affected_keys.update(keys)

            affected_by_index[name] = affected_keys

            # Save updated index
            index.save_to_disk()

            if affected_keys:
                logger.debug(
                    "index_updated_incremental",
                    name=name,
                    affected_keys=len(affected_keys),
                )

        return affected_by_index

    def get(self, index_name: str) -> "QueryIndex | None":
        """
        Get index by name.

        Args:
            index_name: Index name (e.g., 'section', 'author')

        Returns:
            QueryIndex instance or None if not found
        """
        self._ensure_initialized()
        return self.indexes.get(index_name)

    def __getattr__(self, name: str) -> "QueryIndex":
        """
        Allow attribute-style access: registry.section instead of registry.get('section').

        Args:
            name: Index name

        Returns:
            QueryIndex instance

        Raises:
            AttributeError: If index not found
        """
        self._ensure_initialized()

        if name.startswith("_"):
            # Don't intercept private attributes
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        index = self.indexes.get(name)
        if index is None:
            raise AttributeError(f"No index named '{name}' is registered")
        return index

    def has(self, index_name: str) -> bool:
        """
        Check if index exists.

        Args:
            index_name: Index name

        Returns:
            True if index is registered
        """
        self._ensure_initialized()
        return index_name in self.indexes

    def save_all(self) -> None:
        """Save all indexes to disk."""
        self._ensure_initialized()

        for name, index in self.indexes.items():
            try:
                index.save_to_disk()
            except Exception as e:
                logger.warning("index_save_failed", name=name, error=str(e))

    def stats(self) -> dict[str, Any]:
        """
        Get statistics for all indexes.

        Returns:
            Dict with index stats
        """
        self._ensure_initialized()

        return {
            "total_indexes": len(self.indexes),
            "indexes": {name: index.stats() for name, index in self.indexes.items()},
        }

    def __repr__(self) -> str:
        """String representation."""
        self._ensure_initialized()
        return f"QueryIndexRegistry(indexes={list(self.indexes.keys())})"
