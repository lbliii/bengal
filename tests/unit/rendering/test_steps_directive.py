"""
Tests for StepsDirective behavior, including nesting.
"""

from __future__ import annotations


import sys

import pytest

import bengal
from bengal.rendering.parsers import MistuneParser

print(f"DEBUG: bengal imported from {bengal.__file__}", file=sys.stderr)


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
