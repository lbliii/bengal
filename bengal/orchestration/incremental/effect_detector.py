"""
Unified effect-based change detector.

RFC: Snapshot-Enabled v2 Opportunities (Effect-Traced Builds)

Replaces 13 detector classes with ONE unified model:
- file_detector.py → Effect.depends_on includes source file
- template_detector.py → Effect.depends_on includes layout + includes
- cascade_tracker.py → Effect.depends_on includes parent _index.md
- taxonomy_detector.py → Effect.invalidates includes taxonomy keys
- data_detector.py → Effect.depends_on includes data/*.yaml paths
- version_detector.py → Effect.depends_on includes version file

Thread-safe because it operates on frozen SiteSnapshot and EffectTracer.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.effects import EffectTracer
from bengal.effects.block_diff import BlockDiffService

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.snapshots.types import SiteSnapshot


class EffectBasedDetector:
    """
    Unified change detector using the Effect system.

    Replaces 13 detector files with one unified model.

    Key improvements over legacy detectors:
    - Single source of truth for dependencies
    - Transitive invalidation computed automatically
    - Content-aware diffing for smarter rebuilds
    - Debug tooling via `bengal build --show-effects`

    Usage:
        >>> detector = EffectBasedDetector(site, tracer, snapshot)
        >>> pages_to_rebuild = detector.detect_changes(changed_paths)
    """

    def __init__(
        self,
        site: Site,
        tracer: EffectTracer,
        old_snapshot: SiteSnapshot | None = None,
        new_snapshot: SiteSnapshot | None = None,
    ) -> None:
        """
        Initialize detector.

        Args:
            site: Mutable Site instance (for backward compatibility)
            tracer: EffectTracer with recorded effects from previous build
            old_snapshot: Previous build's snapshot (for content-aware diffing)
            new_snapshot: Current snapshot (for content-aware diffing)
        """
        self.site = site
        self.tracer = tracer
        self._block_diff: BlockDiffService | None = None

        if old_snapshot and new_snapshot:
            self._block_diff = BlockDiffService(old_snapshot, new_snapshot)

    def detect_changes(
        self,
        changed_paths: set[Path],
        *,
        verbose: bool = False,
    ) -> set[Path]:
        """
        Detect pages that need rebuilding based on changed files.

        Uses the Effect system to compute transitive invalidations.

        Args:
            changed_paths: Files that changed since last build
            verbose: Whether to log detailed change information

        Returns:
            Set of page source paths that need rebuilding
        """
        pages_to_rebuild: set[Path] = set()

        # Use EffectTracer for transitive invalidation
        outputs_needing_rebuild = self.tracer.outputs_needing_rebuild(changed_paths)

        # Map outputs back to source paths
        for output_path in outputs_needing_rebuild:
            deps = self.tracer.get_dependencies_for_output(output_path)
            for dep in deps:
                if isinstance(dep, Path) and dep.suffix == ".md":
                    pages_to_rebuild.add(dep)

        # Also check direct content changes
        for path in changed_paths:
            if path.suffix == ".md":
                # Content file changed directly
                if self._should_rebuild_content(path):
                    pages_to_rebuild.add(path)
            elif path.suffix in (".html", ".jinja", ".j2"):
                # Template changed - find affected pages
                pages_to_rebuild.update(self._pages_for_template(path))
            elif path.suffix in (".yaml", ".yml", ".json", ".toml"):
                # Config or data file changed
                if "data/" in str(path) or path.name.startswith("_"):
                    pages_to_rebuild.update(self._pages_for_data_file(path))
                elif "config" in path.name.lower():
                    # Config change - rebuild all
                    pages_to_rebuild.update(self._all_page_paths())
            elif path.suffix in (".css", ".scss", ".sass", ".less"):
                # Style change - rebuild all (affects all pages)
                pages_to_rebuild.update(self._all_page_paths())

        return pages_to_rebuild

    def _should_rebuild_content(self, source_path: Path) -> bool:
        """
        Check if a content file change requires rebuild.

        Uses content-aware diffing when available.
        """
        if self._block_diff is None:
            return True  # No diffing available, assume rebuild needed

        result = self._block_diff.diff_page(source_path)
        return result.requires_rebuild

    def _pages_for_template(self, template_path: Path) -> set[Path]:
        """Get pages affected by a template change."""
        pages: set[Path] = set()
        template_name = template_path.name

        # Check EffectTracer for pages using this template
        for effect in self.tracer.effects:
            if template_name in effect.depends_on or template_path in effect.depends_on:
                # Find source path in dependencies
                for dep in effect.depends_on:
                    if isinstance(dep, Path) and dep.suffix == ".md":
                        pages.add(dep)

        # Fallback: scan all pages if tracer doesn't have info
        if not pages:
            for page in self.site.pages:
                if hasattr(page, "template") and page.template == template_name:
                    pages.add(page.source_path)

        return pages

    def _pages_for_data_file(self, data_path: Path) -> set[Path]:
        """Get pages affected by a data file change."""
        pages: set[Path] = set()

        # Check EffectTracer for pages using this data file
        for effect in self.tracer.effects:
            if data_path in effect.depends_on:
                for dep in effect.depends_on:
                    if isinstance(dep, Path) and dep.suffix == ".md":
                        pages.add(dep)

        return pages

    def _all_page_paths(self) -> set[Path]:
        """Get all page source paths."""
        return {page.source_path for page in self.site.pages}

    def get_invalidated_cache_keys(self, changed_paths: set[Path]) -> set[str]:
        """
        Get cache keys that should be invalidated.

        Useful for cache cleanup after incremental builds.
        """
        return self.tracer.invalidated_by(changed_paths)

    def get_statistics(self) -> dict[str, Any]:
        """Get detection statistics for debugging."""
        return {
            "tracer_effects": len(self.tracer.effects),
            "has_block_diff": self._block_diff is not None,
            **self.tracer.get_statistics(),
        }


def create_detector_from_build(
    site: Site,
    old_snapshot: SiteSnapshot | None = None,
    new_snapshot: SiteSnapshot | None = None,
) -> EffectBasedDetector:
    """
    Create detector from a build's effect tracer.

    Convenience function for integrating with build orchestrator.

    Args:
        site: Site instance
        old_snapshot: Previous build's snapshot
        new_snapshot: Current snapshot

    Returns:
        EffectBasedDetector ready for change detection
    """
    from bengal.effects import BuildEffectTracer

    tracer = BuildEffectTracer.get_instance().tracer
    return EffectBasedDetector(
        site=site,
        tracer=tracer,
        old_snapshot=old_snapshot,
        new_snapshot=new_snapshot,
    )
