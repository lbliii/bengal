"""
Tests for cross-reference functionality.

Covers:
- Cross-reference index building
- Template functions (ref, doc, anchor, relref)
- Mistune [[link]] plugin
"""

import pytest
from pathlib import Path
from bengal.core.site import Site
from bengal.core.page import Page
from bengal.orchestration.content import ContentOrchestrator
from bengal.rendering.template_functions import crossref
from bengal.rendering.mistune_plugins import CrossReferencePlugin


class TestCrossReferenceIndex:
    """Test cross-reference index building."""
    
    def test_index_creation(self, tmp_path):
        """Test that xref_index is created during content discovery."""
        # Create a simple site
        site = Site(
            root_path=tmp_path,
            config={'title': 'Test Site'},
            theme='default'
        )
        
        # Create content directory with some pages
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        
        (content_dir / "index.md").write_text("""---
title: Home
---
Home page
""")
        
        (content_dir / "about.md").write_text("""---
title: About
id: about-page
---
About us
""")
        
        docs_dir = content_dir / "docs"
        docs_dir.mkdir()
        (docs_dir / "installation.md").write_text("""---
title: Installation Guide
---
# Installation

## Prerequisites

Install the software
""")
        
        # Discover content (this should build the xref_index)
        orchestrator = ContentOrchestrator(site)
        orchestrator.discover_content()
        
        # Verify index was created
        assert hasattr(site, 'xref_index')
        assert 'by_path' in site.xref_index
        assert 'by_slug' in site.xref_index
        assert 'by_id' in site.xref_index
        assert 'by_heading' in site.xref_index
    
    def test_index_by_path(self, tmp_path):
        """Test path-based lookups in index."""
        site = Site(
            root_path=tmp_path,
            config={'title': 'Test Site'},
            theme='default'
        )
        
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        docs_dir = content_dir / "docs"
        docs_dir.mkdir()
        
        (docs_dir / "installation.md").write_text("""---
title: Installation Guide
---
Content""")
        
        orchestrator = ContentOrchestrator(site)
        orchestrator.discover_content()
        
        # Should be indexed by path without extension
        assert 'docs/installation' in site.xref_index['by_path']
        page = site.xref_index['by_path']['docs/installation']
        assert page.title == 'Installation Guide'
    
    def test_index_by_id(self, tmp_path):
        """Test custom ID lookups in index."""
        site = Site(
            root_path=tmp_path,
            config={'title': 'Test Site'},
            theme='default'
        )
        
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        
        (content_dir / "about.md").write_text("""---
title: About Us
id: about-page
---
Content""")
        
        orchestrator = ContentOrchestrator(site)
        orchestrator.discover_content()
        
        # Should be indexed by custom ID
        assert 'about-page' in site.xref_index['by_id']
        page = site.xref_index['by_id']['about-page']
        assert page.title == 'About Us'


class TestCrossReferenceTemplateFunctions:
    """Test template functions for cross-references."""
    
    def test_ref_function_by_path(self):
        """Test ref() function with path reference."""
        # Mock page
        page = Page(source_path=Path('docs/install.md'))
        page.title = "Installation"
        page.url = "/docs/installation/"
        
        index = {
            'by_path': {'docs/installation': page},
            'by_slug': {},
            'by_id': {},
            'by_heading': {},
        }
        
        # Test reference with auto title
        result = crossref.ref('docs/installation', index)
        assert '<a href="/docs/installation/">Installation</a>' in result
        
        # Test reference with custom text
        result = crossref.ref('docs/installation', index, 'Install Guide')
        assert '<a href="/docs/installation/">Install Guide</a>' in result
    
    def test_ref_function_broken_link(self):
        """Test ref() function with broken reference."""
        index = {
            'by_path': {},
            'by_slug': {},
            'by_id': {},
            'by_heading': {},
        }
        
        result = crossref.ref('nonexistent/page', index)
        assert 'broken-ref' in result
        assert 'nonexistent/page' in result
    
    def test_doc_function(self):
        """Test doc() function returns page object."""
        page = Page(source_path=Path('about.md'))
        page.title = "About"
        page.url = "/about/"
        
        index = {
            'by_path': {'about': page},
            'by_slug': {},
            'by_id': {},
            'by_heading': {},
        }
        
        result = crossref.doc('about', index)
        assert result is page
        assert result.title == "About"
    
    def test_relref_function(self):
        """Test relref() function returns URL only."""
        page = Page(source_path=Path('docs/api.md'))
        page.url = "/docs/api/"
        
        index = {
            'by_path': {'docs/api': page},
            'by_slug': {},
            'by_id': {},
            'by_heading': {},
        }
        
        result = crossref.relref('docs/api', index)
        assert result == "/docs/api/"


class TestCrossReferenceMistunePlugin:
    """Test Mistune [[link]] plugin."""
    
    def test_plugin_initialization(self):
        """Test CrossReferencePlugin can be initialized."""
        index = {
            'by_path': {},
            'by_slug': {},
            'by_id': {},
            'by_heading': {},
        }
        
        plugin = CrossReferencePlugin(index)
        assert plugin.xref_index == index
        assert plugin.pattern is not None
    
    def test_plugin_pattern_matching(self):
        """Test the regex pattern matches [[link]] syntax."""
        index = {}
        plugin = CrossReferencePlugin(index)
        
        # Test various patterns
        assert plugin.pattern.search('[[docs/installation]]')
        assert plugin.pattern.search('[[docs/api|API Reference]]')
        assert plugin.pattern.search('[[id:my-page]]')
        assert plugin.pattern.search('[[#heading]]')
    
    def test_resolve_path_success(self):
        """Test _resolve_path with valid page."""
        page = Page(source_path=Path('docs/install.md'))
        page.title = "Installation"
        page.url = "/docs/installation/"
        
        index = {
            'by_path': {'docs/installation': page},
            'by_slug': {},
            'by_id': {},
            'by_heading': {},
        }
        
        plugin = CrossReferencePlugin(index)
        result = plugin._resolve_path('docs/installation')
        
        assert '<a href="/docs/installation/">Installation</a>' in result
    
    def test_resolve_path_with_custom_text(self):
        """Test _resolve_path with custom link text."""
        page = Page(source_path=Path('docs/install.md'))
        page.title = "Installation"
        page.url = "/docs/installation/"
        
        index = {
            'by_path': {'docs/installation': page},
            'by_slug': {},
            'by_id': {},
            'by_heading': {},
        }
        
        plugin = CrossReferencePlugin(index)
        result = plugin._resolve_path('docs/installation', 'Install Now')
        
        assert '<a href="/docs/installation/">Install Now</a>' in result
    
    def test_resolve_path_broken_link(self):
        """Test _resolve_path with non-existent page."""
        index = {
            'by_path': {},
            'by_slug': {},
            'by_id': {},
            'by_heading': {},
        }
        
        plugin = CrossReferencePlugin(index)
        result = plugin._resolve_path('nonexistent/page')
        
        assert 'broken-ref' in result
        assert 'nonexistent/page' in result
    
    def test_resolve_id(self):
        """Test _resolve_id with custom ID."""
        page = Page(source_path=Path('about.md'))
        page.title = "About Us"
        page.url = "/about/"
        
        index = {
            'by_path': {},
            'by_slug': {},
            'by_id': {'about-page': page},
            'by_heading': {},
        }
        
        plugin = CrossReferencePlugin(index)
        result = plugin._resolve_id('about-page')
        
        assert '<a href="/about/">About Us</a>' in result


def test_integration_mistune_parser_with_xref(tmp_path):
    """Integration test: parser with cross-reference plugin."""
    from bengal.rendering.parser import MistuneParser
    
    # Create parser
    parser = MistuneParser()
    
    # Create mock page for xref_index
    page = Page(source_path=Path('docs/api.md'))
    page.title = "API Reference"
    page.url = "/docs/api/"
    
    xref_index = {
        'by_path': {'docs/api': page},
        'by_slug': {},
        'by_id': {},
        'by_heading': {},
    }
    
    # Enable cross-references
    parser.enable_cross_references(xref_index)
    
    # Parse markdown with [[link]] syntax
    markdown = """
# Documentation

Check out [[docs/api]] for details.

Also see [[docs/api|our API docs]].
"""
    
    result = parser.parse(markdown, {})
    
    # Verify links were resolved
    assert '<a href="/docs/api/">API Reference</a>' in result
    assert '<a href="/docs/api/">our API docs</a>' in result

