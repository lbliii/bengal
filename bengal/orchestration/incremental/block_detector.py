"""Block-level change detection for incremental builds.

Detects and classifies block-level template changes to enable smart
rebuild decisions. Uses Kida's introspection API to determine which
blocks changed and their cache scope.

RFC: block-level-incremental-builds

Key Insight:
    Most template edits (nav, footer, header) are to site-scoped blocks.
    These don't require per-page rebuilds—just re-cache the block once.

Architecture:
    ```
    Template Change Detected
            │
            ▼
    ┌───────────────────────────────────────┐
    │    BlockChangeDetector                │
    │  ├── Detect changed blocks            │
    │  ├── Classify by cache scope          │
    │  └── Return: BlockChangeSet           │
    └───────────────────────────────────────┘
    ```

Thread-Safety:
    Stateless detection logic. Thread-safe for concurrent calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.rendering.block_cache import BlockCache
    from bengal.rendering.engines.kida import KidaTemplateEngine

logger = get_logger(__name__)


class BlockChangeSet(NamedTuple):
    """Classification of changed blocks by scope.

    Attributes:
        site_scoped: Blocks that only need re-caching (no page rebuilds)
        page_scoped: Blocks that may require page rebuilds
        unknown_scoped: Blocks we can't classify (conservative rebuild)
    """

    site_scoped: set[str]
    page_scoped: set[str]
    unknown_scoped: set[str]

    def is_empty(self) -> bool:
        """Check if no blocks changed."""
        return not (self.site_scoped or self.page_scoped or self.unknown_scoped)

    def only_site_scoped(self) -> bool:
        """Check if only site-scoped blocks changed."""
        return bool(self.site_scoped) and not (self.page_scoped or self.unknown_scoped)


class BlockChangeDetector:
    """Detects and classifies block-level template changes.

    Uses Kida's introspection API to determine which blocks changed
    and what scope they have, enabling smart rebuild decisions.

    Example:
        >>> detector = BlockChangeDetector(engine, block_cache)
        >>> changes = detector.detect_and_classify("base.html")
        >>> if changes.only_site_scoped():
        ...     # Just re-warm site blocks, skip page rebuilds
        ...     pass

    Thread-Safety:
        Stateless. Safe for concurrent calls with different templates.
    """

    def __init__(
        self,
        engine: KidaTemplateEngine,
        block_cache: BlockCache,
    ) -> None:
        """Initialize block change detector.

        Args:
            engine: KidaTemplateEngine instance for introspection
            block_cache: BlockCache for hash tracking
        """
        self.engine = engine
        self.block_cache = block_cache

    def detect_and_classify(
        self,
        template_name: str,
    ) -> BlockChangeSet:
        """Detect changed blocks and classify by scope.

        Args:
            template_name: Template to analyze

        Returns:
            BlockChangeSet with blocks grouped by scope
        """
        # Get changed blocks
        changed_blocks = self.block_cache.detect_changed_blocks(self.engine, template_name)

        if not changed_blocks:
            return BlockChangeSet(set(), set(), set())

        # Get block metadata from introspection
        cacheable = self.engine.get_cacheable_blocks(template_name)

        # Classify by scope
        site_scoped: set[str] = set()
        page_scoped: set[str] = set()
        unknown_scoped: set[str] = set()

        for block_name in changed_blocks:
            scope = cacheable.get(block_name, "unknown")

            if scope == "site":
                site_scoped.add(block_name)
            elif scope == "page":
                page_scoped.add(block_name)
            else:
                unknown_scoped.add(block_name)

        logger.debug(
            "block_change_classification",
            template=template_name,
            site_scoped=list(site_scoped),
            page_scoped=list(page_scoped),
            unknown_scoped=list(unknown_scoped),
        )

        return BlockChangeSet(site_scoped, page_scoped, unknown_scoped)
