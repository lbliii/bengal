"""Integration tests for cascading frontmatter with full content discovery.

Uses Phase 1 infrastructure: @pytest.mark.bengal with test-cascade root.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site


class TestCascadeIntegration:
    """Integration tests for cascade with real file system."""

    @pytest.fixture
    def temp_site(self):
        """Create a temporary site directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.bengal(testroot="test-cascade")
    def test_full_cascade_workflow(self, site):
        """Test complete cascade workflow with nested sections.

        Uses test-cascade root with products/widgets hierarchy.
        Tests that cascade properties flow from parent sections to child pages.
        """
        # Find the pages
        super_widget = next(p for p in site.pages if "super-widget" in str(p.source_path))
        custom_widget = next(p for p in site.pages if "custom-widget" in str(p.source_path))

        # Verify cascade applied to super-widget
        assert super_widget.metadata["type"] == "product"  # from products cascade
        assert super_widget.metadata["show_price"] is True  # from products cascade
        assert super_widget.metadata["product_line"] == "current"  # from products cascade
        assert super_widget.metadata["category"] == "widget"  # from widgets cascade
        assert super_widget.metadata["warranty"] == "2-year"  # from widgets cascade
        assert super_widget.metadata["title"] == "Super Widget"  # own metadata
        assert super_widget.metadata["price"] == "$99.99"  # own metadata

        # Verify cascade override in custom-widget
        assert custom_widget.metadata["type"] == "custom-product"  # overridden
        assert custom_widget.metadata["show_price"] is True  # from cascade
        assert custom_widget.metadata["category"] == "widget"  # from cascade

    def test_cascade_with_nested_sections(self, temp_site):
        """Test cascade through multiple nested sections."""
        content_dir = temp_site / "content"
        api_dir = content_dir / "api"
        v1_dir = api_dir / "v1"
        v2_dir = api_dir / "v2"

        v1_dir.mkdir(parents=True)
        v2_dir.mkdir(parents=True)

        # Root API section
        (api_dir / "_index.md").write_text("""---
title: "API Documentation"
cascade:
  type: api-doc
  api_base: https://api.example.com
---
""")

        # Version 1
        (v1_dir / "_index.md").write_text("""---
title: "API v1"
cascade:
  version: "1.0"
  deprecated: true
---
""")

        (v1_dir / "auth.md").write_text("""---
title: "Authentication v1"
---
""")

        # Version 2
        (v2_dir / "_index.md").write_text("""---
title: "API v2"
cascade:
  version: "2.0"
  stable: true
---
""")

        (v2_dir / "auth.md").write_text("""---
title: "Authentication v2"
---
""")

        # Create and discover
        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)

        # Find pages
        v1_auth = next(p for p in site.pages if p.metadata.get("title") == "Authentication v1")
        v2_auth = next(p for p in site.pages if p.metadata.get("title") == "Authentication v2")

        # Verify v1 auth has correct cascade
        assert v1_auth.metadata["type"] == "api-doc"
        assert v1_auth.metadata["api_base"] == "https://api.example.com"
        assert v1_auth.metadata["version"] == "1.0"
        assert v1_auth.metadata["deprecated"] is True
        assert "stable" not in v1_auth.metadata

        # Verify v2 auth has correct cascade
        assert v2_auth.metadata["type"] == "api-doc"
        assert v2_auth.metadata["api_base"] == "https://api.example.com"
        assert v2_auth.metadata["version"] == "2.0"
        assert v2_auth.metadata["stable"] is True
        assert "deprecated" not in v2_auth.metadata

    def test_cascade_does_not_affect_other_sections(self, temp_site):
        """Test that cascade only affects pages in the same hierarchy."""
        content_dir = temp_site / "content"
        blog_dir = content_dir / "blog"
        docs_dir = content_dir / "docs"

        blog_dir.mkdir(parents=True)
        docs_dir.mkdir(parents=True)

        # Blog with cascade
        (blog_dir / "_index.md").write_text("""---
title: "Blog"
cascade:
  type: post
  author: Blog Team
---
""")

        (blog_dir / "my-post.md").write_text("""---
title: "My Post"
---
""")

        # Docs without cascade
        (docs_dir / "_index.md").write_text("""---
title: "Documentation"
---
""")

        (docs_dir / "guide.md").write_text("""---
title: "Guide"
---
""")

        # Create and discover
        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)

        # Find pages
        blog_post = next(p for p in site.pages if p.metadata.get("title") == "My Post")
        doc_page = next(p for p in site.pages if p.metadata.get("title") == "Guide")

        # Blog post should have cascade
        assert blog_post.metadata["type"] == "post"
        assert blog_post.metadata["author"] == "Blog Team"

        # Doc page should NOT have blog's cascade
        assert "type" not in doc_page.metadata
        assert "author" not in doc_page.metadata

    def test_empty_sections_with_cascade(self, temp_site):
        """Test cascade with sections that have index but no other pages."""
        content_dir = temp_site / "content"
        empty_dir = content_dir / "empty"

        empty_dir.mkdir(parents=True)

        # Section with cascade but no other pages
        (empty_dir / "_index.md").write_text("""---
title: "Empty Section"
cascade:
  type: test
  value: 123
---
""")

        # Should not error
        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)

        # Find the section
        empty_section = next(s for s in site.sections if s.name == "empty")

        # Should have cascade metadata
        assert "cascade" in empty_section.metadata
        assert empty_section.metadata["cascade"]["type"] == "test"

    def test_deeply_nested_cascade_type_propagation(self, temp_site):
        """Test that type: doc cascades through deeply nested section hierarchy.

        This tests the specific bug where site.sections is a flat list and
        nested sections weren't inheriting cascade from their ancestors.
        Regression test for the cascade engine root-section filtering fix.
        """
        content_dir = temp_site / "content"

        # Create a 3-level deep docs hierarchy: docs -> building -> configuration
        docs_dir = content_dir / "docs"
        building_dir = docs_dir / "building"
        config_dir = building_dir / "configuration"

        config_dir.mkdir(parents=True)

        # Root docs section with cascade type: doc
        (docs_dir / "_index.md").write_text("""---
title: "Documentation"
cascade:
  type: doc
  layout: docs-layout
---
""")

        # Middle section (building) - also has cascade
        (building_dir / "_index.md").write_text("""---
title: "Building"
cascade:
  type: doc
  category: building
---
""")

        # Deepest section (configuration) - no cascade, should inherit
        (config_dir / "_index.md").write_text("""---
title: "Configuration"
description: "How to configure Bengal"
---
""")

        # A page in the deepest section
        (config_dir / "profiles.md").write_text("""---
title: "Build Profiles"
---
""")

        # Create and discover
        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)

        # Find the configuration index and the profiles page
        config_index = next(
            (p for p in site.pages if "configuration/_index" in str(p.source_path)),
            None,
        )
        profiles_page = next(
            (p for p in site.pages if "profiles" in str(p.source_path)),
            None,
        )

        # Both pages must have inherited type: doc from ancestors
        assert config_index is not None, "Configuration index page not found"
        assert profiles_page is not None, "Profiles page not found"

        # Configuration index should have cascade from building (which has type: doc)
        assert config_index.metadata.get("type") == "doc", (
            f"Configuration index missing cascaded type. Got: {config_index.metadata.get('type')}"
        )
        assert config_index.metadata.get("category") == "building"

        # Profiles page should also have cascaded type: doc
        assert profiles_page.metadata.get("type") == "doc", (
            f"Profiles page missing cascaded type. Got: {profiles_page.metadata.get('type')}"
        )
        assert profiles_page.metadata.get("category") == "building"


class TestEagerCascadeMergeDuality:
    """Test that eager cascade merge eliminates the metadata/property duality.

    After the eager cascade merge, page.metadata.get("type") and page.type
    should always return the same value, eliminating a class of bugs where
    code used the wrong access pattern.
    """

    @pytest.fixture
    def temp_site(self):
        """Create a temporary site directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_metadata_get_equals_property_for_cascaded_type(self, temp_site):
        """Test that page.metadata.get("type") == page.type for cascaded values."""
        content_dir = temp_site / "content"
        docs_dir = content_dir / "docs"
        docs_dir.mkdir(parents=True)

        # Section with cascade type
        (docs_dir / "_index.md").write_text("""---
title: "Documentation"
cascade:
  type: doc
  variant: sidebar
---
""")

        # Page that relies on cascade (no explicit type)
        (docs_dir / "guide.md").write_text("""---
title: "User Guide"
---
Content here.
""")

        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)

        guide = next(p for p in site.pages if "guide" in str(p.source_path))

        # CRITICAL: Both access patterns must return the same value
        assert guide.metadata.get("type") == guide.type
        assert guide.metadata.get("type") == "doc"

        # Also verify variant
        assert guide.metadata.get("variant") == guide.variant
        assert guide.metadata.get("variant") == "sidebar"

    def test_metadata_get_equals_property_for_frontmatter_type(self, temp_site):
        """Test that page.metadata.get("type") == page.type for frontmatter values."""
        content_dir = temp_site / "content"
        docs_dir = content_dir / "docs"
        docs_dir.mkdir(parents=True)

        # Section with cascade type
        (docs_dir / "_index.md").write_text("""---
title: "Documentation"
cascade:
  type: doc
---
""")

        # Page with explicit type (overrides cascade)
        (docs_dir / "special.md").write_text("""---
title: "Special Page"
type: custom
---
Content here.
""")

        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)

        special = next(p for p in site.pages if "special" in str(p.source_path))

        # Frontmatter should take precedence over cascade
        assert special.metadata.get("type") == special.type
        assert special.metadata.get("type") == "custom"

    def test_metadata_get_equals_property_nested_sections(self, temp_site):
        """Test duality elimination works through nested section hierarchy."""
        content_dir = temp_site / "content"

        # Create nested structure: docs -> api -> v2
        api_v2_dir = content_dir / "docs" / "api" / "v2"
        api_v2_dir.mkdir(parents=True)

        # Root docs cascade
        (content_dir / "docs" / "_index.md").write_text("""---
title: "Docs"
cascade:
  type: doc
  layout: docs-layout
---
""")

        # API section adds more cascade
        (content_dir / "docs" / "api" / "_index.md").write_text("""---
title: "API"
cascade:
  variant: api-sidebar
---
""")

        # v2 section - no cascade
        (api_v2_dir / "_index.md").write_text("""---
title: "API v2"
---
""")

        # Page in deepest section
        (api_v2_dir / "endpoints.md").write_text("""---
title: "Endpoints"
---
""")

        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)

        endpoints = next(p for p in site.pages if "endpoints" in str(p.source_path))

        # Should inherit type from docs cascade
        assert endpoints.metadata.get("type") == endpoints.type
        assert endpoints.metadata.get("type") == "doc"

        # Should inherit layout from docs cascade
        assert endpoints.metadata.get("layout") == "docs-layout"

        # Should inherit variant from api cascade
        assert endpoints.metadata.get("variant") == endpoints.variant
        assert endpoints.metadata.get("variant") == "api-sidebar"

    def test_cascade_keys_tracking(self, temp_site):
        """Test that _cascade_keys tracks which keys came from cascade."""
        content_dir = temp_site / "content"
        docs_dir = content_dir / "docs"
        docs_dir.mkdir(parents=True)

        (docs_dir / "_index.md").write_text("""---
title: "Docs"
cascade:
  type: doc
  custom_key: cascaded-value
---
""")

        (docs_dir / "page.md").write_text("""---
title: "Page"
author: John
---
""")

        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)

        page = next(p for p in site.pages if "page.md" in str(p.source_path))

        # _cascade_keys should track which keys came from cascade
        cascade_keys = page.metadata.get("_cascade_keys", [])
        assert "type" in cascade_keys
        assert "custom_key" in cascade_keys

        # Frontmatter keys should NOT be in _cascade_keys
        assert "author" not in cascade_keys
        assert "title" not in cascade_keys


class TestCascadeWarmBuild:
    """Test cascade persistence across warm/incremental builds."""

    @pytest.fixture
    def temp_site(self):
        """Create a temporary site directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_cascade_persists_after_unrelated_file_change(self, temp_site):
        """Test that cascade values persist when unrelated files change.

        Simulates a warm build where only some files are modified.
        The cascade values should still be correctly applied.
        """
        content_dir = temp_site / "content"
        docs_dir = content_dir / "docs"
        docs_dir.mkdir(parents=True)

        # Initial content with cascade
        (docs_dir / "_index.md").write_text("""---
title: "Docs"
cascade:
  type: doc
  version: "1.0"
---
""")

        (docs_dir / "page1.md").write_text("""---
title: "Page 1"
---
Content for page 1.
""")

        (docs_dir / "page2.md").write_text("""---
title: "Page 2"
---
Content for page 2.
""")

        # First discovery
        site1 = Site(root_path=temp_site, config={})
        site1.discover_content(content_dir)

        page1_v1 = next(p for p in site1.pages if "page1" in str(p.source_path))
        page2_v1 = next(p for p in site1.pages if "page2" in str(p.source_path))

        # Both pages should have cascade
        assert page1_v1.metadata["type"] == "doc"
        assert page2_v1.metadata["type"] == "doc"

        # Simulate warm build: modify only page2
        (docs_dir / "page2.md").write_text("""---
title: "Page 2 - Updated"
---
Updated content for page 2.
""")

        # Second discovery (simulates warm build re-discovery)
        site2 = Site(root_path=temp_site, config={})
        site2.discover_content(content_dir)

        page1_v2 = next(p for p in site2.pages if "page1" in str(p.source_path))
        page2_v2 = next(p for p in site2.pages if "page2" in str(p.source_path))

        # CRITICAL: Both pages must still have cascade after warm build
        assert page1_v2.metadata["type"] == "doc", "Page 1 lost cascade after warm build"
        assert page2_v2.metadata["type"] == "doc", "Page 2 lost cascade after warm build"
        assert page2_v2.metadata["title"] == "Page 2 - Updated"

    def test_cascade_updates_when_parent_cascade_changes(self, temp_site):
        """Test that child pages get updated cascade when parent cascade changes."""
        content_dir = temp_site / "content"
        docs_dir = content_dir / "docs"
        docs_dir.mkdir(parents=True)

        # Initial cascade
        (docs_dir / "_index.md").write_text("""---
title: "Docs"
cascade:
  type: doc
  version: "1.0"
---
""")

        (docs_dir / "guide.md").write_text("""---
title: "Guide"
---
""")

        # First discovery
        site1 = Site(root_path=temp_site, config={})
        site1.discover_content(content_dir)

        guide_v1 = next(p for p in site1.pages if "guide" in str(p.source_path))
        assert guide_v1.metadata["version"] == "1.0"

        # Update parent cascade
        (docs_dir / "_index.md").write_text("""---
title: "Docs"
cascade:
  type: doc
  version: "2.0"
---
""")

        # Second discovery
        site2 = Site(root_path=temp_site, config={})
        site2.discover_content(content_dir)

        guide_v2 = next(p for p in site2.pages if "guide" in str(p.source_path))

        # Guide should have updated cascade version
        assert guide_v2.metadata["version"] == "2.0"
