"""
Unit tests for effects utility functions.
"""

from bengal.effects.utils import (
    compute_content_hash,
    extract_body_after_frontmatter,
    frozenset_or_none,
)


class TestComputeContentHash:
    """Tests for compute_content_hash function."""

    def test_returns_hex_string(self) -> None:
        """Hash is a hex string."""
        result = compute_content_hash("hello")
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

    def test_default_length_is_16(self) -> None:
        """Default prefix length is 16 characters."""
        result = compute_content_hash("hello")
        assert len(result) == 16

    def test_custom_prefix_length(self) -> None:
        """Custom prefix length is respected."""
        result = compute_content_hash("hello", prefix_length=8)
        assert len(result) == 8

    def test_same_content_same_hash(self) -> None:
        """Same content produces same hash."""
        assert compute_content_hash("hello") == compute_content_hash("hello")

    def test_different_content_different_hash(self) -> None:
        """Different content produces different hash."""
        assert compute_content_hash("hello") != compute_content_hash("world")

    def test_empty_string(self) -> None:
        """Empty string produces valid hash."""
        result = compute_content_hash("")
        assert len(result) == 16

    def test_unicode_content(self) -> None:
        """Unicode content is handled correctly."""
        result = compute_content_hash("héllo wörld 日本語")
        assert len(result) == 16


class TestExtractBodyAfterFrontmatter:
    """Tests for extract_body_after_frontmatter function."""

    def test_no_frontmatter_returns_original(self) -> None:
        """Content without frontmatter is returned as-is."""
        content = "# Hello\n\nThis is content."
        assert extract_body_after_frontmatter(content) == content

    def test_extracts_body_after_frontmatter(self) -> None:
        """Body after frontmatter delimiters is extracted."""
        content = """---
title: Hello
---
# Hello

This is content."""
        result = extract_body_after_frontmatter(content)
        assert result == "# Hello\n\nThis is content."

    def test_empty_frontmatter(self) -> None:
        """Empty frontmatter is handled."""
        content = """---
---
Body content"""
        result = extract_body_after_frontmatter(content)
        assert result == "Body content"

    def test_frontmatter_with_dashes_in_content(self) -> None:
        """Dashes in body content don't confuse parser."""
        content = """---
title: Test
---
Content with --- dashes"""
        result = extract_body_after_frontmatter(content)
        assert result == "Content with --- dashes"

    def test_only_opening_delimiter(self) -> None:
        """Only opening delimiter returns original content."""
        content = """---
title: Test
no closing delimiter"""
        result = extract_body_after_frontmatter(content)
        # No closing delimiter found, so body_start stays at 0 - returns original
        assert result == content

    def test_empty_body(self) -> None:
        """Frontmatter with no body returns empty string."""
        content = """---
title: Test
---"""
        result = extract_body_after_frontmatter(content)
        assert result == ""

    def test_preserves_body_formatting(self) -> None:
        """Body formatting (whitespace, newlines) is preserved."""
        content = """---
title: Test
---

  Indented line

Another line"""
        result = extract_body_after_frontmatter(content)
        assert result == "\n  Indented line\n\nAnother line"


class TestFrozensetOrNone:
    """Tests for frozenset_or_none function."""

    def test_empty_set_returns_none(self) -> None:
        """Empty set returns None."""
        result = frozenset_or_none(set())
        assert result is None

    def test_non_empty_set_returns_frozenset(self) -> None:
        """Non-empty set returns frozenset."""
        result = frozenset_or_none({1, 2, 3})
        assert result == frozenset({1, 2, 3})
        assert isinstance(result, frozenset)

    def test_single_element_set(self) -> None:
        """Single element set returns frozenset."""
        result = frozenset_or_none({"a"})
        assert result == frozenset({"a"})

    def test_preserves_elements(self) -> None:
        """All elements are preserved in conversion."""
        original = {"a", "b", "c"}
        result = frozenset_or_none(original)
        assert result is not None
        assert set(result) == original

    def test_with_path_objects(self) -> None:
        """Works with Path objects."""
        from pathlib import Path

        paths = {Path("a.txt"), Path("b.txt")}
        result = frozenset_or_none(paths)
        assert result is not None
        assert Path("a.txt") in result
        assert Path("b.txt") in result
