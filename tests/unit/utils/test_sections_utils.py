"""
Tests for section utility helpers.

Covers:
- resolve_page_section_path() function
- Handling of Section objects vs string paths
- Edge cases (None, missing attributes, proxy errors)
"""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

from bengal.utils.sections import resolve_page_section_path


class TestResolvePageSectionPath:
    """Tests for resolve_page_section_path function."""

    def test_returns_none_for_none_page(self):
        """Returns None when page is None."""
        result = resolve_page_section_path(None)
        assert result is None

    def test_returns_none_when_page_has_no_section(self):
        """Returns None when page has no section attribute."""
        page = MagicMock(spec=[])  # No attributes
        result = resolve_page_section_path(page)
        assert result is None

    def test_returns_none_for_none_section(self):
        """Returns None when page.section is None."""
        page = MagicMock()
        page.section = None

        result = resolve_page_section_path(page)
        assert result is None

    def test_returns_none_for_empty_string_section(self):
        """Returns None when page.section is empty string."""
        page = MagicMock()
        page.section = ""

        result = resolve_page_section_path(page)
        assert result is None

    def test_extracts_path_from_section_object(self):
        """Extracts path from Section-like object with .path attribute."""

        @dataclass
        class MockSection:
            path: Path

        page = MagicMock()
        page.section = MockSection(path=Path("docs/tutorials"))

        result = resolve_page_section_path(page)

        assert result == "docs/tutorials"

    def test_handles_string_section_directly(self):
        """Handles string section values directly."""
        page = MagicMock()
        page.section = "api/reference"

        result = resolve_page_section_path(page)

        assert result == "api/reference"

    def test_handles_path_section_directly(self):
        """Handles Path section values directly."""
        page = MagicMock()
        page.section = Path("guides/getting-started")

        result = resolve_page_section_path(page)

        assert result == "guides/getting-started"

    def test_handles_section_with_string_path(self):
        """Handles Section object where .path is a string."""

        @dataclass
        class StringPathSection:
            path: str

        page = MagicMock()
        page.section = StringPathSection(path="string/path/section")

        result = resolve_page_section_path(page)

        assert result == "string/path/section"

    def test_handles_getattr_exception(self):
        """Handles exception during getattr (proxy edge case)."""

        # Create a class that raises on section access
        class ProxyPage:
            @property
            def section(self):
                raise AttributeError("Proxy error")

        page = ProxyPage()

        result = resolve_page_section_path(page)

        # Should catch exception and return None
        assert result is None

    def test_handles_path_str_conversion_error(self):
        """Handles error during path string conversion via str()."""
        # Test that section values without .path attribute get stringified

        class SectionWithoutPath:
            """Section that doesn't have a .path attribute."""

            def __str__(self):
                return "stringified-section"

        page = MagicMock()
        page.section = SectionWithoutPath()

        result = resolve_page_section_path(page)

        # Should convert to string when no .path attribute
        assert result == "stringified-section"

    def test_stringifies_unknown_section_types(self):
        """Converts unknown section types to string."""

        class CustomSection:
            def __str__(self):
                return "custom/section/path"

        page = MagicMock()
        page.section = CustomSection()

        result = resolve_page_section_path(page)

        assert result == "custom/section/path"

    def test_handles_section_with_none_path(self):
        """Handles Section object where .path is None."""

        @dataclass
        class NonePathSection:
            path: None = None

        page = MagicMock()
        page.section = NonePathSection()

        result = resolve_page_section_path(page)

        # .path is None, so str(None) = "None"
        assert result == "None"


class TestResolvePageSectionPathEdgeCases:
    """Edge case tests for resolve_page_section_path."""

    def test_handles_falsy_section_values(self):
        """Handles various falsy section values."""
        page = MagicMock()

        # Empty list
        page.section = []
        assert resolve_page_section_path(page) is None

        # Empty dict
        page.section = {}
        assert resolve_page_section_path(page) is None

        # Zero
        page.section = 0
        assert resolve_page_section_path(page) is None

        # False
        page.section = False
        assert resolve_page_section_path(page) is None

    def test_handles_numeric_section(self):
        """Handles numeric section values (converts to string)."""
        page = MagicMock()
        page.section = 42

        result = resolve_page_section_path(page)

        assert result == "42"

    def test_preserves_unicode_paths(self):
        """Preserves Unicode in section paths."""
        page = MagicMock()
        page.section = "文档/教程"  # Chinese: docs/tutorials

        result = resolve_page_section_path(page)

        assert result == "文档/教程"

    def test_handles_deeply_nested_section_object(self):
        """Handles Section with nested path object."""

        class NestedPath:
            def __init__(self):
                self.path = Path("nested/path")

        class NestedSection:
            def __init__(self):
                self.path = Path("actual/section/path")

        page = MagicMock()
        page.section = NestedSection()

        result = resolve_page_section_path(page)

        assert result == "actual/section/path"

    def test_handles_relative_and_absolute_paths(self):
        """Handles both relative and absolute paths."""
        page = MagicMock()

        # Relative path
        page.section = Path("relative/path")
        assert resolve_page_section_path(page) == "relative/path"

        # Absolute path
        page.section = Path("/absolute/path")
        result = resolve_page_section_path(page)
        assert "/absolute/path" in result

    def test_handles_windows_style_paths(self):
        """Handles Windows-style path separators."""
        page = MagicMock()
        page.section = "docs\\windows\\path"

        result = resolve_page_section_path(page)

        # Result preserves original path string
        assert "docs" in result


class TestResolvePageSectionPathWithRealMocks:
    """Tests using more realistic mock structures."""

    def test_with_bengal_like_page(self):
        """Test with structure matching Bengal Page object."""

        @dataclass
        class MockSection:
            name: str
            title: str
            path: Path

            def __str__(self):
                return str(self.path)

        @dataclass
        class MockPage:
            title: str
            section: MockSection | None = None

        # Page with section
        section = MockSection(name="tutorials", title="Tutorials", path=Path("tutorials"))
        page = MockPage(title="Getting Started", section=section)

        result = resolve_page_section_path(page)
        assert result == "tutorials"

        # Page without section (root level)
        root_page = MockPage(title="Home", section=None)
        result = resolve_page_section_path(root_page)
        assert result is None

    def test_with_cached_page_proxy(self):
        """Test with cached page proxy that returns string section."""
        # Cached pages may store section as string instead of object
        page = MagicMock()
        page.section = "cached/section/string"

        result = resolve_page_section_path(page)

        assert result == "cached/section/string"

    def test_with_lazy_loaded_page(self):
        """Test with lazy-loaded page that might have deferred section."""

        class LazySection:
            """Section that loads path lazily."""

            def __init__(self, path_str):
                self._path_str = path_str
                self._loaded = False

            @property
            def path(self):
                self._loaded = True
                return Path(self._path_str)

        page = MagicMock()
        page.section = LazySection("lazy/loaded/section")

        result = resolve_page_section_path(page)

        assert result == "lazy/loaded/section"
        assert page.section._loaded is True


class TestResolvePageSectionPathUsagePatterns:
    """Tests for common usage patterns."""

    def test_collecting_sections_from_pages(self):
        """Test collecting unique sections from multiple pages."""

        @dataclass
        class Section:
            path: Path

        pages = [
            MagicMock(section=Section(path=Path("docs"))),
            MagicMock(section=Section(path=Path("tutorials"))),
            MagicMock(section=Section(path=Path("docs"))),  # Duplicate
            MagicMock(section=None),  # No section
        ]

        sections = set()
        for page in pages:
            section_path = resolve_page_section_path(page)
            if section_path:
                sections.add(section_path)

        assert sections == {"docs", "tutorials"}

    def test_filtering_pages_by_section(self):
        """Test filtering pages by section path."""

        @dataclass
        class Section:
            path: Path

        pages = [
            MagicMock(title="Doc 1", section=Section(path=Path("docs"))),
            MagicMock(title="Tutorial 1", section=Section(path=Path("tutorials"))),
            MagicMock(title="Doc 2", section=Section(path=Path("docs"))),
        ]

        docs_pages = [p for p in pages if resolve_page_section_path(p) == "docs"]

        assert len(docs_pages) == 2
        assert all(p.title.startswith("Doc") for p in docs_pages)

    def test_grouping_pages_by_section(self):
        """Test grouping pages by their section."""
        from collections import defaultdict

        @dataclass
        class Section:
            path: Path

        pages = [
            MagicMock(title="A", section=Section(path=Path("alpha"))),
            MagicMock(title="B", section=Section(path=Path("beta"))),
            MagicMock(title="C", section=Section(path=Path("alpha"))),
            MagicMock(title="D", section=None),
        ]

        grouped = defaultdict(list)
        for page in pages:
            section_path = resolve_page_section_path(page) or "_root"
            grouped[section_path].append(page)

        assert len(grouped["alpha"]) == 2
        assert len(grouped["beta"]) == 1
        assert len(grouped["_root"]) == 1
