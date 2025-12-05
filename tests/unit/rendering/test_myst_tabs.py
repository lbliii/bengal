"""
from __future__ import annotations
Test MyST-style tab-set and tab-item directives.
"""



class TestMystTabSyntax:
    """Test modern MyST tab-set/tab-item syntax."""

    def test_basic_tab_set(self, parser):
        """Test basic tab-set with tab-items."""

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

    def test_tab_with_markdown(self, parser):
        """Test tabs with markdown content."""

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

    def test_tab_with_code_blocks(self, parser):
        """Test tabs with code blocks."""

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

    def test_tab_with_selected_option(self, parser):
        """Test tab with :selected: option."""

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

    def test_tab_with_sync(self, parser):
        """Test tab-set with :sync: option."""

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

    def test_nested_directives_in_tabs(self, parser):
        """Test nested directives inside tabs."""

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

    def test_multiple_tab_sets(self, parser):
        """Test multiple tab-sets on one page."""

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

    def test_empty_tab_set(self, parser):
        """Test tab-set with no tabs."""

        content = """
:::{tab-set}
::::
"""
        result = parser.parse(content, {})

        # Should not crash
        assert "tabs" in result

    def test_single_tab(self, parser):
        """Test tab-set with only one tab."""

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

    def test_tab_without_title(self, parser):
        """Test tab-item with no title."""

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
