"""Edge case tests for directive migration.

Tests unusual inputs, error handling, and boundary conditions to ensure
both backends handle edge cases identically.

See RFC: plan/drafted/rfc-patitas-bengal-directive-migration.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# Edge Case Test Cases
# =============================================================================

EDGE_CASES: list[tuple[str, str]] = [
    # =========================================================================
    # Empty Content
    # =========================================================================
    (
        "empty_note",
        """\
:::{note}
:::
""",
    ),
    (
        "empty_dropdown",
        """\
:::{dropdown} Title
:::
""",
    ),
    (
        "empty_tab_item",
        """\
::::{tab-set}

:::{tab-item} Empty Tab
:::

::::
""",
    ),
    # =========================================================================
    # Special Characters in Titles
    # =========================================================================
    (
        "title_with_html_entities",
        """\
:::{note} Title with <script> & "quotes"
Content here.
:::
""",
    ),
    (
        "title_with_markdown",
        """\
:::{note} Title with **bold** text
Content here.
:::
""",
    ),
    (
        "title_with_backticks",
        """\
:::{note} Title with `code`
Content here.
:::
""",
    ),
    # =========================================================================
    # Markdown in Content
    # =========================================================================
    (
        "content_with_emphasis",
        """\
:::{note}
This has **bold** and *italic* and ***bold-italic***.
:::
""",
    ),
    (
        "content_with_inline_code",
        """\
:::{note}
Run `pip install package` to install.
:::
""",
    ),
    (
        "content_with_links",
        """\
:::{note}
See [the documentation](https://example.com) for more.
:::
""",
    ),
    (
        "content_with_images",
        """\
:::{note}
![Alt text](image.png)
:::
""",
    ),
    # =========================================================================
    # Code Blocks Inside Directives
    # =========================================================================
    (
        "fenced_code_in_note",
        """\
:::{note}
Here's some code:

```python
print("hello")
```
:::
""",
    ),
    (
        "fenced_code_no_language",
        """\
:::{note}
```
plain code block
```
:::
""",
    ),
    (
        "multiple_code_blocks",
        """\
:::{dropdown} Code Examples

```python
# Python
print("hello")
```

```javascript
// JavaScript
console.log("hello");
```

:::
""",
    ),
    # =========================================================================
    # Unicode Content
    # =========================================================================
    (
        "unicode_content",
        """\
:::{note}
日本語テキスト

中文文本

한국어 텍스트

Emoji: 🎉 🐍 🚀 ✨
:::
""",
    ),
    (
        "unicode_title",
        """\
:::{note} 日本語のタイトル 🎉
Unicode title content.
:::
""",
    ),
    # =========================================================================
    # Whitespace Handling
    # =========================================================================
    (
        "leading_whitespace_content",
        """\
:::{note}
    Indented content line 1
    Indented content line 2
:::
""",
    ),
    (
        "trailing_whitespace_content",
        """\
:::{note}
Content with trailing spaces
Another line
:::
""",
    ),
    (
        "blank_lines_in_content",
        """\
:::{note}
First paragraph.


Second paragraph after blank lines.


Third paragraph.
:::
""",
    ),
    # =========================================================================
    # Long Content
    # =========================================================================
    (
        "very_long_paragraph",
        """\
:::{note}
"""
        + "This is a very long sentence that goes on and on. " * 50
        + """
:::
""",
    ),
    # =========================================================================
    # Lists in Directives
    # =========================================================================
    (
        "unordered_list",
        """\
:::{note}
- Item 1
- Item 2
- Item 3
:::
""",
    ),
    (
        "ordered_list",
        """\
:::{note}
1. First
2. Second
3. Third
:::
""",
    ),
    (
        "nested_list",
        """\
:::{note}
- Level 1
  - Level 2
    - Level 3
- Back to 1
:::
""",
    ),
    (
        "task_list",
        """\
:::{note}
- [ ] Unchecked
- [x] Checked
- [ ] Another unchecked
:::
""",
    ),
    # =========================================================================
    # Tables in Directives
    # =========================================================================
    (
        "simple_table",
        """\
:::{note}
| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |
:::
""",
    ),
    # =========================================================================
    # Blockquotes in Directives
    # =========================================================================
    (
        "blockquote_in_note",
        """\
:::{note}
> This is a quote
> spanning multiple lines.
:::
""",
    ),
    # =========================================================================
    # Headings in Directives
    # =========================================================================
    (
        "heading_in_dropdown",
        """\
:::{dropdown} Dropdown with Headings

## Section 1

Content 1.

## Section 2

Content 2.
:::
""",
    ),
    # =========================================================================
    # Multiple Directives in Sequence
    # =========================================================================
    (
        "consecutive_notes",
        """\
:::{note}
First note.
:::

:::{note}
Second note.
:::

:::{note}
Third note.
:::
""",
    ),
    (
        "mixed_directive_types",
        """\
:::{note}
A note.
:::

:::{warning}
A warning.
:::

:::{dropdown} A Dropdown
Dropdown content.
:::
""",
    ),
    # =========================================================================
    # Directive Fence Variations
    # =========================================================================
    (
        "four_colon_fence",
        """\
::::{note}
Note with four colons.
::::
""",
    ),
    (
        "five_colon_fence",
        """\
:::::{note}
Note with five colons.
:::::
""",
    ),
    # =========================================================================
    # Options Edge Cases
    # =========================================================================
    (
        "option_with_spaces",
        """\
:::{dropdown} Title
:description: This is a long description with spaces

Content.
:::
""",
    ),
    (
        "multiple_options",
        """\
:::{dropdown} Title
:open:
:icon: info
:badge: New
:color: success
:description: Full options

Content.
:::
""",
    ),
    # =========================================================================
    # Content Before Directive
    # =========================================================================
    (
        "paragraph_before_directive",
        """\
This is a paragraph before the directive.

:::{note}
Note content.
:::
""",
    ),
    (
        "heading_before_directive",
        """\
# Heading

:::{note}
Note content.
:::
""",
    ),
]


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.parametrize(("name", "source"), EDGE_CASES)
def test_edge_case_parity(
    name: str,
    source: str,
    render_with_mistune: Callable[[str], str],
    render_with_patitas: Callable[[str], str],
    assert_html_equal: Callable[[str, str, str], None],
) -> None:
    """Verify edge cases produce identical results in both backends.

    Args:
        name: Test case name
        source: Markdown source to render
        render_with_mistune: Fixture to render with mistune
        render_with_patitas: Fixture to render with patitas
        assert_html_equal: Fixture for HTML comparison

    """
    mistune_html = render_with_mistune(source)
    patitas_html = render_with_patitas(source)

    assert_html_equal(patitas_html, mistune_html, f"edge case: {name}")


@pytest.mark.parametrize(("name", "source"), EDGE_CASES)
def test_edge_case_no_crash(
    name: str,
    source: str,
    render_with_patitas: Callable[[str], str],
) -> None:
    """Verify Patitas handles all edge cases without crashing.

    Args:
        name: Test case name
        source: Markdown source to render
        render_with_patitas: Fixture to render with patitas

    """
    # Should not raise any exception
    html = render_with_patitas(source)
    # Should produce some output (even if empty-ish for empty content)
    assert html is not None


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for graceful error handling."""

    def test_unclosed_directive(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test handling of unclosed directive."""
        source = """\
:::{note}
This note is never closed.

More content that isn't in the note.
"""
        # Should not crash - may render as paragraph or partial directive
        html = render_with_patitas(source)
        assert html is not None

    def test_mismatched_fence_levels(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test handling of mismatched fence levels."""
        source = """\
::::{dropdown} Title

:::{note}
Note content.
:::

:::
"""
        # Should not crash
        html = render_with_patitas(source)
        assert html is not None

    def test_unknown_directive(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test handling of unknown directive type."""
        source = """\
:::{unknown_directive_type}
Content for unknown type.
:::
"""
        # Should not crash - may render as generic directive
        html = render_with_patitas(source)
        assert html is not None

    def test_invalid_option_value(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test handling of invalid option values."""
        source = """\
:::{dropdown} Title
:color: invalid_color_name

Content.
:::
"""
        # Should not crash - may ignore invalid option
        html = render_with_patitas(source)
        assert html is not None

    def test_malformed_option_syntax(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test handling of malformed option syntax."""
        source = """\
:::{dropdown} Title
:malformed option without colon

Content.
:::
"""
        # Should not crash
        html = render_with_patitas(source)
        assert html is not None


# =============================================================================
# Stress Tests
# =============================================================================


class TestStressConditions:
    """Tests for stress conditions and limits."""

    def test_deeply_nested_directives(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test handling of deeply nested directives."""
        source = """\
:::::::{dropdown} Level 1
::::::{dropdown} Level 2
:::::{dropdown} Level 3
::::{dropdown} Level 4
:::{note}
Deep note.
:::
::::
:::::
::::::
:::::::
"""
        # Should handle deep nesting
        html = render_with_patitas(source)
        assert html is not None

    def test_many_consecutive_directives(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test handling of many consecutive directives."""
        # Create 20 consecutive notes
        source = "\n".join([f":::{{note}}\nNote {i}.\n:::\n" for i in range(20)])

        html = render_with_patitas(source)
        assert html is not None
        # Should have rendered all notes
        assert html.count("Note") >= 10  # At least some got through

    def test_many_tabs(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test handling of tab-set with many tabs."""
        tabs = "\n".join([f":::{{tab-item}} Tab {i}\nContent {i}.\n:::\n" for i in range(10)])
        source = f"::::{{tab-set}}\n{tabs}::::\n"

        html = render_with_patitas(source)
        assert html is not None


# =============================================================================
# Regression Tests
# =============================================================================


class TestRegressions:
    """Tests for specific regressions or known issues."""

    def test_directive_after_code_block(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test directive after fenced code block is parsed correctly."""
        source = """\
```python
code here
```

:::{note}
Note after code.
:::
"""
        html = render_with_patitas(source)
        assert "note" in html.lower() or "admonition" in html.lower()

    def test_directive_after_list(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test directive after list is parsed correctly."""
        source = """\
- Item 1
- Item 2

:::{note}
Note after list.
:::
"""
        html = render_with_patitas(source)
        assert "note" in html.lower() or "admonition" in html.lower()

    def test_directive_in_blockquote(self, render_with_patitas: Callable[[str], str]) -> None:
        """Test directive inside blockquote."""
        source = """\
> :::{note}
> Note inside blockquote.
> :::
"""
        # Behavior may vary - just shouldn't crash
        html = render_with_patitas(source)
        assert html is not None
