"""
Cascade snapshot mixin for Site.

Provides the immutable cascade snapshot that maps section paths to
inherited frontmatter metadata. Thread-safe for parallel rendering.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.cascade_snapshot import CascadeSnapshot
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.orchestration.build_state import BuildState


class SiteCascadeMixin:
    """
    Mixin providing cascade snapshot access for Site.

    Expects from host class:
        root_path: Path
        sections: list[Section]
        pages: list[Page]
        _current_build_state: BuildState | None
        _cascade_snapshot: CascadeSnapshot | None
    """

    root_path: Path
    sections: list[Section]
    pages: list[Page]
    _current_build_state: BuildState | None
    _cascade_snapshot: CascadeSnapshot | None

    @property
    def cascade(self) -> CascadeSnapshot:
        """
        Get the immutable cascade snapshot for this build.

        Resolution order:
            1. BuildState.cascade_snapshot (during builds — structurally fresh)
            2. Local _cascade_snapshot (outside builds — tests, CLI)
            3. Empty snapshot (graceful fallback)

        The cascade snapshot provides thread-safe access to cascade metadata
        without locks. It is computed once at build start and can be safely
        accessed from multiple render threads in free-threaded Python.

        Returns:
            CascadeSnapshot instance (empty if not yet built)

        Example:
            >>> page_type = site.cascade.resolve("docs/guide", "type")
            >>> all_cascade = site.cascade.resolve_all("docs/guide")
        """
        if self._current_build_state is not None:
            snapshot = self._current_build_state.cascade_snapshot
            if snapshot is not None:
                return snapshot

        if self._cascade_snapshot is not None:
            return self._cascade_snapshot

        from bengal.core.cascade_snapshot import CascadeSnapshot

        return CascadeSnapshot.empty()

    def build_cascade_snapshot(self) -> None:
        """
        Build the immutable cascade snapshot from all sections.

        Delegates to bengal.core.cascade_snapshot.build_cascade_from_content()
        and stores the result on BuildState (primary) and _cascade_snapshot (fallback).

        Uses dataclasses.replace() to ensure a new instance identity each build,
        so CascadeView caches (keyed by id(snapshot)) invalidate across rebuilds.
        """
        from bengal.core.cascade_snapshot import build_cascade_from_content

        snapshot = build_cascade_from_content(self.root_path, self.sections, self.pages)
        snapshot = dataclasses.replace(snapshot)  # New id for cache invalidation

        if self._current_build_state is not None:
            self._current_build_state.cascade_snapshot = snapshot

        self._cascade_snapshot = snapshot
