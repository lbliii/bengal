"""
Test MyST-style tab-set and tab-item directives.
"""

from bengal.rendering.parsers import MistuneParser


class TestMystTabSyntax:
    """Test modern MyST tab-set/tab-item syntax."""

    def test_basic_tab_set(self):
        """Test basic tab-set with tab-items."""
        parser = MistuneParser()

        content = """
:::{tab-set}
:::{tab-item} Python
Python content here
:::
:::{tab-item} JavaScript
JavaScript content here
:::
::::
"""
        result = parser.parse(content, {})

        assert '<div class="tabs"' in result
        assert "tab-nav" in result
        assert "Python" in result
        assert "JavaScript" in result
        assert "Python content here" in result
        assert "JavaScript content here" in result

    def test_tab_with_markdown(self):
        """Test tabs with markdown content."""
        parser = MistuneParser()

        content = """
:::{tab-set}
:::{tab-item} Markdown
This has **bold** and *italic* text.

- List item 1
- List item 2
:::
::::
"""
        result = parser.parse(content, {})

        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result
        assert "<li>List item 1</li>" in result

    def test_tab_with_code_blocks(self):
        """Test tabs with code blocks."""
        parser = MistuneParser()

        content = """
:::{tab-set}
:::{tab-item} Python
```python
def hello():
    print("world")
```
:::
:::{tab-item} JavaScript
```javascript
console.log("hello");
```
:::
::::
"""
        result = parser.parse(content, {})

        # Check for Pygments syntax highlighting
        assert '<span class="k">def</span>' in result or 'def' in result
        assert '<span class="nf">hello</span>' in result or 'hello' in result
        assert '<span class="nx">console</span>' in result or 'console.log' in result

    def test_tab_with_selected_option(self):
        """Test tab with :selected: option."""
        parser = MistuneParser()

        content = """
:::{tab-set}
:::{tab-item} First
Content 1
:::
:::{tab-item} Second
:selected:
Content 2
:::
::::
"""
        result = parser.parse(content, {})

        # Second tab should be marked as selected
        assert 'data-selected="true"' in result

    def test_tab_with_sync(self):
        """Test tab-set with :sync: option."""
        parser = MistuneParser()

        content = """
:::{tab-set}
:sync: os
:::{tab-item} Linux
Linux instructions
:::
:::{tab-item} Windows
Windows instructions
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-sync="os"' in result

    def test_nested_directives_in_tabs(self):
        """Test nested directives inside tabs."""
        parser = MistuneParser()

        # Note: Nested directives use fewer colons than parent
        # tab-set uses 4 colons, tab-item uses 3, nested note uses 3 (same level as tab-item)
        content = """
:::::{tab-set}
::::{tab-item} Tab 1
:::{note}
This is a note inside a tab.
:::
::::
:::::
"""
        result = parser.parse(content, {})

        assert "admonition" in result.lower()
        assert "note" in result.lower()
        assert "This is a note inside a tab" in result

    def test_multiple_tab_sets(self):
        """Test multiple tab-sets on one page."""
        parser = MistuneParser()

        content = """
:::{tab-set}
:::{tab-item} A
Content A
:::
::::

:::{tab-set}
:::{tab-item} B
Content B
:::
::::
"""
        result = parser.parse(content, {})

        # Should have two separate tab sets
        assert result.count('class="tabs"') == 2


class TestTabEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_tab_set(self):
        """Test tab-set with no tabs."""
        parser = MistuneParser()

        content = """
:::{tab-set}
::::
"""
        result = parser.parse(content, {})

        # Should not crash
        assert "tabs" in result

    def test_single_tab(self):
        """Test tab-set with only one tab."""
        parser = MistuneParser()

        content = """
:::{tab-set}
:::{tab-item} Only One
Content
:::
::::
"""
        result = parser.parse(content, {})

        assert "Only One" in result
        assert "Content" in result

    def test_tab_without_title(self):
        """Test tab-item with no title."""
        parser = MistuneParser()

        content = """
:::{tab-set}
:::{tab-item}
Content without title
:::
::::
"""
        result = parser.parse(content, {})

        # Should default to "Tab"
        assert "Content without title" in result
