"""
Test MyST Markdown syntax compatibility.

Verifies that Bengal supports colon-fenced directive syntax (MyST standard).

Note: Backtick-fenced directives (```{directive}) are NOT supported.
This is intentional to avoid conflicts with code blocks in documentation.
Only colon-fenced directives (:::{directive}) are processed.
"""

import pytest

from bengal.rendering.parsers import MistuneParser


class TestMystSyntaxCompatibility:
    """Test that colon fence style works for directives."""

    def test_backtick_fenced_renders_as_code_block(self):
        """Backtick-style fenced directive renders as code block (not directive).

        This is intentional - backticks are reserved for code blocks to avoid
        conflicts when directives appear in code examples.
        """
        parser = MistuneParser()

        content = """
```{note}
This is a note using backticks.
```
"""
        result = parser.parse(content, {})

        # Should render as code block, NOT as admonition
        assert "admonition" not in result.lower()
        assert '<pre><code' in result or '<code' in result

    def test_colon_fenced_note(self):
        """Test colon-style fenced directive (MyST Markdown syntax)."""
        parser = MistuneParser()

        content = """
:::{note}
This is a note using colons.
:::
"""
        result = parser.parse(content, {})

        assert "admonition" in result.lower()
        assert "note" in result.lower()
        assert "This is a note using colons" in result

    def test_code_blocks_and_directives_coexist(self):
        """Test that code blocks and directives work together."""
        parser = MistuneParser()

        content = """
# Mixed Content Test

```python
# This is a code block
print("hello")
```

Some text in between.

:::{warning}
This warning uses colons.
:::
"""
        result = parser.parse(content, {})

        # Code block should render as code
        assert 'print' in result
        # Directive should render as admonition
        assert "This warning uses colons" in result
        assert "warning" in result.lower()

    def test_nested_colon_directives(self):
        """Test nested MyST-style directives with different colon counts."""
        parser = MistuneParser()

        content = """
::::{note} Outer note
This is the outer note.

:::{tip} Inner tip
This is nested inside.
:::

Back to outer note.
::::
"""
        result = parser.parse(content, {})

        assert "Outer note" in result
        assert "Inner tip" in result
        assert "This is nested inside" in result

    def test_colon_dropdown(self):
        """Test MyST-style dropdown directive."""
        parser = MistuneParser()

        content = """
:::{dropdown} Click to expand
Hidden content here.
:::
"""
        result = parser.parse(content, {})

        assert "Click to expand" in result
        assert "Hidden content here" in result

    def test_colon_tabs(self):
        """Test MyST-style tabs directive."""
        parser = MistuneParser()

        content = """
:::{tabs}
### Tab: Python
```python
print("Hello")
```

### Tab: JavaScript
```javascript
console.log("Hello");
```
:::
"""
        result = parser.parse(content, {})

        assert "Python" in result
        assert "JavaScript" in result
        # Check for Pygments highlighting or escaped HTML
        assert '<span class="nb">print</span>' in result or 'print(&quot;Hello&quot;)' in result

    def test_directive_with_options_colon_style(self):
        """Test MyST-style directive with options."""
        parser = MistuneParser()

        content = """
:::{note}
:class: custom-class
:name: my-note

Content with options.
:::
"""
        result = parser.parse(content, {})

        # Should render (options may or may not be used depending on directive implementation)
        assert "Content with options" in result


class TestMystGridSyntaxParsing:
    """Test that MyST grid syntax is at least parsed (may not render yet)."""

    def test_grid_syntax_doesnt_break_parser(self):
        """Test that grid syntax doesn't cause parser errors."""
        parser = MistuneParser()

        # Even if grid isn't implemented, it shouldn't crash
        content = """
:::{grid} 1 2 2 2
:gutter: 1

This is grid content.
:::
"""
        try:
            result = parser.parse(content, {})
            # Should complete without exception
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Parser should not crash on unimplemented directives: {e}")

    def test_grid_item_card_syntax(self):
        """Test that grid-item-card syntax doesn't crash."""
        parser = MistuneParser()

        content = """
:::{grid-item-card} Card Title
:link: docs/page
:link-type: doc

Card content here.
:::
"""
        try:
            result = parser.parse(content, {})
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Parser should not crash on unimplemented directives: {e}")


class TestColonSyntaxSupport:
    """Test colon-fenced syntax for all directive types."""

    def test_all_admonition_types(self):
        """Test that all admonition types work with colon syntax."""
        parser = MistuneParser()

        admonition_types = ["note", "tip", "warning", "danger", "info", "important"]

        for adm_type in admonition_types:
            content = f"""
:::{{{adm_type}}}
This is a {adm_type}.
:::
"""
            result = parser.parse(content, {})
            assert f"This is a {adm_type}" in result
            assert "admonition" in result.lower()

    def test_dropdown_with_colon_syntax(self):
        """Test dropdown directive with colon syntax."""
        parser = MistuneParser()

        content = """
:::{dropdown} Title
Content
:::
"""
        result = parser.parse(content, {})
        assert "Title" in result
        assert "Content" in result
        assert "<details" in result

    def test_code_tabs_with_colon_syntax(self):
        """Test code-tabs directive with colon syntax."""
        parser = MistuneParser()

        content = """
:::{code-tabs}
### Python
print("test")

### JavaScript
console.log("test")
:::
"""
        result = parser.parse(content, {})
        assert "Python" in result
        assert "JavaScript" in result
