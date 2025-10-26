"""Unit tests for PageCore dataclass."""

from dataclasses import asdict
from datetime import datetime

from bengal.core.page.page_core import PageCore


class TestPageCoreCreation:
    """Test PageCore instantiation and initialization."""

    def test_page_core_minimal_fields(self):
        """Test PageCore with only required fields."""
        core = PageCore(
            source_path="content/test.md",
            title="Test Page",
        )

        assert core.source_path == "content/test.md"
        assert core.title == "Test Page"
        assert core.date is None
        assert core.tags == []
        assert core.slug is None
        assert core.weight is None
        assert core.lang is None
        assert core.type is None
        assert core.section is None
        assert core.file_hash is None

    def test_page_core_all_fields(self):
        """Test PageCore with all fields populated."""
        test_date = datetime(2025, 10, 26, 12, 0, 0)
        core = PageCore(
            source_path="content/posts/my-post.md",
            title="My Post",
            date=test_date,
            tags=["python", "web", "testing"],
            slug="my-custom-slug",
            weight=42,
            lang="en",
            type="doc",
            section="content/posts",
            file_hash="abc123def456",
        )

        assert core.source_path == "content/posts/my-post.md"
        assert core.title == "My Post"
        assert core.date == test_date
        assert core.tags == ["python", "web", "testing"]
        assert core.slug == "my-custom-slug"
        assert core.weight == 42
        assert core.lang == "en"
        assert core.type == "doc"
        assert core.section == "content/posts"
        assert core.file_hash == "abc123def456"

    def test_page_core_empty_title_becomes_untitled(self):
        """Test that empty title defaults to 'Untitled'."""
        core = PageCore(
            source_path="content/test.md",
            title="",  # Empty string
        )

        assert core.title == "Untitled"

    def test_page_core_none_tags_becomes_empty_list(self):
        """Test that None tags defaults to empty list."""
        core = PageCore(
            source_path="content/test.md",
            title="Test",
            tags=None,  # None instead of list
        )

        assert core.tags == []
        assert isinstance(core.tags, list)


class TestPageCoreSerialization:
    """Test PageCore JSON serialization/deserialization."""

    def test_page_core_to_dict(self):
        """Test converting PageCore to dictionary."""
        test_date = datetime(2025, 10, 26, 12, 0, 0)
        core = PageCore(
            source_path="content/test.md",
            title="Test Page",
            date=test_date,
            tags=["python"],
            slug="test-slug",
        )

        data = asdict(core)

        assert isinstance(data, dict)
        assert data["source_path"] == "content/test.md"
        assert data["title"] == "Test Page"
        assert data["date"] == test_date
        assert data["tags"] == ["python"]
        assert data["slug"] == "test-slug"

    def test_page_core_from_dict(self):
        """Test reconstructing PageCore from dictionary."""
        data = {
            "source_path": "content/test.md",
            "title": "Test Page",
            "date": datetime(2025, 10, 26),
            "tags": ["python", "web"],
            "slug": "test-slug",
            "weight": 10,
            "lang": "en",
            "type": "doc",
            "section": "content/posts",
            "file_hash": "abc123",
        }

        core = PageCore(**data)

        assert core.source_path == "content/test.md"
        assert core.title == "Test Page"
        assert core.date == datetime(2025, 10, 26)
        assert core.tags == ["python", "web"]
        assert core.slug == "test-slug"
        assert core.weight == 10
        assert core.lang == "en"
        assert core.type == "doc"
        assert core.section == "content/posts"
        assert core.file_hash == "abc123"

    def test_page_core_roundtrip_serialization(self):
        """Test that PageCore survives dict → PageCore → dict roundtrip."""
        original = PageCore(
            source_path="content/posts/test.md",
            title="Original Title",
            date=datetime(2025, 10, 26, 15, 30, 0),
            tags=["tag1", "tag2", "tag3"],
            slug="original-slug",
            weight=5,
            lang="es",
            type="post",
            section="content/posts",
            file_hash="original_hash",
        )

        # Serialize to dict
        data = asdict(original)

        # Deserialize back to PageCore
        reconstructed = PageCore(**data)

        # All fields should match
        assert reconstructed.source_path == original.source_path
        assert reconstructed.title == original.title
        assert reconstructed.date == original.date
        assert reconstructed.tags == original.tags
        assert reconstructed.slug == original.slug
        assert reconstructed.weight == original.weight
        assert reconstructed.lang == original.lang
        assert reconstructed.type == original.type
        assert reconstructed.section == original.section
        assert reconstructed.file_hash == original.file_hash
