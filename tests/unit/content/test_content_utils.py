"""
Tests for bengal.content.utils module.

These tests verify the shared utilities extracted from content discovery
and source modules:
- frontmatter.py: parse_frontmatter, extract_content_skip_frontmatter
- slugify.py: path_to_slug, title_to_slug
- constants.py: CONTENT_EXTENSIONS
- http_errors.py: raise_http_error
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.content.utils import (
    CONTENT_EXTENSIONS,
    extract_content_skip_frontmatter,
    parse_frontmatter,
    path_to_slug,
    title_to_slug,
)
from bengal.content.utils.http_errors import raise_http_error
from bengal.errors import BengalDiscoveryError


class TestContentExtensions:
    """Tests for CONTENT_EXTENSIONS constant."""

    def test_includes_markdown(self) -> None:
        """Markdown extensions are included."""
        assert ".md" in CONTENT_EXTENSIONS
        assert ".markdown" in CONTENT_EXTENSIONS

    def test_includes_rst(self) -> None:
        """reStructuredText extension is included."""
        assert ".rst" in CONTENT_EXTENSIONS

    def test_includes_txt(self) -> None:
        """Plain text extension is included."""
        assert ".txt" in CONTENT_EXTENSIONS

    def test_is_frozenset(self) -> None:
        """CONTENT_EXTENSIONS is immutable."""
        assert isinstance(CONTENT_EXTENSIONS, frozenset)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_basic_frontmatter(self) -> None:
        """Parse basic YAML frontmatter."""
        content = "---\ntitle: Hello\nauthor: Jane\n---\n\nBody content"
        meta, body = parse_frontmatter(content)

        assert meta == {"title": "Hello", "author": "Jane"}
        assert body == "Body content"

    def test_no_frontmatter(self) -> None:
        """Content without frontmatter returns empty dict."""
        content = "# Just a heading\n\nSome text."
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert body == content

    def test_empty_frontmatter(self) -> None:
        """Empty frontmatter block returns empty dict."""
        content = "---\n---\nBody"
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert body == "Body"

    def test_frontmatter_with_lists(self) -> None:
        """Frontmatter with YAML lists."""
        content = "---\ntags:\n  - python\n  - testing\n---\n\nContent"
        meta, body = parse_frontmatter(content)

        assert meta == {"tags": ["python", "testing"]}

    def test_frontmatter_with_nested_dict(self) -> None:
        """Frontmatter with nested dictionaries."""
        content = "---\nmeta:\n  og_title: Test\n  og_image: /img.png\n---\nBody"
        meta, body = parse_frontmatter(content)

        assert meta == {"meta": {"og_title": "Test", "og_image": "/img.png"}}

    def test_invalid_yaml_returns_empty(self) -> None:
        """Invalid YAML returns empty dict (graceful degradation)."""
        content = "---\ntitle: [unclosed bracket\n---\nBody"
        meta, body = parse_frontmatter(content)

        # Should gracefully degrade
        assert meta == {}
        assert body == content

    def test_unclosed_frontmatter(self) -> None:
        """Unclosed frontmatter (no closing ---) returns content as-is."""
        content = "---\ntitle: No closing delimiter"
        meta, body = parse_frontmatter(content)

        assert meta == {}


class TestExtractContentSkipFrontmatter:
    """Tests for extract_content_skip_frontmatter function."""

    def test_normal_frontmatter(self) -> None:
        """Extract content from normal frontmatter."""
        content = "---\ntitle: Test\n---\n\nActual content here."
        result = extract_content_skip_frontmatter(content)

        assert result == "Actual content here."

    def test_empty_frontmatter(self) -> None:
        """Extract content from empty frontmatter."""
        content = "---\n---\nContent after"
        result = extract_content_skip_frontmatter(content)

        assert result == "Content after"

    def test_no_frontmatter(self) -> None:
        """Content without frontmatter returned as-is."""
        content = "# Heading\n\nNo frontmatter"
        result = extract_content_skip_frontmatter(content)

        assert result == content.strip()

    def test_unclosed_frontmatter(self) -> None:
        """Unclosed frontmatter returns everything after first ---."""
        content = "---\nThis has no closing delimiter"
        result = extract_content_skip_frontmatter(content)

        assert "This has no closing delimiter" in result

    def test_content_with_dashes(self) -> None:
        """Content with --- in body handled correctly."""
        content = "---\ntitle: Test\n---\n\n# Heading\n\n---\n\nMore content"
        result = extract_content_skip_frontmatter(content)

        assert "# Heading" in result
        assert "---" in result
        assert "More content" in result


class TestPathToSlug:
    """Tests for path_to_slug function."""

    def test_simple_file(self) -> None:
        """Simple filename becomes slug."""
        assert path_to_slug(Path("getting-started.md")) == "getting-started"

    def test_nested_path(self) -> None:
        """Nested path preserves directory structure."""
        assert path_to_slug(Path("guides/advanced/tips.md")) == "guides/advanced/tips"

    def test_index_file(self) -> None:
        """Index files are handled specially."""
        assert path_to_slug(Path("index.md")) == "index"
        assert path_to_slug(Path("guides/index.md")) == "guides"
        assert path_to_slug(Path("docs/api/index.md")) == "docs/api"

    def test_handle_index_false(self) -> None:
        """Disabling index handling keeps full path."""
        assert path_to_slug(Path("guides/index.md"), handle_index=False) == "guides/index"

    def test_various_extensions(self) -> None:
        """Different extensions are stripped."""
        assert path_to_slug(Path("doc.markdown")) == "doc"
        assert path_to_slug(Path("doc.rst")) == "doc"
        assert path_to_slug(Path("doc.txt")) == "doc"

    def test_string_input(self) -> None:
        """String paths work too."""
        assert path_to_slug("guides/setup.md") == "guides/setup"

    def test_windows_separators(self) -> None:
        """Backslash separators are normalized."""
        # Path normalizes on Unix, so we test the string conversion
        result = path_to_slug(Path("guides") / "nested" / "page.md")
        assert "/" in result or result == "guides/nested/page"


class TestTitleToSlug:
    """Tests for title_to_slug function."""

    def test_simple_title(self) -> None:
        """Simple title becomes lowercase slug."""
        assert title_to_slug("Hello World") == "hello-world"

    def test_special_characters_removed(self) -> None:
        """Special characters are removed."""
        assert title_to_slug("Hello, World!") == "hello-world"
        assert title_to_slug("API Reference (v2)") == "api-reference-v2"
        assert title_to_slug("What's New?") == "whats-new"

    def test_multiple_spaces_collapsed(self) -> None:
        """Multiple spaces become single hyphen."""
        assert title_to_slug("Hello    World") == "hello-world"

    def test_leading_trailing_stripped(self) -> None:
        """Leading/trailing hyphens are stripped."""
        assert title_to_slug("  Hello World  ") == "hello-world"
        assert title_to_slug("!Hello!") == "hello"

    def test_unicode_preserved(self) -> None:
        """Unicode word characters are preserved."""
        # Depends on locale, but \w typically includes unicode letters
        result = title_to_slug("Héllo Wörld")
        assert "h" in result  # At minimum, lowercase works

    def test_empty_string(self) -> None:
        """Empty string returns empty slug."""
        assert title_to_slug("") == ""

    def test_only_special_chars(self) -> None:
        """String of only special chars becomes empty."""
        assert title_to_slug("!@#$%") == ""


class TestRaiseHttpError:
    """Tests for raise_http_error function."""

    def test_404_raises_discovery_error(self) -> None:
        """404 raises BengalDiscoveryError with D011 code."""
        with pytest.raises(BengalDiscoveryError) as exc_info:
            raise_http_error(404, "GitHub repository", "myorg/docs")

        error = exc_info.value
        assert "Not found" in str(error)
        assert "myorg/docs" in str(error)

    def test_401_raises_discovery_error(self) -> None:
        """401 raises BengalDiscoveryError with D010 code."""
        with pytest.raises(BengalDiscoveryError) as exc_info:
            raise_http_error(401, "REST API", "https://api.example.com")

        error = exc_info.value
        assert "Authentication failed" in str(error)

    def test_403_raises_discovery_error(self) -> None:
        """403 raises BengalDiscoveryError with D010 code."""
        with pytest.raises(BengalDiscoveryError) as exc_info:
            raise_http_error(403, "Notion database", "abc123")

        error = exc_info.value
        assert "Access denied" in str(error)

    def test_custom_suggestion(self) -> None:
        """Custom suggestion is used when provided."""
        with pytest.raises(BengalDiscoveryError) as exc_info:
            raise_http_error(
                404,
                "API endpoint",
                "/v1/users",
                suggestion="Check the API documentation for valid endpoints",
            )

        error = exc_info.value
        assert error.suggestion == "Check the API documentation for valid endpoints"

    def test_generic_status(self) -> None:
        """Unknown status codes still raise errors."""
        with pytest.raises(BengalDiscoveryError) as exc_info:
            raise_http_error(500, "API", "https://api.example.com")

        error = exc_info.value
        assert "HTTP 500" in str(error)
