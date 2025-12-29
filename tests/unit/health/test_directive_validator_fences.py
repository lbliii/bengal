"""
Tests for DirectiveValidator fence nesting checks.

NOTE: H202 fence nesting warnings have been removed as they produced false positives.
Patitas handles fence validation correctly. See: rfc-patitas-structural-validation.md

These tests now verify that NO fence nesting warnings are produced (the old behavior
produced false positives for valid MyST syntax).
"""

from __future__ import annotations

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
