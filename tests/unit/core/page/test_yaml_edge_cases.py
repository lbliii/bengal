"""
Tests for YAML edge case handling in PageCore.

Verifies that frontmatter fields with special YAML values are properly
sanitized to prevent downstream errors.

Edge cases tested:
- null/~ → None (filtered out)
- true/false → bool (converted to string)
- numbers → int/float (converted to string)
- dates → datetime.date (converted to string)
- empty strings (filtered out)
- whitespace-only strings (filtered out)
- nested lists/dicts (filtered out)
"""

from datetime import date

from bengal.core.page.page_core import PageCore


class TestTagsSanitization:
    """Tests for tags field sanitization."""

    def test_filters_none_values(self) -> None:
        """None values (from YAML null/~) should be filtered out."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=[None, "valid", None],  # type: ignore[list-item]
        )
        assert core.tags == ["valid"]

    def test_converts_bool_to_string(self) -> None:
        """Boolean values should be converted to strings."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=[True, False, "valid"],  # type: ignore[list-item]
        )
        assert core.tags == ["True", "False", "valid"]

    def test_converts_int_to_string(self) -> None:
        """Integer values should be converted to strings."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=[404, 200, "valid"],  # type: ignore[list-item]
        )
        assert core.tags == ["404", "200", "valid"]

    def test_converts_float_to_string(self) -> None:
        """Float values should be converted to strings."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=[3.14, 2.718, "valid"],  # type: ignore[list-item]
        )
        assert core.tags == ["3.14", "2.718", "valid"]

    def test_converts_date_to_string(self) -> None:
        """Date values should be converted to strings."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=[date(2024, 1, 1), "valid"],  # type: ignore[list-item]
        )
        assert core.tags == ["2024-01-01", "valid"]

    def test_filters_empty_strings(self) -> None:
        """Empty strings should be filtered out."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=["", "valid", ""],
        )
        assert core.tags == ["valid"]

    def test_filters_whitespace_only_strings(self) -> None:
        """Whitespace-only strings should be filtered out."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=["   ", "valid", "\t\n"],
        )
        assert core.tags == ["valid"]

    def test_filters_nested_lists(self) -> None:
        """Nested lists should be filtered out."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=[["nested", "list"], "valid"],  # type: ignore[list-item]
        )
        assert core.tags == ["valid"]

    def test_filters_nested_dicts(self) -> None:
        """Nested dicts should be filtered out."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=[{"key": "value"}, "valid"],  # type: ignore[list-item]
        )
        assert core.tags == ["valid"]

    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace should be stripped."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=["  valid  ", "\ttag\n"],
        )
        assert core.tags == ["valid", "tag"]

    def test_handles_none_tags_list(self) -> None:
        """None for entire tags list should become empty list."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=None,  # type: ignore[arg-type]
        )
        assert core.tags == []

    def test_comprehensive_yaml_edge_cases(self) -> None:
        """Test all YAML edge cases together."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            tags=[
                None,  # null
                True,  # true
                False,  # false
                404,  # int
                3.14,  # float
                date(2024, 1, 1),  # date
                "",  # empty
                "   ",  # whitespace
                ["nested"],  # list
                {"key": "val"},  # dict
                "valid-tag",  # valid string
                "  Another Tag  ",  # string with whitespace
            ],  # type: ignore[list-item]
        )
        # Should keep: True, False, 404, 3.14, date, valid-tag, Another Tag
        assert core.tags == [
            "True",
            "False",
            "404",
            "3.14",
            "2024-01-01",
            "valid-tag",
            "Another Tag",
        ]


class TestAliasesSanitization:
    """Tests for aliases field sanitization (same logic as tags)."""

    def test_filters_none_values(self) -> None:
        """None values should be filtered from aliases."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            aliases=[None, "/valid/", None],  # type: ignore[list-item]
        )
        assert core.aliases == ["/valid/"]

    def test_filters_nested_structures(self) -> None:
        """Nested lists/dicts should be filtered from aliases."""
        core = PageCore(
            source_path="test.md",
            title="Test",
            aliases=[["nested"], "/valid/", {"key": "val"}],  # type: ignore[list-item]
        )
        assert core.aliases == ["/valid/"]


class TestSanitizationReporting:
    """Tests that sanitization reports filtered values correctly."""

    def test_reports_filtered_tags(self) -> None:
        """Should report filtered values via internal method."""
        # Test the internal method directly since structlog doesn't integrate with caplog
        sanitized, filtered = PageCore._sanitize_string_list_with_report(
            [None, "valid", ["nested"], {"key": "val"}, "", "  "]
        )

        assert sanitized == ["valid"]
        assert "null/None" in filtered
        assert "nested list" in filtered
        assert "nested dict" in filtered
        assert "empty string" in filtered

    def test_no_report_when_all_valid(self) -> None:
        """Should report no filtered values when all are valid."""
        sanitized, filtered = PageCore._sanitize_string_list_with_report(
            ["valid", "also-valid", "third"]
        )

        assert sanitized == ["valid", "also-valid", "third"]
        assert filtered == []

    def test_handles_none_input(self) -> None:
        """Should handle None input gracefully."""
        sanitized, filtered = PageCore._sanitize_string_list_with_report(None)

        assert sanitized == []
        assert filtered == []
