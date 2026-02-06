"""
Unified dependency tracking via effect tracing.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 1)

EffectTracer replaces 13 detector classes with one unified model:
- file_detector.py → Effect.depends_on includes source file
- template_detector.py → Effect.depends_on includes layout + includes
- cascade_tracker.py → Effect.depends_on includes parent _index.md
- taxonomy_detector.py → Effect.invalidates includes taxonomy keys
- data_detector.py → Effect.depends_on includes data/*.yaml paths
- version_detector.py → Effect.depends_on includes version file

Thread-safe because it only reads frozen SiteSnapshot.
"""

import threading
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.effects.effect import Effect

if TYPE_CHECKING:
    from bengal.snapshots.types import SiteSnapshot


class EffectTracer:
    """
    Unified dependency tracking.

    Thread-safe because it only reads frozen SiteSnapshot.
    Records effects during rendering and computes invalidation sets.

    Replaces 13 detector classes with one unified model.

    Usage:
        >>> tracer = EffectTracer()
        >>>
        >>> # During rendering, record effects
        >>> tracer.record(Effect.for_page_render(...))
        >>>
        >>> # After file change, query what's invalidated
        >>> invalidated = tracer.invalidated_by({Path("content/page.md")})
        >>> outputs = tracer.outputs_needing_rebuild({Path("content/page.md")})

    Attributes:
        effects: All recorded effects
        _dep_index: Reverse index from dependency → effects
        _output_index: Index from output → effect
        _invalidation_index: Index from cache key → effects
    """

    def __init__(self) -> None:
        """Initialize empty tracer."""
        self._effects: list[Effect] = []
        self._lock = threading.Lock()

        # Indexes for fast lookup
        # dependency (Path | str) → list of effects that depend on it
        self._dep_index: dict[Path | str, list[Effect]] = defaultdict(list)
        # output Path → effect that produces it
        self._output_index: dict[Path, Effect] = {}
        # cache key → list of effects that invalidate it
        self._invalidation_index: dict[str, list[Effect]] = defaultdict(list)

    @property
    def effects(self) -> list[Effect]:
        """All recorded effects (read-only copy)."""
        with self._lock:
            return list(self._effects)

    def _index_effect(self, effect: Effect) -> None:
        """
        Index a single effect into all lookup structures.

        Must be called while holding self._lock.

        Args:
            effect: Effect to index
        """
        self._effects.append(effect)

        # Update dependency index
        for dep in effect.depends_on:
            self._dep_index[dep].append(effect)

        # Update output index
        for output in effect.outputs:
            self._output_index[output] = effect

        # Update invalidation index
        for key in effect.invalidates:
            self._invalidation_index[key].append(effect)

    def _effects_for_path(self, path: Path) -> list[Effect]:
        """
        Get effects depending on a path (checks both Path and name forms).

        Templates are often referenced by name only, so we check both
        the full path and just the filename.

        Must be called while holding self._lock.

        Args:
            path: Path to look up

        Returns:
            List of effects that depend on this path (may have duplicates)
        """
        effects = list(self._dep_index.get(path, []))
        # Also check template name form
        effects.extend(self._dep_index.get(path.name, []))
        return effects

    def record(self, effect: Effect) -> None:
        """
        Record an effect during rendering.

        Thread-safe: Uses lock for index updates.

        Args:
            effect: Effect to record
        """
        with self._lock:
            self._index_effect(effect)

    def record_batch(self, effects: list[Effect]) -> None:
        """
        Record multiple effects at once.

        More efficient than recording one at a time.

        Args:
            effects: List of effects to record
        """
        with self._lock:
            for effect in effects:
                self._index_effect(effect)

    def invalidated_by(self, changed: set[Path]) -> set[str]:
        """
        What cache keys are invalidated by these changes?

        Computes transitive closure of invalidations.

        Args:
            changed: Set of changed file paths

        Returns:
            Set of cache keys that should be invalidated
        """
        invalidated: set[str] = set()

        with self._lock:
            # Direct invalidations
            for path in changed:
                for effect in self._effects_for_path(path):
                    invalidated.update(effect.invalidates)

            # Transitive invalidations (if an output changes, its dependents are invalidated)
            outputs_changed = self._outputs_for_deps(changed)
            for output in outputs_changed:
                for effect in self._effects_for_path(output):
                    invalidated.update(effect.invalidates)

        return invalidated

    def outputs_needing_rebuild(self, changed: set[Path]) -> set[Path]:
        """
        Which outputs need rebuilding? (transitive)

        Args:
            changed: Set of changed file paths

        Returns:
            Set of output paths that need to be regenerated
        """
        outputs: set[Path] = set()
        seen: set[Path] = set()
        queue = list(changed)

        with self._lock:
            while queue:
                path = queue.pop()
                if path in seen:
                    continue
                seen.add(path)

                # Find effects that depend on this path (both full path and name)
                for effect in self._effects_for_path(path):
                    outputs.update(effect.outputs)
                    # Add outputs to queue for transitive deps
                    queue.extend(effect.outputs)

        return outputs

    def _outputs_for_deps(self, deps: set[Path]) -> set[Path]:
        """Get outputs that are produced by effects depending on these paths."""
        outputs: set[Path] = set()
        for dep in deps:
            for effect in self._dep_index.get(dep, []):
                outputs.update(effect.outputs)
        return outputs

    def get_dependencies_for_output(self, output_path: Path) -> frozenset[Path | str]:
        """
        Get all dependencies for a specific output.

        Args:
            output_path: Path to the output file

        Returns:
            Frozen set of dependencies (files and template names)
        """
        with self._lock:
            effect = self._output_index.get(output_path)
            if effect:
                return effect.depends_on
            return frozenset()

    def get_effects_for_cache_key(self, cache_key: str) -> list[Effect]:
        """
        Get effects that would invalidate a cache key.

        Args:
            cache_key: Cache key to look up

        Returns:
            List of effects that invalidate this key
        """
        with self._lock:
            return list(self._invalidation_index.get(cache_key, []))

    def clear(self) -> None:
        """Clear all recorded effects and indexes."""
        with self._lock:
            self._effects.clear()
            self._dep_index.clear()
            self._output_index.clear()
            self._invalidation_index.clear()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about recorded effects.

        Useful for debugging and `bengal build --show-effects`.
        """
        with self._lock:
            operations: dict[str, int] = defaultdict(int)
            for effect in self._effects:
                operations[effect.operation or "unknown"] += 1

            return {
                "total_effects": len(self._effects),
                "unique_dependencies": len(self._dep_index),
                "unique_outputs": len(self._output_index),
                "cache_keys": len(self._invalidation_index),
                "by_operation": dict(operations),
            }

    def to_dependency_graph(self) -> dict[str, list[str]]:
        """
        Export dependency graph for visualization.

        Returns:
            Dict mapping output paths to their dependencies
        """
        with self._lock:
            graph: dict[str, list[str]] = {}
            for output, effect in self._output_index.items():
                deps = [str(d) if isinstance(d, Path) else d for d in effect.depends_on]
                graph[str(output)] = deps
            return graph


class SnapshotEffectBuilder:
    """
    Build effects from a SiteSnapshot.

    Pre-computes effects for all pages in the snapshot,
    enabling fast incremental rebuild queries.
    """

    def __init__(self, snapshot: SiteSnapshot) -> None:
        """
        Initialize builder with snapshot.

        Args:
            snapshot: Frozen site snapshot
        """
        self._snapshot = snapshot
        self._tracer = EffectTracer()

    def build_effects(self) -> EffectTracer:
        """
        Build effects for all pages in the snapshot.

        Pre-populates cascade sources and template dependencies for each page,
        providing the EffectTracer with a complete baseline dependency graph.
        Render-time recording enriches this with dynamically discovered deps.

        Returns:
            EffectTracer with all page effects recorded
        """
        effects: list[Effect] = []

        # Build page → section path mapping for cascade resolution
        page_section_map = self._build_page_section_map()

        for page in self._snapshot.pages:
            # Get template includes from template snapshot
            template_includes: frozenset[str] = frozenset()
            if page.template_name in self._snapshot.templates:
                template_snap = self._snapshot.templates[page.template_name]
                template_includes = template_snap.all_dependencies

            # Resolve cascade sources (parent _index.md files)
            cascade_sources = self._resolve_cascade_sources(page, page_section_map)

            # Create effect for this page
            effect = Effect.for_page_render(
                source_path=page.source_path,
                output_path=page.output_path,
                template_name=page.template_name,
                template_includes=template_includes,
                page_href=page.href,
                cascade_sources=frozenset(cascade_sources) if cascade_sources else None,
            )
            effects.append(effect)

        self._tracer.record_batch(effects)
        return self._tracer

    def _build_page_section_map(self) -> dict[Path, list[Path]]:
        """
        Build a mapping from page source_path to section _index.md paths.

        Walks the section hierarchy to find all _index.md files that
        contribute cascade metadata to each page.

        Returns:
            Dict mapping page source_path to list of cascade source paths
        """
        page_sections: dict[Path, list[Path]] = {}

        def _process_section(
            section: Any,
            parent_index_paths: list[Path],
        ) -> None:
            """Recursively process sections and map pages to their cascade sources."""
            # Build cascade source list for this section
            section_index_paths = list(parent_index_paths)
            if section.path is not None:
                index_path = section.path / "_index.md"
                section_index_paths.append(index_path)

            # Map all pages in this section to cascade sources
            for page in section.pages:
                page_sections[page.source_path] = section_index_paths

            # Recurse into subsections
            for subsection in section.subsections:
                _process_section(subsection, section_index_paths)

        # Start from root section
        _process_section(self._snapshot.root_section, [])

        return page_sections

    def _resolve_cascade_sources(
        self,
        page: Any,
        page_section_map: dict[Path, list[Path]],
    ) -> list[Path]:
        """
        Get cascade source _index.md paths for a page.

        Args:
            page: PageSnapshot to resolve cascade sources for
            page_section_map: Pre-built mapping from page → section index paths

        Returns:
            List of _index.md paths that cascade to this page
        """
        return page_section_map.get(page.source_path, [])

    @classmethod
    def from_snapshot(cls, snapshot: SiteSnapshot) -> EffectTracer:
        """
        Convenience method to build tracer from snapshot.

        Args:
            snapshot: Frozen site snapshot

        Returns:
            EffectTracer with all page effects
        """
        builder = cls(snapshot)
        return builder.build_effects()
