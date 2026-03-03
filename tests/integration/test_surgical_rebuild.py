"""Integration tests for surgical warm rebuild (Tier 2 FRONTMATTER, Tier 3a CASCADE).

Tests the SurgicalRebuildHandler with real Site builds: frontmatter patch,
cascade subtree rebuild, and regression cases (rapid edits, page-not-found).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.server.change_classifier import RebuildScope, RebuildTier
from bengal.server.surgical_handler import SurgicalRebuildHandler, _build_page_index


@pytest.fixture
def temp_site() -> Path:
    """Create a temporary site directory with minimal config."""
    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "bengal.toml").write_text(
        '[site]\ntitle = "Surgical Rebuild Test"\nbaseurl = "/"\n\n'
        '[build]\ncontent_dir = "content"\noutput_dir = "public"\ntheme = "default"\n\n'
        "[markdown]\n"
    )
    yield temp_dir
    shutil.rmtree(temp_dir)


def _find_page(site: Site, name_fragment: str):
    """Find a page by substring match on source_path."""
    matches = [p for p in site.pages if name_fragment in str(p.source_path)]
    assert matches, (
        f"No page found matching '{name_fragment}' in {[str(p.source_path) for p in site.pages]}"
    )
    return matches[0]


# ---------------------------------------------------------------------------
# Tier 2: FRONTMATTER - handle_frontmatter_change
# ---------------------------------------------------------------------------


class TestSurgicalFrontmatterChange:
    """Tier 2: frontmatter-only edits patch page and re-render."""

    def test_title_change_patches_and_rerenders(self, temp_site: Path) -> None:
        """Changing title patches page and writes updated HTML."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "page.md").write_text("---\ntitle: Original\n---\nBody.\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        # Simulate frontmatter edit
        (content / "page.md").write_text("---\ntitle: Updated Title\n---\nBody.\n")

        output_dir = temp_site / "public"
        handler = SurgicalRebuildHandler(site, output_dir)
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=content / "page.md",
            cascade_dirty=False,
            nav_dirty=True,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter={"title": "Updated Title"},
        )

        outputs = handler.handle_frontmatter_change(content / "page.md", scope, page_index)
        assert len(outputs) >= 1

        page = _find_page(site, "page")
        assert page.metadata.get("title") == "Updated Title"

    def test_weight_change_patches_page(self, temp_site: Path) -> None:
        """Changing weight patches page metadata."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "page.md").write_text("---\ntitle: Page\nweight: 1\n---\nBody.\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        (content / "page.md").write_text("---\ntitle: Page\nweight: 5\n---\nBody.\n")

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=content / "page.md",
            cascade_dirty=False,
            nav_dirty=True,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter={"title": "Page", "weight": 5},
        )

        handler.handle_frontmatter_change(content / "page.md", scope, page_index)
        page = _find_page(site, "page")
        assert page.metadata.get("weight") == 5

    def test_description_change_patches_page(self, temp_site: Path) -> None:
        """Changing description (SAFE_KEYS) patches without nav_dirty."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "page.md").write_text("---\ntitle: Page\ndescription: Old\n---\nBody.\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        (content / "page.md").write_text("---\ntitle: Page\ndescription: New desc\n---\nBody.\n")

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=content / "page.md",
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter={"title": "Page", "description": "New desc"},
        )

        handler.handle_frontmatter_change(content / "page.md", scope, page_index)
        page = _find_page(site, "page")
        assert page.metadata.get("description") == "New desc"

    def test_frontmatter_override_persists_after_patch(self, temp_site: Path) -> None:
        """Page-level type override survives surgical patch."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (content / "special.md").write_text("---\ntitle: Special\ntype: custom\n---\nContent.\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        (content / "special.md").write_text(
            "---\ntitle: Special Updated\ntype: custom\n---\nContent.\n"
        )

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=content / "special.md",
            cascade_dirty=False,
            nav_dirty=True,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter={"title": "Special Updated", "type": "custom"},
        )

        handler.handle_frontmatter_change(content / "special.md", scope, page_index)
        page = _find_page(site, "special")
        assert page.metadata.get("type") == "custom"
        assert page.metadata.get("title") == "Special Updated"


# ---------------------------------------------------------------------------
# Tier 3a: CASCADE - handle_cascade_change
# ---------------------------------------------------------------------------


class TestSurgicalCascadeChange:
    """Tier 3a: _index.md cascade block change rebuilds subtree."""

    def test_cascade_change_propagates_to_children(self, temp_site: Path) -> None:
        """Changing cascade in _index.md propagates to child pages."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (content / "guide.md").write_text("---\ntitle: Guide\n---\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))
        assert _find_page(site, "guide").metadata.get("type") == "doc"

        # Change cascade
        (content / "_index.md").write_text(
            "---\ntitle: Docs\ncascade:\n  type: doc\n  version: '2.0'\n---\n"
        )

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        outputs = handler.handle_cascade_change(content / "_index.md", page_index)
        assert len(outputs) >= 1

        page = _find_page(site, "guide")
        assert page.metadata.get("type") == "doc"
        assert page.metadata.get("version") == "2.0"


# ---------------------------------------------------------------------------
# Regressions
# ---------------------------------------------------------------------------


class TestSurgicalRegressions:
    """Regression tests for surgical rebuild edge cases."""

    def test_page_not_found_returns_empty(self, temp_site: Path) -> None:
        """Unknown path returns empty list (no crash)."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=temp_site / "content" / "nonexistent.md",
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter={},
        )

        outputs = handler.handle_frontmatter_change(
            temp_site / "content" / "nonexistent.md", scope, page_index
        )
        assert outputs == []

    def test_tags_changed_returns_empty_fallback(self, temp_site: Path) -> None:
        """Tags change returns empty (caller should do full rebuild)."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "page.md").write_text("---\ntitle: Page\ntags: [a]\n---\nBody.\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=content / "page.md",
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=True,
            old_frontmatter=None,
            new_frontmatter={"title": "Page", "tags": ["a", "b"]},
        )

        outputs = handler.handle_frontmatter_change(content / "page.md", scope, page_index)
        assert outputs == []
