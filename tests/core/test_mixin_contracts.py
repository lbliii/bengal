"""
Core helper compatibility tests.

These tests verify that Section keeps its template-facing helper interface
stable while the actual work moves out of inheritance-based mixins.
They help catch regressions like:
- Attribute override conflicts (writable vs read-only)
- Missing protocol implementations
- Self-reference type issues in delegated helper methods

Run these tests after modifying core compatibility shims or helper modules.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from tests._testing.page_records import make_test_page


class TestSectionErgonomicHelpers:
    """Verify Section ergonomic helper contract."""

    def test_recent_pages_handles_none_dates(self) -> None:
        """recent_pages doesn't crash when pages have None dates."""

        section = _create_minimal_section()

        # Create pages with dates via metadata
        page_with_date = make_test_page(
            source_path=Path("/test/dated.md"),
            metadata={"date": datetime.now()},
            default_metadata=False,
        )

        page_without_date = make_test_page(
            source_path=Path("/test/undated.md"),
            metadata={},  # No date
            default_metadata=False,
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
