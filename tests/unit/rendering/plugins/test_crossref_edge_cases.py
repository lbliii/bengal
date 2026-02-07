"""
Edge case tests for cross-reference resolution.

These tests verify graceful handling of malformed xref_index entries
and boundary conditions in cross-reference resolution.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from bengal.rendering.plugins.cross_references import CrossReferencePlugin


def make_mock_page(
    title: str = "Test Page",
    href: str = "/test/",
    source_path: str = "content/test.md",
) -> SimpleNamespace:
    """Create a mock page for testing."""
    return SimpleNamespace(
        title=title,
        href=href,
        source_path=source_path,
    )


class TestCrossRefMalformedEntries:
    """Test cross-reference resolution with malformed xref_index entries."""

    def test_anchor_entry_with_one_element(self) -> None:
        """Verify graceful handling of anchor entries with only 1 element."""
        page = make_mock_page()
        xref_index: dict[str, Any] = {
            "by_anchor": {
                "malformed": [(page,)]  # Missing anchor_id - only 1 element
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_target("malformed")

        assert 'class="broken-ref"' in result
        assert "malformed" in result.lower()

    def test_anchor_entry_with_empty_tuple(self) -> None:
        """Verify handling of empty tuple in anchor entries."""
        xref_index: dict[str, Any] = {
            "by_anchor": {
                "empty-tuple": [()]  # Empty tuple
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_target("empty-tuple")

        assert 'class="broken-ref"' in result

    def test_anchor_entry_empty_list(self) -> None:
        """Verify handling of empty anchor entry list."""
        xref_index: dict[str, Any] = {
            "by_anchor": {
                "empty": []  # Empty list
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        # Empty list should fall through to "not found"
        result = plugin._resolve_target("empty")

        assert 'class="broken-ref"' in result
        assert "not found" in result.lower() or "empty" in result.lower()

    def test_heading_with_malformed_anchor_falls_back(self) -> None:
        """Verify heading resolution falls back when anchor is malformed."""
        page = make_mock_page(title="Valid Page", href="/valid/")
        xref_index: dict[str, Any] = {
            "by_anchor": {
                "test-heading": [(page,)]  # Malformed - missing anchor_id
            },
            "by_heading": {
                "test-heading": [(page, "test-heading")]  # Valid fallback
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_heading("#test-heading")

        # Should fall back to by_heading and succeed
        assert "<a href=" in result
        assert "/valid/" in result

    def test_heading_with_no_fallback(self) -> None:
        """Verify heading resolution returns broken ref when both sources fail."""
        page = make_mock_page()
        xref_index: dict[str, Any] = {
            "by_anchor": {
                "broken-heading": [(page,)]  # Malformed
            },
            "by_heading": {},  # No fallback
            "by_path": {},
            "by_id": {},
            "by_slug": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_heading("#broken-heading")

        assert 'class="broken-ref"' in result

    def test_anchor_entry_with_two_elements_valid(self) -> None:
        """Verify 2-element tuples (page, anchor_id) are handled correctly."""
        page = make_mock_page(title="Two Element", href="/two/")
        xref_index: dict[str, Any] = {
            "by_anchor": {
                "two-element": [(page, "two-element")]  # 2 elements - valid legacy format
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_target("two-element")

        assert "<a href=" in result
        assert "/two/#two-element" in result

    def test_anchor_entry_with_three_elements_valid(self) -> None:
        """Verify 3-element tuples (page, anchor_id, version) are handled correctly."""
        page = make_mock_page(title="Three Element", href="/three/")
        xref_index: dict[str, Any] = {
            "by_anchor": {
                "three-element": [(page, "three-element", "v1")]  # 3 elements - full format
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_target("three-element")

        assert "<a href=" in result
        assert "/three/#three-element" in result


class TestCrossRefVersionMatching:
    """Test version-aware cross-reference resolution."""

    def test_prefers_same_version_anchor(self) -> None:
        """Verify same-version anchor is preferred over other versions."""
        page_v1 = make_mock_page(title="V1 Page", href="/v1/page/")
        page_v2 = make_mock_page(title="V2 Page", href="/v2/page/")

        xref_index: dict[str, Any] = {
            "by_anchor": {
                "my-anchor": [
                    (page_v1, "my-anchor", "v1"),
                    (page_v2, "my-anchor", "v2"),
                ]
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)
        plugin.current_version = "v2"

        result = plugin._resolve_target("my-anchor")

        # Should prefer v2
        assert "/v2/page/" in result

    def test_falls_back_to_first_when_no_version_match(self) -> None:
        """Verify falls back to first entry when no version matches."""
        page_v1 = make_mock_page(title="V1 Page", href="/v1/page/")
        page_v2 = make_mock_page(title="V2 Page", href="/v2/page/")

        xref_index: dict[str, Any] = {
            "by_anchor": {
                "my-anchor": [
                    (page_v1, "my-anchor", "v1"),
                    (page_v2, "my-anchor", "v2"),
                ]
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)
        plugin.current_version = "v3"  # No match

        result = plugin._resolve_target("my-anchor")

        # Should fall back to first (v1)
        assert "/v1/page/" in result

    def test_no_version_set_uses_first(self) -> None:
        """Verify uses first entry when current_version is None."""
        page = make_mock_page(title="Page", href="/page/")

        xref_index: dict[str, Any] = {
            "by_anchor": {
                "my-anchor": [
                    (page, "my-anchor", "v1"),
                ]
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)
        plugin.current_version = None

        result = plugin._resolve_target("my-anchor")

        assert "<a href=" in result
        assert "/page/" in result


class TestCrossRefPathResolution:
    """Test path-based cross-reference resolution edge cases."""

    def test_path_with_md_extension(self) -> None:
        """Verify .md extension is stripped from paths."""
        page = make_mock_page(title="Guide", href="/guide/")

        xref_index: dict[str, Any] = {
            "by_path": {
                "docs/guide": page,
            },
            "by_anchor": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_path("docs/guide.md")

        assert "<a href=" in result
        assert "/guide/" in result

    def test_path_with_anchor_fragment(self) -> None:
        """Verify anchor fragments are preserved."""
        page = make_mock_page(title="Guide", href="/guide/")

        xref_index: dict[str, Any] = {
            "by_path": {
                "docs/guide": page,
            },
            "by_anchor": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_path("docs/guide#installation")

        assert "<a href=" in result
        assert "/guide/#installation" in result

    def test_path_not_found_falls_back_to_slug(self) -> None:
        """Verify path resolution falls back to slug lookup."""
        page = make_mock_page(title="Guide", href="/guide/")

        xref_index: dict[str, Any] = {
            "by_path": {},  # Not found by path
            "by_slug": {
                "guide": [page],  # Found by slug
            },
            "by_anchor": {},
            "by_id": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_path("guide")

        assert "<a href=" in result
        assert "/guide/" in result

    def test_path_not_found_returns_broken_ref(self) -> None:
        """Verify broken ref returned when path not found anywhere."""
        xref_index: dict[str, Any] = {
            "by_path": {},
            "by_slug": {},
            "by_anchor": {},
            "by_id": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_path("nonexistent/page")

        assert 'class="broken-ref"' in result
        assert "nonexistent/page" in result


class TestCrossRefCustomText:
    """Test custom link text handling."""

    def test_custom_text_used_for_path(self) -> None:
        """Verify custom text is used instead of page title."""
        page = make_mock_page(title="Full Page Title", href="/page/")

        xref_index: dict[str, Any] = {
            "by_path": {"page": page},
            "by_anchor": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_path("page", text="Custom Text")

        assert "Custom Text" in result
        assert "Full Page Title" not in result

    def test_custom_text_used_for_target(self) -> None:
        """Verify custom text is used for target directive."""
        page = make_mock_page(title="Page", href="/page/")

        xref_index: dict[str, Any] = {
            "by_anchor": {
                "my-target": [(page, "my-target", "v1")],
            },
            "by_path": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_target("my-target", text="Custom Target Text")

        assert "Custom Target Text" in result

    def test_custom_text_used_for_broken_ref(self) -> None:
        """Verify custom text appears in broken ref."""
        xref_index: dict[str, Any] = {
            "by_path": {},
            "by_anchor": {},
            "by_id": {},
            "by_slug": {},
            "by_heading": {},
        }
        plugin = CrossReferencePlugin(xref_index)

        result = plugin._resolve_path("missing", text="Custom Text")

        assert "Custom Text" in result
        assert 'class="broken-ref"' in result
