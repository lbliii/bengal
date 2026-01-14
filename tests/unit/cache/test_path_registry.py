"""
Tests for PathRegistry.

RFC: rfc-cache-invalidation-architecture
Tests canonical path representation for consistent cache keys.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.cache.path_registry import PathRegistry


@pytest.fixture
def mock_site():
    """Create a mock Site with paths configured."""
    site = MagicMock()
    site.root_path = Path("/project")
    site.output_dir = Path("/project/public")

    # Mock BengalPaths
    paths = MagicMock()
    paths.content_dir = Path("/project/content")
    paths.generated_dir = Path("/project/.bengal/generated")
    site.paths = paths

    return site


@pytest.fixture
def registry(mock_site):
    """Create a PathRegistry with mock site."""
    return PathRegistry(mock_site)


class TestPathRegistry:
    """Tests for PathRegistry class."""

    def test_initialization(self, registry, mock_site):
        """Registry initializes with correct paths."""
        assert registry.site is mock_site
        assert registry._content_dir == Path("/project/content")
        assert registry._generated_dir == Path("/project/.bengal/generated")
        assert registry._output_dir == Path("/project/public")

    def test_canonical_source_content_page(self, registry):
        """canonical_source returns relative path for content pages."""
        page = MagicMock()
        page.source_path = Path("/project/content/about.md")
        page.metadata = {}

        result = registry.canonical_source(page)

        assert result == Path("about.md")

    def test_canonical_source_nested_content_page(self, registry):
        """canonical_source returns relative path for nested content pages."""
        page = MagicMock()
        page.source_path = Path("/project/content/docs/guide/intro.md")
        page.metadata = {}

        result = registry.canonical_source(page)

        assert result == Path("docs/guide/intro.md")

    def test_canonical_source_generated_page(self, registry):
        """canonical_source returns prefixed path for generated pages."""
        page = MagicMock()
        page.source_path = Path("/project/.bengal/generated/tags/python/index.md")
        page.metadata = {"_generated": True}

        result = registry.canonical_source(page)

        assert result == Path("generated/tags/python/index.md")

    def test_canonical_source_autodoc_page(self, registry):
        """canonical_source returns prefixed path for autodoc pages."""
        page = MagicMock()
        page.source_path = Path("/project/src/mypackage/core.py")
        page.metadata = {"is_autodoc": True}

        result = registry.canonical_source(page)

        assert result == Path("autodoc/src/mypackage/core.py")

    def test_cache_key(self, registry):
        """cache_key returns string version of canonical_source."""
        page = MagicMock()
        page.source_path = Path("/project/content/about.md")
        page.metadata = {}

        result = registry.cache_key(page)

        assert result == "about.md"

    def test_is_generated_true_for_generated_path(self, registry):
        """is_generated returns True for generated paths."""
        path = Path("/project/.bengal/generated/tags/python/index.md")

        assert registry.is_generated(path) is True

    def test_is_generated_false_for_content_path(self, registry):
        """is_generated returns False for content paths."""
        path = Path("/project/content/about.md")

        assert registry.is_generated(path) is False

    def test_is_generated_for_shorthand_path(self, registry):
        """is_generated handles shorthand .bengal/generated paths."""
        path = Path(".bengal/generated/tags/python/index.md")

        assert registry.is_generated(path) is True

    def test_virtual_path_for_taxonomy(self, registry):
        """virtual_path_for_taxonomy returns correct path."""
        result = registry.virtual_path_for_taxonomy("tags", "python")

        assert result == Path("/project/.bengal/generated/tags/python/index.md")

    def test_output_path_with_trailing_slash(self, registry):
        """output_path handles URLs with trailing slash."""
        page = MagicMock()
        page.url = "/about/"

        result = registry.output_path(page)

        assert result == Path("/project/public/about/index.html")

    def test_output_path_without_trailing_slash(self, registry):
        """output_path handles URLs without trailing slash."""
        page = MagicMock()
        page.url = "/about"

        result = registry.output_path(page)

        assert result == Path("/project/public/about/index.html")

    def test_normalize_string_path(self, registry):
        """normalize handles string paths."""
        result = registry.normalize("content/about.md")

        # Should resolve to absolute path
        assert result.is_absolute()

    def test_normalize_path_object(self, registry):
        """normalize handles Path objects."""
        result = registry.normalize(Path("content/about.md"))

        # Should resolve to absolute path
        assert result.is_absolute()

    def test_repr(self, registry):
        """Registry has useful repr."""
        result = repr(registry)

        assert "PathRegistry" in result
        assert "/project" in result


class TestPathRegistryWithoutPaths:
    """Tests for PathRegistry when site.paths is not available."""

    def test_fallback_paths(self):
        """Registry uses fallback paths when site.paths is missing."""
        site = MagicMock(spec=[])  # No paths attribute
        site.root_path = Path("/project")
        site.output_dir = Path("/project/public")

        # Delete paths to trigger fallback
        del site.paths

        registry = PathRegistry(site)

        # Should fall back to root_path/content
        assert registry._content_dir == Path("/project/content")
        assert registry._generated_dir == Path("/project/.bengal/generated")
