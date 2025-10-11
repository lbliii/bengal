"""
Test parser configuration and selection logic.

Ensures the rendering pipeline correctly selects the markdown parser
based on different configuration formats.
"""

import pytest
from unittest.mock import Mock

from bengal.rendering.pipeline import RenderingPipeline
from bengal.rendering.parser import MistuneParser, PythonMarkdownParser


class TestParserSelection:
    """Test that the correct parser is selected based on configuration."""
    
    def test_mistune_parser_selected_from_nested_config(self, tmp_path):
        """Test parser selection when config has nested [markdown] section."""
        # Simulate Site with nested markdown config (like bengal.toml)
        site = Mock()
        site.config = {
            'markdown': {
                'parser': 'mistune',
                'table_of_contents': True,
            },
            'site': {'title': 'Test Site'},
            'theme': 'default',
        }
        site.theme = 'default'  # Must be accessible as attribute for path operations
        site.xref_index = {}
        site.root_path = tmp_path
        site.output_dir = tmp_path / 'public'  # Required for template cache
        
        pipeline = RenderingPipeline(site, quiet=True)
        
        # Should select MistuneParser
        assert isinstance(pipeline.parser, MistuneParser), \
            "Failed to select Mistune parser from nested [markdown] config"
    
    def test_mistune_parser_selected_from_flat_config(self, tmp_path):
        """Test parser selection when config has top-level markdown_engine."""
        # Simulate Site with flat config (legacy format)
        site = Mock()
        site.config = {
            'markdown_engine': 'mistune',
            'site': {'title': 'Test Site'},
            'theme': 'default',
        }
        site.theme = 'default'  # Must be accessible as attribute for path operations
        site.xref_index = {}
        site.root_path = tmp_path
        site.output_dir = tmp_path / 'public'  # Required for template cache
        
        pipeline = RenderingPipeline(site, quiet=True)
        
        # Should select MistuneParser
        assert isinstance(pipeline.parser, MistuneParser), \
            "Failed to select Mistune parser from flat markdown_engine config"
    
    def test_python_markdown_parser_default(self, tmp_path):
        """Test that python-markdown is the default when not specified."""
        site = Mock()
        site.config = {
            'site': {'title': 'Test Site'},
            'theme': 'default',
        }
        site.theme = 'default'  # Must be accessible as attribute for path operations
        site.xref_index = {}
        site.root_path = tmp_path
        site.output_dir = tmp_path / 'public'  # Required for template cache
        
        pipeline = RenderingPipeline(site, quiet=True)
        
        # Should default to PythonMarkdownParser
        assert isinstance(pipeline.parser, PythonMarkdownParser), \
            "Failed to default to python-markdown parser"
    
    def test_flat_config_takes_precedence(self, tmp_path):
        """Test that flat markdown_engine takes precedence over nested."""
        # Both present - flat should win for backward compatibility
        site = Mock()
        site.config = {
            'markdown_engine': 'python-markdown',  # Flat
            'markdown': {
                'parser': 'mistune',  # Nested
            },
            'theme': 'default',
        }
        site.theme = 'default'  # Must be accessible as attribute for path operations
        site.xref_index = {}
        site.root_path = tmp_path
        site.output_dir = tmp_path / 'public'  # Required for template cache
        
        pipeline = RenderingPipeline(site, quiet=True)
        
        # Should use flat config (backward compatibility)
        assert isinstance(pipeline.parser, PythonMarkdownParser), \
            "Flat markdown_engine should take precedence for backward compatibility"
    
    def test_parser_reuse_across_threads(self, tmp_path):
        """Test that parsers are reused within the same thread."""
        site1 = Mock()
        site1.config = {'markdown': {'parser': 'mistune'}, 'theme': 'default'}
        site1.theme = 'default'  # Must be accessible as attribute for path operations
        site1.xref_index = {}
        site1.root_path = tmp_path
        site1.output_dir = tmp_path / 'public'  # Required for template cache
        
        site2 = Mock()
        site2.config = {'markdown': {'parser': 'mistune'}, 'theme': 'default'}
        site2.theme = 'default'  # Must be accessible as attribute for path operations
        site2.xref_index = {}
        site2.root_path = tmp_path
        site2.output_dir = tmp_path / 'public'  # Required for template cache
        
        pipeline1 = RenderingPipeline(site1, quiet=True)
        pipeline2 = RenderingPipeline(site2, quiet=True)
        
        # Same thread, same engine = same parser instance (thread-local caching)
        assert pipeline1.parser is pipeline2.parser, \
            "Parser should be reused within the same thread"


class TestMistuneDirectives:
    """Test that Mistune parser has directives enabled."""
    
    def test_mistune_parser_has_directives(self):
        """Test that MistuneParser can handle custom directives."""
        from bengal.rendering.parser import MistuneParser
        
        parser = MistuneParser()
        
        # Test a simple directive
        markdown = """
```{note}
This is a note directive.
```
"""
        
        html = parser.parse(markdown, {})
        
        # Should contain admonition HTML (not raw text)
        assert '<div class="admonition' in html, \
            "Mistune parser should process note directive"
        assert 'This is a note directive' in html
        # Should NOT contain the raw directive syntax
        assert '```{note}' not in html
    
    def test_mistune_parser_has_tabs(self):
        """Test that MistuneParser can handle tabs directive."""
        from bengal.rendering.parser import MistuneParser
        
        parser = MistuneParser()
        
        markdown = """
```{tabs}
:id: test-tabs

### Tab: First

First tab content

### Tab: Second

Second tab content
```
"""
        
        html = parser.parse(markdown, {})
        
        # Should contain tabs HTML
        assert 'class="tabs"' in html or 'class="tab' in html, \
            "Mistune parser should process tabs directive"
        assert 'First' in html
        assert 'Second' in html
        # Should NOT contain raw directive syntax
        assert '```{tabs}' not in html
    
    def test_python_markdown_ignores_directives(self):
        """Test that PythonMarkdownParser doesn't have our custom directives."""
        from bengal.rendering.parser import PythonMarkdownParser
        
        parser = PythonMarkdownParser()
        
        markdown = """
```{note}
This is a note directive.
```
"""
        
        html = parser.parse(markdown, {})
        
        # Python-markdown will treat this as a code block
        # (it doesn't have our custom directives)
        assert '<code>' in html or '<pre>' in html, \
            "python-markdown should render directive syntax as code"


class TestConfigIntegration:
    """Integration tests for config loading and parser selection."""
    
    def test_showcase_site_uses_mistune(self, tmp_path):
        """Test that a site with [markdown] parser = mistune uses Mistune."""
        from bengal.config.loader import ConfigLoader
        
        # Create a test config like showcase site
        config_content = """
[site]
title = "Test Site"

[markdown]
parser = "mistune"
table_of_contents = true
"""
        
        config_file = tmp_path / "bengal.toml"
        config_file.write_text(config_content)
        
        loader = ConfigLoader(tmp_path)
        config = loader.load(config_file)
        
        # Verify config structure
        assert 'markdown' in config
        assert config['markdown']['parser'] == 'mistune'
        
        # Create mock site with this config
        site = Mock()
        site.config = config
        site.config['theme'] = 'default'
        site.theme = 'default'  # Must be accessible as attribute for path operations
        site.xref_index = {}
        site.root_path = tmp_path
        site.output_dir = tmp_path / 'public'  # Required for template cache
        
        pipeline = RenderingPipeline(site, quiet=True)
        
        # CRITICAL: Should use Mistune, not python-markdown
        assert isinstance(pipeline.parser, MistuneParser), \
            "Site with [markdown] parser='mistune' should use MistuneParser"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

