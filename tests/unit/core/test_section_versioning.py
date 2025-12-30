"""
Tests for version-aware Section methods.

Tests the versioning functionality that filters pages and subsections
by their version attribute for multi-version documentation sites.
"""

from pathlib import Path

from bengal.core.page import Page
from bengal.core.section import Section


def make_page(
    tmp_path: Path,
    name: str,
    version: str | None = None,
    title: str | None = None,
    weight: int | None = None,
) -> Page:
    """Helper to create a test page with optional version."""
    metadata: dict = {"title": title or name.title()}
    if version is not None:
        metadata["version"] = version
    if weight is not None:
        metadata["weight"] = weight
    return Page(
        source_path=tmp_path / f"{name}.md",
        _raw_content=f"Content for {name}",
        metadata=metadata,
    )


class TestPagesForVersion:
    """Test Section.pages_for_version() method."""

    def test_returns_all_pages_when_version_is_none(self, tmp_path):
        """pages_for_version(None) returns all sorted pages."""
        section = Section(name="docs", path=tmp_path / "docs")
        page1 = make_page(tmp_path, "page1", version="v1")
        page2 = make_page(tmp_path, "page2", version="v2")
        page3 = make_page(tmp_path, "page3")  # No version
        section.pages = [page1, page2, page3]

        result = section.pages_for_version(None)

        assert len(result) == 3
        assert result == section.sorted_pages

    def test_filters_pages_by_version(self, tmp_path):
        """pages_for_version filters to matching version only."""
        section = Section(name="docs", path=tmp_path / "docs")
        page_v1_a = make_page(tmp_path, "page1", version="v1", weight=1)
        page_v1_b = make_page(tmp_path, "page2", version="v1", weight=2)
        page_v2 = make_page(tmp_path, "page3", version="v2")
        section.pages = [page_v1_a, page_v1_b, page_v2]

        result = section.pages_for_version("v1")

        assert len(result) == 2
        assert all(p.version == "v1" for p in result)
        assert page_v1_a in result
        assert page_v1_b in result

    def test_returns_empty_for_nonexistent_version(self, tmp_path):
        """pages_for_version returns empty list for version with no pages."""
        section = Section(name="docs", path=tmp_path / "docs")
        page = make_page(tmp_path, "page1", version="v1")
        section.pages = [page]

        result = section.pages_for_version("v999")

        assert result == []

    def test_pages_without_version_not_matched(self, tmp_path):
        """Pages without version attribute are not matched."""
        section = Section(name="docs", path=tmp_path / "docs")
        page_v1 = make_page(tmp_path, "page1", version="v1")
        page_no_version = make_page(tmp_path, "page2")  # No version
        section.pages = [page_v1, page_no_version]

        result = section.pages_for_version("v1")

        assert len(result) == 1
        assert result[0] == page_v1

    def test_preserves_weight_order(self, tmp_path):
        """Filtered pages maintain weight-based sort order."""
        section = Section(name="docs", path=tmp_path / "docs")
        page_high_weight = make_page(tmp_path, "page1", version="v1", weight=100)
        page_low_weight = make_page(tmp_path, "page2", version="v1", weight=1)
        page_mid_weight = make_page(tmp_path, "page3", version="v1", weight=50)
        section.pages = [page_high_weight, page_low_weight, page_mid_weight]

        result = section.pages_for_version("v1")

        # Should be sorted by weight: 1, 50, 100
        assert result[0] == page_low_weight
        assert result[1] == page_mid_weight
        assert result[2] == page_high_weight

    def test_empty_section_returns_empty(self, tmp_path):
        """Empty section returns empty list."""
        section = Section(name="docs", path=tmp_path / "docs")

        result = section.pages_for_version("v1")

        assert result == []


class TestSubsectionsForVersion:
    """Test Section.subsections_for_version() method."""

    def test_returns_all_subsections_when_version_is_none(self, tmp_path):
        """subsections_for_version(None) returns all sorted subsections."""
        parent = Section(name="parent", path=tmp_path / "parent")
        child1 = Section(name="child1", path=tmp_path / "parent/child1")
        child2 = Section(name="child2", path=tmp_path / "parent/child2")
        parent.subsections = [child1, child2]

        result = parent.subsections_for_version(None)

        assert len(result) == 2
        assert result == parent.sorted_subsections

    def test_filters_by_index_page_version(self, tmp_path):
        """Subsection included if its index page matches version."""
        parent = Section(name="parent", path=tmp_path / "parent")

        child_v1 = Section(name="child_v1", path=tmp_path / "parent/child_v1")
        child_v1.index_page = make_page(tmp_path, "_index_v1", version="v1")

        child_v2 = Section(name="child_v2", path=tmp_path / "parent/child_v2")
        child_v2.index_page = make_page(tmp_path, "_index_v2", version="v2")

        parent.subsections = [child_v1, child_v2]

        result = parent.subsections_for_version("v1")

        assert len(result) == 1
        assert result[0] == child_v1

    def test_filters_by_page_content_version(self, tmp_path):
        """Subsection included if any of its pages match version."""
        parent = Section(name="parent", path=tmp_path / "parent")

        child_v1 = Section(name="child_v1", path=tmp_path / "parent/child_v1")
        child_v1.pages = [make_page(tmp_path, "page_v1", version="v1")]

        child_v2 = Section(name="child_v2", path=tmp_path / "parent/child_v2")
        child_v2.pages = [make_page(tmp_path, "page_v2", version="v2")]

        parent.subsections = [child_v1, child_v2]

        result = parent.subsections_for_version("v1")

        assert len(result) == 1
        assert result[0] == child_v1

    def test_index_page_takes_precedence(self, tmp_path):
        """Index page version check runs first (optimization)."""
        parent = Section(name="parent", path=tmp_path / "parent")

        child = Section(name="child", path=tmp_path / "parent/child")
        child.index_page = make_page(tmp_path, "_index", version="v1")
        # Even though pages have v2, index page v1 should match
        child.pages = [make_page(tmp_path, "page", version="v2")]

        parent.subsections = [child]

        result = parent.subsections_for_version("v1")

        assert len(result) == 1
        assert result[0] == child

    def test_empty_subsections_returns_empty(self, tmp_path):
        """Parent with no subsections returns empty list."""
        parent = Section(name="parent", path=tmp_path / "parent")

        result = parent.subsections_for_version("v1")

        assert result == []

    def test_preserves_weight_order(self, tmp_path):
        """Filtered subsections maintain weight-based sort order."""
        parent = Section(name="parent", path=tmp_path / "parent")

        child_high = Section(name="z_child", path=tmp_path / "parent/z_child")
        child_high.metadata = {"weight": 100}
        child_high.pages = [make_page(tmp_path, "page1", version="v1")]

        child_low = Section(name="a_child", path=tmp_path / "parent/a_child")
        child_low.metadata = {"weight": 1}
        child_low.pages = [make_page(tmp_path, "page2", version="v1")]

        parent.subsections = [child_high, child_low]

        result = parent.subsections_for_version("v1")

        # Should be sorted by weight: 1, 100
        assert result[0] == child_low
        assert result[1] == child_high


class TestHasContentForVersion:
    """Test Section.has_content_for_version() method."""

    def test_returns_true_when_version_is_none(self, tmp_path):
        """has_content_for_version(None) always returns True."""
        section = Section(name="docs", path=tmp_path / "docs")

        assert section.has_content_for_version(None) is True

    def test_returns_true_when_index_page_matches(self, tmp_path):
        """Returns True if index page version matches."""
        section = Section(name="docs", path=tmp_path / "docs")
        section.index_page = make_page(tmp_path, "_index", version="v1")

        assert section.has_content_for_version("v1") is True
        assert section.has_content_for_version("v2") is False

    def test_returns_true_when_any_page_matches(self, tmp_path):
        """Returns True if any regular page version matches."""
        section = Section(name="docs", path=tmp_path / "docs")
        section.pages = [
            make_page(tmp_path, "page1", version="v2"),
            make_page(tmp_path, "page2", version="v1"),
        ]

        assert section.has_content_for_version("v1") is True
        assert section.has_content_for_version("v2") is True
        assert section.has_content_for_version("v3") is False

    def test_returns_false_when_no_content_matches(self, tmp_path):
        """Returns False when no pages match the version."""
        section = Section(name="docs", path=tmp_path / "docs")
        section.pages = [make_page(tmp_path, "page1", version="v1")]

        assert section.has_content_for_version("v999") is False

    def test_returns_false_for_empty_section(self, tmp_path):
        """Returns False for section with no index page or pages."""
        section = Section(name="docs", path=tmp_path / "docs")

        assert section.has_content_for_version("v1") is False

    def test_short_circuits_on_index_page_match(self, tmp_path):
        """Optimization: returns early if index page matches."""
        section = Section(name="docs", path=tmp_path / "docs")
        section.index_page = make_page(tmp_path, "_index", version="v1")
        # Even with many pages, should return quickly from index check
        section.pages = [make_page(tmp_path, f"page{i}", version="v2") for i in range(100)]

        # This should be fast due to short-circuit
        assert section.has_content_for_version("v1") is True

    def test_recursively_checks_subsections(self, tmp_path):
        """Returns True if any subsection recursively has content for version.

        This is critical for versioned docs where the version container section
        (e.g., 'v1') has no direct pages but its subsections (e.g., 'docs') do.
        """
        # Structure: v1/ -> docs/ -> page.md (version="v1")
        v1_section = Section(name="v1", path=tmp_path / "v1")
        # v1 has no direct pages
        v1_section.pages = []

        docs_section = Section(name="docs", path=tmp_path / "v1/docs")
        docs_section.pages = [make_page(tmp_path, "guide", version="v1")]

        v1_section.subsections = [docs_section]

        # v1 should report having content for v1 because docs subsection has v1 pages
        assert v1_section.has_content_for_version("v1") is True
        assert v1_section.has_content_for_version("v2") is False

    def test_deeply_nested_subsection_content(self, tmp_path):
        """Recursion works through multiple levels of nesting."""
        # Structure: root/ -> level1/ -> level2/ -> page.md (version="v1")
        root = Section(name="root", path=tmp_path / "root")
        level1 = Section(name="level1", path=tmp_path / "root/level1")
        level2 = Section(name="level2", path=tmp_path / "root/level1/level2")

        level2.pages = [make_page(tmp_path, "deep_page", version="v1")]
        level1.subsections = [level2]
        root.subsections = [level1]

        # All levels should report having content for v1
        assert level2.has_content_for_version("v1") is True
        assert level1.has_content_for_version("v1") is True
        assert root.has_content_for_version("v1") is True

        # None should have content for v2
        assert root.has_content_for_version("v2") is False


class TestVersionFilteringIntegration:
    """Integration tests for version filtering across nested sections."""

    def test_nested_section_filtering(self, tmp_path):
        """Version filtering works correctly for nested sections."""
        # Create nested structure:
        # docs/
        #   getting-started/  (v1 content)
        #   advanced/         (v2 content)
        #   common/           (both v1 and v2 content)

        root = Section(name="docs", path=tmp_path / "docs")

        getting_started = Section(name="getting-started", path=tmp_path / "docs/getting-started")
        getting_started.pages = [make_page(tmp_path, "install", version="v1")]

        advanced = Section(name="advanced", path=tmp_path / "docs/advanced")
        advanced.pages = [make_page(tmp_path, "performance", version="v2")]

        common = Section(name="common", path=tmp_path / "docs/common")
        common.pages = [
            make_page(tmp_path, "faq_v1", version="v1"),
            make_page(tmp_path, "faq_v2", version="v2"),
        ]

        root.subsections = [getting_started, advanced, common]

        # v1 should include getting-started and common
        v1_sections = root.subsections_for_version("v1")
        assert len(v1_sections) == 2
        assert getting_started in v1_sections
        assert common in v1_sections

        # v2 should include advanced and common
        v2_sections = root.subsections_for_version("v2")
        assert len(v2_sections) == 2
        assert advanced in v2_sections
        assert common in v2_sections
