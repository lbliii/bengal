"""
Tests for nested fence validation in DirectiveValidator.
"""

from bengal.directives.validator import DirectiveSyntaxValidator


class TestNestedFenceValidation:
    """Test nested fence validation logic."""

    def test_valid_nesting_variable_lengths(self):
        """Test valid nesting with different fence lengths."""
        content = """
::::{tab-set}
:::{tab-item} Tab 1
Content
:::
::::
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert len(errors) == 0

    def test_invalid_nesting_same_lengths(self):
        """Test invalid nesting with same fence lengths (ambiguous)."""
        content = """
:::{tab-set}
:::{tab-item} Tab 1
Content
:::
:::
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert len(errors) > 0
        assert "same fence length" in errors[0]
        # The error recommends using named closers for clarity
        assert "Use named closers" in errors[0] or "Recommended" in errors[0]

    def test_unclosed_fence(self):
        """Test detection of unclosed fences."""
        content = """
:::{note}
Unclosed note
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert len(errors) > 0
        assert "never closed" in errors[0]

    def test_orphaned_closing_fence(self):
        """Test detection of orphaned closing fences."""
        content = """
:::
Orphaned
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert len(errors) > 0
        assert "Orphaned closing fence" in errors[0]

    def test_mismatched_closing_fence_shorter(self):
        """Test closing fence that is too short."""
        content = """
::::{note}
Content
:::
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert len(errors) > 0
        assert "too short" in errors[0]

    def test_mismatched_closing_fence_longer_but_valid_parent(self):
        """Test closing fence that matches a parent but skips a child."""
        content = """
::::{tab-set}
:::{tab-item}
Content
::::
"""
        # Here :::: matches tab-set (4), but tab-item (3) is still open.
        # This should error because tab-item is unclosed.
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert len(errors) > 0
        assert "leaves inner directives unclosed" in errors[0]
        assert "'tab-item'" in errors[0]

    def test_indented_child_is_valid(self):
        """Test that indented child with same fence length is valid."""
        content = """
:::{tab-set}
    :::{tab-item} Tab 1
    Content
    :::
:::
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert len(errors) == 0

    def test_multiple_siblings_valid(self):
        """Test multiple siblings at same level."""
        content = """
::::{tab-set}
:::{tab-item} 1
Content
:::

:::{tab-item} 2
Content
:::
::::
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert len(errors) == 0
