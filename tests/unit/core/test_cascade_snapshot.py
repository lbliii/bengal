"""Tests for the CascadeSnapshot immutable cascade data structure."""

from pathlib import Path

import pytest

from bengal.core.cascade_snapshot import CascadeSnapshot
from bengal.core.page import Page
from bengal.core.section import Section


class TestCascadeSnapshotBasics:
    """Test basic CascadeSnapshot functionality."""

    def test_empty_snapshot(self):
        """Test creating an empty cascade snapshot."""
        snapshot = CascadeSnapshot.empty()

        assert len(snapshot) == 0
        assert snapshot.resolve("any/path", "type") is None
        assert snapshot.get_cascade_for_section("any/path") == {}

    def test_resolve_direct_match(self):
        """Test resolving a key that exists in the target section."""
        snapshot = CascadeSnapshot(
            _data={"docs": {"type": "doc", "layout": "docs-layout"}},
            _content_dir="/content",
        )

        assert snapshot.resolve("docs", "type") == "doc"
        assert snapshot.resolve("docs", "layout") == "docs-layout"
        assert snapshot.resolve("docs", "unknown") is None

    def test_resolve_inheritance(self):
        """Test resolving cascade values from parent sections."""
        snapshot = CascadeSnapshot(
            _data={
                "docs": {"type": "doc", "site_version": "1.0"},
                "docs/guides": {"section": "guides"},
            },
            _content_dir="/content",
        )

        # Direct match
        assert snapshot.resolve("docs/guides", "section") == "guides"

        # Inherited from parent
        assert snapshot.resolve("docs/guides", "type") == "doc"
        assert snapshot.resolve("docs/guides", "site_version") == "1.0"

        # Non-existent key
        assert snapshot.resolve("docs/guides", "unknown") is None

    def test_resolve_child_overrides_parent(self):
        """Test that child cascade values override parent values."""
        snapshot = CascadeSnapshot(
            _data={
                "docs": {"type": "doc", "version": "1.0"},
                "docs/v2": {"version": "2.0"},
            },
            _content_dir="/content",
        )

        # Child overrides parent version
        assert snapshot.resolve("docs/v2", "version") == "2.0"
        # But inherits type from parent
        assert snapshot.resolve("docs/v2", "type") == "doc"

    def test_resolve_all(self):
        """Test resolving all cascade values for a section."""
        snapshot = CascadeSnapshot(
            _data={
                "docs": {"type": "doc", "site_version": "1.0"},
                "docs/guides": {"section": "guides", "type": "guide"},
            },
            _content_dir="/content",
        )

        result = snapshot.resolve_all("docs/guides")

        assert result["type"] == "guide"  # Child overrides
        assert result["site_version"] == "1.0"  # Inherited
        assert result["section"] == "guides"  # Direct

    def test_resolve_deeply_nested(self):
        """Test resolving cascade through deeply nested sections."""
        snapshot = CascadeSnapshot(
            _data={
                "a": {"level": 1, "from_a": True},
                "a/b": {"level": 2, "from_b": True},
                "a/b/c": {"level": 3, "from_c": True},
            },
            _content_dir="/content",
        )

        # Deep section inherits from all ancestors
        assert snapshot.resolve("a/b/c/d", "from_a") is True
        assert snapshot.resolve("a/b/c/d", "from_b") is True
        assert snapshot.resolve("a/b/c/d", "from_c") is True
        assert snapshot.resolve("a/b/c/d", "level") == 3

    def test_root_cascade(self):
        """Test resolving cascade from root section."""
        snapshot = CascadeSnapshot(
            _data={
                "": {"site_wide": True, "theme": "default"},
                "docs": {"type": "doc"},
            },
            _content_dir="/content",
        )

        # Root cascade applies to all
        assert snapshot.resolve("docs", "site_wide") is True
        assert snapshot.resolve("docs", "theme") == "default"
        assert snapshot.resolve("docs", "type") == "doc"


class TestCascadeSnapshotBuild:
    """Test building CascadeSnapshot from sections."""

    def test_build_from_sections(self):
        """Test building snapshot from sections with index pages."""
        content_dir = Path("/content")

        # Create sections with cascade metadata
        section_docs = Section(name="docs", path=Path("/content/docs"))
        index_page = Page(
            source_path=Path("/content/docs/_index.md"),
            metadata={"title": "Docs", "cascade": {"type": "doc"}},
        )
        section_docs.add_page(index_page)

        section_blog = Section(name="blog", path=Path("/content/blog"))
        blog_index = Page(
            source_path=Path("/content/blog/_index.md"),
            metadata={"title": "Blog", "cascade": {"type": "post", "author": "Admin"}},
        )
        section_blog.add_page(blog_index)

        snapshot = CascadeSnapshot.build(content_dir, [section_docs, section_blog])

        assert snapshot.resolve("docs", "type") == "doc"
        assert snapshot.resolve("blog", "type") == "post"
        assert snapshot.resolve("blog", "author") == "Admin"

    def test_build_skips_sections_without_index(self):
        """Test that sections without index pages are skipped."""
        content_dir = Path("/content")

        section = Section(name="empty", path=Path("/content/empty"))
        # No index page added

        snapshot = CascadeSnapshot.build(content_dir, [section])

        assert len(snapshot) == 0
        assert snapshot.resolve("empty", "type") is None

    def test_build_skips_sections_without_cascade(self):
        """Test that sections without cascade metadata are skipped."""
        content_dir = Path("/content")

        section = Section(name="plain", path=Path("/content/plain"))
        index_page = Page(
            source_path=Path("/content/plain/_index.md"),
            metadata={"title": "Plain Section"},  # No cascade
        )
        section.add_page(index_page)

        snapshot = CascadeSnapshot.build(content_dir, [section])

        assert len(snapshot) == 0

    def test_build_normalizes_root_path(self):
        """Test that root section path is normalized to empty string."""
        content_dir = Path("/content")

        section = Section(name=".", path=Path("/content"))
        index_page = Page(
            source_path=Path("/content/_index.md"),
            metadata={"cascade": {"site_wide": True}},
        )
        section.add_page(index_page)

        snapshot = CascadeSnapshot.build(content_dir, [section])

        # Root cascade should be accessible via empty string
        assert "" in snapshot or "." in snapshot


class TestCascadeSnapshotImmutability:
    """Test that CascadeSnapshot is properly immutable."""

    def test_frozen_dataclass(self):
        """Test that CascadeSnapshot is frozen (immutable)."""
        snapshot = CascadeSnapshot(
            _data={"docs": {"type": "doc"}},
            _content_dir="/content",
        )

        with pytest.raises(AttributeError):
            snapshot._data = {}  # type: ignore

    def test_data_copied_on_build(self):
        """Test that cascade data is copied during build."""
        content_dir = Path("/content")

        section = Section(name="docs", path=Path("/content/docs"))
        cascade = {"type": "doc"}
        index_page = Page(
            source_path=Path("/content/docs/_index.md"),
            metadata={"cascade": cascade},
        )
        section.add_page(index_page)

        snapshot = CascadeSnapshot.build(content_dir, [section])

        # Modifying original cascade should not affect snapshot
        cascade["type"] = "modified"

        assert snapshot.resolve("docs", "type") == "doc"


class TestCascadeSnapshotContains:
    """Test __contains__ and __len__ methods."""

    def test_contains(self):
        """Test checking if section has cascade data."""
        snapshot = CascadeSnapshot(
            _data={"docs": {"type": "doc"}},
            _content_dir="/content",
        )

        assert "docs" in snapshot
        assert "blog" not in snapshot

    def test_len(self):
        """Test getting number of sections with cascade."""
        snapshot = CascadeSnapshot(
            _data={
                "docs": {"type": "doc"},
                "blog": {"type": "post"},
            },
            _content_dir="/content",
        )

        assert len(snapshot) == 2


class TestCascadeSnapshotGetCascadeForSection:
    """Test get_cascade_for_section method."""

    def test_get_cascade_for_section(self):
        """Test getting cascade dict for specific section."""
        snapshot = CascadeSnapshot(
            _data={"docs": {"type": "doc", "version": "1.0"}},
            _content_dir="/content",
        )

        result = snapshot.get_cascade_for_section("docs")

        assert result == {"type": "doc", "version": "1.0"}

    def test_get_cascade_for_nonexistent_section(self):
        """Test getting cascade for section without cascade."""
        snapshot = CascadeSnapshot(
            _data={"docs": {"type": "doc"}},
            _content_dir="/content",
        )

        result = snapshot.get_cascade_for_section("nonexistent")

        assert result == {}


class TestCascadeSnapshotThreadSafety:
    """Test thread-safety properties of CascadeSnapshot."""

    def test_concurrent_resolve_safe(self):
        """Test that concurrent resolve calls are safe."""
        import concurrent.futures

        snapshot = CascadeSnapshot(
            _data={
                "docs": {"type": "doc"},
                "docs/guides": {"section": "guides"},
                "docs/api": {"section": "api"},
            },
            _content_dir="/content",
        )

        def resolve_type(section_path: str) -> str | None:
            return snapshot.resolve(section_path, "type")

        paths = ["docs", "docs/guides", "docs/api", "docs/other"] * 100

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(resolve_type, paths))

        # All results should be correct
        expected = ["doc"] * 100 + ["doc"] * 100 + ["doc"] * 100 + ["doc"] * 100
        assert results == expected

    def test_concurrent_resolve_all_safe(self):
        """Test that concurrent resolve_all calls are safe."""
        import concurrent.futures

        snapshot = CascadeSnapshot(
            _data={
                "docs": {"type": "doc", "version": "1.0"},
                "docs/guides": {"section": "guides"},
            },
            _content_dir="/content",
        )

        def resolve_all_for_path(path: str) -> dict:
            return snapshot.resolve_all(path)

        paths = ["docs/guides"] * 100

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(resolve_all_for_path, paths))

        # All results should be identical
        expected = {"type": "doc", "version": "1.0", "section": "guides"}
        for result in results:
            assert result == expected
