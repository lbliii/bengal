"""
Tests for ContentParser frontmatter extraction edge cases.

These tests verify that _extract_content_skip_frontmatter handles:
- Normal frontmatter (---content---)
- Empty frontmatter (---\n---)
- No frontmatter
- File starting with --- but no closing delimiter
- Various edge cases with whitespace and content
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.content.discovery.content_parser import ContentParser


@pytest.fixture
def parser(tmp_path: Path) -> ContentParser:
    """Create a ContentParser instance for testing."""
    return ContentParser(tmp_path)


class TestExtractContentSkipFrontmatter:
    """Test _extract_content_skip_frontmatter edge cases."""

    def test_normal_frontmatter_extraction(self, parser: ContentParser) -> None:
        """Normal frontmatter should extract content correctly."""
        content = "---\ntitle: Test\nauthor: Jane\n---\n\nActual content here."
        result = parser._extract_content_skip_frontmatter(content)
        assert result == "Actual content here."

    def test_empty_frontmatter(self, parser: ContentParser) -> None:
        """Empty frontmatter (---\\n---) should return content."""
        content = "---\n---\nContent after empty frontmatter"
        result = parser._extract_content_skip_frontmatter(content)
        assert result == "Content after empty frontmatter"

    def test_no_frontmatter(self, parser: ContentParser) -> None:
        """File without frontmatter returns full content."""
        content = "# Just a heading\n\nSome content without frontmatter."
        result = parser._extract_content_skip_frontmatter(content)
        assert result == content.strip()

    def test_content_not_starting_with_dashes(self, parser: ContentParser) -> None:
        """Content not starting with --- should return as-is."""
        content = "Hello world\n---\nThis is not frontmatter"
        result = parser._extract_content_skip_frontmatter(content)
        assert result == content.strip()

    def test_single_dash_line_not_frontmatter(self, parser: ContentParser) -> None:
        """Single --- line without closing delimiter."""
        content = "---\nThis looks like frontmatter but has no closing delimiter"
        result = parser._extract_content_skip_frontmatter(content)
        # Should treat everything after first --- as content
        assert "This looks like frontmatter" in result

    def test_file_with_only_dashes(self, parser: ContentParser) -> None:
        """File with only '---' should not crash."""
        content = "---"
        result = parser._extract_content_skip_frontmatter(content)
        # Should handle gracefully
        assert result == "" or result == "---"

    def test_multiple_dash_sections(self, parser: ContentParser) -> None:
        """Content with multiple --- sections uses first two."""
        content = "---\nfrontmatter\n---\ncontent\n---\nmore dashes"
        result = parser._extract_content_skip_frontmatter(content)
        # Should get content after second ---, including the third ---
        assert "content" in result
        assert "more dashes" in result

    def test_frontmatter_with_dashes_in_content(self, parser: ContentParser) -> None:
        """Frontmatter with --- in the body content."""
        content = "---\ntitle: Test\n---\n\nContent with --- horizontal rule"
        result = parser._extract_content_skip_frontmatter(content)
        assert "Content with --- horizontal rule" in result

    def test_whitespace_after_frontmatter(self, parser: ContentParser) -> None:
        """Whitespace after frontmatter should be stripped."""
        content = "---\ntitle: Test\n---\n\n\n\nContent with leading whitespace"
        result = parser._extract_content_skip_frontmatter(content)
        assert result == "Content with leading whitespace"

    def test_whitespace_before_and_after(self, parser: ContentParser) -> None:
        """All whitespace should be stripped."""
        content = "---\ntitle: Test\n---\n\n  Content  \n\n"
        result = parser._extract_content_skip_frontmatter(content)
        assert result == "Content"

    def test_empty_file(self, parser: ContentParser) -> None:
        """Empty file should return empty string."""
        content = ""
        result = parser._extract_content_skip_frontmatter(content)
        assert result == ""

    def test_only_whitespace(self, parser: ContentParser) -> None:
        """File with only whitespace returns empty string."""
        content = "   \n\n   "
        result = parser._extract_content_skip_frontmatter(content)
        assert result == ""

    def test_frontmatter_with_yaml_list(self, parser: ContentParser) -> None:
        """Frontmatter with YAML list should extract correctly."""
        content = """---
title: Test
tags:
  - python
  - testing
---

Content here."""
        result = parser._extract_content_skip_frontmatter(content)
        assert result == "Content here."

    def test_frontmatter_with_multiline_string(self, parser: ContentParser) -> None:
        """Frontmatter with multiline YAML string."""
        content = """---
title: Test
description: |
  This is a multiline
  description field
---

Body content."""
        result = parser._extract_content_skip_frontmatter(content)
        assert result == "Body content."


class TestContentParserParseFile:
    """Test full parse_file method with edge cases."""

    def test_parse_file_with_bom(self, tmp_path: Path) -> None:
        """UTF-8 BOM should be handled correctly."""
        test_file = tmp_path / "bom.md"
        # Write UTF-8 BOM followed by frontmatter
        test_file.write_bytes(b"\xef\xbb\xbf---\ntitle: BOM Test\n---\n\nContent")

        parser = ContentParser(tmp_path)
        content, metadata = parser.parse_file(test_file)

        # Should parse successfully
        assert "Content" in content

    def test_parse_file_yaml_error_recovery(self, tmp_path: Path) -> None:
        """Invalid YAML should be recovered gracefully."""
        test_file = tmp_path / "bad_yaml.md"
        # Invalid YAML (tabs in wrong places, etc.)
        test_file.write_text("---\ntitle: [unclosed bracket\n---\n\nContent body")

        parser = ContentParser(tmp_path)
        content, metadata = parser.parse_file(test_file)

        # Should recover and return content
        assert "Content body" in content
        # Should have parse error marker
        assert "_parse_error" in metadata

    def test_parse_file_empty_file(self, tmp_path: Path) -> None:
        """Empty file should parse without error."""
        test_file = tmp_path / "empty.md"
        test_file.write_text("")

        parser = ContentParser(tmp_path)
        content, metadata = parser.parse_file(test_file)

        assert content == ""
        assert isinstance(metadata, dict)

    def test_parse_file_no_frontmatter(self, tmp_path: Path) -> None:
        """File without frontmatter should parse as content only."""
        test_file = tmp_path / "no_fm.md"
        test_file.write_text("# Just Content\n\nNo frontmatter here.")

        parser = ContentParser(tmp_path)
        content, metadata = parser.parse_file(test_file)

        assert "# Just Content" in content
        assert metadata == {}


class TestContentParserStrictMode:
    """Test strict validation mode behavior."""

    def test_strict_mode_raises_on_validation_error(self, tmp_path: Path) -> None:
        """Strict mode should raise on validation errors."""
        from bengal.collections import CollectionConfig
        from dataclasses import dataclass

        @dataclass
        class RequiredSchema:
            title: str
            required_field: str  # This is required

        collections = {
            "docs": CollectionConfig(
                schema=RequiredSchema,
                directory=tmp_path,
                strict=True,
            )
        }

        # File missing required_field
        test_file = tmp_path / "missing.md"
        test_file.write_text("---\ntitle: Test\n---\nContent")

        parser = ContentParser(
            tmp_path,
            collections=collections,
            strict_validation=True,
        )

        from bengal.collections import ContentValidationError

        with pytest.raises(ContentValidationError):
            parser.parse_file(test_file)
            parser.validate_against_collection(test_file, {"title": "Test"})

    def test_lenient_mode_logs_validation_error(self, tmp_path: Path) -> None:
        """Lenient mode should log but not raise validation errors."""
        from bengal.collections import CollectionConfig
        from dataclasses import dataclass

        @dataclass
        class RequiredSchema:
            title: str
            required_field: str

        collections = {
            "docs": CollectionConfig(
                schema=RequiredSchema,
                directory=tmp_path,
                strict=True,
            )
        }

        test_file = tmp_path / "missing.md"
        test_file.write_text("---\ntitle: Test\n---\nContent")

        parser = ContentParser(
            tmp_path,
            collections=collections,
            strict_validation=False,  # Lenient
        )

        content, metadata = parser.parse_file(test_file)
        # Should complete parsing
        result = parser.validate_against_collection(test_file, metadata)

        # Should return original metadata (no exception)
        assert isinstance(result, dict)
