"""
Snapshot Engine for Bengal SSG.

Provides immutable snapshots of site content for thread-safe parallel rendering.
Snapshots are created once after content discovery and used throughout rendering.

Public API:
create_site_snapshot: Create immutable snapshot from mutable Site
WaveScheduler: Topological wave-based rendering scheduler
ScoutThread: Predictive cache warming thread

Key Concepts:
- Immutable snapshots: Frozen dataclasses with pre-computed properties
- Zero lock contention: All data is read-only after snapshot creation
- Topological waves: Pages grouped by section/template for cache locality
- Scout thread: Predictive cache warming ahead of workers

See Also:
- plan/rfc-bengal-snapshot-engine.md: Full design document

"""

from __future__ import annotations

from bengal.snapshots.builder import (
    ShadowModeValidator,
    SpeculativeRenderer,
    create_site_snapshot,
    pages_affected_by_template_change,
    predict_affected,
    update_snapshot,
)
from bengal.snapshots.scheduler import WaveScheduler
from bengal.snapshots.scout import ScoutThread
from bengal.snapshots.types import (
    NO_SECTION,
    MenuItemSnapshot,
    PageSnapshot,
    ScoutHint,
    SectionSnapshot,
    SiteSnapshot,
    TemplateSnapshot,
)

__all__ = [
    "NO_SECTION",
    "MenuItemSnapshot",
    # Snapshot types
    "PageSnapshot",
    "ScoutHint",
    "ScoutThread",
    "SectionSnapshot",
    "ShadowModeValidator",
    "SiteSnapshot",
    # Speculative rendering
    "SpeculativeRenderer",
    "TemplateSnapshot",
    # Scheduling
    "WaveScheduler",
    # Snapshot creation
    "create_site_snapshot",
    # Incremental build helpers
    "pages_affected_by_template_change",
    "predict_affected",
    "update_snapshot",
]
