"""
Tests for template syntax escaping in markdown content.

These tests ensure that documentation pages can show template examples
without those examples being processed by the template engine.
"""

import pytest
from bengal.rendering.plugins.variable_substitution import VariableSubstitutionPlugin
from datetime import datetime


class TestVariableSubstitutionEscaping:
    """Test the {{/* ... */}} escape pattern."""
    
    def test_basic_escape_pattern(self):
        """Test that {{/* expression */}} becomes HTML-escaped {{ expression }}."""
        context = {'page': type('obj', (), {'title': 'Test'})}
        plugin = VariableSubstitutionPlugin(context)
        
        text = "Use {{/* page.title */}} to display the title."
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        # Should be HTML-escaped so Jinja2 won't process it
        assert result == "Use &#123;&#123; page.title &#125;&#125; to display the title."
        # Browser will render this as: Use {{ page.title }} to display the title.
    
    def test_escape_with_filters(self):
        """Test escaping template syntax with filters."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        text = "Example: {{/* post.content | truncatewords(50) */}}"
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        assert result == "Example: &#123;&#123; post.content | truncatewords(50) &#125;&#125;"
    
    def test_escape_with_complex_expression(self):
        """Test escaping complex template expressions."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        text = "Use {{/* page.date | format_date('%Y-%m-%d') */}} for dates."
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        assert result == "Use &#123;&#123; page.date | format_date('%Y-%m-%d') &#125;&#125; for dates."
    
    def test_normal_variables_still_work(self):
        """Test that normal variable substitution still works alongside escaping."""
        page = type('obj', (), {'title': 'My Page'})
        context = {'page': page}
        plugin = VariableSubstitutionPlugin(context)
        
        text = "Title: {{ page.title }}. Show syntax: {{/* page.title */}}"
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        # First {{ page.title }} should be substituted
        # Second {{/* page.title */}} should become HTML-escaped
        assert result == "Title: My Page. Show syntax: &#123;&#123; page.title &#125;&#125;"
    
    def test_multiple_escapes_in_text(self):
        """Test multiple escape patterns in same text."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        text = """
        Use {{/* page.title */}} for the title.
        Use {{/* page.content | strip_html */}} for plain text.
        Use {{/* site.baseurl */}} for the base URL.
        """
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        assert "&#123;&#123; page.title &#125;&#125;" in result
        assert "&#123;&#123; page.content | strip_html &#125;&#125;" in result
        assert "&#123;&#123; site.baseurl &#125;&#125;" in result
        assert "{{/*" not in result  # Escape markers should be gone
    
    def test_escape_preserves_whitespace(self):
        """Test that escaping preserves internal whitespace."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        text = "{{/*  page.title  */}}"
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        # Should preserve the internal spaces (HTML escaped)
        assert result == "&#123;&#123;  page.title  &#125;&#125;"
    
    def test_nested_braces_in_escape(self):
        """Test escaping expressions with nested braces."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        # JSX example from output-formats.md
        text = "{{/* __html: page.content_html */}}"
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        assert result == "&#123;&#123; __html: page.content_html &#125;&#125;"
    
    def test_escape_with_hugo_style_comments(self):
        """Test that Hugo comment syntax {{/* ... */}} works."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        # This is the actual escape pattern
        text = "{{/* .Title */}}"
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        assert result == "&#123;&#123; .Title &#125;&#125;"
    
    def test_incomplete_escape_patterns(self):
        """Test that incomplete escape patterns don't break."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        # Missing closing */}}
        text = "{{/* page.title"
        result = plugin._substitute_variables(text)
        
        # Should leave it unchanged if pattern is incomplete
        assert "{{/*" in result or result == text


class TestDocumentationPages:
    """Integration tests for documentation pages with template examples."""
    
    def test_documentation_page_with_examples(self, tmp_path):
        """Test that a documentation page with template examples builds correctly."""
        # Create a minimal site
        site_dir = tmp_path / "test_site"
        content_dir = site_dir / "content"
        content_dir.mkdir(parents=True)
        
        # Create a documentation page with template examples
        doc_page = content_dir / "template-docs.md"
        doc_page.write_text("""---
title: Template Documentation
date: 2025-10-04
---

# Template Functions

Use {{/* page.title */}} to display the page title.

## Examples

To truncate content:

```jinja2
{{/* post.content | truncatewords(50) */}}
```

For dates:

```jinja2
{{/* page.date | format_date('%Y-%m-%d') */}}
```
""")
        
        # This should NOT raise template errors
        # (In a full integration test, we'd build the site and verify no errors)
        # For now, just test the escape pattern works
        plugin = VariableSubstitutionPlugin({})
        
        content = doc_page.read_text()
        # Extract the template examples
        assert "{{/* page.title */}}" in content
        assert "{{/* post.content | truncatewords(50) */}}" in content
        
        # After processing through plugin, they should become HTML-escaped
        processed = plugin._substitute_variables(content)
        processed = plugin.restore_placeholders(processed)
        assert "&#123;&#123; page.title &#125;&#125;" in processed
        assert "&#123;&#123; post.content | truncatewords(50) &#125;&#125;" in processed
        assert "{{/*" not in processed  # All escape markers removed
    
    def test_mixed_real_and_example_templates(self, tmp_path):
        """Test page with both real variables and template examples."""
        site_dir = tmp_path / "test_site"
        content_dir = site_dir / "content"
        content_dir.mkdir(parents=True)
        
        doc_page = content_dir / "mixed-templates.md"
        doc_page.write_text("""---
title: Template Guide
author: Bengal Team
---

# Written by {{ page.metadata.author }}

To show the author, use {{/* page.metadata.author */}}.

Published on {{ page.date }}.

To show dates, use {{/* page.date | format_date */}}.
""")
        
        # Simulate processing
        page = type('obj', (), {
            'metadata': {'author': 'Bengal Team'},
            'date': datetime(2025, 10, 4)
        })
        context = {'page': page}
        plugin = VariableSubstitutionPlugin(context)
        
        content = doc_page.read_text()
        processed = plugin._substitute_variables(content)
        processed = plugin.restore_placeholders(processed)
        
        # Real variables should be substituted
        assert "Written by Bengal Team" in processed
        
        # Examples should become HTML-escaped (not substituted)
        assert "use &#123;&#123; page.metadata.author &#125;&#125;" in processed
        assert "use &#123;&#123; page.date | format_date &#125;&#125;" in processed


class TestRegressionPrevention:
    """Tests to prevent regressions of the showcase site issues."""
    
    def test_no_error_on_nonexistent_filter(self):
        """Test that escaped filters don't cause errors even if filter doesn't exist."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        # These filters don't exist in context, but shouldn't error when escaped
        examples = [
            "{{/* post.content | truncatewords(50) */}}",
            "{{/* url | absolute_url */}}",
            "{{/* date | time_ago */}}",
            "{{/* text | meta_description(160) */}}",
        ]
        
        for example in examples:
            result = plugin._substitute_variables(example)
            result = plugin.restore_placeholders(result)
            # Should become HTML-escaped, not cause error
            assert "&#123;&#123;" in result and "&#125;&#125;" in result
            assert "{{/*" not in result
    
    def test_jsx_syntax_in_docs(self):
        """Test JSX examples from output-formats.md don't cause errors."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        # The problematic JSX from output-formats.md
        text = '<div dangerouslySetInnerHTML={{/* __html: page.content_html */}} />'
        result = plugin._substitute_variables(text)
        result = plugin.restore_placeholders(result)
        
        # Should become HTML-escaped JSX (safe from Jinja2)
        assert "&#123;&#123; __html: page.content_html &#125;&#125;" in result
        assert "expected token 'end of print statement'" not in result
    
    def test_hugo_syntax_examples(self):
        """Test Hugo template examples from from-hugo.md migration guide."""
        context = {}
        plugin = VariableSubstitutionPlugin(context)
        
        # Hugo syntax from migration guide
        examples = [
            "{{/* .Title */}}",
            "{{/* .Content */}}",
            "{{/* .Date */}}",
            "{{/* .Params.author */}}",
        ]
        
        for example in examples:
            result = plugin._substitute_variables(example)
            result = plugin.restore_placeholders(result)
            # Should preserve the dot syntax as HTML-escaped
            assert "&#123;&#123;" in result and "&#125;&#125;" in result
            # Should not have the escape markers
            assert "{{/*" not in result


# Pytest fixtures and helpers
@pytest.fixture
def mock_page():
    """Create a mock page for testing."""
    return type('Page', (), {
        'title': 'Test Page',
        'content': 'Test content',
        'date': datetime(2025, 10, 4),
        'metadata': {
            'author': 'Test Author',
            'description': 'Test description'
        }
    })


@pytest.fixture
def mock_site():
    """Create a mock site for testing."""
    return type('Site', (), {
        'title': 'Test Site',
        'baseurl': 'https://example.com',
        'config': {
            'title': 'Test Site'
        }
    })

