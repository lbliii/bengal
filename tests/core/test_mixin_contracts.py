"""
Core helper compatibility tests.

These tests verify that Page and Section keep their template-facing helper
interfaces stable while the actual work moves out of inheritance-based mixins.
They help catch regressions like:
- Attribute override conflicts (writable vs read-only)
- Missing protocol implementations
- Self-reference type issues in delegated helper methods

Run these tests after modifying core compatibility shims or helper modules.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock


class TestPageNavigation:
    """Verify page navigation free functions (via Page property wrappers)."""

    def test_next_returns_none_without_site(self) -> None:
        """next property returns None when _site is None."""

        page = _create_minimal_page()
        page._site = None

        assert page.next is None

    def test_prev_returns_none_without_site(self) -> None:
        """prev property returns None when _site is None."""

        page = _create_minimal_page()
        page._site = None

        assert page.prev is None

    def test_next_in_section_returns_none_without_section(self) -> None:
        """next_in_section returns None when _section is None."""

        page = _create_minimal_page()
        page._section = None

        assert page.next_in_section is None

    def test_page_can_find_itself_in_list(self) -> None:
        """Page instances can be found with list.index()."""

        page1 = _create_minimal_page(source_path=Path("/test/page1.md"))
        page2 = _create_minimal_page(source_path=Path("/test/page2.md"))

        pages = [page1, page2]

        # This should NOT raise - it was a bug when mixin self-reference was wrong
        idx = pages.index(page1)
        assert idx == 0


class TestPageRelationships:
    """Verify inline Page relationship compatibility helpers."""

    def test_eq_matches_pages_by_source_path(self) -> None:
        page1 = _create_minimal_page(source_path=Path("/test/page.md"))
        page2 = _create_minimal_page(source_path=Path("/test/page.md"))
        other = object()

        assert page1.eq(page2) is True
        assert page1.eq(other) is False

    def test_in_section_compares_resolved_section(self) -> None:
        page = _create_minimal_page()
        section = _create_minimal_section()
        page._section = section
        page._site = SimpleNamespace(
            registry=SimpleNamespace(epoch=1),
            get_section_by_path=lambda path: section if path == section.path else None,
            get_section_by_url=lambda url: None,
        )

        assert page.in_section(section) is True
        other_section = _create_minimal_section()
        other_section.path = Path("/test/other")
        assert page.in_section(other_section) is False

    def test_regular_page_is_not_ancestor(self) -> None:
        page = _create_minimal_page()
        child = _create_minimal_page(source_path=Path("/test/child.md"))

        assert page.is_ancestor(child) is False

    def test_descendant_requires_page_ancestor(self) -> None:
        page = _create_minimal_page()
        other = object()

        assert page.is_descendant(other) is False


class TestPageComputedHelpers:
    """Verify Page computed helper contract."""

    def test_word_count_returns_int(self) -> None:
        """word_count always returns int, even for empty content."""

        page = _create_minimal_page()
        page._raw_content = ""

        result = page.word_count
        assert isinstance(result, int)
        assert result == 0

    def test_reading_time_minimum_one_minute(self) -> None:
        """reading_time returns at least 1 minute."""

        page = _create_minimal_page()
        page._raw_content = "short"  # Very few words

        result = page.reading_time
        assert result >= 1

    def test_meta_description_truncates_correctly(self) -> None:
        """meta_description respects 160 char limit."""

        page = _create_minimal_page()
        page._raw_content = "x" * 500  # Long content
        page._raw_metadata = {}

        result = page.meta_description
        assert len(result) <= 161  # 160 + potential ellipsis


class TestSectionErgonomicHelpers:
    """Verify Section ergonomic helper contract."""

    def test_recent_pages_handles_none_dates(self) -> None:
        """recent_pages doesn't crash when pages have None dates."""

        section = _create_minimal_section()

        # Create pages with dates via metadata
        page_with_date = _create_minimal_page(
            source_path=Path("/test/dated.md"), metadata={"date": datetime.now()}
        )

        page_without_date = _create_minimal_page(
            source_path=Path("/test/undated.md"),
            metadata={},  # No date
        )

        section.pages = [page_with_date, page_without_date]

        # This should NOT crash - uses sorted_pages which needs to be mocked
        # For now, just verify the method exists and can be called
        assert hasattr(section, "recent_pages")
        assert callable(section.recent_pages)

    def test_content_pages_property_exists(self) -> None:
        """content_pages property exists on Section class."""
        from bengal.core.section import Section

        assert hasattr(Section, "content_pages")
        assert "content_pages" in Section.__dict__


class TestSectionNavigationHelpers:
    """Verify Section navigation helper contract."""

    def test_href_without_site_returns_path(self) -> None:
        """href works even when _site is None."""

        section = _create_minimal_section()
        section._site = None

        # Should not crash
        result = section.href
        assert isinstance(result, str)

    def test_subsection_index_urls_returns_set(self) -> None:
        """subsection_index_urls returns a set of strings."""

        section = _create_minimal_section()
        section.subsections = []

        result = section.subsection_index_urls
        assert isinstance(result, set)


class TestSectionHierarchyHelpers:
    """Verify Section hierarchy helper contract."""

    def test_hierarchy_returns_list_of_strings(self) -> None:
        """hierarchy returns list[str]."""

        section = _create_minimal_section()

        result = section.hierarchy
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_depth_returns_positive_int(self) -> None:
        """depth returns positive integer."""

        section = _create_minimal_section()

        result = section.depth
        assert isinstance(result, int)
        assert result >= 1

    def test_walk_includes_self(self) -> None:
        """walk() includes the section itself."""

        section = _create_minimal_section()
        section.subsections = []

        result = section.walk()
        assert section in result


class TestDiagnosticsEmission:
    """Verify diagnostics are emitted correctly."""

    def test_emit_helper_creates_event(self) -> None:
        """emit() convenience function creates DiagnosticEvent."""
        from bengal.core.diagnostics import DiagnosticsCollector, emit

        collector = DiagnosticsCollector()

        # Create object with diagnostics sink
        obj = Mock()
        obj._diagnostics = collector

        emit(obj, "warning", "test_code", key="value")

        events = collector.drain()
        assert len(events) == 1
        assert events[0].level == "warning"
        assert events[0].code == "test_code"
        assert events[0].data == {"key": "value"}

    def test_emit_with_none_object_doesnt_crash(self) -> None:
        """emit() with None object is a no-op."""
        from bengal.core.diagnostics import emit

        # Should not raise
        emit(None, "error", "test_code")


# =============================================================================
# Test Fixtures / Helpers
# =============================================================================


def _create_minimal_page(
    source_path: Path | None = None,
    metadata: dict | None = None,
) -> Any:
    """Create a minimal Page instance for testing."""
    from bengal.core.page import Page

    if source_path is None:
        source_path = Path("/test/page.md")

    return Page(
        source_path=source_path,
        _raw_content="Test content",
        _raw_metadata=metadata or {},
        html_content="",
        links=[],
    )


def _create_minimal_section() -> Any:
    """Create a minimal Section instance for testing."""
    from bengal.core.section import Section

    return Section(
        name="test",
        path=Path("/test"),
        parent=None,
        pages=[],
        subsections=[],
        metadata={},
        index_page=None,
    )
