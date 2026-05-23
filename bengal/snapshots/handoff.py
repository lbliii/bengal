"""Immutable render handoff facts derived from a site snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from bengal.snapshots.types import SiteSnapshot


@dataclass(frozen=True, slots=True)
class RenderSnapshotHandoff:
    """Small immutable summary of snapshot-to-render worker inputs."""

    page_sources: tuple[Path, ...]
    missing_snapshot_sources: tuple[Path, ...]
    extra_snapshot_sources: tuple[Path, ...]
    page_count: int
    section_count: int
    template_count: int

    @property
    def is_complete(self) -> bool:
        """Return whether live render pages and snapshot pages agree."""
        return not self.missing_snapshot_sources and not self.extra_snapshot_sources


def create_render_snapshot_handoff(
    snapshot: SiteSnapshot,
    live_pages: Iterable[Any],
) -> RenderSnapshotHandoff:
    """Create immutable facts for the hybrid snapshot-to-render handoff."""
    snapshot_sources = tuple(page.source_path for page in snapshot.pages)
    live_sources = tuple(page.source_path for page in live_pages)
    snapshot_source_set = set(snapshot_sources)
    live_source_set = set(live_sources)

    return RenderSnapshotHandoff(
        page_sources=snapshot_sources,
        missing_snapshot_sources=tuple(
            source for source in live_sources if source not in snapshot_source_set
        ),
        extra_snapshot_sources=tuple(
            source for source in snapshot_sources if source not in live_source_set
        ),
        page_count=snapshot.page_count,
        section_count=snapshot.section_count,
        template_count=len(snapshot.schedule.templates),
    )
