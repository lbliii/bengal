"""
Tests for DirectiveValidator fence nesting checks.

NOTE: H202 fence nesting warnings have been removed as they produced false positives.
Patitas handles fence validation correctly. See: rfc-patitas-structural-validation.md

These tests now verify that NO fence nesting warnings are produced (the old behavior
produced false positives for valid MyST syntax).

Also includes regression tests for edge cases in fence parsing (e.g., null pointer
safety when code_block_fence is None).
"""

from __future__ import annotations

from bengal.directives.validator import DirectiveSyntaxValidator
from bengal.health.report import CheckStatus
from bengal.health.validators.directives import DirectiveValidator
from tests._testing.mocks import MockPage, MockSite


class TestDirectiveValidatorFences:
    """Tests that verify fence nesting warnings are NOT produced (they caused false positives)."""

    def test_valid_myst_nested_directives_no_warning(self, tmp_path):
        """Valid MyST nested directives should NOT trigger warnings."""
        content = """
:::{tab-set}
:::{tab-item} Tab 1
Content
:::
:::
"""
        source_file = tmp_path / "valid_myst.md"
        source_file.write_text(content)

        page = MockPage(title="Test", source_path=source_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Should NOT have a warning about fence nesting (this was a false positive)
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        fence_warnings = [w for w in warnings if "fence nesting" in w.message]
        assert len(fence_warnings) == 0, (
            f"False positive: valid MyST nested directives should not trigger warnings: {fence_warnings}"
        )

    def test_unclosed_directive_no_fence_warning(self, tmp_path):
        """Unclosed directives are handled by patitas, not fence nesting checks."""
        content = """
:::{note}
Unclosed
"""
        source_file = tmp_path / "unclosed.md"
        source_file.write_text(content)

        page = MockPage(title="Test", source_path=source_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Fence nesting warnings should NOT be produced (handled by patitas)
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        fence_warnings = [w for w in warnings if "fence nesting" in w.message]
        assert len(fence_warnings) == 0, (
            f"Fence nesting warnings should not be produced: {fence_warnings}"
        )

    def test_sequential_code_blocks_no_warning(self, tmp_path):
        """Sequential code blocks should NOT trigger warnings."""
        content = """
**Hugo:**
```go-html-template
{{ $posts := where .Site.RegularPages "Section" "blog" }}
```

**Bengal:**
```jinja2
{% set posts = site.pages | where('section', 'blog') %}
```
"""
        source_file = tmp_path / "sequential.md"
        source_file.write_text(content)

        page = MockPage(title="Test", source_path=source_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Should NOT have warnings about fence nesting for sequential blocks
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        fence_warnings = [
            w
            for w in warnings
            if "fence nesting" in w.message and "sequential.md" in str(w.details)
        ]
        assert len(fence_warnings) == 0, (
            f"False positive: sequential code blocks flagged as nested: {fence_warnings}"
        )

    def test_code_blocks_inside_markdown_no_warning(self, tmp_path):
        """Code blocks inside markdown fence are valid documentation patterns."""
        # This pattern is common for documenting code examples
        content = """
```markdown
Here's some markdown with a code example:

```python
print("hello")
```
```
"""
        source_file = tmp_path / "documentation.md"
        source_file.write_text(content)

        page = MockPage(title="Test", source_path=source_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Should NOT have warnings (patitas handles fence parsing correctly)
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        fence_warnings = [w for w in warnings if "fence nesting" in w.message]
        assert len(fence_warnings) == 0, (
            f"Fence nesting warnings should not be produced: {fence_warnings}"
        )


class TestDirectiveSyntaxValidatorEdgeCases:
    """Regression tests for edge cases in DirectiveSyntaxValidator.
    
    These tests ensure the validator handles malformed input gracefully,
    particularly around code fence state tracking where null pointer bugs
    could occur.
    """

    def test_orphaned_closing_code_fence_no_crash(self):
        """Closing code fence without opening should not crash (null pointer regression)."""
        content = """
Some text before
```
More text after orphaned fence
"""
        # Should not raise any exceptions
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    def test_only_opening_code_fence_no_crash(self):
        """Opening code fence without closing should be handled gracefully."""
        content = """
```python
def unclosed():
    pass
# No closing fence
"""
        # Should not crash even with unclosed fence
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    def test_mismatched_fence_markers_no_crash(self):
        """Mismatched fence types (backticks vs tildes) should not crash."""
        content = """
```python
code here
~~~
More code
~~~
```
"""
        # Should handle mismatched markers gracefully
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    def test_empty_content_no_crash(self):
        """Empty content should be handled gracefully."""
        errors = DirectiveSyntaxValidator.validate_nested_fences("")
        assert errors == []

    def test_only_fence_markers_no_crash(self):
        """Content with only fence markers should not crash."""
        content = "```\n```\n~~~\n~~~\n:::\n:::"
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    def test_interleaved_code_and_directive_fences_no_crash(self):
        """Interleaved code blocks and directive fences should not crash."""
        content = """
:::{note}
```python
code
```
:::

```python
:::{tip}
This is inside a code block
:::
```
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    def test_deeply_nested_fences_no_crash(self):
        """Deeply nested fences should not cause stack overflow or crash."""
        # Create deeply nested content
        content = ""
        for i in range(20):
            content += ":" * (3 + i) + "{note}\n"
        for i in range(19, -1, -1):
            content += ":" * (3 + i) + "\n"
        
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    def test_code_fence_with_special_characters_no_crash(self):
        """Code fences with special characters in info string should not crash."""
        content = '''
```python!@#$%^&*()
code
```

```go-html-template[special]
template
```
'''
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    def test_unicode_content_no_crash(self):
        """Unicode content including emoji should not crash."""
        content = """
```python
# 你好世界 🌍
print("Hello 世界 🎉")
```

:::{note} 注意事项 ⚠️
这是一个笔记
:::
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    def test_very_long_fence_no_crash(self):
        """Very long fence markers should not crash."""
        long_fence = "`" * 100
        content = f"""
{long_fence}python
code
{long_fence}
"""
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)
