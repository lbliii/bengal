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

        assert "def hello" in result or "hello()" in result
        assert "console.log" in result

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

        content = """
:::{tab-set}
:::{tab-item} Tab 1
```{note}
This is a note inside a tab.
```
:::
::::
"""
        result = parser.parse(content, {})

        assert "admonition note" in result
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


class TestLegacyTabSyntax:
    """Test legacy Bengal tab syntax for backward compatibility."""

    def test_legacy_tabs_syntax(self):
        """Test old ### Tab: syntax still works."""
        parser = MistuneParser()

        content = """
````{tabs}
### Tab: Python
Python content
### Tab: JavaScript
JavaScript content
````
"""
        result = parser.parse(content, {})

        assert '<div class="tabs"' in result
        assert "Python" in result
        assert "JavaScript" in result
        assert "Python content" in result
        assert "JavaScript content" in result

    def test_legacy_with_markdown(self):
        """Test legacy tabs with markdown content."""
        parser = MistuneParser()

        content = """
````{tabs}
### Tab: Test
This has **bold** text.
````
"""
        result = parser.parse(content, {})

        assert "<strong>bold</strong>" in result


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


class TestTabComparison:
    """Compare modern and legacy syntax output."""

    def test_both_syntaxes_produce_similar_output(self):
        """Both syntaxes should produce similar HTML structure."""
        parser = MistuneParser()

        modern = """
:::{tab-set}
:::{tab-item} A
Content A
:::
:::{tab-item} B
Content B
:::
::::
"""

        legacy = """
````{tabs}
### Tab: A
Content A
### Tab: B
Content B
````
"""

        modern_result = parser.parse(modern, {})
        legacy_result = parser.parse(legacy, {})

        # Both should have tabs class
        assert 'class="tabs"' in modern_result
        assert 'class="tabs"' in legacy_result

        # Both should have the content
        assert "Content A" in modern_result
        assert "Content A" in legacy_result
        assert "Content B" in modern_result
        assert "Content B" in legacy_result
