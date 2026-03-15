"""Tests for BuildContext.get_section_snapshot handoff checkpoint.

Ensures section→SectionSnapshot lookup returns NO_SECTION when section is
missing from snapshot (orphan, wrong path) or when snapshot is None.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.orchestration.build_context import BuildContext
from bengal.snapshots.types import NO_SECTION, SectionSnapshot


def _make_section_snapshot(name: str, path: Path | None) -> SectionSnapshot:
    """Create a minimal SectionSnapshot for tests."""
    return SectionSnapshot(
        name=name,
        title=name.title(),
        nav_title=name.title(),
        href=f"/{name}/",
        path=path,
        pages=(),
        sorted_pages=(),
        regular_pages=(),
        subsections=(),
        sorted_subsections=(),
    )


class TestGetSectionSnapshot:
    """get_section_snapshot returns correct result for handoff edge cases."""

    def test_none_returns_no_section(self) -> None:
        """None section returns NO_SECTION sentinel."""
        ctx = BuildContext(site=MagicMock(), snapshot=None)
        assert ctx.get_section_snapshot(None) is NO_SECTION

    def test_section_snapshot_passthrough(self) -> None:
        """SectionSnapshot input returned as-is."""
        snap = _make_section_snapshot("docs", Path("/site/content/docs"))
        ctx = BuildContext(site=MagicMock(), snapshot=MagicMock())

        result = ctx.get_section_snapshot(snap)
        assert result is snap

    def test_no_snapshot_returns_no_section(self) -> None:
        """When ctx.snapshot is None, returns NO_SECTION for mutable Section."""
        section = MagicMock()
        section.path = Path("/site/content/docs")
        section.name = "docs"

        ctx = BuildContext(site=MagicMock(), snapshot=None)

        assert ctx.get_section_snapshot(section) is NO_SECTION

    def test_section_not_in_snapshot_returns_no_section(self) -> None:
        """Section with path/name not in snapshot returns NO_SECTION."""
        docs_snap = _make_section_snapshot("docs", Path("/site/content/docs"))
        site_snapshot = MagicMock()
        site_snapshot.sections = [docs_snap]

        ctx = BuildContext(site=MagicMock(), snapshot=site_snapshot)

        # Section with path not in snapshot (orphan)
        orphan = MagicMock()
        orphan.path = Path("/site/content/orphan")
        orphan.name = "orphan"

        assert ctx.get_section_snapshot(orphan) is NO_SECTION

    def test_section_in_snapshot_by_path_returns_snapshot(self) -> None:
        """Section matching snapshot by path returns SectionSnapshot."""
        docs_path = Path("/site/content/docs")
        docs_snap = _make_section_snapshot("docs", docs_path)
        site_snapshot = MagicMock()
        site_snapshot.sections = [docs_snap]

        ctx = BuildContext(site=MagicMock(), snapshot=site_snapshot)

        section = MagicMock()
        section.path = docs_path
        section.name = "docs"

        result = ctx.get_section_snapshot(section)
        assert result is docs_snap

    def test_section_in_snapshot_by_name_returns_snapshot(self) -> None:
        """Section matching snapshot by name (when path lookup fails) returns SectionSnapshot."""
        docs_snap = _make_section_snapshot("docs", Path("/site/content/docs"))
        site_snapshot = MagicMock()
        site_snapshot.sections = [docs_snap]

        ctx = BuildContext(site=MagicMock(), snapshot=site_snapshot)

        # Section with different path but same name (e.g. path not yet resolved)
        section = MagicMock()
        section.path = None
        section.name = "docs"

        result = ctx.get_section_snapshot(section)
        assert result is docs_snap
