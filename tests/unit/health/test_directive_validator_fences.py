"""
Tests for DirectiveValidator fence nesting checks.
"""

from pathlib import Path

from bengal.health.report import CheckStatus
from bengal.health.validators.directives import DirectiveValidator


class MockPage:
    def __init__(self, source_path, metadata=None):
        self.source_path = source_path
        self.metadata = metadata or {}
        self.output_path = Path("output.html")


class MockSite:
    def __init__(self, pages):
        self.pages = pages


class TestDirectiveValidatorFences:
    def test_detects_ambiguous_nesting(self, tmp_path):
        content = """
:::{tab-set}
:::{tab-item} Tab 1
Content
:::
:::
"""
        source_file = tmp_path / "ambiguous.md"
        source_file.write_text(content)

        page = MockPage(source_file)
        site = MockSite([page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Should have a warning about fence nesting
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        assert len(warnings) > 0
        fence_warnings = [w for w in warnings if "fence nesting" in w.message]
        assert len(fence_warnings) > 0
        # Details now show grouped format: "file:line - N issue(s)"
        assert "ambiguous.md" in str(fence_warnings[0].details)

    def test_detects_unclosed_fence(self, tmp_path):
        content = """
:::{note}
Unclosed
"""
        source_file = tmp_path / "unclosed.md"
        source_file.write_text(content)

        page = MockPage(source_file)
        site = MockSite([page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Unclosed fences are syntax errors, not fence nesting warnings
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        warnings = [r for r in results if r.status == CheckStatus.WARNING]

        # Should have either an error or a warning
        assert len(errors) > 0 or len(warnings) > 0

        # Check if it's a syntax error (unclosed) or fence nesting warning
        if errors:
            syntax_errors = [e for e in errors if "syntax" in e.message.lower()]
            assert len(syntax_errors) > 0
            # Details format: "file:line - type: error message"
            assert "unclosed.md" in str(syntax_errors[0].details)
        elif warnings:
            fence_warnings = [w for w in warnings if "fence nesting" in w.message]
            if fence_warnings:
                # Details format: "file:line - N issue(s)"
                assert "unclosed.md" in str(fence_warnings[0].details)

    def test_sequential_code_blocks_not_nested(self, tmp_path):
        """Test that sequential code blocks (not nested) don't trigger false positives."""
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

        page = MockPage(source_file)
        site = MockSite([page])

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

    def test_actually_nested_code_blocks_detected(self, tmp_path):
        """Test that truly nested code blocks (one inside another) are still detected."""
        content = """
```markdown
Here's some markdown with a code example:

```python
print("hello")
```
```
"""
        source_file = tmp_path / "nested.md"
        source_file.write_text(content)

        page = MockPage(source_file)
        site = MockSite([page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # SHOULD have warnings about fence nesting for truly nested blocks
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        fence_warnings = [
            w for w in warnings if "fence nesting" in w.message and "nested.md" in str(w.details)
        ]
        assert len(fence_warnings) > 0, "Should detect truly nested code blocks"
