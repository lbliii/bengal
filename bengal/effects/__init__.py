"""
Effect-Traced Build System for Bengal SSG.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 1)

Replaces 13 detector classes with a unified declarative effect model:
- Effect: Declarative effect of a build operation
- EffectTracer: Unified dependency tracking
- BlockDiffService: Content-aware diffing for template blocks

Key Benefits:
- Single unified model for all dependency tracking
- Transitive dependencies computed automatically
- Debug tooling via `bengal build --show-effects`
- Thread-safe (operates on frozen snapshots)

Usage:
    >>> tracer = EffectTracer()
    >>> effect = Effect(
    ...     outputs=frozenset({Path("public/page.html")}),
    ...     depends_on=frozenset({Path("content/page.md"), "page.html"}),
    ...     invalidates=frozenset({"page:/page/"}),
    ... )
    >>> tracer.record(effect)
    >>> 
    >>> # Query what's invalidated by changes
    >>> invalidated = tracer.invalidated_by({Path("content/page.md")})

"""

from bengal.effects.effect import Effect
from bengal.effects.tracer import EffectTracer, SnapshotEffectBuilder
from bengal.effects.block_diff import BlockDiffService
from bengal.effects.render_integration import (
    BuildEffectTracer,
    RenderEffectRecorder,
    enable_effect_tracing_from_config,
    get_current_effect_context,
    record_cascade_source,
    record_data_file_access,
    record_extra_dependency,
    record_template_include,
)

__all__ = [
    # Core effect types
    "Effect",
    "EffectTracer",
    "SnapshotEffectBuilder",
    "BlockDiffService",
    # Integration helpers
    "BuildEffectTracer",
    "RenderEffectRecorder",
    "enable_effect_tracing_from_config",
    "get_current_effect_context",
    "record_cascade_source",
    "record_data_file_access",
    "record_extra_dependency",
    "record_template_include",
]
