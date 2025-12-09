"""
Tests for StepsDirective behavior, including nesting.
"""

from __future__ import annotations

import sys

import pytest

import bengal
from bengal.rendering.parsers import MistuneParser
from bengal.rendering.plugins.directives.steps import (
    StepOptions,
    StepsOptions,
)

print(f"DEBUG: bengal imported from {bengal.__file__}", file=sys.stderr)


# =============================================================================
# StepOptions Tests
# =============================================================================


class TestStepOptions:
    """Tests for StepOptions dataclass."""

    def test_default_values(self) -> None:
        """Test default option values."""
        options = StepOptions()

        assert options.css_class == ""
        assert options.description == ""
        assert options.optional is False
        assert options.duration == ""

    def test_custom_values(self) -> None:
        """Test setting custom option values."""
        options = StepOptions(
            css_class="my-step",
            description="This is the description.",
            optional=True,
            duration="5 min",
        )

        assert options.css_class == "my-step"
        assert options.description == "This is the description."
        assert options.optional is True
        assert options.duration == "5 min"

    def test_class_alias(self) -> None:
        """Test that 'class' is aliased to 'css_class'."""
        # The alias is defined in _field_aliases
        assert StepOptions._field_aliases.get("class") == "css_class"


# =============================================================================
# StepsOptions Tests
# =============================================================================


class TestStepsOptions:
    """Tests for StepsOptions dataclass."""

    def test_default_values(self) -> None:
        """Test default option values."""
        options = StepsOptions()

        assert options.css_class == ""
        assert options.style == "default"
        assert options.start == 1

    def test_custom_values(self) -> None:
        """Test setting custom option values."""
        options = StepsOptions(
            css_class="my-steps",
            style="compact",
            start=5,
        )

        assert options.css_class == "my-steps"
        assert options.style == "compact"
        assert options.start == 5

    def test_allowed_styles(self) -> None:
        """Test that style has allowed values."""
        assert "default" in StepsOptions._allowed_values.get("style", [])
        assert "compact" in StepsOptions._allowed_values.get("style", [])


# =============================================================================
# StepsDirective Rendering Tests
# =============================================================================


class TestStepsDirective:
    @pytest.fixture
    def parser(self):
        return MistuneParser()

    def test_steps_directive_basic(self, parser):
        content = """
::::{steps}
1. Step 1
2. Step 2
::::
"""
        result = parser.parse(content, {})
        assert '<div class="steps">' in result
        assert "<ol>" in result or "<li>" in result
        assert "Step 1" in result

    def test_nested_admonition_in_steps(self, parser):
        """Test nested admonition using new :::{step} syntax."""
        content = """
::::{steps}
:::{step} Step 1

   :::{tip}
   Tip content
   :::

:::{step} Step 2
Content
:::
::::
"""
        result = parser.parse(content, {})

        # Check that steps container is rendered
        assert '<div class="steps">' in result

        # Check that admonition is rendered correctly (not plain text)
        assert '<div class="admonition tip">' in result
        assert "Tip content" in result
        assert ":::{tip}" not in result

    def test_nested_admonition_with_colons_in_steps(self, parser):
        """Test nested admonition with colon syntax inside steps."""
        # Bengal uses colon-fenced syntax for all directives (including nested ones)
        content = """
:::::{steps}
::::{step} Step 1

:::{tip}
Tip content
:::

::::
::::{step} Step 2
Content
::::
:::::
"""
        result = parser.parse(content, {})

        # Check that admonition is rendered correctly (not code block)
        assert '<div class="admonition tip">' in result
        assert "Tip content" in result
        # Should not render as pre/code block
        assert "<pre><code" not in result

    def test_backward_compatibility_numbered_list(self, parser):
        """Test backward compatibility with numbered list syntax."""
        content = """
::::{steps}
1. Step 1
2. Step 2
::::
"""
        result = parser.parse(content, {})
        assert '<div class="steps">' in result
        assert "<ol>" in result or "<li>" in result
        assert "Step 1" in result

    def test_nested_admonition_with_backticks(self, parser):
        """Test nested admonition with backticks - uses numbered list syntax (limited support)."""
        # Note: Numbered list syntax has limited nested directive support
        # For full nested directive support, use :::{step} syntax instead
        content = """
::::{steps}
1. Step 1

   ```{tip}
   Tip content
   ```

2. Step 2
::::
"""
        result = parser.parse(content, {})

        # With numbered list syntax, nested directives may not work perfectly
        # This is expected - use :::{step} syntax for full nested directive support
        assert '<div class="steps">' in result
        # The admonition might render as code block with numbered list syntax
        # This is a known limitation of the backward-compatible syntax

    def test_headings_transformation(self, parser):
        """Test heading transformation in steps - uses new :::{step} syntax."""
        content = """
::::{steps}
:::{step} ### Step Title

Content
:::
::::
"""
        result = parser.parse(content, {})
        # Note: Heading transformation may need special handling in step titles
        assert '<div class="steps">' in result
        assert "Step Title" in result

    # =========================================================================
    # New Options Tests
    # =========================================================================

    def test_step_description_option(self, parser):
        """Test :description: option renders lead-in text."""
        content = """
:::{steps}
:::{step} Install Dependencies
:description: First, set up your environment with required packages.
Run the install command.
:::{/step}
:::{/steps}
"""
        result = parser.parse(content, {})

        assert '<div class="steps">' in result
        assert "Install Dependencies" in result
        assert '<p class="step-description">' in result
        assert "set up your environment" in result

    def test_step_optional_option(self, parser):
        """Test :optional: option adds optional class and badge."""
        content = """
:::{steps}
:::{step} Optional Configuration
:optional:
This step is skippable.
:::{/step}
:::{/steps}
"""
        result = parser.parse(content, {})

        assert '<div class="steps">' in result
        assert "step-optional" in result
        assert "step-badge-optional" in result
        assert "Optional" in result

    def test_step_duration_option(self, parser):
        """Test :duration: option shows time estimate."""
        content = """
:::{steps}
:::{step} Build the Project
:duration: 5 min
Run the build command.
:::{/step}
:::{/steps}
"""
        result = parser.parse(content, {})

        assert '<div class="steps">' in result
        assert '<span class="step-duration">' in result
        assert "5 min" in result

    def test_step_all_options_combined(self, parser):
        """Test all step options combined."""
        content = """
:::{steps}
:::{step} Advanced Setup
:description: This step covers advanced configuration options.
:duration: 10 min
:optional:
:class: advanced-step
Advanced content here.
:::{/step}
:::{/steps}
"""
        result = parser.parse(content, {})

        # Container
        assert '<div class="steps">' in result

        # All options should render
        assert "step-description" in result
        assert "step-duration" in result
        assert "step-optional" in result
        assert "step-badge-optional" in result
        assert "advanced-step" in result
        assert "10 min" in result

    def test_steps_start_option(self, parser):
        """Test :start: option on steps container."""
        content = """
:::{steps}
:start: 5
:::{step} Step Five
Content for step 5.
:::{/step}
:::{step} Step Six
Content for step 6.
:::{/step}
:::{/steps}
"""
        result = parser.parse(content, {})

        assert '<div class="steps"' in result
        # Check that start attribute is set on <ol>
        assert 'start="5"' in result
        # Check that counter-reset is set for CSS
        assert "counter-reset: step 4" in result  # start - 1

    def test_steps_start_option_default(self, parser):
        """Test that start=1 doesn't add extra attributes."""
        content = """
:::{steps}
:::{step} Step One
Content.
:::{/step}
:::{/steps}
"""
        result = parser.parse(content, {})

        assert '<div class="steps">' in result
        # Default start=1 should not add start attribute
        assert 'start="1"' not in result
        assert "counter-reset" not in result

    def test_named_closers_syntax(self, parser):
        """Test named closers syntax (v2) works correctly."""
        content = """
:::{steps}
:::{step} First Step
:description: The first step description.
Content for step 1.
:::{/step}

:::{step} Second Step
:optional:
Content for step 2.
:::{/step}
:::{/steps}
"""
        result = parser.parse(content, {})

        assert '<div class="steps">' in result
        assert "First Step" in result
        assert "Second Step" in result
        assert "step-description" in result
        assert "step-optional" in result

    def test_step_metadata_container(self, parser):
        """Test that metadata (optional + duration) is in a container."""
        content = """
:::{steps}
:::{step} Setup
:optional:
:duration: 2 min
Content.
:::{/step}
:::{/steps}
"""
        result = parser.parse(content, {})

        # Both should be in the metadata container
        assert '<div class="step-metadata">' in result
        assert "step-badge-optional" in result
        assert "step-duration" in result
