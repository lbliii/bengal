"""Tests for navigation functionality including breadcrumbs and section URLs."""

import pytest
from pathlib import Path
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site


class TestSectionURLGeneration:
    """Test section URL generation with various configurations."""
    
    def test_section_url_without_index_page(self):
        """Test section URL when no index page exists."""
        section = Section(name="docs", path=Path("/content/docs"))
        
        # Should construct URL from section name
        assert section.url == "/docs/"
    
    def test_section_url_with_index_page_no_output_path(self):
        """Test section URL when index page exists but has no output_path yet."""
        section = Section(name="docs", path=Path("/content/docs"))
        
        index_page = Page(
            source_path=Path("/content/docs/index.md"),
            metadata={'title': 'Documentation'}
        )
        section.add_page(index_page)
        
        # Should fall back to hierarchy-based URL (not index page's fallback URL)
        assert section.url == "/docs/"
    
    def test_section_url_with_index_page_with_output_path(self):
        """Test section URL when index page has output_path set."""
        site = Site(root_path=Path("/site"), config={})
        site.output_dir = Path("/site/public")
        
        section = Section(name="docs", path=Path("/content/docs"))
        section._site = site
        
        index_page = Page(
            source_path=Path("/content/docs/index.md"),
            metadata={'title': 'Documentation'},
            output_path=Path("/site/public/docs/index.html")
        )
        index_page._site = site
        section.add_page(index_page)
        
        # Should use index page's properly computed URL
        assert section.url == "/docs/"
    
    def test_nested_section_url_hierarchy(self):
        """Test URL generation for nested sections using hierarchy."""
        parent = Section(name="api", path=Path("/content/api"))
        child = Section(name="v2", path=Path("/content/api/v2"))
        
        parent.add_subsection(child)
        
        # Parent URL
        assert parent.url == "/api/"
        
        # Child should construct from parent's URL
        assert child.url == "/api/v2/"
    
    def test_deeply_nested_section_url(self):
        """Test URL generation for deeply nested sections."""
        level1 = Section(name="docs", path=Path("/content/docs"))
        level2 = Section(name="guides", path=Path("/content/docs/guides"))
        level3 = Section(name="advanced", path=Path("/content/docs/guides/advanced"))
        
        level1.add_subsection(level2)
        level2.add_subsection(level3)
        
        assert level1.url == "/docs/"
        assert level2.url == "/docs/guides/"
        assert level3.url == "/docs/guides/advanced/"
    
    def test_root_section_child_url(self):
        """Test that child of root section doesn't include 'root' in URL."""
        root = Section(name="root", path=Path("/content"))
        child = Section(name="docs", path=Path("/content/docs"))
        
        root.add_subsection(child)
        
        # Child of root should not have '/root/' in URL
        assert child.url == "/docs/"


class TestPageAncestors:
    """Test page.ancestors property for breadcrumb generation."""
    
    def test_page_with_no_section(self):
        """Test page with no section has empty ancestors."""
        page = Page(
            source_path=Path("/content/page.md"),
            metadata={'title': 'Page'}
        )
        
        assert page.ancestors == []
    
    def test_page_in_single_section(self):
        """Test page in a single section."""
        site = Site(root_path=Path("/site"), config={})
        section = Section(name="docs", path=Path("/content/docs"))
        
        page = Page(
            source_path=Path("/content/docs/intro.md"),
            metadata={'title': 'Introduction'}
        )
        
        section.add_page(page)
        section._site = site
        page._site = site
        page._section = section
        
        ancestors = page.ancestors
        assert len(ancestors) == 1
        assert ancestors[0] == section
    
    def test_page_in_nested_sections(self):
        """Test page in nested sections returns all ancestors."""
        site = Site(root_path=Path("/site"), config={})
        
        parent = Section(name="docs", path=Path("/content/docs"))
        child = Section(name="guides", path=Path("/content/docs/guides"))
        
        page = Page(
            source_path=Path("/content/docs/guides/intro.md"),
            metadata={'title': 'Guide Introduction'}
        )
        
        parent.add_subsection(child)
        child.add_page(page)
        
        parent._site = site
        child._site = site
        page._site = site
        page._section = child
        
        ancestors = page.ancestors
        # Should have immediate parent first, then grandparent
        assert len(ancestors) == 2
        assert ancestors[0] == child  # guides
        assert ancestors[1] == parent  # docs
    
    def test_page_with_root_section_ancestor(self):
        """Test that root section is included in ancestors (template filters it)."""
        site = Site(root_path=Path("/site"), config={})
        
        root = Section(name="root", path=Path("/content"))
        section = Section(name="docs", path=Path("/content/docs"))
        
        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={'title': 'Page'}
        )
        
        root.add_subsection(section)
        section.add_page(page)
        
        root._site = site
        section._site = site
        page._site = site
        page._section = section
        
        ancestors = page.ancestors
        # Should include both section and root
        assert len(ancestors) == 2
        assert ancestors[0] == section  # docs
        assert ancestors[1] == root  # root
        
        # Template should filter out root by checking ancestor.name != 'root'
        filtered_ancestors = [a for a in ancestors if a.name != 'root']
        assert len(filtered_ancestors) == 1
        assert filtered_ancestors[0] == section
    
    def test_ancestors_order_from_child_to_root(self):
        """Test that ancestors are ordered from immediate parent to root."""
        site = Site(root_path=Path("/site"), config={})
        
        level1 = Section(name="api", path=Path("/content/api"))
        level2 = Section(name="v2", path=Path("/content/api/v2"))
        level3 = Section(name="auth", path=Path("/content/api/v2/auth"))
        
        page = Page(
            source_path=Path("/content/api/v2/auth/oauth.md"),
            metadata={'title': 'OAuth'}
        )
        
        level1.add_subsection(level2)
        level2.add_subsection(level3)
        level3.add_page(page)
        
        level1._site = site
        level2._site = site
        level3._site = site
        page._site = site
        page._section = level3
        
        ancestors = page.ancestors
        assert len(ancestors) == 3
        assert ancestors[0] == level3  # auth (immediate parent)
        assert ancestors[1] == level2  # v2
        assert ancestors[2] == level1  # api (root)


class TestBreadcrumbLogic:
    """Test breadcrumb generation logic."""
    
    def test_breadcrumb_filtering_root_section(self):
        """Test that breadcrumb logic filters out root section."""
        site = Site(root_path=Path("/site"), config={})
        
        root = Section(name="root", path=Path("/content"))
        docs = Section(name="docs", path=Path("/content/docs"))
        
        page = Page(
            source_path=Path("/content/docs/advanced.md"),
            metadata={'title': 'Advanced Topics'}
        )
        
        root.add_subsection(docs)
        docs.add_page(page)
        
        root._site = site
        docs._site = site
        page._site = site
        page._section = docs
        
        # Simulate breadcrumb template logic:
        # {% for ancestor in page.ancestors | reverse %}
        #   {% if ancestor.name != 'root' %}
        ancestors = page.ancestors
        breadcrumb_items = []
        
        for ancestor in reversed(ancestors):
            if ancestor.name != 'root':
                breadcrumb_items.append({
                    'title': ancestor.title,
                    'url': ancestor.url
                })
        
        # Should only have docs, not root
        assert len(breadcrumb_items) == 1
        assert breadcrumb_items[0]['title'] == 'Docs'
        assert breadcrumb_items[0]['url'] == '/docs/'
    
    def test_breadcrumb_with_nested_sections_no_root(self):
        """Test breadcrumb generation with nested sections excluding root."""
        site = Site(root_path=Path("/site"), config={})
        
        root = Section(name="root", path=Path("/content"))
        api = Section(name="api", path=Path("/content/api"))
        v2 = Section(name="v2", path=Path("/content/api/v2"))
        
        page = Page(
            source_path=Path("/content/api/v2/users.md"),
            metadata={'title': 'User Management'}
        )
        
        root.add_subsection(api)
        api.add_subsection(v2)
        v2.add_page(page)
        
        root._site = site
        api._site = site
        v2._site = site
        page._site = site
        page._section = v2
        
        # Simulate breadcrumb generation
        ancestors = page.ancestors
        breadcrumb_items = []
        
        for ancestor in reversed(ancestors):
            if ancestor.name != 'root':
                breadcrumb_items.append({
                    'title': ancestor.title,
                    'url': ancestor.url
                })
        
        # Should have: Api → V2 (no root)
        assert len(breadcrumb_items) == 2
        assert breadcrumb_items[0]['title'] == 'Api'
        assert breadcrumb_items[0]['url'] == '/api/'
        assert breadcrumb_items[1]['title'] == 'V2'
        assert breadcrumb_items[1]['url'] == '/api/v2/'


class TestNavigationEdgeCases:
    """Test edge cases in navigation."""
    
    def test_section_without_parent(self):
        """Test section without parent generates correct URL."""
        section = Section(name="blog", path=Path("/content/blog"))
        
        assert section.url == "/blog/"
        assert section.parent is None
    
    def test_page_parent_property(self):
        """Test that page.parent returns the section."""
        section = Section(name="docs", path=Path("/content/docs"))
        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={'title': 'Page'}
        )
        
        section.add_page(page)
        page._section = section
        
        assert page.parent == section
    
    def test_section_hierarchy_property(self):
        """Test section.hierarchy returns correct path."""
        parent = Section(name="docs", path=Path("/content/docs"))
        child = Section(name="guides", path=Path("/content/docs/guides"))
        
        parent.add_subsection(child)
        
        assert parent.hierarchy == ["docs"]
        assert child.hierarchy == ["docs", "guides"]

