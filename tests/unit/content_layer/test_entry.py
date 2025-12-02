"""Tests for ContentEntry dataclass."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bengal.content_layer.entry import ContentEntry


class TestContentEntry:
    """Tests for ContentEntry."""

    def test_basic_creation(self) -> None:
        """Test basic ContentEntry creation."""
        entry = ContentEntry(
            id="test.md",
            slug="test",
            content="# Hello World",
            frontmatter={"title": "Test Page"},
            source_type="local",
            source_name="docs",
        )

        assert entry.id == "test.md"
        assert entry.slug == "test"
        assert entry.content == "# Hello World"
        assert entry.frontmatter == {"title": "Test Page"}
        assert entry.source_type == "local"
        assert entry.source_name == "docs"

    def test_title_from_frontmatter(self) -> None:
        """Test title property extracts from frontmatter."""
        entry = ContentEntry(
            id="test.md",
            slug="test-page",
            content="content",
            frontmatter={"title": "My Custom Title"},
        )

        assert entry.title == "My Custom Title"

    def test_title_fallback_to_slug(self) -> None:
        """Test title falls back to formatted slug."""
        entry = ContentEntry(
            id="test.md",
            slug="my-test-page",
            content="content",
            frontmatter={},
        )

        assert entry.title == "My Test Page"

    def test_is_remote_local(self) -> None:
        """Test is_remote returns False for local sources."""
        entry = ContentEntry(
            id="test.md",
            slug="test",
            content="content",
            source_type="local",
        )

        assert not entry.is_remote

    def test_is_remote_github(self) -> None:
        """Test is_remote returns True for remote sources."""
        entry = ContentEntry(
            id="test.md",
            slug="test",
            content="content",
            source_type="github",
        )

        assert entry.is_remote

    def test_is_cached(self) -> None:
        """Test is_cached property."""
        # Not cached
        entry1 = ContentEntry(id="1.md", slug="1", content="")
        assert not entry1.is_cached

        # Cached
        entry2 = ContentEntry(
            id="2.md",
            slug="2",
            content="",
            cached_path=Path("/tmp/cache/2.md"),
            cached_at=datetime.now(),
        )
        assert entry2.is_cached

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization round-trip."""
        now = datetime.now()

        original = ContentEntry(
            id="test.md",
            slug="test",
            content="# Test",
            frontmatter={"title": "Test", "tags": ["a", "b"]},
            source_type="github",
            source_name="docs",
            source_url="https://github.com/org/repo",
            last_modified=now,
            checksum="abc123",
            etag="etag-value",
        )

        data = original.to_dict()
        restored = ContentEntry.from_dict(data)

        assert restored.id == original.id
        assert restored.slug == original.slug
        assert restored.content == original.content
        assert restored.frontmatter == original.frontmatter
        assert restored.source_type == original.source_type
        assert restored.source_name == original.source_name
        assert restored.source_url == original.source_url
        assert restored.checksum == original.checksum
        assert restored.etag == original.etag

    def test_to_page_kwargs(self) -> None:
        """Test conversion to Page kwargs."""
        entry = ContentEntry(
            id="test.md",
            slug="test-page",
            content="# Content",
            frontmatter={"title": "Test"},
            source_type="github",
            source_url="https://github.com/org/repo",
        )

        kwargs = entry.to_page_kwargs()

        assert kwargs["content"] == "# Content"
        assert kwargs["frontmatter"] == {"title": "Test"}
        assert kwargs["source_type"] == "github"
        assert kwargs["source_url"] == "https://github.com/org/repo"
        assert kwargs["slug"] == "test-page"

