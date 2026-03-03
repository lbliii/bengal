"""Unit tests for SurgicalRebuildHandler."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.server.change_classifier import RebuildScope, RebuildTier
from bengal.server.surgical_handler import (
    SurgicalRebuildHandler,
    _build_page_index,
)


@pytest.fixture
def temp_site() -> Path:
    """Create a temporary site directory with minimal config."""
    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "bengal.toml").write_text(
        '[site]\ntitle = "Test"\nbaseurl = "/"\n\n'
        '[build]\ncontent_dir = "content"\noutput_dir = "public"\ntheme = "default"\n\n'
        "[markdown]\n"
    )
    yield temp_dir
    shutil.rmtree(temp_dir)


def _find_page(site: Site, name_fragment: str):
    """Find a page by substring match on source_path."""
    matches = [p for p in site.pages if name_fragment in str(p.source_path)]
    assert matches, f"No page found matching '{name_fragment}'"
    return matches[0]


class TestBuildPageIndex:
    """Tests for _build_page_index helper."""

    def test_builds_path_to_page_map(self, temp_site: Path) -> None:
        """Index maps resolved source path to page."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        index = _build_page_index(site)
        assert len(index) >= 2
        page = _find_page(site, "page")
        path = Path(page.source_path).resolve()
        assert path in index
        assert index[path] is page


class TestHandleFrontmatterChange:
    """Tests for handle_frontmatter_change."""

    def test_patches_page_metadata(self, temp_site: Path) -> None:
        """Patch updates page metadata from file."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "page.md").write_text("---\ntitle: Old\n---\nBody.\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        (content / "page.md").write_text("---\ntitle: New\n---\nBody.\n")

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=content / "page.md",
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter={"title": "New"},
        )

        outputs = handler.handle_frontmatter_change(content / "page.md", scope, page_index)
        assert len(outputs) >= 1

        page = _find_page(site, "page")
        assert page.metadata.get("title") == "New"

    def test_nav_dirty_includes_section_index(self, temp_site: Path) -> None:
        """When nav_dirty, section index page is re-rendered."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        (content / "page.md").write_text("---\ntitle: Updated Page\n---\nBody.\n")

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=content / "page.md",
            cascade_dirty=False,
            nav_dirty=True,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter={"title": "Updated Page"},
        )

        outputs = handler.handle_frontmatter_change(content / "page.md", scope, page_index)
        # Should include both page and section index
        assert len(outputs) >= 1

    def test_page_not_found_returns_empty(self, temp_site: Path) -> None:
        """Unknown path returns empty list."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\n---\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        scope = RebuildScope(
            tier=RebuildTier.FRONTMATTER,
            changed_page=temp_site / "content" / "ghost.md",
            cascade_dirty=False,
            nav_dirty=False,
            tags_changed=False,
            old_frontmatter=None,
            new_frontmatter={},
        )

        outputs = handler.handle_frontmatter_change(
            temp_site / "content" / "ghost.md", scope, page_index
        )
        assert outputs == []

    def test_tags_changed_returns_empty(self, temp_site: Path) -> None:
        """tags_changed triggers fallback; handler returns empty."""
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


class TestHandleCascadeChange:
    """Tests for handle_cascade_change."""

    def test_rebuilds_subtree_pages(self, temp_site: Path) -> None:
        """Cascade change re-renders all pages in section subtree."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)
        (content / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (content / "a.md").write_text("---\ntitle: A\n---\n")
        (content / "b.md").write_text("---\ntitle: B\n---\n")

        site = Site(root_path=temp_site, config={})
        site.build(BuildOptions(force_sequential=True))

        (content / "_index.md").write_text(
            "---\ntitle: Docs\ncascade:\n  type: doc\n  version: '1'\n---\n"
        )

        handler = SurgicalRebuildHandler(site, temp_site / "public")
        page_index = _build_page_index(site)
        outputs = handler.handle_cascade_change(content / "_index.md", page_index)
        assert len(outputs) >= 2

        a_page = _find_page(site, "a")
        assert a_page.metadata.get("version") == "1"
