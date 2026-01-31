"""Tests for cascading frontmatter functionality.

These tests verify the CascadeSnapshot/CascadeView architecture where:
- CascadeSnapshot: Built from _index.md files, stores cascade data per section
- CascadeView: Provides dict-like access combining frontmatter with cascade resolution
- Frontmatter values always take precedence over cascade values
"""

from pathlib import Path

import pytest

from bengal.core.cascade import CascadeView
from bengal.core.cascade_snapshot import CascadeSnapshot
from bengal.core.page import Page
from bengal.core.section import Section


class TestSectionCascadeExtraction:
    """Test that sections extract cascade metadata from their index pages."""

    def test_extract_cascade_from_index_page(self):
        """Test that cascade metadata is available from index page."""
        section = Section(name="products", path=Path("/content/products"))

        # Create index page with cascade
        index_page = Page(
            source_path=Path("/content/products/_index.md"),
            _raw_metadata={
                "title": "Products",
                "cascade": {"type": "product", "version": "2.0"},
            },
        )

        section.add_page(index_page)

        # Index page should be set and cascade available in its metadata
        assert section.index_page == index_page
        assert index_page.metadata.get("cascade") == {"type": "product", "version": "2.0"}

    def test_no_cascade_in_index_page(self):
        """Test that sections work fine without cascade."""
        section = Section(name="blog", path=Path("/content/blog"))

        index_page = Page(
            source_path=Path("/content/blog/_index.md"),
            _raw_metadata={"title": "Blog"},
        )

        section.add_page(index_page)

        # Should not have cascade
        assert index_page.metadata.get("cascade") is None
        assert section.index_page == index_page

    def test_regular_page_does_not_become_index(self):
        """Test that regular pages don't become section index."""
        section = Section(name="blog", path=Path("/content/blog"))

        regular_page = Page(
            source_path=Path("/content/blog/post.md"),
            _raw_metadata={
                "title": "Post",
                "cascade": {"type": "post"},  # Regular pages can have cascade in frontmatter
            },
        )

        section.add_page(regular_page)

        # Regular page should not become index_page
        assert section.index_page is None


class TestCascadeSnapshotBasics:
    """Test CascadeSnapshot creation and resolution."""

    def test_cascade_snapshot_from_data(self):
        """Test creating snapshot from raw cascade data."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "layout": "sidebar"}},
            content_dir="/site/content",
        )

        assert snapshot.resolve("docs", "type") == "doc"
        assert snapshot.resolve("docs", "layout") == "sidebar"

    def test_cascade_snapshot_inheritance(self):
        """Test that child sections inherit from parent cascade."""
        snapshot = CascadeSnapshot.from_data(
            {
                "docs": {"type": "doc"},
                "docs/guide": {"layout": "tutorial"},
            },
            content_dir="/site/content",
        )

        # Child inherits type from parent
        assert snapshot.resolve("docs/guide", "type") == "doc"
        # Child has its own layout
        assert snapshot.resolve("docs/guide", "layout") == "tutorial"

    def test_cascade_snapshot_override(self):
        """Test that child cascade overrides parent cascade."""
        snapshot = CascadeSnapshot.from_data(
            {
                "docs": {"type": "doc", "version": "1.0"},
                "docs/v2": {"version": "2.0"},  # Override version
            },
            content_dir="/site/content",
        )

        # Child keeps parent type but overrides version
        assert snapshot.resolve("docs/v2", "type") == "doc"
        assert snapshot.resolve("docs/v2", "version") == "2.0"


class TestCascadeViewBasics:
    """Test CascadeView combining frontmatter with cascade."""

    def test_frontmatter_only(self):
        """Test view with only frontmatter, no cascade."""
        snapshot = CascadeSnapshot.empty()
        view = CascadeView.for_page(
            frontmatter={"title": "My Page", "type": "landing"},
            section_path="",
            snapshot=snapshot,
        )

        assert view.get("title") == "My Page"
        assert view.get("type") == "landing"
        assert view.get("missing") is None

    def test_cascade_only(self):
        """Test view where values come entirely from cascade."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "layout": "sidebar"}},
            content_dir="/site/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Guide"},  # No type or layout
            section_path="docs",
            snapshot=snapshot,
        )

        assert view.get("title") == "Guide"  # From frontmatter
        assert view.get("type") == "doc"  # From cascade
        assert view.get("layout") == "sidebar"  # From cascade

    def test_frontmatter_overrides_cascade(self):
        """Test that frontmatter takes precedence over cascade."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "author": "Default Author"}},
            content_dir="/site/content",
        )
        view = CascadeView.for_page(
            frontmatter={"title": "Guide", "author": "John Doe"},  # Override author
            section_path="docs",
            snapshot=snapshot,
        )

        assert view.get("type") == "doc"  # From cascade
        assert view.get("author") == "John Doe"  # From frontmatter (override)


class TestBasicCascade:
    """Test basic cascade application to pages."""

    def test_cascade_applies_to_child_pages(self):
        """Test that cascade metadata is resolved for child pages."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "documentation", "version": "1.0"}},
            content_dir="/site/content",
        )

        # Create pages without explicit type/version
        page1_view = CascadeView.for_page(
            frontmatter={"title": "Introduction"},
            section_path="docs",
            snapshot=snapshot,
        )
        page2_view = CascadeView.for_page(
            frontmatter={"title": "Guide"},
            section_path="docs",
            snapshot=snapshot,
        )

        # Both pages should resolve cascade values
        assert page1_view.get("type") == "documentation"
        assert page1_view.get("version") == "1.0"
        assert page2_view.get("type") == "documentation"
        assert page2_view.get("version") == "1.0"

        # Original metadata preserved
        assert page1_view.get("title") == "Introduction"
        assert page2_view.get("title") == "Guide"

    def test_page_metadata_overrides_cascade(self):
        """Test that page's own metadata takes precedence over cascade."""
        snapshot = CascadeSnapshot.from_data(
            {"blog": {"type": "post", "author": "Default Author"}},
            content_dir="/site/content",
        )

        # Page with one override
        view = CascadeView.for_page(
            frontmatter={"title": "My Post", "author": "John Doe"},  # Override cascade
            section_path="blog",
            snapshot=snapshot,
        )

        # Type comes from cascade, author from frontmatter
        assert view.get("type") == "post"
        assert view.get("author") == "John Doe"  # Not 'Default Author'

    def test_empty_cascade_does_nothing(self):
        """Test that empty cascade metadata doesn't add values."""
        snapshot = CascadeSnapshot.from_data(
            {"pages": {}},  # Empty cascade
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "About"},
            section_path="pages",
            snapshot=snapshot,
        )

        # Only frontmatter value, no cascade values
        assert view.get("title") == "About"
        assert view.get("type") is None


class TestNestedCascade:
    """Test cascade accumulation through section hierarchy."""

    def test_nested_cascade_accumulation(self):
        """Test that cascades accumulate from parent to child sections."""
        snapshot = CascadeSnapshot.from_data(
            {
                "api": {"type": "api-doc", "api_base": "https://api.example.com"},
                "api/v2": {"version": "2.0", "stable": True},
            },
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Authentication"},
            section_path="api/v2",
            snapshot=snapshot,
        )

        # Should have values from both parent and child cascades
        assert view.get("type") == "api-doc"  # from parent
        assert view.get("api_base") == "https://api.example.com"  # from parent
        assert view.get("version") == "2.0"  # from child
        assert view.get("stable") is True  # from child

    def test_child_cascade_overrides_parent(self):
        """Test that child section cascade can override parent cascade."""
        snapshot = CascadeSnapshot.from_data(
            {
                "docs": {"version": "1.0", "status": "draft"},
                "docs/stable": {"version": "2.0", "status": "stable"},  # Override both
            },
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Guide"},
            section_path="docs/stable",
            snapshot=snapshot,
        )

        # Child cascade values win
        assert view.get("version") == "2.0"
        assert view.get("status") == "stable"

    def test_three_level_cascade(self):
        """Test cascade through three levels of sections."""
        snapshot = CascadeSnapshot.from_data(
            {
                "products": {"product_line": "current"},
                "products/widgets": {"category": "widget", "warranty": "1-year"},
                "products/widgets/v3": {"version": "3.0", "warranty": "2-year"},  # Override warranty
            },
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Specifications"},
            section_path="products/widgets/v3",
            snapshot=snapshot,
        )

        # Should accumulate all three levels
        assert view.get("product_line") == "current"  # from root
        assert view.get("category") == "widget"  # from category
        assert view.get("version") == "3.0"  # from version
        assert view.get("warranty") == "2-year"  # from version (overrides category)


class TestFlatSectionListCascade:
    """Test cascade with flat section lists.

    CascadeSnapshot.from_data handles path ordering automatically, so cascade
    inheritance works correctly regardless of the order sections are defined.
    """

    def test_flat_list_child_before_parent_ordering(self):
        """Test cascade works when child sections defined before parents.

        from_data processes paths by depth, so parent cascade is always
        available when computing child cascade, regardless of definition order.
        """
        # Define child BEFORE parent in the dict
        snapshot = CascadeSnapshot.from_data(
            {
                "docs/guides": {},  # Child first, no cascade
                "docs": {"type": "doc", "layout": "docs-layout"},  # Parent second
            },
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Introduction"},
            section_path="docs/guides",
            snapshot=snapshot,
        )

        # Page MUST have parent's cascade even though child was listed first
        assert view.get("type") == "doc"
        assert view.get("layout") == "docs-layout"

    def test_deeply_nested_flat_list_random_order(self):
        """Test cascade with deeply nested sections in random order."""
        # Create 4-level hierarchy in shuffled order
        snapshot = CascadeSnapshot.from_data(
            {
                "root/level1/level2/level3": {},  # Deepest first
                "root/level1": {"from_level1": True, "depth": 1},
                "root": {"from_root": True, "depth": 0},
                "root/level1/level2": {"from_level2": True, "depth": 2},
            },
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Deep Page"},
            section_path="root/level1/level2/level3",
            snapshot=snapshot,
        )

        # All parent cascades should be inherited
        assert view.get("from_root") is True
        assert view.get("from_level1") is True
        assert view.get("from_level2") is True
        assert view.get("depth") == 2  # Most recent override wins

    def test_multiple_root_sections_flat_list(self):
        """Test cascade with multiple independent root sections."""
        snapshot = CascadeSnapshot.from_data(
            {
                "docs": {"type": "doc"},
                "blog": {"type": "post"},
                "api": {"type": "api-ref"},
            },
            content_dir="/site/content",
        )

        docs_view = CascadeView.for_page({"title": "Guide"}, "docs", snapshot)
        blog_view = CascadeView.for_page({"title": "Post"}, "blog", snapshot)
        api_view = CascadeView.for_page({"title": "Endpoint"}, "api", snapshot)

        # Each section should have its own cascade
        assert docs_view.get("type") == "doc"
        assert blog_view.get("type") == "post"
        assert api_view.get("type") == "api-ref"


class TestRootLevelCascade:
    """Test root-level cascade affecting all sections."""

    def test_root_cascade_to_nested_sections(self):
        """Test that root cascade applies to nested sections."""
        # Root cascade with empty path ""
        snapshot = CascadeSnapshot.from_data(
            {
                "": {"site_name": "My Site", "lang": "en"},
                "docs": {"type": "doc"},
            },
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Guide"},
            section_path="docs",
            snapshot=snapshot,
        )

        # Should have both root and docs cascade
        assert view.get("site_name") == "My Site"
        assert view.get("lang") == "en"
        assert view.get("type") == "doc"

    def test_root_cascade_with_section_override(self):
        """Test section overriding root cascade values."""
        snapshot = CascadeSnapshot.from_data(
            {
                "": {"lang": "en", "theme": "default"},
                "es": {"lang": "es"},  # Override lang for Spanish section
            },
            content_dir="/site/content",
        )

        en_view = CascadeView.for_page({"title": "English"}, "docs", snapshot)
        es_view = CascadeView.for_page({"title": "Spanish"}, "es", snapshot)

        # English section uses root cascade
        assert en_view.get("lang") == "en"
        assert en_view.get("theme") == "default"

        # Spanish section overrides lang but keeps theme
        assert es_view.get("lang") == "es"
        assert es_view.get("theme") == "default"

    def test_root_cascade_to_multiple_sections(self):
        """Test root cascade applies to all sections."""
        snapshot = CascadeSnapshot.from_data(
            {
                "": {"copyright": "2025 Company"},
                "docs": {"type": "doc"},
                "blog": {"type": "post"},
            },
            content_dir="/site/content",
        )

        docs_view = CascadeView.for_page({"title": "Guide"}, "docs", snapshot)
        blog_view = CascadeView.for_page({"title": "Post"}, "blog", snapshot)

        # Both should have root cascade
        assert docs_view.get("copyright") == "2025 Company"
        assert blog_view.get("copyright") == "2025 Company"

        # And their own cascade
        assert docs_view.get("type") == "doc"
        assert blog_view.get("type") == "post"


class TestOrphanedSectionCascade:
    """Test cascade with orphaned sections (no direct parent defined)."""

    def test_orphaned_section_inherits_nothing_from_missing_parent(self):
        """Test that orphaned sections don't inherit from undefined parents."""
        # Only define "api/v2", not "api"
        snapshot = CascadeSnapshot.from_data(
            {"api/v2": {"version": "2.0"}},
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Endpoint"},
            section_path="api/v2",
            snapshot=snapshot,
        )

        # Should only have the section's own cascade
        assert view.get("version") == "2.0"
        # No inherited values from non-existent "api" parent
        assert view.get("type") is None

    def test_mixed_root_and_orphaned_sections(self):
        """Test cascade with mix of rooted and orphaned sections."""
        snapshot = CascadeSnapshot.from_data(
            {
                "docs": {"type": "doc"},
                "docs/guide": {"layout": "tutorial"},  # Has parent
                "api/v2": {"version": "2.0"},  # Orphaned (no "api" defined)
            },
            content_dir="/site/content",
        )

        # docs/guide should inherit from docs
        docs_view = CascadeView.for_page({"title": "Guide"}, "docs/guide", snapshot)
        assert docs_view.get("type") == "doc"
        assert docs_view.get("layout") == "tutorial"

        # api/v2 should only have its own cascade
        api_view = CascadeView.for_page({"title": "Endpoint"}, "api/v2", snapshot)
        assert api_view.get("version") == "2.0"
        assert api_view.get("type") is None

    def test_multiple_orphaned_sections_with_cascade(self):
        """Test multiple orphaned sections each with their own cascade."""
        snapshot = CascadeSnapshot.from_data(
            {
                "a/b/c": {"depth": 3},
                "x/y": {"area": "xy"},
                "foo": {"name": "foo"},
            },
            content_dir="/site/content",
        )

        abc_view = CascadeView.for_page({}, "a/b/c", snapshot)
        xy_view = CascadeView.for_page({}, "x/y", snapshot)
        foo_view = CascadeView.for_page({}, "foo", snapshot)

        # Each orphan has only its own cascade
        assert abc_view.get("depth") == 3
        assert abc_view.get("area") is None

        assert xy_view.get("area") == "xy"
        assert xy_view.get("depth") is None

        assert foo_view.get("name") == "foo"


class TestCascadeEdgeCases:
    """Test edge cases in cascade behavior."""

    def test_cascade_does_not_affect_index_page(self):
        """Test that cascade doesn't apply to the defining index page.

        The _index.md file that defines a cascade should NOT have that
        cascade applied to itself - it's for child pages only.
        """
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "layout": "sidebar"}},
            content_dir="/site/content",
        )

        # Index page itself - cascade should NOT apply
        # (In practice, index pages are in their own section path)
        index_view = CascadeView.for_page(
            frontmatter={"title": "Documentation", "cascade": {"type": "doc", "layout": "sidebar"}},
            section_path="",  # Index page is at root of its section, not a child
            snapshot=snapshot,
        )

        # The cascade block is stored in frontmatter, but type/layout are not
        # automatically applied to the index page itself
        assert index_view.get("cascade") == {"type": "doc", "layout": "sidebar"}
        # type would only resolve if the index page's section has cascade
        # With section_path="", there's no cascade for root level
        assert index_view.get("type") is None

    def test_cascade_with_complex_values(self):
        """Test cascade with non-scalar values (lists, dicts)."""
        snapshot = CascadeSnapshot.from_data(
            {
                "docs": {
                    "tags": ["documentation", "guide"],
                    "meta": {"author": "Team", "version": "1.0"},
                }
            },
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Guide"},
            section_path="docs",
            snapshot=snapshot,
        )

        # Complex values should be preserved
        assert view.get("tags") == ["documentation", "guide"]
        assert view.get("meta") == {"author": "Team", "version": "1.0"}

    def test_cascade_keys_tracking(self):
        """Test that CascadeView tracks which keys came from cascade."""
        snapshot = CascadeSnapshot.from_data(
            {"docs": {"type": "doc", "version": "1.0"}},
            content_dir="/site/content",
        )

        view = CascadeView.for_page(
            frontmatter={"title": "Guide", "type": "landing"},  # Override type
            section_path="docs",
            snapshot=snapshot,
        )

        # Only version should be marked as from cascade (type is overridden)
        cascade_keys = view.cascade_keys()
        assert "version" in cascade_keys
        assert "type" not in cascade_keys  # Overridden by frontmatter

        frontmatter_keys = view.frontmatter_keys()
        assert "title" in frontmatter_keys
        assert "type" in frontmatter_keys
