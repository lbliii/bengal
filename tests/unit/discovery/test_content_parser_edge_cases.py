"""
Tests for ContentParser frontmatter extraction edge cases.

ContentParser uses patitas.parse_frontmatter and patitas.extract_body.
extract_body edge cases are covered by Patitas test_frontmatter.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.content.discovery.content_parser import ContentParser

if TYPE_CHECKING:
    from pathlib import Path


class TestContentParserParseFile:
    """Test full parse_file method with edge cases."""

    def test_parse_file_with_bom(self, tmp_path: Path) -> None:
        """UTF-8 BOM should be handled correctly."""
        test_file = tmp_path / "bom.md"
        # Write UTF-8 BOM followed by frontmatter
        test_file.write_bytes(b"\xef\xbb\xbf---\ntitle: BOM Test\n---\n\nContent")

        parser = ContentParser(tmp_path)
        content, _metadata = parser.parse_file(test_file)

        # Should parse successfully
        assert "Content" in content

    def test_parse_file_yaml_error_recovery(self, tmp_path: Path) -> None:
        """Invalid YAML should be recovered gracefully via patitas."""
        test_file = tmp_path / "bad_yaml.md"
        # Invalid YAML (tabs in wrong places, etc.)
        test_file.write_text("---\ntitle: [unclosed bracket\n---\n\nContent body")

        parser = ContentParser(tmp_path)
        content, metadata = parser.parse_file(test_file)

        # Patitas returns body with frontmatter stripped, empty metadata
        assert "Content body" in content
        assert metadata == {}

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

    def test_parser_with_no_collections_validates_all(self, tmp_path: Path) -> None:
        """Parser without collections should accept any frontmatter."""
        test_file = tmp_path / "any.md"
        test_file.write_text("---\ncustom_field: value\n---\nContent")

        parser = ContentParser(tmp_path)  # No collections
        content, metadata = parser.parse_file(test_file)

        assert metadata.get("custom_field") == "value"
        assert "Content" in content

    def test_validate_against_collection_no_op_without_collections(self, tmp_path: Path) -> None:
        """validate_against_collection should be no-op without collections."""
        parser = ContentParser(tmp_path)  # No collections

        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Test\n---\nContent")

        metadata = {"title": "Test"}
        result = parser.validate_against_collection(test_file, metadata)

        # Should return metadata unchanged
        assert result == metadata

    def test_validation_errors_tracked(self, tmp_path: Path) -> None:
        """Validation errors should be tracked for later reporting."""
        # This tests that the parser has validation error tracking infrastructure
        parser = ContentParser(tmp_path)

        # Initially no validation errors
        assert parser._validation_errors == []
