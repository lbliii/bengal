"""
SiteContext Protocol — read-only Site surface consumed by Page and Section.

Page and Section type their `_site` field as `SiteContext` (not Site) so
they cannot reach into orchestration/server/rendering internals by accident.
The concrete `Site` class implements this Protocol structurally — no
explicit base class is needed.

Evolution rule: new Site attributes do NOT implicitly join this protocol.
They must be added here explicitly. This keeps the Page/Section coupling
surface visible and auditable.

See `plan/rfc-site-context-protocol.md` for the audit and migration plan.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.cascade_snapshot import CascadeSnapshot
    from bengal.core.version import VersionConfig
    from bengal.protocols.core import PageLike, SectionLike


@runtime_checkable
class RegistryContext(Protocol):
    """Minimal registry surface that Page consumes."""

    @property
    def epoch(self) -> int:
        """Monotonic counter incremented when registry contents change."""
        ...

    def page_index(self, pages: list[PageLike]) -> dict[PageLike, int]:
        """Memoized page→index map for next/prev navigation lookups."""
        ...


@runtime_checkable
class SiteContext(Protocol):
    """
    Read-only Site surface consumed by Page and Section types.

    Site implements this structurally; Page and Section type-hint
    SiteContext to avoid coupling to the full Site class.

    """

    # --- Read-only configuration ---------------------------------------
    @property
    def root_path(self) -> Path:
        """Absolute project root."""
        ...

    @property
    def output_dir(self) -> Path:
        """Where rendered HTML is written."""
        ...

    @property
    def config(self) -> dict:
        """Resolved site configuration dict."""
        ...

    @property
    def cascade(self) -> CascadeSnapshot | None:
        """Cascade snapshot for frontmatter inheritance (None pre-build)."""
        ...

    @property
    def versioning_enabled(self) -> bool:
        """True when versioning is configured."""
        ...

    @property
    def version_config(self) -> VersionConfig | None:
        """Versioning configuration, or None when disabled."""
        ...

    # --- Page collection & queries -------------------------------------
    # Returns are PageLike/SectionLike (not concrete Page/Section) to match
    # Site's existing signatures and avoid binding the Protocol to concrete
    # classes — keeps coupling minimal.
    @property
    def pages(self) -> list[PageLike]:
        """All pages in the site."""
        ...

    @property
    def indexes(self) -> object:
        """Computed indexes (series, tags, etc.). Typed `object` until IndexRegistry lands."""
        ...

    def get_section_by_path(self, path: Path | str) -> SectionLike | None:
        """Look up a section by its source path."""
        ...

    def get_section_by_url(self, url: str) -> SectionLike | None:
        """Look up a section by its URL."""
        ...

    def get_page_path_map(self) -> dict[str, PageLike]:
        """String-keyed page lookup map for O(1) resolution."""
        ...

    # --- Registry epoch (for memo invalidation) ------------------------
    @property
    def registry(self) -> RegistryContext:
        """Registry exposing the epoch counter for cache invalidation."""
        ...

    # --- Build-time concern (TODO: relocate to BuildContext post-B2) ---
    # diagnostics is reached via `getattr(site, "diagnostics", None)` from
    # Section._emit_diagnostic. Kept on SiteContext for now to avoid
    # threading BuildContext through Section construction in B2 scope.
    # Marked for removal when BuildContext lands.
    @property
    def diagnostics(self) -> object | None:
        """Diagnostic sink for structured warnings during build."""
        ...
