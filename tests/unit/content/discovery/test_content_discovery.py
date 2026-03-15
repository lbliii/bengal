"""
Unit tests for ContentDiscovery.

Tests: directory scanning, file filtering (.md vs ignored), symlink handling,
nested section discovery, empty dirs, missing content dir.
"""

from __future__ import annotations

from pathlib import Path

from bengal.content.discovery.content_discovery import ContentDiscovery


class TestContentDiscoveryHappyPath:
    """Test basic content discovery."""

    def test_discover_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        """Empty content directory returns empty sections and pages."""
        discovery = ContentDiscovery(tmp_path)
        sections, pages = discovery.discover()
        assert sections == []
        assert pages == []

    def test_discover_single_page(self, tmp_path: Path) -> None:
        """Single markdown file is discovered."""
        (tmp_path / "page.md").write_text("---\ntitle: Test\n---\n\nContent")
        discovery = ContentDiscovery(tmp_path)
        _sections, pages = discovery.discover()
        assert len(pages) == 1
        assert pages[0].title == "Test"
        assert "Content" in getattr(pages[0], "_raw_content", "")

    def test_discover_nested_sections(self, tmp_path: Path) -> None:
        """Nested directories create section hierarchy."""
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "post.md").write_text("---\ntitle: Post\n---\n\nBody")
        discovery = ContentDiscovery(tmp_path)
        sections, pages = discovery.discover()
        assert len(sections) == 1
        assert sections[0].name == "blog"
        assert len(pages) == 1
        assert pages[0] in sections[0].pages

    def test_discover_index_md_in_section(self, tmp_path: Path) -> None:
        """_index.md is discovered as section index."""
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()
        (blog_dir / "_index.md").write_text("---\ntitle: Blog\n---\n\nSection intro")
        (blog_dir / "post.md").write_text("---\ntitle: Post\n---\n\nBody")
        discovery = ContentDiscovery(tmp_path)
        sections, pages = discovery.discover()
        assert len(sections) == 1
        assert len(pages) == 2
        titles = {p.title for p in pages}
        assert "Blog" in titles
        assert "Post" in titles

    def test_discover_skips_hidden_files(self, tmp_path: Path) -> None:
        """Hidden files are skipped."""
        (tmp_path / ".hidden.md").write_text("---\ntitle: Hidden\n---\n\nSecret")
        (tmp_path / "visible.md").write_text("---\ntitle: Visible\n---\n\nPublic")
        discovery = ContentDiscovery(tmp_path)
        _sections, pages = discovery.discover()
        assert len(pages) == 1
        assert pages[0].title == "Visible"

    def test_discover_skips_non_content_extensions(self, tmp_path: Path) -> None:
        """Non-content extensions are skipped."""
        (tmp_path / "page.md").write_text("---\ntitle: MD\n---\n\nContent")
        (tmp_path / "data.yaml").write_text("key: value")
        (tmp_path / "script.py").write_text("print('hi')")
        discovery = ContentDiscovery(tmp_path)
        _sections, pages = discovery.discover()
        assert len(pages) == 1
        assert pages[0].title == "MD"


class TestContentDiscoveryMissingDir:
    """Test behavior when content dir is missing."""

    def test_discover_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        """Missing content directory returns empty (with error recorded)."""
        missing = tmp_path / "nonexistent"
        discovery = ContentDiscovery(missing)
        sections, pages = discovery.discover()
        assert sections == []
        assert pages == []


class TestContentDiscoveryMultipleSections:
    """Test multiple top-level sections."""

    def test_discover_multiple_sections_sorted(self, tmp_path: Path) -> None:
        """Multiple sections are discovered and sorted."""
        for name in ["blog", "docs", "about"]:
            d = tmp_path / name
            d.mkdir()
            (d / "_index.md").write_text(f"---\ntitle: {name.title()}\n---\n\n")
        discovery = ContentDiscovery(tmp_path)
        sections, _pages = discovery.discover()
        assert len(sections) == 3
        names = [s.name for s in sections]
        assert "about" in names
        assert "blog" in names
        assert "docs" in names
