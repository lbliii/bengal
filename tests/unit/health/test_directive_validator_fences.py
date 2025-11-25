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
        assert "ambiguity" in fence_warnings[0].details[0]

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

        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        assert len(warnings) > 0
        fence_warnings = [w for w in warnings if "fence nesting" in w.message]
        assert len(fence_warnings) > 0
        assert "never closed" in fence_warnings[0].details[0]
