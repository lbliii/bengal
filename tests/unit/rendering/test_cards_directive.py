"""
Test cards directive system (modern and Sphinx-Design compatibility).
"""

import pytest
from bengal.rendering.parser import MistuneParser


class TestModernCardsDirective:
    """Test the modern cards/card directive syntax."""
    
    def test_simple_card_grid(self):
        """Test basic cards grid with auto-layout."""
        parser = MistuneParser()
        
        content = """
:::{cards}

:::{card} Card One
First card content.
:::

:::{card} Card Two
Second card content.
:::

::::
"""
        result = parser.parse(content, {})
        
        assert 'card-grid' in result
        assert 'Card One' in result
        assert 'Card Two' in result
        assert 'First card content' in result
        assert 'Second card content' in result
    
    def test_card_with_icon(self):
        """Test card with icon."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:::{card} Documentation
:icon: book

Complete docs here.
:::
::::
"""
        result = parser.parse(content, {})
        
        assert 'card-icon' in result
        assert 'data-icon="book"' in result
        assert 'Documentation' in result
    
    def test_card_with_link(self):
        """Test card that's a clickable link."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:::{card} API Reference
:link: /api/

Check out the API.
:::
::::
"""
        result = parser.parse(content, {})
        
        assert '<a' in result
        assert 'href="/api/"' in result
        assert 'API Reference' in result
    
    def test_card_with_color(self):
        """Test card with color accent."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:::{card} Important
:color: blue

This is important.
:::
::::
"""
        result = parser.parse(content, {})
        
        assert 'card-color-blue' in result
    
    def test_responsive_columns(self):
        """Test responsive column specification."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:columns: 1-2-3

:::{card} One
:::
:::{card} Two
:::
:::{card} Three
:::
::::
"""
        result = parser.parse(content, {})
        
        assert 'data-columns="1-2-3"' in result
    
    def test_fixed_columns(self):
        """Test fixed column count."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:columns: 3

:::{card} A
:::
:::{card} B
:::
:::{card} C
:::
::::
"""
        result = parser.parse(content, {})
        
        assert 'data-columns="3"' in result
    
    def test_card_with_all_options(self):
        """Test card with all available options."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:columns: 2
:gap: large

:::{card} Feature
:icon: rocket
:link: /feature/
:color: purple
:footer: Updated 2025

Amazing new feature with **markdown** support!
:::
::::
"""
        result = parser.parse(content, {})
        
        assert 'data-columns="2"' in result
        assert 'data-gap="large"' in result
        assert 'card-icon' in result
        assert 'href="/feature/"' in result
        assert 'card-color-purple' in result
        assert 'card-footer' in result
        assert 'Updated 2025' in result
        assert '<strong>markdown</strong>' in result


class TestSphinxDesignCompatibility:
    """Test Sphinx-Design grid/grid-item-card compatibility."""
    
    def test_basic_grid_syntax(self):
        """Test basic Sphinx grid syntax."""
        parser = MistuneParser()
        
        content = """
::::{grid} 1 2 2 2

:::{grid-item-card} My Card
:link: docs/page

Card content here.
:::
::::
"""
        result = parser.parse(content, {})
        
        # Should render as card-grid
        assert 'card-grid' in result
        assert 'My Card' in result
        assert 'Card content here' in result
    
    def test_grid_with_octicon(self):
        """Test grid-item-card with octicon syntax."""
        parser = MistuneParser()
        
        content = """
::::{grid} 1 2 2 2

:::{grid-item-card} {octicon}`book;1.5em;sd-mr-1` Documentation
:link: docs/intro

Learn more about our docs.
:::
::::
"""
        result = parser.parse(content, {})
        
        # Should extract icon from octicon syntax
        assert 'card-icon' in result
        assert 'data-icon="book"' in result
        # Title should be clean (no octicon syntax)
        assert 'Documentation' in result
        # Octicon syntax should be removed
        assert '{octicon}' not in result
    
    def test_grid_column_conversion(self):
        """Test that Sphinx breakpoints are converted correctly."""
        parser = MistuneParser()
        
        content = """
::::{grid} 1 2 3 4

:::{grid-item-card} Card
:::
::::
"""
        result = parser.parse(content, {})
        
        # Should convert "1 2 3 4" to "1-2-3-4"
        assert 'data-columns="1-2-3-4"' in result
    
    def test_grid_gutter_conversion(self):
        """Test that Sphinx gutter is converted to gap."""
        parser = MistuneParser()
        
        content = """
::::{grid} 2
:gutter: 3

:::{grid-item-card} Card
:::
::::
"""
        result = parser.parse(content, {})
        
        # Gutter 3 should convert to gap large
        assert 'data-gap="large"' in result
    
    def test_multiple_grid_cards(self):
        """Test multiple cards in Sphinx grid."""
        parser = MistuneParser()
        
        content = """
::::{grid} 2

:::{grid-item-card} {octicon}`star` First
:link: first/
First content.
:::

:::{grid-item-card} {octicon}`rocket` Second  
:link: second/
Second content.
:::
::::
"""
        result = parser.parse(content, {})
        
        assert 'First' in result
        assert 'Second' in result
        assert 'data-icon="star"' in result
        assert 'data-icon="rocket"' in result
        assert 'href="first/"' in result
        assert 'href="second/"' in result


class TestCardMarkdownSupport:
    """Test that cards support full markdown in content."""
    
    def test_markdown_in_card_content(self):
        """Test markdown rendering in card content."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:::{card} Test

This has **bold** and *italic* text.

- List item 1
- List item 2

[A link](/page/)
:::
::::
"""
        result = parser.parse(content, {})
        
        assert '<strong>bold</strong>' in result
        assert '<em>italic</em>' in result
        assert '<li>List item 1</li>' in result
        assert 'href="/page/"' in result
    
    def test_code_in_card(self):
        """Test code blocks in cards."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:::{card} Code Example

```python
def hello():
    print("world")
```
:::
::::
"""
        result = parser.parse(content, {})
        
        assert 'def hello' in result or 'hello()' in result
        assert '<code' in result or '<pre' in result


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_cards_grid(self):
        """Test cards with no children."""
        parser = MistuneParser()
        
        content = """
:::{cards}
::::
"""
        result = parser.parse(content, {})
        
        # Should not crash
        assert 'card-grid' in result
    
    def test_card_without_title(self):
        """Test card with no title."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:::{card}
Content only, no title.
:::
::::
"""
        result = parser.parse(content, {})
        
        assert 'Content only' in result
    
    def test_invalid_column_value(self):
        """Test that invalid columns default to auto."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:columns: invalid

:::{card} Test
:::
::::
"""
        result = parser.parse(content, {})
        
        # Should default to auto
        assert 'data-columns="auto"' in result
    
    def test_invalid_color(self):
        """Test that invalid colors are ignored."""
        parser = MistuneParser()
        
        content = """
:::{cards}
:::{card} Test
:color: notacolor

Content
:::
::::
"""
        result = parser.parse(content, {})
        
        # Should not have a color class
        assert 'card-color-notacolor' not in result

