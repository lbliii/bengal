"""Integration tests for cascading frontmatter with full content discovery."""

import pytest
import tempfile
import shutil
from pathlib import Path
from bengal.core.site import Site


class TestCascadeIntegration:
    """Integration tests for cascade with real file system."""
    
    @pytest.fixture
    def temp_site(self):
        """Create a temporary site directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_full_cascade_workflow(self, temp_site):
        """Test complete cascade workflow with file system."""
        # Create content structure
        content_dir = temp_site / "content"
        products_dir = content_dir / "products"
        widgets_dir = products_dir / "widgets"
        
        products_dir.mkdir(parents=True)
        widgets_dir.mkdir()
        
        # Create products/_index.md with cascade
        products_index = products_dir / "_index.md"
        products_index.write_text("""---
title: "Products"
cascade:
  type: product
  show_price: true
  product_line: current
---

# Products

All our products.
""")
        
        # Create widgets/_index.md with additional cascade
        widgets_index = widgets_dir / "_index.md"
        widgets_index.write_text("""---
title: "Widgets"
cascade:
  category: widget
  warranty: 2-year
---

# Widgets

Widget products.
""")
        
        # Create a product page
        widget_page = widgets_dir / "super-widget.md"
        widget_page.write_text("""---
title: "Super Widget"
price: "$99.99"
---

# Super Widget

An amazing widget!
""")
        
        # Create a product page with override
        custom_widget = widgets_dir / "custom-widget.md"
        custom_widget.write_text("""---
title: "Custom Widget"
price: "$149.99"
type: custom-product
---

# Custom Widget

A customizable widget!
""")
        
        # Create site and discover content
        site = Site(root_path=temp_site, config={})
        site.discover_content(content_dir)
        
        # Find the pages
        super_widget = next(p for p in site.pages if 'super-widget' in str(p.source_path))
        custom_widget = next(p for p in site.pages if 'custom-widget' in str(p.source_path))
        
        # Verify cascade applied to super-widget
        assert super_widget.metadata['type'] == 'product'  # from products cascade
        assert super_widget.metadata['show_price'] is True  # from products cascade
        assert super_widget.metadata['product_line'] == 'current'  # from products cascade
        assert super_widget.metadata['category'] == 'widget'  # from widgets cascade
        assert super_widget.metadata['warranty'] == '2-year'  # from widgets cascade
        assert super_widget.metadata['title'] == 'Super Widget'  # own metadata
        assert super_widget.metadata['price'] == '$99.99'  # own metadata
        
        # Verify cascade override in custom-widget
        assert custom_widget.metadata['type'] == 'custom-product'  # overridden
        assert custom_widget.metadata['show_price'] is True  # from cascade
        assert custom_widget.metadata['category'] == 'widget'  # from cascade
    
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
        v1_auth = next(p for p in site.pages if p.metadata.get('title') == 'Authentication v1')
        v2_auth = next(p for p in site.pages if p.metadata.get('title') == 'Authentication v2')
        
        # Verify v1 auth has correct cascade
        assert v1_auth.metadata['type'] == 'api-doc'
        assert v1_auth.metadata['api_base'] == 'https://api.example.com'
        assert v1_auth.metadata['version'] == '1.0'
        assert v1_auth.metadata['deprecated'] is True
        assert 'stable' not in v1_auth.metadata
        
        # Verify v2 auth has correct cascade
        assert v2_auth.metadata['type'] == 'api-doc'
        assert v2_auth.metadata['api_base'] == 'https://api.example.com'
        assert v2_auth.metadata['version'] == '2.0'
        assert v2_auth.metadata['stable'] is True
        assert 'deprecated' not in v2_auth.metadata
    
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
        blog_post = next(p for p in site.pages if p.metadata.get('title') == 'My Post')
        doc_page = next(p for p in site.pages if p.metadata.get('title') == 'Guide')
        
        # Blog post should have cascade
        assert blog_post.metadata['type'] == 'post'
        assert blog_post.metadata['author'] == 'Blog Team'
        
        # Doc page should NOT have blog's cascade
        assert 'type' not in doc_page.metadata
        assert 'author' not in doc_page.metadata
    
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
        empty_section = next(s for s in site.sections if s.name == 'empty')
        
        # Should have cascade metadata
        assert 'cascade' in empty_section.metadata
        assert empty_section.metadata['cascade']['type'] == 'test'

