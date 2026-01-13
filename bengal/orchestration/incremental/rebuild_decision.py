"""Smart rebuild decision engine for block-level incremental builds.

Makes rebuild decisions based on block-level change classification.
Key insight: If only site-scoped blocks changed, we can skip page
rebuilds entirely and just re-warm those blocks.

RFC: block-level-incremental-builds

Architecture:
    ```
    BlockChangeSet
            │
            ▼
    ┌───────────────────────────────────────┐
    │    RebuildDecisionEngine              │
    │  ├── Site-scoped only? → Re-warm      │
    │  ├── Check child template overrides   │
    │  ├── Page-scoped? → Find affected     │
    │  └── Return: RebuildDecision          │
    └───────────────────────────────────────┘
    ```

Thread-Safety:
Uses cached inheritance data. Safe for concurrent calls.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.orchestration.incremental.block_detector import (
    BlockChangeDetector,
)
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.rendering.block_cache import BlockCache
    from bengal.rendering.engines.kida import KidaTemplateEngine

logger = get_logger(__name__)


@dataclass
class RebuildDecision:
    """Rebuild decision for a template change.
    
    Attributes:
        blocks_to_rewarm: Site-scoped blocks to re-cache
        pages_to_rebuild: Pages that need full rebuild
        skip_all_pages: True if only site-scoped blocks changed
        reason: Human-readable explanation
        child_templates: Child templates also affected (inheritance)
        
    """

    blocks_to_rewarm: set[str] = field(default_factory=set)
    pages_to_rebuild: set[Path] = field(default_factory=set)
    skip_all_pages: bool = False
    reason: str = ""
    child_templates: set[str] = field(default_factory=set)


class RebuildDecisionEngine:
    """Makes smart rebuild decisions based on block-level changes.
    
    Key insight: If only site-scoped blocks changed, we can skip
    page rebuilds entirely and just re-warm those blocks.
    
    Handles template inheritance: When base.html changes, child templates
    (page.html extends base.html) may also need block re-hashing.
    
    Example:
            >>> engine = RebuildDecisionEngine(detector, cache, tracker, kida)
            >>> decision = engine.decide("base.html", Path("templates/base.html"))
            >>> if decision.skip_all_pages:
            ...     # Only re-warm blocks, no page rebuilds needed!
            ...     for block in decision.blocks_to_rewarm:
            ...         rewarm_block(block)
    
    Thread-Safety:
        Uses cached inheritance data. Safe for concurrent calls.
        
    """

    def __init__(
        self,
        block_detector: BlockChangeDetector,
        block_cache: BlockCache,
        build_cache: BuildCache,
        engine: KidaTemplateEngine,
    ) -> None:
        """Initialize rebuild decision engine.

        Args:
            block_detector: BlockChangeDetector for change classification
            block_cache: BlockCache for block operations
            build_cache: BuildCache for affected page lookup
            engine: KidaTemplateEngine for introspection
        """
        self.block_detector = block_detector
        self.block_cache = block_cache
        self.build_cache = build_cache
        self.engine = engine
        self._inheritance_cache: dict[str, set[str]] = {}

    def decide(
        self,
        template_name: str,
        template_path: Path,
    ) -> RebuildDecision:
        """Decide what to rebuild for a template change.

        Args:
            template_name: Template that changed (e.g., "base.html")
            template_path: Path to template file

        Returns:
            RebuildDecision with blocks to re-warm and pages to rebuild
        """
        # Classify changed blocks in this template
        changes = self.block_detector.detect_and_classify(template_name)

        # Find child templates that inherit from this one
        child_templates = self._get_child_templates(template_name)

        # Case 1: No blocks changed (file touched but content identical)
        if changes.is_empty():
            logger.debug(
                "rebuild_decision_no_changes",
                template=template_name,
            )
            return RebuildDecision(
                blocks_to_rewarm=set(),
                pages_to_rebuild=set(),
                skip_all_pages=True,
                reason="No block content changed",
                child_templates=set(),
            )

        # Case 2: Only site-scoped blocks changed
        if changes.only_site_scoped():
            # Check if child templates override any of the changed blocks
            child_overrides = self._check_child_overrides(child_templates, changes.site_scoped)

            if child_overrides:
                # Some children override changed blocks - need page rebuilds
                affected_pages = self._get_affected_pages_from_templates(child_overrides)
                logger.debug(
                    "rebuild_decision_child_overrides",
                    template=template_name,
                    child_overrides=list(child_overrides),
                    affected_pages=len(affected_pages),
                )
                return RebuildDecision(
                    blocks_to_rewarm=changes.site_scoped,
                    pages_to_rebuild=affected_pages,
                    skip_all_pages=False,
                    reason=f"Child templates override changed blocks: {child_overrides}",
                    child_templates=child_overrides,
                )

            logger.info(
                "rebuild_decision_site_scoped_only",
                template=template_name,
                blocks=list(changes.site_scoped),
                pages_skipped=True,
            )
            return RebuildDecision(
                blocks_to_rewarm=changes.site_scoped,
                pages_to_rebuild=set(),
                skip_all_pages=True,
                reason=f"Only site-scoped blocks changed: {changes.site_scoped}",
                child_templates=set(),
            )

        # Case 3: Page-scoped or unknown blocks changed
        # Need to rebuild affected pages
        affected_pages = self._get_affected_pages(template_path)

        logger.debug(
            "rebuild_decision_page_scoped",
            template=template_name,
            page_scoped=list(changes.page_scoped),
            unknown_scoped=list(changes.unknown_scoped),
            affected_pages=len(affected_pages),
        )

        return RebuildDecision(
            blocks_to_rewarm=changes.site_scoped,  # Still re-warm site blocks
            pages_to_rebuild=affected_pages,
            skip_all_pages=False,
            reason=f"Page-scoped blocks changed: {changes.page_scoped | changes.unknown_scoped}",
            child_templates=child_templates,
        )

    def _get_child_templates(self, parent_name: str) -> set[str]:
        """Find all templates that extend the given parent.

        Uses template introspection's `extends` field to build
        an inheritance graph.

        Args:
            parent_name: Parent template name (e.g., "base.html")

        Returns:
            Set of child template names (e.g., {"page.html", "post.html"})
        """
        if parent_name in self._inheritance_cache:
            return self._inheritance_cache[parent_name]

        children = set()

        # Scan all loaded templates for inheritance relationships
        try:
            for name in self.engine.env.list_templates():
                try:
                    template = self.engine.env.get_template(name)
                    meta = template.template_metadata()
                    if meta and meta.extends == parent_name:
                        children.add(name)
                except Exception:
                    continue
        except Exception:
            pass

        self._inheritance_cache[parent_name] = children
        return children

    def _check_child_overrides(
        self,
        child_templates: set[str],
        changed_blocks: set[str],
    ) -> set[str]:
        """Check which child templates override any of the changed blocks.

        Args:
            child_templates: Set of child template names
            changed_blocks: Blocks that changed in parent

        Returns:
            Set of child template names that override changed blocks
        """
        overriding_children: set[str] = set()

        for child_name in child_templates:
            try:
                template = self.engine.env.get_template(child_name)
                meta = template.template_metadata()
                if meta:
                    child_blocks = set(meta.blocks.keys())
                    if child_blocks & changed_blocks:
                        overriding_children.add(child_name)
            except Exception:
                # If we can't analyze, assume it might override (conservative)
                overriding_children.add(child_name)

        return overriding_children

    def _get_affected_pages_from_templates(
        self,
        template_names: set[str],
    ) -> set[Path]:
        """Get pages using any of the given templates.

        Args:
            template_names: Set of template names to check

        Returns:
            Set of page paths using these templates
        """
        affected: set[Path] = set()
        for name in template_names:
            # Resolve template name to path, then get affected pages
            template_path = self.engine.get_template_path(name)
            if template_path:
                pages = self.build_cache.get_affected_pages(template_path)
                affected.update(Path(p) for p in pages)
        return affected

    def _get_affected_pages(
        self,
        template_path: Path,
    ) -> set[Path]:
        """Get pages affected by template changes.

        Uses existing dependency tracking infrastructure.

        Args:
            template_path: Path to the changed template

        Returns:
            Set of page paths that need rebuilding
        """
        affected = self.build_cache.get_affected_pages(template_path)
        return {Path(p) for p in affected}

    def clear_inheritance_cache(self) -> None:
        """Clear cached inheritance data.

        Call this at the start of a new build to refresh
        inheritance relationships.
        """
        self._inheritance_cache.clear()
