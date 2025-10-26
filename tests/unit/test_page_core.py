"""Unit tests for PageCore dataclass."""

from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from bengal.core.page.page_core import PageCore


class TestPageCoreCreation:
    """Test PageCore instantiation and initialization."""

    def test_page_core_minimal_fields(self):
        """Test PageCore with only required fields."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test Page",
        )

        assert core.source_path == Path("content/test.md")
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
            source_path=Path("content/posts/my-post.md"),
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

        assert core.source_path == Path("content/posts/my-post.md")
        assert core.title == "My Post"
        assert core.date == test_date
        assert core.tags == ["python", "web", "testing"]
        assert core.slug == "my-custom-slug"
        assert core.weight == 42
        assert core.lang == "en"
        assert core.type == "doc"
        assert core.section == "content/posts"
        assert core.file_hash == "abc123def456"

    def test_page_core_string_path_converted(self):
        """Test that string paths are converted to Path objects."""
        core = PageCore(
            source_path="content/test.md",  # String
            title="Test",
        )

        assert isinstance(core.source_path, Path)
        assert core.source_path == Path("content/test.md")

    def test_page_core_empty_title_becomes_untitled(self):
        """Test that empty title defaults to 'Untitled'."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="",  # Empty string
        )

        assert core.title == "Untitled"

    def test_page_core_none_tags_becomes_empty_list(self):
        """Test that None tags defaults to empty list."""
        core = PageCore(
            source_path=Path("content/test.md"),
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
            source_path=Path("content/test.md"),
            title="Test Page",
            date=test_date,
            tags=["python"],
            slug="test-slug",
        )

        data = asdict(core)

        assert isinstance(data, dict)
        assert data["source_path"] == Path("content/test.md")
        assert data["title"] == "Test Page"
        assert data["date"] == test_date
        assert data["tags"] == ["python"]
        assert data["slug"] == "test-slug"

    def test_page_core_from_dict(self):
        """Test reconstructing PageCore from dictionary."""
        data = {
            "source_path": Path("content/test.md"),
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

        assert core.source_path == Path("content/test.md")
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
            source_path=Path("content/posts/test.md"),
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

    def test_page_core_roundtrip_with_none_values(self):
        """Test roundtrip with None values (common case)."""
        original = PageCore(
            source_path=Path("content/page.md"),
            title="Minimal Page",
            # All optional fields are None
        )

        data = asdict(original)
        reconstructed = PageCore(**data)

        assert reconstructed.source_path == original.source_path
        assert reconstructed.title == original.title
        assert reconstructed.date is None
        assert reconstructed.tags == []
        assert reconstructed.slug is None
        assert reconstructed.weight is None
        assert reconstructed.lang is None
        assert reconstructed.type is None
        assert reconstructed.section is None
        assert reconstructed.file_hash is None


class TestPageCoreFieldDefaults:
    """Test PageCore field defaults and optional values."""

    def test_page_core_default_tags_is_empty_list(self):
        """Test that tags defaults to empty list, not None."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
        )

        assert core.tags == []
        assert isinstance(core.tags, list)

        # Should be able to append without errors
        core.tags.append("new-tag")
        assert "new-tag" in core.tags

    def test_page_core_optional_fields_default_to_none(self):
        """Test that optional fields default to None."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
        )

        assert core.date is None
        assert core.slug is None
        assert core.weight is None
        assert core.lang is None
        assert core.type is None
        assert core.section is None
        assert core.file_hash is None


class TestPageCoreFieldTypes:
    """Test PageCore field type handling."""

    def test_page_core_path_field(self):
        """Test source_path is Path type."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
        )

        assert isinstance(core.source_path, Path)

    def test_page_core_datetime_field(self):
        """Test date is datetime type when provided."""
        test_date = datetime(2025, 10, 26, 14, 30, 0)
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
            date=test_date,
        )

        assert isinstance(core.date, datetime)
        assert core.date.year == 2025
        assert core.date.month == 10
        assert core.date.day == 26

    def test_page_core_tags_is_list(self):
        """Test tags is list type."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
            tags=["python", "web"],
        )

        assert isinstance(core.tags, list)
        assert len(core.tags) == 2

    def test_page_core_weight_is_int(self):
        """Test weight is int type when provided."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
            weight=42,
        )

        assert isinstance(core.weight, int)
        assert core.weight == 42


class TestPageCoreEquality:
    """Test PageCore equality comparisons."""

    def test_page_core_equality_same_values(self):
        """Test that two PageCore objects with same values are equal."""
        core1 = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
            tags=["python"],
        )
        core2 = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
            tags=["python"],
        )

        assert core1 == core2

    def test_page_core_inequality_different_values(self):
        """Test that PageCore objects with different values are not equal."""
        core1 = PageCore(
            source_path=Path("content/test1.md"),
            title="Test 1",
        )
        core2 = PageCore(
            source_path=Path("content/test2.md"),
            title="Test 2",
        )

        assert core1 != core2


class TestPageCoreImmutability:
    """Test PageCore field mutability (dataclasses are mutable by default)."""

    def test_page_core_fields_are_mutable(self):
        """Test that PageCore fields can be updated (needed for property setters)."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Original Title",
        )

        # Fields should be mutable
        core.title = "Updated Title"
        assert core.title == "Updated Title"

        core.tags.append("new-tag")
        assert "new-tag" in core.tags

        core.weight = 42
        assert core.weight == 42


class TestPageCoreEdgeCases:
    """Test PageCore edge cases and error handling."""

    def test_page_core_with_very_long_title(self):
        """Test PageCore with very long title."""
        long_title = "A" * 1000
        core = PageCore(
            source_path=Path("content/test.md"),
            title=long_title,
        )

        assert core.title == long_title
        assert len(core.title) == 1000

    def test_page_core_with_empty_tags_list(self):
        """Test PageCore with explicitly empty tags list."""
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
            tags=[],
        )

        assert core.tags == []
        assert isinstance(core.tags, list)

    def test_page_core_with_many_tags(self):
        """Test PageCore with many tags."""
        many_tags = [f"tag{i}" for i in range(100)]
        core = PageCore(
            source_path=Path("content/test.md"),
            title="Test",
            tags=many_tags,
        )

        assert len(core.tags) == 100
        assert core.tags[0] == "tag0"
        assert core.tags[99] == "tag99"

    def test_page_core_with_unicode_title(self):
        """Test PageCore with unicode characters in title."""
        unicode_title = "测试页面 🚀 Тест"
        core = PageCore(
            source_path=Path("content/test.md"),
            title=unicode_title,
        )

        assert core.title == unicode_title

    def test_page_core_with_relative_path(self):
        """Test PageCore with relative path."""
        core = PageCore(
            source_path=Path("content/posts/2025/test.md"),
            title="Test",
        )

        assert core.source_path == Path("content/posts/2025/test.md")
        assert not core.source_path.is_absolute()

    def test_page_core_with_absolute_path(self):
        """Test PageCore with absolute path."""
        abs_path = Path("/Users/test/site/content/test.md")
        core = PageCore(
            source_path=abs_path,
            title="Test",
        )

        assert core.source_path == abs_path
        assert core.source_path.is_absolute()
