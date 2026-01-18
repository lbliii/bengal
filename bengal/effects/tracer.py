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

from __future__ import annotations

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

    def record(self, effect: Effect) -> None:
        """
        Record an effect during rendering.
        
        Thread-safe: Uses lock for index updates.
        
        Args:
            effect: Effect to record
        """
        with self._lock:
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

    def record_batch(self, effects: list[Effect]) -> None:
        """
        Record multiple effects at once.
        
        More efficient than recording one at a time.
        
        Args:
            effects: List of effects to record
        """
        with self._lock:
            for effect in effects:
                self._effects.append(effect)
                
                for dep in effect.depends_on:
                    self._dep_index[dep].append(effect)
                
                for output in effect.outputs:
                    self._output_index[output] = effect
                
                for key in effect.invalidates:
                    self._invalidation_index[key].append(effect)

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
                for effect in self._dep_index.get(path, []):
                    invalidated.update(effect.invalidates)
                
                # Also check string form for templates
                for effect in self._dep_index.get(path.name, []):
                    invalidated.update(effect.invalidates)
            
            # Transitive invalidations (if an output changes, its dependents are invalidated)
            outputs_changed = self._outputs_for_deps(changed)
            for output in outputs_changed:
                for effect in self._dep_index.get(output, []):
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
                
                # Find effects that depend on this path
                for effect in self._dep_index.get(path, []):
                    outputs.update(effect.outputs)
                    # Add outputs to queue for transitive deps
                    queue.extend(effect.outputs)
                
                # Also check string form for templates
                for effect in self._dep_index.get(path.name, []):
                    outputs.update(effect.outputs)
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
                deps = [
                    str(d) if isinstance(d, Path) else d
                    for d in effect.depends_on
                ]
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
