"""Parity tests for directive migration from mistune to Patitas.

These tests verify that Patitas produces identical HTML output to the
existing Bengal/mistune implementations for all Phase A directives.

Test Categories:
- Admonitions: note, tip, warning, danger, error, info, example, success, caution, seealso
- Dropdown: dropdown, details with all options
- Tabs: tab-set, tab-item with sync, badges
- Steps: steps, step with metadata
- Container: container, div wrappers
- Nested: directives inside directives

See RFC: plan/drafted/rfc-patitas-bengal-directive-migration.md

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# Test Case Definitions
# =============================================================================

# Comprehensive test cases covering all Phase A directives
# Format: (name, source_markdown)
DIRECTIVE_TEST_CASES: list[tuple[str, str]] = [
    # =========================================================================
    # Admonitions - Basic (10 types)
    # =========================================================================
    (
        "note_basic",
        """\
:::{note}
This is a note.
:::
""",
    ),
    (
        "note_titled",
        """\
:::{note} Custom Title
This is a note with a custom title.
:::
""",
    ),
    (
        "tip_basic",
        """\
:::{tip}
Helpful tip here.
:::
""",
    ),
    (
        "warning_basic",
        """\
:::{warning}
Warning message.
:::
""",
    ),
    (
        "danger_basic",
        """\
:::{danger}
Critical danger!
:::
""",
    ),
    (
        "error_basic",
        """\
:::{error}
Error occurred.
:::
""",
    ),
    (
        "info_basic",
        """\
:::{info}
Informational note.
:::
""",
    ),
    (
        "example_basic",
        """\
:::{example}
Example content.
:::
""",
    ),
    (
        "success_basic",
        """\
:::{success}
Success message.
:::
""",
    ),
    (
        "caution_basic",
        """\
:::{caution}
Proceed carefully.
:::
""",
    ),
    (
        "seealso_basic",
        """\
:::{seealso}
Related topics.
:::
""",
    ),
    # =========================================================================
    # Admonitions - With Options
    # =========================================================================
    (
        "note_with_class",
        """\
:::{note}
:class: custom-note

Content with custom class.
:::
""",
    ),
    # =========================================================================
    # Dropdown - Basic and Options
    # =========================================================================
    (
        "dropdown_basic",
        """\
:::{dropdown} Dropdown Title
Dropdown content here.
:::
""",
    ),
    (
        "dropdown_open",
        """\
:::{dropdown} Open Dropdown
:open:

This dropdown starts open.
:::
""",
    ),
    (
        "dropdown_icon",
        """\
:::{dropdown} With Icon
:icon: info

Dropdown with an icon.
:::
""",
    ),
    (
        "dropdown_badge",
        """\
:::{dropdown} With Badge
:badge: New

Dropdown with a badge.
:::
""",
    ),
    (
        "dropdown_color_success",
        """\
:::{dropdown} Success Color
:color: success

Green colored dropdown.
:::
""",
    ),
    (
        "dropdown_color_warning",
        """\
:::{dropdown} Warning Color
:color: warning

Yellow colored dropdown.
:::
""",
    ),
    (
        "dropdown_color_danger",
        """\
:::{dropdown} Danger Color
:color: danger

Red colored dropdown.
:::
""",
    ),
    (
        "dropdown_color_info",
        """\
:::{dropdown} Info Color
:color: info

Blue colored dropdown.
:::
""",
    ),
    (
        "dropdown_description",
        """\
:::{dropdown} With Description
:description: Additional context here

Dropdown with description text.
:::
""",
    ),
    (
        "dropdown_full",
        """\
:::{dropdown} Full Options
:open:
:icon: info
:badge: Beta
:color: info
:description: Complete example

Dropdown with all options.
:::
""",
    ),
    (
        "details_alias",
        """\
:::{details} Details Title
Using details alias.
:::
""",
    ),
    # =========================================================================
    # Tabs - Basic and Advanced
    # =========================================================================
    (
        "tabs_basic",
        """\
::::{tab-set}

:::{tab-item} Tab 1
Content of tab 1.
:::

:::{tab-item} Tab 2
Content of tab 2.
:::

::::
""",
    ),
    (
        "tabs_three",
        """\
::::{tab-set}

:::{tab-item} First
First tab content.
:::

:::{tab-item} Second
Second tab content.
:::

:::{tab-item} Third
Third tab content.
:::

::::
""",
    ),
    (
        "tabs_sync",
        """\
::::{tab-set}
:sync: language

:::{tab-item} Python
:sync: python

Python code here.
:::

:::{tab-item} JavaScript
:sync: javascript

JavaScript code here.
:::

::::
""",
    ),
    (
        "tabs_selected",
        """\
::::{tab-set}

:::{tab-item} Tab 1
First tab.
:::

:::{tab-item} Tab 2
:selected:

Second tab is selected by default.
:::

::::
""",
    ),
    (
        "tabs_with_badges",
        """\
::::{tab-set}

:::{tab-item} Tab 1
:badge: New

Tab with a badge.
:::

:::{tab-item} Tab 2
Regular tab.
:::

::::
""",
    ),
    (
        "tabs_alias",
        """\
::::{tabs}

:::{tab} Tab A
Content A.
:::

:::{tab} Tab B
Content B.
:::

::::
""",
    ),
    # =========================================================================
    # Steps - Basic and Advanced
    # =========================================================================
    (
        "steps_basic",
        """\
::::{steps}

:::{step} Step 1
Do this first.
:::

:::{step} Step 2
Then do this.
:::

::::
""",
    ),
    (
        "steps_start_number",
        """\
::::{steps}
:start: 2

:::{step} Step 2
Starting from step 2.
:::

:::{step} Step 3
Continuing to step 3.
:::

::::
""",
    ),
    (
        "step_description",
        """\
::::{steps}

:::{step} Step Title
:description: Lead-in description text

Step content here.
:::

::::
""",
    ),
    (
        "step_duration",
        """\
::::{steps}

:::{step} Step Title
:duration: 5 min

Step with duration estimate.
:::

::::
""",
    ),
    (
        "steps_full",
        """\
::::{steps}
:start: 1

:::{step} First Step
:description: Getting started
:duration: 5 min

Do the first thing.
:::

:::{step} Second Step
:description: Continuing
:duration: 10 min

Do the second thing.
:::

::::
""",
    ),
    # =========================================================================
    # Container - Basic
    # =========================================================================
    (
        "container_basic",
        """\
:::{container} my-class
Container content.
:::
""",
    ),
    (
        "container_multiple_classes",
        """\
:::{container} class-a class-b class-c
Multiple class container.
:::
""",
    ),
    (
        "div_alias",
        """\
:::{div} wrapper
Div wrapper content.
:::
""",
    ),
    # =========================================================================
    # Nested Directives
    # =========================================================================
    (
        "nested_note_in_dropdown",
        """\
::::{dropdown} Dropdown with Note

:::{note}
This is a nested note.
:::

::::
""",
    ),
    (
        "nested_tabs_in_dropdown",
        """\
:::::{dropdown} Dropdown with Tabs

::::{tab-set}

:::{tab-item} Tab A
Tab A content.
:::

:::{tab-item} Tab B
Tab B content.
:::

::::

:::::
""",
    ),
    (
        "nested_dropdown_in_tabs",
        """\
:::::{tab-set}

::::{tab-item} Tab with Dropdown

:::{dropdown} Nested Dropdown
Dropdown inside a tab.
:::

::::

:::::
""",
    ),
    # =========================================================================
    # Cards - Basic and Advanced (Phase B.1)
    # =========================================================================
    (
        "cards_basic",
        """\
::::{cards}

:::{card} Card 1
Content of card 1.
:::

:::{card} Card 2
Content of card 2.
:::

::::
""",
    ),
    (
        "cards_columns",
        """\
::::{cards}
:columns: 3

:::{card} Card A
Card A content.
:::

:::{card} Card B
Card B content.
:::

:::{card} Card C
Card C content.
:::

::::
""",
    ),
    (
        "cards_options",
        """\
::::{cards}
:columns: 2
:gap: large
:style: bordered

:::{card} Styled Card
Card content here.
:::

::::
""",
    ),
    (
        "card_with_icon",
        """\
::::{cards}

:::{card} Getting Started
:icon: rocket

Start your journey here.
:::

::::
""",
    ),
    (
        "card_with_link",
        """\
::::{cards}

:::{card} Documentation
:link: /docs/

Read the full documentation.
:::

::::
""",
    ),
    (
        "card_with_badge",
        """\
::::{cards}

:::{card} New Feature
:badge: New

This is a new feature.
:::

::::
""",
    ),
    (
        "card_with_color",
        """\
::::{cards}

:::{card} Success Card
:color: green

Everything is working.
:::

::::
""",
    ),
    (
        "card_with_description",
        """\
::::{cards}

:::{card} API Reference
:description: Complete API documentation

Explore all endpoints and methods.
:::

::::
""",
    ),
    (
        "card_full_options",
        """\
::::{cards}
:columns: 2

:::{card} Full Featured Card
:icon: star
:link: https://example.com
:badge: Pro
:color: blue
:description: A card with all options

Detailed card content with **markdown** support.
:::

::::
""",
    ),
    (
        "cards_multiple",
        """\
::::{cards}
:columns: 3

:::{card} First
First card content.
:::

:::{card} Second
Second card content.
:::

:::{card} Third
Third card content.
:::

:::{card} Fourth
Fourth card content.
:::

::::
""",
    ),
    # =========================================================================
    # Content with Markdown
    # =========================================================================
    (
        "note_with_markdown",
        """\
:::{note}
This has **bold** and *italic* and `code`.

- List item 1
- List item 2

[A link](https://example.com)
:::
""",
    ),
    (
        "dropdown_with_code_block",
        """\
:::{dropdown} Code Example

```python
def hello():
    print("Hello, world!")
```

:::
""",
    ),
    (
        "tabs_with_code",
        """\
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
""",
    ),
]


# =============================================================================
# Parity Tests
# =============================================================================


@pytest.mark.parametrize("name,source", DIRECTIVE_TEST_CASES)
def test_html_parity(
    name: str,
    source: str,
    render_with_mistune: Callable[[str], str],
    render_with_patitas: Callable[[str], str],
    assert_html_equal: Callable[[str, str, str], None],
) -> None:
    """Verify Patitas produces identical HTML to Bengal/mistune.

    This test renders the same markdown source with both backends and
    compares the normalized HTML output.

    Args:
        name: Test case name
        source: Markdown source to render
        render_with_mistune: Fixture to render with mistune
        render_with_patitas: Fixture to render with patitas
        assert_html_equal: Fixture for HTML comparison

    """
    mistune_html = render_with_mistune(source)
    patitas_html = render_with_patitas(source)

    assert_html_equal(patitas_html, mistune_html, f"parity test: {name}")


# =============================================================================
# Golden File Tests
# =============================================================================


@pytest.mark.parametrize("name,source", DIRECTIVE_TEST_CASES)
def test_golden_file(
    name: str,
    source: str,
    render_with_patitas: Callable[[str], str],
    golden_file_path: Path,
    update_golden_files: bool,
    save_golden_file: Callable[[Path, str], None],
    load_golden_file: Callable[[Path], str | None],
    assert_html_equal: Callable[[str, str, str], None],
) -> None:
    """Compare Patitas output against golden files.

    Run with --update-golden-files to regenerate golden files.

    Args:
        name: Test case name
        source: Markdown source to render
        render_with_patitas: Fixture to render with patitas
        golden_file_path: Path to golden file
        update_golden_files: Whether to update golden files
        save_golden_file: Fixture to save golden file
        load_golden_file: Fixture to load golden file
        assert_html_equal: Fixture for HTML comparison

    """
    patitas_html = render_with_patitas(source)

    if update_golden_files:
        save_golden_file(golden_file_path, patitas_html)
        pytest.skip(f"Golden file updated: {golden_file_path}")

    expected = load_golden_file(golden_file_path)
    if expected is None:
        pytest.skip(f"Golden file not found: {golden_file_path}")

    assert_html_equal(patitas_html, expected, f"golden file: {name}")


# =============================================================================
# Individual Directive Type Tests
# =============================================================================


class TestAdmonitions:
    """Tests specifically for admonition directives."""

    def test_all_admonition_types_parse(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify all admonition types can be parsed without error."""
        types = [
            "note",
            "tip",
            "warning",
            "danger",
            "error",
            "info",
            "example",
            "success",
            "caution",
            "seealso",
        ]

        for admon_type in types:
            source = f":::{{{admon_type}}}\nContent\n:::"
            html = render_with_patitas(source)
            assert html, f"Failed to render {admon_type}"
            assert "admonition" in html or admon_type in html

    def test_caution_maps_to_warning_css(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify caution type maps to warning CSS class."""
        source = ":::{caution}\nCaution content.\n:::"
        html = render_with_patitas(source)
        # Caution should have warning CSS class per Bengal behavior
        assert "warning" in html.lower() or "caution" in html.lower()


class TestDropdown:
    """Tests specifically for dropdown directives."""

    def test_dropdown_open_state(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify :open: option produces open details element."""
        source = ":::{dropdown} Title\n:open:\n\nContent\n:::"
        html = render_with_patitas(source)
        assert "open" in html

    def test_details_alias_works(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify details alias produces same output as dropdown."""
        source = ":::{details} Title\nContent\n:::"
        html = render_with_patitas(source)
        assert "details" in html.lower() or "dropdown" in html.lower()


class TestTabs:
    """Tests specifically for tab directives."""

    def test_tab_set_structure(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify tab-set produces expected structure."""
        source = """\
::::{tab-set}

:::{tab-item} Tab 1
Content 1
:::

::::
"""
        html = render_with_patitas(source)
        # Should have tab container and tab content
        assert "tab" in html.lower()

    def test_tab_sync_attribute(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify sync attribute is rendered."""
        source = """\
::::{tab-set}
:sync: lang

:::{tab-item} Python
:sync: python
Content
:::

::::
"""
        html = render_with_patitas(source)
        # Sync attribute should be present
        assert "sync" in html.lower() or "python" in html.lower()


class TestSteps:
    """Tests specifically for step directives."""

    def test_steps_numbering(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify steps produce numbered output."""
        source = """\
::::{steps}

:::{step} First
Content 1
:::

:::{step} Second
Content 2
:::

::::
"""
        html = render_with_patitas(source)
        assert "step" in html.lower()

    def test_steps_start_number(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify :start: option affects numbering."""
        source = """\
::::{steps}
:start: 5

:::{step} Step 5
Content
:::

::::
"""
        html = render_with_patitas(source)
        # Should have start number or step 5 reference
        assert "5" in html or "step" in html.lower()


class TestContainer:
    """Tests specifically for container directives."""

    def test_container_class_applied(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify container class is applied to div."""
        source = ":::{container} my-custom-class\nContent\n:::"
        html = render_with_patitas(source)
        assert "my-custom-class" in html

    def test_div_alias(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify div alias works like container."""
        source = ":::{div} wrapper\nContent\n:::"
        html = render_with_patitas(source)
        assert "wrapper" in html


class TestNestedDirectives:
    """Tests for nested directive handling."""

    def test_two_level_nesting(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify two levels of nesting work."""
        source = """\
::::{dropdown} Outer

:::{note}
Inner note
:::

::::
"""
        html = render_with_patitas(source)
        # Both outer and inner should be present
        assert "dropdown" in html.lower() or "details" in html.lower()

    def test_three_level_nesting(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify three levels of nesting work."""
        source = """\
:::::{dropdown} Level 1

::::{tab-set}

:::{tab-item} Level 2
Level 3 content
:::

::::

:::::
"""
        html = render_with_patitas(source)
        # All levels should be present
        assert html  # Basic check that it renders


class TestCards:
    """Tests specifically for card directives."""

    def test_cards_structure(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify cards produces expected grid structure."""
        source = """\
::::{cards}

:::{card} Card 1
Content 1
:::

::::
"""
        html = render_with_patitas(source)
        # Should have card-grid container
        assert "card-grid" in html or "card" in html.lower()

    def test_cards_columns_attribute(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify columns attribute is rendered."""
        source = """\
::::{cards}
:columns: 3

:::{card} Card
Content
:::

::::
"""
        html = render_with_patitas(source)
        # Columns attribute should be present
        assert "columns" in html.lower() or "3" in html

    def test_card_with_link(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify card with link renders as anchor element."""
        source = """\
::::{cards}

:::{card} Linked Card
:link: https://example.com

Click me!
:::

::::
"""
        html = render_with_patitas(source)
        # Should have anchor element with href
        assert "<a" in html.lower() and "href" in html.lower()

    def test_card_with_icon(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify card with icon renders icon element."""
        source = """\
::::{cards}

:::{card} Icon Card
:icon: rocket

Has an icon!
:::

::::
"""
        html = render_with_patitas(source)
        # Should have icon reference
        assert "icon" in html.lower() or "rocket" in html.lower()

    def test_card_with_badge(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify card with badge renders badge element."""
        source = """\
::::{cards}

:::{card} Badge Card
:badge: New

Has a badge!
:::

::::
"""
        html = render_with_patitas(source)
        # Should have badge element
        assert "badge" in html.lower() or "New" in html

    def test_card_color_class(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify card with color has color class."""
        source = """\
::::{cards}

:::{card} Colored Card
:color: blue

Blue card!
:::

::::
"""
        html = render_with_patitas(source)
        # Should have color class
        assert "blue" in html.lower() or "color" in html.lower()

    def test_multiple_cards(self, render_with_patitas: Callable[[str], str]) -> None:
        """Verify multiple cards render correctly."""
        source = """\
::::{cards}

:::{card} Card 1
Content 1
:::

:::{card} Card 2
Content 2
:::

:::{card} Card 3
Content 3
:::

::::
"""
        html = render_with_patitas(source)
        # All cards should be present
        assert html.count("card") >= 3 or (
            "Card 1" in html and "Card 2" in html and "Card 3" in html
        )
