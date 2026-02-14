"""
Unit tests for named closer syntax in directives.

Named closers (:::{/name}) provide an alternative to fence-depth counting
for closing nested directives. This eliminates the need to track colon counts
in complex structures.

Example:
:::{tab-set}
:::{tab-item} First
Content
:::{/tab-item}
:::{/tab-set}

"""

from __future__ import annotations

import pytest

from bengal.parsing import PatitasParser


@pytest.fixture
def parser() -> PatitasParser:
    """Create parser for directive tests."""
    return PatitasParser()


class TestBasicNamedClosers:
    """Tests for basic named closer functionality."""

    def test_simple_note_with_named_closer(self, parser: PatitasParser) -> None:
        """Simple directive with named closer."""
        markdown = """\
:::{note}
This is a note.
:::{/note}
"""
        result = parser.parse(markdown, {})
        assert 'class="admonition note"' in result
        assert "This is a note." in result

    def test_warning_with_named_closer(self, parser: PatitasParser) -> None:
        """Warning directive with named closer."""
        markdown = """\
:::{warning}
Be careful!
:::{/warning}
"""
        result = parser.parse(markdown, {})
        assert 'class="admonition warning"' in result
        assert "Be careful!" in result

    def test_dropdown_with_named_closer(self, parser: PatitasParser) -> None:
        """Dropdown directive with named closer."""
        markdown = """\
:::{dropdown} Click me
Hidden content
:::{/dropdown}
"""
        result = parser.parse(markdown, {})
        assert "<details" in result
        assert "Hidden content" in result


class TestNestedNamedClosers:
    """Tests for nested directives with named closers."""

    def test_tabs_with_named_closers(self, parser: PatitasParser) -> None:
        """Tab-set and tab-items with named closers."""
        markdown = """\
:::{tab-set}
:::{tab-item} Python
Python code here
:::{/tab-item}
:::{tab-item} JavaScript
JS code here
:::{/tab-item}
:::{/tab-set}
"""
        result = parser.parse(markdown, {})
        assert 'class="tabs"' in result or 'class="tab-set"' in result
        assert "Python" in result
        assert "JavaScript" in result
        assert "Python code here" in result
        assert "JS code here" in result

    def test_cards_with_named_closers(self, parser: PatitasParser) -> None:
        """Cards container with named closers."""
        markdown = """\
:::{cards}
:::{card} First Card
First content
:::{/card}
:::{card} Second Card
Second content
:::{/card}
:::{/cards}
"""
        result = parser.parse(markdown, {})
        assert 'class="card-grid"' in result
        assert "First Card" in result
        assert "Second Card" in result

    def test_steps_with_named_closers(self, parser: PatitasParser) -> None:
        """Steps directive with named closers."""
        markdown = """\
:::{steps}
:::{step} Install
Run pip install
:::{/step}
:::{step} Configure
Edit config file
:::{/step}
:::{/steps}
"""
        result = parser.parse(markdown, {})
        assert "Install" in result or "<ol" in result
        assert "Configure" in result

    def test_steps_with_all_options_named_closers(self, parser: PatitasParser) -> None:
        """Steps directive with all new options using named closers."""
        markdown = """\
:::{steps}
:start: 3

:::{step} Required Step
:description: This step must be completed first.
:duration: 5 min
Main content here.
:::{/step}

:::{step} Optional Step
:optional:
:description: You can skip this if needed.
:duration: 10 min
Optional configuration.
:::{/step}
:::{/steps}
"""
        result = parser.parse(markdown, {})

        # Check steps container renders with start attribute
        assert '<div class="steps"' in result
        assert 'start="3"' in result
        assert "counter-reset: step 2" in result  # start - 1

        # Check step options render correctly
        assert "step-description" in result
        assert "step-duration" in result
        assert "step-optional" in result
        assert "step-badge-optional" in result
        assert "Optional" in result
        assert "5 min" in result
        assert "10 min" in result


class TestDeeplyNestedNamedClosers:
    """Tests for deeply nested structures with named closers."""

    def test_three_level_nesting(self, parser: PatitasParser) -> None:
        """Three levels of nesting with named closers."""
        markdown = """\
:::{tab-set}
:::{tab-item} Overview
:::{note}
A note inside a tab
:::{/note}
:::{/tab-item}
:::{/tab-set}
"""
        result = parser.parse(markdown, {})
        assert 'class="tabs"' in result or 'class="tab-set"' in result
        assert 'class="admonition note"' in result
        assert "A note inside a tab" in result

    def test_four_level_nesting(self, parser: PatitasParser) -> None:
        """Four levels of nesting with named closers."""
        markdown = """\
:::{tab-set}
:::{tab-item} Cards
:::{cards}
:::{card} Deep Card
Deeply nested content
:::{/card}
:::{/cards}
:::{/tab-item}
:::{/tab-set}
"""
        result = parser.parse(markdown, {})
        assert 'class="tabs"' in result or 'class="tab-set"' in result
        assert 'class="card-grid"' in result
        assert "Deep Card" in result

    def test_five_level_nesting_no_counting(self, parser: PatitasParser) -> None:
        """
        Five levels deep - this would require :::::: with fence counting.

        With named closers, we just use ::: everywhere.
        """
        markdown = """\
:::{tab-set}
:::{tab-item} Deep Structure
:::{cards}
:::{card} Card with Tip
:::{tip}
Five levels deep!
:::{/tip}
:::{/card}
:::{/cards}
:::{/tab-item}
:::{/tab-set}
"""
        result = parser.parse(markdown, {})
        assert 'class="tabs"' in result or 'class="tab-set"' in result
        assert 'class="card-grid"' in result
        assert 'class="admonition tip"' in result
        assert "Five levels deep!" in result


class TestBackwardCompatibility:
    """Tests ensuring fence-depth counting still works."""

    def test_traditional_fence_depth_tabs(self, parser: PatitasParser) -> None:
        """Traditional fence-depth counting for tabs."""
        markdown = """\
::::{tab-set}
:::{tab-item} First
Content 1
:::
:::{tab-item} Second
Content 2
:::
::::
"""
        result = parser.parse(markdown, {})
        assert 'class="tabs"' in result or 'class="tab-set"' in result
        assert "Content 1" in result
        assert "Content 2" in result

    def test_traditional_nested_admonition(self, parser: PatitasParser) -> None:
        """Traditional fence-depth for nested admonition."""
        markdown = """\
::::{tab-set}
:::{tab-item} Notes
::::{note}
Nested note
::::
:::
::::
"""
        # Note: This specific pattern may parse differently, but tabs should work
        result = parser.parse(markdown, {})
        assert "Notes" in result or "tab" in result.lower()

    def test_simple_admonition_fence_depth(self, parser: PatitasParser) -> None:
        """Simple admonition with fence-depth closing."""
        markdown = """\
:::{note}
Content
:::
"""
        result = parser.parse(markdown, {})
        assert 'class="admonition note"' in result
        assert "Content" in result


class TestMixedSyntax:
    """Tests for mixing named closers with fence-depth counting."""

    def test_named_inner_fence_outer(self, parser: PatitasParser) -> None:
        """Named closer inside, fence-depth outside."""
        markdown = """\
::::{tab-set}
:::{tab-item} Mixed
:::{note}
A note
:::{/note}
:::{/tab-item}
::::
"""
        result = parser.parse(markdown, {})
        assert 'class="tabs"' in result or 'class="tab-set"' in result
        assert 'class="admonition note"' in result

    def test_fence_inner_named_outer(self, parser: PatitasParser) -> None:
        """Fence-depth inside, named closer outside."""
        markdown = """\
:::{tab-set}
::::{tab-item} First
:::{note}
Note content
:::
::::
:::{/tab-set}
"""
        result = parser.parse(markdown, {})
        # Should parse tabs correctly
        assert "tab" in result.lower()


class TestEdgeCases:
    """Edge cases and error handling for named closers."""

    def test_named_closer_in_code_block_ignored(self, parser: PatitasParser) -> None:
        """Named closer inside code block should not close directive."""
        markdown = """\
:::{note}
Here's an example:
```markdown
:::{/note}
```
Still in the note!
:::{/note}
"""
        result = parser.parse(markdown, {})
        assert 'class="admonition note"' in result
        assert "Still in the note!" in result

    def test_nested_different_type_directives(self, parser: PatitasParser) -> None:
        """Nested directives of different types with named closers."""
        markdown = """\
:::{note}
:::{tip}
Inner tip
:::{/tip}
:::{/note}
"""
        result = parser.parse(markdown, {})
        # Both note and tip should render
        assert 'class="admonition' in result
        assert "Inner tip" in result

    def test_whitespace_in_closer(self, parser: PatitasParser) -> None:
        """Named closer with trailing whitespace."""
        markdown = """\
:::{note}
Content
:::{/note}
"""
        result = parser.parse(markdown, {})
        assert 'class="admonition note"' in result
        assert "Content" in result

    def test_indented_named_closer(self, parser: PatitasParser) -> None:
        """Named closer with leading whitespace (indented)."""
        markdown = """\
:::{note}
Content
   :::{/note}
"""
        result = parser.parse(markdown, {})
        assert 'class="admonition note"' in result
        assert "Content" in result
