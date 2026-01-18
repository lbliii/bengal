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

from bengal.snapshots.builder import create_site_snapshot
from bengal.snapshots.scheduler import WaveScheduler
from bengal.snapshots.scout import ScoutThread
from bengal.snapshots.types import (
    MenuItemSnapshot,
    NO_SECTION,
    PageSnapshot,
    ScoutHint,
    SectionSnapshot,
    SiteSnapshot,
)

__all__ = [
    "create_site_snapshot",
    "WaveScheduler",
    "ScoutThread",
    "PageSnapshot",
    "SectionSnapshot",
    "SiteSnapshot",
    "MenuItemSnapshot",
    "ScoutHint",
    "NO_SECTION",
]
