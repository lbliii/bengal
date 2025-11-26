"""
Tests for StepsDirective behavior, including nesting.
"""

import sys

import pytest

import bengal

print(f"DEBUG: bengal imported from {bengal.__file__}", file=sys.stderr)

from bengal.rendering.parsers import MistuneParser


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
        content = """
::::{steps}
1. Step 1

   :::{tip}
   Tip content
   :::

2. Step 2
::::
"""
        result = parser.parse(content, {})

        # Check that steps container is rendered
        assert '<div class="steps">' in result

        # Check that admonition is rendered correctly (not plain text)
        assert '<div class="admonition tip">' in result
        assert "Tip content" in result
        assert ":::{tip}" not in result

    def test_nested_admonition_with_backticks(self, parser):
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

        # Check that admonition is rendered correctly (not code block)
        assert '<div class="admonition tip">' in result
        assert "Tip content" in result
        # Should not render as pre/code block
        assert "<pre><code" not in result

    def test_headings_transformation(self, parser):
        content = """
::::{steps}
1. ### Step Title

   Content
::::
"""
        result = parser.parse(content, {})
        assert '<div class="step-title">Step Title</div>' in result
        assert "<h3" not in result
