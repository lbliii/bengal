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

import json
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

        # File fingerprints for change detection
        self._fingerprints: dict[str, dict[str, Any]] = {}  # path -> {mtime, size}
        self._pending_fingerprints: set[Path] = set()  # Deferred updates

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

    # --- File Fingerprinting ---

    def update_fingerprint(self, path: Path) -> None:
        """Record current file fingerprint (deferred until flush)."""
        self._pending_fingerprints.add(path)

    def flush_pending_fingerprints(self) -> None:
        """Apply all pending fingerprint updates."""
        with self._lock:
            for path in self._pending_fingerprints:
                if path.exists():
                    stat = path.stat()
                    self._fingerprints[str(path)] = {
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                    }
                else:
                    self._fingerprints.pop(str(path), None)
            self._pending_fingerprints.clear()

    def is_changed(self, path: Path) -> bool:
        """Check if a file has changed since last fingerprint."""
        key = str(path)
        cached = self._fingerprints.get(key)
        if cached is None:
            return True  # New file
        if not path.exists():
            return True  # Deleted file
        stat = path.stat()
        return stat.st_mtime != cached["mtime"] or stat.st_size != cached["size"]

    def get_changed_files(self, root_path: Path) -> set[Path]:
        """Get all files that have changed since last fingerprint."""
        changed: set[Path] = set()
        for path_str in self._fingerprints:
            path = Path(path_str)
            if self.is_changed(path):
                changed.add(path)
        return changed

    # --- Persistence ---

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracer state to dict."""
        with self._lock:
            return {
                "effects": [e.to_dict() for e in self._effects],
                "fingerprints": dict(self._fingerprints),
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EffectTracer:
        """Deserialize tracer from dict."""
        tracer = cls()
        effects = [Effect.from_dict(e) for e in data.get("effects", [])]
        tracer.record_batch(effects)
        tracer._fingerprints = dict(data.get("fingerprints", {}))
        return tracer

    def save(self, path: Path) -> None:
        """Save tracer state to a JSON file."""
        data = self.to_dict()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, separators=(",", ":"))

    @classmethod
    def load(cls, path: Path) -> EffectTracer:
        """Load tracer state from a JSON file."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

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

        Returns:
            EffectTracer with all page effects recorded
        """
        effects: list[Effect] = []

        for page in self._snapshot.pages:
            # Get template includes from template snapshot
            template_includes: frozenset[str] = frozenset()
            if page.template_name in self._snapshot.templates:
                template_snap = self._snapshot.templates[page.template_name]
                template_includes = template_snap.all_dependencies

            # Create effect for this page
            effect = Effect.for_page_render(
                source_path=page.source_path,
                output_path=page.output_path,
                template_name=page.template_name,
                template_includes=template_includes,
                page_href=page.href,
            )
            effects.append(effect)

        self._tracer.record_batch(effects)
        return self._tracer

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
