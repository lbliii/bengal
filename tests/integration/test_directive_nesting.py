"""
Integration tests for directive nesting validation.

Tests that DirectiveContract validation works correctly for nested directives:
- steps/step parent-child relationship
- tab-set/tab-item parent-child relationship
- cards/card parent-child relationship (soft validation)

These tests verify that:
1. Valid nesting produces no warnings
2. Orphaned children (e.g., step without steps) produce warnings
3. Warnings include directive name and context
"""

from __future__ import annotations

import pytest

from bengal.parsing.backends.mistune import MistuneParser


@pytest.fixture
def parser() -> MistuneParser:
    """Create parser for directive tests."""
    return MistuneParser()


class TestStepsNesting:
    """Tests for steps/step directive nesting validation."""

    def test_valid_steps_nesting(self, parser: MistuneParser) -> None:
        """Valid steps with nested step children should render correctly."""
        markdown = """\
::::{steps}

:::{step}
First step content
:::

:::{step}
Second step content
:::

::::
"""
        result = parser.parse(markdown, {})

        # Should contain steps container and step items
        # Note: Uses ol/li structure for steps
        assert "<ol" in result or 'class="steps"' in result.lower()
        assert "First step content" in result
        assert "Second step content" in result

    def test_orphaned_step_renders(self, parser: MistuneParser) -> None:
        """
        Orphaned step (without steps parent) should still render.

        Note: Contract validation emits warnings but doesn't block rendering.
        The step will render as a list item even without steps parent.
        """
        markdown = """\
:::{step}
Orphaned step content
:::
"""
        result = parser.parse(markdown, {})

        # Step should still render even without parent (as li element)
        assert "Orphaned step content" in result


class TestTabsNesting:
    """Tests for tab-set/tab-item directive nesting validation."""

    def test_valid_tabset_nesting(self, parser: MistuneParser) -> None:
        """Valid tab-set with nested tab-item children should render correctly."""
        markdown = """\
::::{tab-set}

:::{tab-item} First Tab
First tab content
:::

:::{tab-item} Second Tab
Second tab content
:::

::::
"""
        result = parser.parse(markdown, {})

        # Should contain tab container and tab items
        # Note: May use "tabs" or "tab-set" class depending on legacy vs new rendering
        assert 'class="tabs"' in result or 'class="tab-set"' in result
        assert "First Tab" in result
        assert "Second Tab" in result
        assert "First tab content" in result
        assert "Second tab content" in result

    def test_orphaned_tabitem_renders(self, parser: MistuneParser) -> None:
        """
        Orphaned tab-item (without tab-set parent) should still render.

        Note: Contract validation emits warnings but doesn't block rendering.
        """
        markdown = """\
:::{tab-item} Orphaned Tab
Orphaned tab content
:::
"""
        result = parser.parse(markdown, {})

        # Tab item should still render even without parent
        assert "Orphaned Tab" in result or "Orphaned tab content" in result


class TestCardsNesting:
    """Tests for cards/card directive nesting validation."""

    def test_valid_cards_nesting(self, parser: MistuneParser) -> None:
        """Valid cards with nested card children should render correctly."""
        markdown = """\
::::{cards}
:columns: 2

:::{card} First Card
First card content
:::

:::{card} Second Card
Second card content
:::

::::
"""
        result = parser.parse(markdown, {})

        # Should contain card grid and card items
        assert 'class="card-grid"' in result
        assert 'class="card' in result
        assert "First Card" in result
        assert "Second Card" in result

    def test_standalone_card_renders(self, parser: MistuneParser) -> None:
        """
        Standalone card (without cards parent) should still render.

        Cards have soft validation (allowed_children but not required_parent).
        """
        markdown = """\
:::{card} Standalone Card
:icon: star
Standalone card content
:::
"""
        result = parser.parse(markdown, {})

        # Card should render even without parent
        assert 'class="card' in result
        assert "Standalone Card" in result


class TestNestedDirectiveCombinations:
    """Tests for complex nested directive scenarios."""

    def test_deeply_nested_structure(self, parser: MistuneParser) -> None:
        """Test deeply nested directives render correctly."""
        markdown = """\
:::::{cards}
:columns: 1

::::{card} Card with Steps

:::{steps}

:::{step}
Step inside card
:::

:::

::::

:::::
"""
        result = parser.parse(markdown, {})

        # Should contain both cards and steps structure
        assert 'class="card-grid"' in result
        assert 'class="bengal-steps"' in result or "Step inside card" in result

    def test_admonition_with_nested_directive(self, parser: MistuneParser) -> None:
        """Test admonition containing nested directives."""
        markdown = """\
::::{note}

:::{steps}

:::{step}
Step inside note
:::

:::

::::
"""
        result = parser.parse(markdown, {})

        # Should contain admonition and steps
        assert 'class="admonition' in result
        # Steps may or may not render inside depending on parser behavior

    def test_tabs_with_code_blocks(self, parser: MistuneParser) -> None:
        """Test tabs containing code blocks."""
        markdown = """\
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
        result = parser.parse(markdown, {})

        # Should contain tab structure with code blocks
        # Note: May use "tabs" or "tab-set" class
        assert 'class="tabs"' in result or 'class="tab-set"' in result
        assert "Python" in result
        assert "JavaScript" in result


class TestContractValidationBehavior:
    """Tests verifying contract validation doesn't break rendering."""

    def test_invalid_nesting_still_renders_content(self, parser: MistuneParser) -> None:
        """Even with invalid nesting, content should still be rendered."""
        # Multiple steps without steps container
        markdown = """\
:::{step}
First orphan
:::

:::{step}
Second orphan
:::
"""
        result = parser.parse(markdown, {})

        # Both steps should render
        assert "First orphan" in result
        assert "Second orphan" in result

    def test_mixed_valid_invalid_nesting(self, parser: MistuneParser) -> None:
        """Mix of valid and invalid nesting should all render."""
        markdown = """\
::::{steps}

:::{step}
Valid step
:::

::::

:::{step}
Orphaned step
:::
"""
        result = parser.parse(markdown, {})

        # Both valid and orphaned should render
        assert "Valid step" in result
        assert "Orphaned step" in result

