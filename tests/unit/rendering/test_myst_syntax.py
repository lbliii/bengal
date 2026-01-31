"""
Test MyST Markdown syntax compatibility.

Verifies that Bengal supports colon-fenced directive syntax (MyST standard).

Note: Backtick-fenced directives (```{directive}) are NOT supported.
This is intentional to avoid conflicts with code blocks in documentation.
Only colon-fenced directives (:::{directive}) are processed.
"""

import pytest


class TestMystSyntaxCompatibility:
    """Test that colon fence style works for directives."""

    def test_backtick_fenced_renders_as_code_block(self, parser):
        """Backtick-style fenced directive renders as code block (not directive).

        This is intentional - backticks are reserved for code blocks to avoid
        conflicts when directives appear in code examples.
        """

        content = """
```{note}
This is a note using backticks.
```
"""
        result = parser.parse(content, {})

        # Should render as code block, NOT as admonition
        assert "admonition" not in result.lower()
        assert "<pre><code" in result or "<code" in result

    def test_colon_fenced_note(self, parser):
        """Test colon-style fenced directive (MyST Markdown syntax)."""

        content = """
:::{note}
This is a note using colons.
:::
"""
        result = parser.parse(content, {})

        assert "admonition" in result.lower()
        assert "note" in result.lower()
        assert "This is a note using colons" in result

    def test_code_blocks_and_directives_coexist(self, parser):
        """Test that code blocks and directives work together."""

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
        assert "print" in result
        # Directive should render as admonition
        assert "This warning uses colons" in result
        assert "warning" in result.lower()

    def test_directive_syntax_inside_code_blocks_preserved(self, parser):
        """Test that ::: sequences inside code blocks are NOT parsed as directives.

        This is critical for documentation that shows directive syntax examples.
        The ::: inside a fenced code block should be literal text, not consumed
        by the directive parser.

        Regression test for: directive closing fence inside code block being
        consumed by enclosing directive.
        """
        content = """
::::{tab-set}

:::{tab-item} Example 1
```markdown
:::note
This is a note
:::
```
:::

:::{tab-item} Example 2
```markdown
:::{note}
This is a note
:::
```
:::

::::

Text after the tabs.
"""
        result = parser.parse(content, {})

        # Both tabs should be present
        assert "Example 1" in result
        assert "Example 2" in result

        # The directive syntax should be preserved as literal text in code blocks
        assert ":::note" in result  # From Example 1 code block
        assert ":::{note}" in result  # From Example 2 code block

        # The text after tabs should be present (not consumed by directive)
        assert "Text after the tabs" in result

    def test_nested_colon_directives(self, parser):
        """Test nested MyST-style directives with different colon counts."""

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

    def test_colon_dropdown(self, parser):
        """Test MyST-style dropdown directive."""

        content = """
:::{dropdown} Click to expand
Hidden content here.
:::
"""
        result = parser.parse(content, {})

        assert "Click to expand" in result
        assert "Hidden content here" in result

    def test_colon_tabs(self, parser):
        """Test MyST-style tabs directive with nested tab-items."""

        content = """
::::{tab-set}
:::{tab-item} Python
```python
print("Hello")
```
:::

:::{tab-item} JavaScript
```javascript
console.log("Hello");
```
:::
::::
"""
        result = parser.parse(content, {})

        assert "Python" in result
        assert "JavaScript" in result
        # Check for syntax highlighting (rosettes or Pygments) or escaped HTML
        assert (
            '<span class="syntax-function">print</span>' in result
            or '<span class="nb">print</span>' in result
            or "print(&quot;Hello&quot;)" in result
        )

    def test_directive_with_options_colon_style(self, parser):
        """Test MyST-style directive with options."""

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

    def test_grid_syntax_doesnt_break_parser(self, parser):
        """Test that grid syntax doesn't cause parser errors."""

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

    def test_grid_item_card_syntax(self, parser):
        """Test that grid-item-card syntax doesn't crash."""

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

    def test_all_admonition_types(self, parser):
        """Test that all admonition types work with colon syntax."""

        # Supported types: note, tip, warning, danger, error, info, example, success, caution
        admonition_types = [
            "note",
            "tip",
            "warning",
            "danger",
            "info",
            "error",
            "example",
            "success",
            "caution",
        ]

        for adm_type in admonition_types:
            content = f"""
:::{{{adm_type}}}
This is a {adm_type}.
:::
"""
            result = parser.parse(content, {})
            assert f"This is a {adm_type}" in result
            assert "admonition" in result.lower()

    def test_dropdown_with_colon_syntax(self, parser):
        """Test dropdown directive with colon syntax."""

        content = """
:::{dropdown} Title
Content
:::
"""
        result = parser.parse(content, {})
        assert "Title" in result
        assert "Content" in result
        assert "<details" in result

    def test_code_tabs_with_colon_syntax(self, parser):
        """Test code-tabs directive with colon syntax."""

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


class TestComplexDirectiveCombinations:
    """
    Test complex directive nesting and edge cases.

    These tests cover scenarios commonly found in documentation:
    - Showing directive syntax examples in code blocks
    - Deep nesting of directives
    - Multiple code blocks within directives
    - Edge cases with fence lengths and matching

    """

    def test_three_level_nesting(self, parser):
        """Test three levels of nested directives with proper fence lengths."""
        content = """
::::::{note} Level 1
Outermost note.

:::::{tip} Level 2
Middle tip.

::::{warning} Level 3
Innermost warning.
::::

Back to level 2.
:::::

Back to level 1.
::::::
"""
        result = parser.parse(content, {})

        assert "Outermost note" in result
        assert "Middle tip" in result
        assert "Innermost warning" in result
        assert "Back to level 2" in result
        assert "Back to level 1" in result

    def test_multiple_code_blocks_in_directive(self, parser):
        """Test directive containing multiple code blocks."""
        content = """
:::{note}
Here's Python:

```python
def hello():
    print("Hello")
```

And JavaScript:

```javascript
function hello() {
    console.log("Hello");
}
```

Both examples work!
:::
"""
        result = parser.parse(content, {})

        # Pygments wraps tokens in spans, so check for key identifiers
        assert "hello" in result  # Function name in both languages
        assert "print" in result  # Python function
        assert "console" in result  # JavaScript object
        assert "Both examples work" in result

    def test_code_block_with_triple_colons_inside(self, parser):
        """Test that standalone ::: inside code blocks is preserved."""
        content = """
:::{note}
Here's how directive syntax looks:

```
:::
::: is the basic closing fence
::::::: also works
```

That's the syntax!
:::
"""
        result = parser.parse(content, {})

        # The ::: inside the code block should be literal text
        assert ":::" in result
        assert "is the basic closing fence" in result
        assert "That's the syntax" in result

    def test_nested_tabs_with_code_examples(self, parser):
        """Test tabs containing code blocks with directive examples - common in docs."""
        content = """
::::::{tab-set}

:::::{tab-item} Before (Other SSGs)
```markdown
.. note::
   RST syntax note

:::tip
Docusaurus tip
:::
```
:::::

:::::{tab-item} After (Bengal)
```markdown
:::{note}
Bengal note with **markdown**
:::

:::{tip}
Bengal tip
:::
```
:::::

::::::

See the difference!
"""
        result = parser.parse(content, {})

        # Both tabs present
        assert "Before" in result
        assert "After" in result

        # Directive syntax preserved as literal text in code blocks
        assert ".. note::" in result  # RST syntax
        assert ":::tip" in result  # Docusaurus syntax
        assert ":::{note}" in result  # Bengal syntax

        # Text after tabs
        assert "See the difference" in result

    def test_dropdown_containing_tabs_with_code(self, parser):
        """Test dropdown > tabs > code with directive examples."""
        content = """
:::::{dropdown} Click to see examples
::::{tab-set}

:::{tab-item} Example 1
```markdown
:::{warning}
Warning example
:::
```
:::

:::{tab-item} Example 2
```markdown
:::{danger}
Danger example
:::
```
:::

::::
:::::
"""
        result = parser.parse(content, {})

        # Dropdown renders
        assert "<details" in result
        assert "Click to see examples" in result

        # Both tab items present
        assert "Example 1" in result
        assert "Example 2" in result

        # Directive syntax preserved in code
        assert ":::{warning}" in result
        assert ":::{danger}" in result

    def test_admonition_with_nested_directive_example(self, parser):
        """Test admonition containing code block showing nested directive syntax."""
        content = """
:::{tip} Pro Tip
You can nest directives! Here's how:

```markdown
::::{note} Outer
Content here

:::{tip} Inner
Nested content
:::

::::
```

Use more colons for outer directives.
:::
"""
        result = parser.parse(content, {})

        assert "Pro Tip" in result
        assert "You can nest directives" in result
        # Nested directive example preserved in code
        assert "::::{note}" in result
        assert ":::{tip}" in result
        assert "Use more colons" in result

    def test_tilde_fence_code_block_inside_directive(self, parser):
        """Test tilde-fenced code block inside a directive."""
        content = """
:::{note}
Using tilde fences:

~~~python
def example():
    # Code with :::
    marker = ":::"
    return marker
~~~

Tildes work too!
:::
"""
        result = parser.parse(content, {})

        # Pygments wraps tokens in spans, so check for key elements
        assert "example" in result  # Function name
        assert "marker" in result  # Variable name
        assert ":::" in result  # The string content (may be escaped)
        assert "Tildes work too" in result

    def test_inline_directive_syntax_in_text(self, parser):
        """Test that inline ::: in text doesn't break parsing."""
        content = """
:::{note}
Use `:::` to close directives. The `:::{name}` opens them.

For example: `:::{warning}` opens a warning box.

Multiple colons like `::::` or `::::::` allow nesting.
:::
"""
        result = parser.parse(content, {})

        assert "Use <code>:::</code>" in result or "Use `:::`" in result
        assert "opens a warning box" in result

    def test_empty_code_block_in_directive(self, parser):
        """Test directive containing empty code block."""
        content = """
:::{note}
Before code.

```python
```

After code.
:::
"""
        result = parser.parse(content, {})

        assert "Before code" in result
        assert "After code" in result

    def test_code_block_with_only_fence_markers(self, parser):
        """Test code block containing only fence-like content."""
        content = """
:::{note}
Fence reference:

```
:::
::::
:::::
```

Those are fence lengths.
:::
"""
        result = parser.parse(content, {})

        assert "Fence reference" in result
        assert "Those are fence lengths" in result

    def test_sequential_directives_after_code_block_example(self, parser):
        """Test multiple directives after one shows directive syntax."""
        content = """
:::{note}
Example syntax:

```markdown
:::{tip}
Tip content
:::
```
:::

:::{warning}
This is a real warning, not an example.
:::

:::{tip}
This is a real tip!
:::
"""
        result = parser.parse(content, {})

        # Example in code block
        assert "Example syntax" in result
        assert "Tip content" in result

        # Real directives after
        assert "This is a real warning" in result
        assert "This is a real tip" in result

        # Should have multiple admonition divs
        assert result.count("admonition") >= 3

    def test_mixed_fence_lengths_deep_nesting(self, parser):
        """Test complex nesting with various fence lengths."""
        content = """
:::::::{tab-set}

::::::{tab-item} Tab A
:::::{note} Note in Tab A
::::{dropdown} Dropdown in Note
:::{tip}
Deeply nested tip!
:::
::::
:::::
::::::

::::::{tab-item} Tab B
Just plain content in Tab B.
::::::

:::::::
"""
        result = parser.parse(content, {})

        assert "Tab A" in result
        assert "Tab B" in result
        assert "Note in Tab A" in result
        assert "Deeply nested tip" in result
        assert "Just plain content" in result

    def test_adjacent_code_blocks_with_directives(self, parser):
        """Test multiple adjacent code blocks containing directive syntax."""
        content = """
:::{note}
Docusaurus syntax:

```markdown
:::note
Note content
:::
```

MyST syntax:

```markdown
:::{note}
Note content
:::
```

Both work differently!
:::
"""
        result = parser.parse(content, {})

        # Both code blocks preserved
        assert "Docusaurus syntax" in result
        assert "MyST syntax" in result
        assert ":::note" in result  # Docusaurus style
        assert ":::{note}" in result  # MyST style
        assert "Both work differently" in result


class TestDirectiveEdgeCases:
    """
    Test edge cases that could cause parsing issues.

    These tests help ensure the health check warnings are accurate
    and that edge cases don't break the build.

    """

    def test_directive_at_end_of_file_no_trailing_newline(self, parser):
        """Test directive at end of file without trailing newline."""
        content = """:::{note}
Content here.
:::"""  # No trailing newline

        result = parser.parse(content, {})
        assert "Content here" in result

    def test_directive_with_blank_lines(self, parser):
        """Test directive with multiple blank lines in content."""
        content = """
:::{note}
First paragraph.


Second paragraph after two blank lines.



Third paragraph after three blank lines.
:::
"""
        result = parser.parse(content, {})

        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "Third paragraph" in result

    def test_unclosed_code_block_in_directive(self, parser):
        """Test handling of unclosed code block inside directive."""
        # This is malformed but shouldn't crash
        content = """
:::{note}
Here's some code:

```python
def broken():
    pass

Missing closing fence above.
:::
"""
        try:
            result = parser.parse(content, {})
            # Should not crash
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Parser should handle malformed content gracefully: {e}")

    def test_mismatched_fence_lengths_graceful(self, parser):
        """Test that mismatched fence lengths are handled gracefully."""
        # Opening with 4, closing with 3 - technically malformed
        content = """
::::{note}
Content here.
:::
"""
        try:
            result = parser.parse(content, {})
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Parser should handle fence mismatch gracefully: {e}")

    def test_directive_name_with_special_chars(self, parser):
        """Test directive names with hyphens and underscores."""
        content = """
:::{tab-set}
:::{tab-item} Test
Content
:::
:::

:::{code-tabs}
### Lang
code
:::
"""
        result = parser.parse(content, {})
        # Should parse without error
        assert isinstance(result, str)

    def test_very_long_fence(self, parser):
        """Test directive with very long fence."""
        content = """
:::::::::::::::::{note}
Content with many colons in fence.
:::::::::::::::::
"""
        result = parser.parse(content, {})
        assert "Content with many colons" in result

    def test_code_block_info_string_with_directive_like_content(self, parser):
        """Test code block with info string containing curly braces."""
        content = """
:::{note}
A code block:

```python {linenos=table}
print("hello")
```

Done.
:::
"""
        result = parser.parse(content, {})
        assert "hello" in result
        assert "Done" in result

    def test_directive_syntax_in_blockquote(self, parser):
        """Test that directive syntax in blockquotes is handled."""
        content = """
> Here's a quoted directive syntax:
>
> ```markdown
> :::{note}
> Quoted note
> :::
> ```

After the blockquote.
"""
        result = parser.parse(content, {})
        assert "<blockquote" in result
        assert "After the blockquote" in result
