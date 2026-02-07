"""Unit tests for bengal.postprocess.utils.page_data module."""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.postprocess.utils.page_data import get_section_name, tags_to_list


class TestGetSectionName:
    """Test get_section_name utility."""

    def test_returns_section_name_when_present(self) -> None:
        """Test extraction of section name from page with section."""
        page = MagicMock()
        page._section = MagicMock()
        page._section.name = "docs"

        result = get_section_name(page)

        assert result == "docs"

    def test_returns_empty_string_when_no_section(self) -> None:
        """Test returns empty string when page has no section."""
        page = MagicMock(spec=[])  # No _section attribute

        result = get_section_name(page)

        assert result == ""

    def test_returns_empty_string_when_section_is_none(self) -> None:
        """Test returns empty string when _section is None."""
        page = MagicMock()
        page._section = None

        result = get_section_name(page)

        assert result == ""

    def test_returns_empty_string_when_section_name_missing(self) -> None:
        """Test returns empty string when section has no name attribute."""
        page = MagicMock()
        page._section = MagicMock(spec=[])  # No name attribute

        result = get_section_name(page)

        assert result == ""

    def test_handles_section_with_empty_name(self) -> None:
        """Test handling of section with empty string name."""
        page = MagicMock()
        page._section = MagicMock()
        page._section.name = ""

        result = get_section_name(page)

        assert result == ""

    def test_handles_various_section_names(self) -> None:
        """Test with various valid section names."""
        test_cases = [
            "blog",
            "api/python",
            "docs/getting-started",
            "release-notes",
            "日本語",  # Unicode
            "section with spaces",
        ]

        for section_name in test_cases:
            page = MagicMock()
            page._section = MagicMock()
            page._section.name = section_name

            result = get_section_name(page)
            assert result == section_name, f"Failed for: {section_name}"


class TestTagsToList:
    """Test tags_to_list utility."""

    def test_converts_list_to_list(self) -> None:
        """Test that list input returns as list."""
        tags = ["python", "api", "docs"]

        result = tags_to_list(tags)

        assert result == ["python", "api", "docs"]

    def test_converts_tuple_to_list(self) -> None:
        """Test that tuple input is converted to list."""
        tags = ("python", "api")

        result = tags_to_list(tags)

        assert result == ["python", "api"]
        assert isinstance(result, list)

    def test_converts_string_to_single_item_list(self) -> None:
        """Test that single string becomes single-item list."""
        tags = "python"

        result = tags_to_list(tags)

        assert result == ["python"]

    def test_returns_empty_list_for_none(self) -> None:
        """Test that None returns empty list."""
        result = tags_to_list(None)

        assert result == []

    def test_returns_empty_list_for_empty_list(self) -> None:
        """Test that empty list returns empty list."""
        result = tags_to_list([])

        assert result == []

    def test_returns_empty_list_for_empty_string(self) -> None:
        """Test that empty string returns empty list."""
        result = tags_to_list("")

        assert result == []

    def test_converts_set_to_list(self) -> None:
        """Test that set is converted to list."""
        tags = {"python", "api"}

        result = tags_to_list(tags)

        assert isinstance(result, list)
        assert set(result) == {"python", "api"}

    def test_converts_generator_to_list(self) -> None:
        """Test that generator is converted to list."""
        tags = (tag for tag in ["a", "b", "c"])

        result = tags_to_list(tags)

        assert result == ["a", "b", "c"]

    def test_converts_non_string_items_to_string(self) -> None:
        """Test that non-string items are converted to strings."""
        tags = [1, 2, 3]

        result = tags_to_list(tags)

        assert result == ["1", "2", "3"]

    def test_handles_mixed_types(self) -> None:
        """Test handling of mixed type items."""
        tags = ["python", 42, True]

        result = tags_to_list(tags)

        assert result == ["python", "42", "True"]

    def test_returns_empty_for_non_iterable(self) -> None:
        """Test that non-iterable returns empty list."""
        result = tags_to_list(42)

        assert result == []

    def test_preserves_order_for_list(self) -> None:
        """Test that list order is preserved."""
        tags = ["z", "a", "m"]

        result = tags_to_list(tags)

        assert result == ["z", "a", "m"]

    def test_handles_whitespace_tags(self) -> None:
        """Test handling of tags with whitespace."""
        tags = ["tag with spaces", "  leading", "trailing  "]

        result = tags_to_list(tags)

        # Should preserve whitespace (cleaning is caller's responsibility)
        assert result == ["tag with spaces", "  leading", "trailing  "]

    def test_handles_unicode_tags(self) -> None:
        """Test handling of unicode tags."""
        tags = ["日本語", "中文", "한국어"]

        result = tags_to_list(tags)

        assert result == ["日本語", "中文", "한국어"]

    def test_handles_frozenset(self) -> None:
        """Test that frozenset is converted to list."""
        tags = frozenset(["a", "b"])

        result = tags_to_list(tags)

        assert isinstance(result, list)
        assert set(result) == {"a", "b"}
