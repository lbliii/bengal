"""
Cascade snapshot mixin for Site.

Provides properties and methods for cascade metadata management.

Architecture:
    During builds, the cascade snapshot lives on BuildState (which is fresh
    each build). The cascade property delegates to BuildState when available,
    eliminating the class of bugs where stale cascade data survived warm
    rebuilds.

    Outside builds (tests, CLI health checks), the cascade snapshot is stored
    locally on _cascade_snapshot as a fallback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.section import Section
    from bengal.orchestration.build_state import BuildState


class SiteCascadeMixin:
    """
    Mixin providing cascade snapshot management for Site.

    Manages immutable cascade data computed once per build for thread-safe access.
    Cascade metadata flows from section _index.md files to descendant pages.
    """

    # These attributes are defined on the Site dataclass
    sections: list[Section]
    pages: list[Any]
    root_path: Any
    _cascade_snapshot: Any
    _current_build_state: BuildState | None

    @property
    def cascade(self) -> Any:
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
        # During builds: delegate to BuildState (structurally fresh each build)
        if self._current_build_state is not None:
            snapshot = self._current_build_state.cascade_snapshot
            if snapshot is not None:
                return snapshot

        # Outside builds (tests, CLI): use local fallback
        if self._cascade_snapshot is not None:
            return self._cascade_snapshot

        # Return empty snapshot for graceful fallback
        from bengal.core.cascade_snapshot import CascadeSnapshot

        return CascadeSnapshot.empty()

    def build_cascade_snapshot(self) -> None:
        """
        Build the immutable cascade snapshot from all sections.

        This scans all sections and extracts cascade metadata from their
        index pages (_index.md). The resulting snapshot is frozen and can
        be safely shared across threads.

        Also extracts root-level cascade from pages not in any section
        (like content/index.md) and applies it site-wide.

        Storage:
            - During builds: stored on BuildState (primary, structurally fresh)
            - Always: stored on _cascade_snapshot (fallback for tests/CLI)

        Called automatically by _apply_cascades() during discovery.
        Can also be called manually to refresh the snapshot after
        incremental changes to _index.md files.

        Example:
            >>> site.build_cascade_snapshot()
            >>> print(f"Cascade data for {len(site.cascade)} sections")
        """
        from bengal.core.cascade_snapshot import CascadeSnapshot

        # Gather all sections including subsections
        all_sections = self._collect_all_sections()

        # Compute content directory
        content_dir = self.root_path / "content"

        # Collect root-level cascade from pages not in any section
        # This handles content/index.md with cascade that applies site-wide
        pages_in_sections: set[Any] = set()
        for section in all_sections:
            pages_in_sections.update(section.get_all_pages(recursive=True))

        root_cascade: dict[str, Any] = {}
        for page in self.pages:
            if page not in pages_in_sections and "cascade" in page.metadata:
                root_cascade.update(page.metadata["cascade"])

        # Build immutable snapshot
        snapshot = CascadeSnapshot.build(
            content_dir, all_sections, root_cascade=root_cascade
        )

        # Store on BuildState if available (primary path during builds)
        if self._current_build_state is not None:
            self._current_build_state.cascade_snapshot = snapshot

        # Always store locally for non-build access (tests, CLI)
        self._cascade_snapshot = snapshot

    def _collect_all_sections(self) -> list[Section]:
        """
        Collect all sections including nested subsections.

        Returns:
            Flat list of all Section objects in the site.
        """
        all_sections: list[Section] = []

        def collect_recursive(sections: list[Section]) -> None:
            for section in sections:
                all_sections.append(section)
                if section.subsections:
                    collect_recursive(section.subsections)

        collect_recursive(self.sections)
        return all_sections
