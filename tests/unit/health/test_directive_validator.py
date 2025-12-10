"""
Tests for DirectiveValidator health check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.directives import DirectiveAnalyzer, DirectiveValidator
from tests._testing.mocks import MockPage, MockSite


class TestDirectiveExtraction:
    """Test directive extraction from markdown content."""

    def test_extract_simple_directive(self, tmp_path):
        """Test extracting a simple directive."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        content = """---
title: Test
---

# Test Page

:::{note} Important
This is a note.
:::

Regular content.
"""
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        analyzer = DirectiveAnalyzer()
        directives = analyzer._extract_directives(content, file_path)

        assert len(directives) == 1
        assert directives[0]["type"] == "note"
        assert directives[0]["title"] == "Important"
        assert "This is a note." in directives[0]["content"]

    def test_extract_multiple_directives(self, tmp_path):
        """Test extracting multiple directives."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        content = """
:::{note} Note 1
Content 1
:::

:::{tip} Tip 1
Content 2
:::

:::{warning} Warning 1
Content 3
:::
"""
        file_path = tmp_path / "test.md"

        analyzer = DirectiveAnalyzer()
        directives = analyzer._extract_directives(content, file_path)

        assert len(directives) == 3
        assert directives[0]["type"] == "note"
        assert directives[1]["type"] == "tip"
        assert directives[2]["type"] == "warning"

    def test_extract_tabs_directive(self, tmp_path):
        """Test extracting tabs directive with tab markers."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        content = """
:::{tabs}
:id: my-tabs

### Tab: Python
Python code here

### Tab: JavaScript
JavaScript code here

### Tab: Ruby
Ruby code here
:::
"""
        file_path = tmp_path / "test.md"

        analyzer = DirectiveAnalyzer()
        directives = analyzer._extract_directives(content, file_path)

        assert len(directives) == 1
        assert directives[0]["type"] == "tabs"
        assert directives[0]["tab_count"] == 3

    def test_detect_unknown_directive(self, tmp_path):
        """Test detection of unknown directive types."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        content = """
:::{unknown_directive} Title
Content
:::
"""
        file_path = tmp_path / "test.md"

        analyzer = DirectiveAnalyzer()
        directives = analyzer._extract_directives(content, file_path)

        assert len(directives) == 1
        assert directives[0]["type"] == "unknown_directive"
        assert "syntax_error" in directives[0]
        assert "Unknown directive type" in directives[0]["syntax_error"]

    def test_extract_with_hyphenated_name(self, tmp_path):
        """Test extracting directive with hyphenated name."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        content = """
:::{code-tabs}
### Tab: Python
code
:::
"""
        file_path = tmp_path / "test.md"

        analyzer = DirectiveAnalyzer()
        directives = analyzer._extract_directives(content, file_path)

        assert len(directives) == 1
        assert directives[0]["type"] == "code-tabs"

    def test_line_number_tracking(self, tmp_path):
        """Test that line numbers are tracked correctly."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        content = """Line 1
Line 2
Line 3
:::{note} Test
Content
:::
Line 7
"""
        file_path = tmp_path / "test.md"

        analyzer = DirectiveAnalyzer()
        directives = analyzer._extract_directives(content, file_path)

        assert len(directives) == 1
        assert directives[0]["line_number"] == 4  # Directive starts on line 4


class TestTabsValidation:
    """Test tabs directive validation."""

    def test_tabs_with_no_markers(self):
        """Test tabs directive with no tab markers."""
        analyzer = DirectiveAnalyzer()
        directive = {
            "type": "tabs",
            "content": "Just some content without markers",
            "title": "",
            "line_number": 10,
            "file_path": Path("test.md"),
        }

        analyzer._validate_tabs_directive(directive)

        assert "completeness_error" in directive
        assert "no tab markers" in directive["completeness_error"].lower()

    def test_tabs_with_single_tab(self):
        """Test tabs directive with only one tab."""
        analyzer = DirectiveAnalyzer()
        directive = {
            "type": "tabs",
            "content": "### Tab: Only One\nContent here",
            "title": "",
            "line_number": 10,
            "file_path": Path("test.md"),
        }

        analyzer._validate_tabs_directive(directive)

        assert "completeness_error" in directive
        assert "only 1 tab" in directive["completeness_error"]

    def test_tabs_with_malformed_marker(self):
        """Test tabs directive with malformed tab marker."""
        analyzer = DirectiveAnalyzer()
        directive = {
            "type": "tabs",
            "content": "### Ta: Python\nContent",  # Typo: "Ta:" instead of "Tab:"
            "title": "",
            "line_number": 10,
            "file_path": Path("test.md"),
        }

        analyzer._validate_tabs_directive(directive)

        assert "syntax_error" in directive
        assert "malformed tab marker" in directive["syntax_error"].lower()

    def test_tabs_with_valid_markers(self):
        """Test tabs directive with valid markers."""
        analyzer = DirectiveAnalyzer()
        directive = {
            "type": "tabs",
            "content": "### Tab: Python\nContent\n### Tab: JavaScript\nMore content",
            "title": "",
            "line_number": 10,
            "file_path": Path("test.md"),
        }

        analyzer._validate_tabs_directive(directive)

        assert directive["tab_count"] == 2
        assert "syntax_error" not in directive
        assert "completeness_error" not in directive

    def test_tabs_with_empty_content(self):
        """Test tabs directive with empty content."""
        analyzer = DirectiveAnalyzer()
        directive = {
            "type": "tabs",
            "content": "",
            "title": "",
            "line_number": 10,
            "file_path": Path("test.md"),
        }

        analyzer._validate_tabs_directive(directive)

        assert "completeness_error" in directive
        assert "no content" in directive["completeness_error"].lower()


class TestDropdownValidation:
    """Test dropdown directive validation."""

    def test_dropdown_with_content(self):
        """Test valid dropdown with content."""
        analyzer = DirectiveAnalyzer()
        directive = {
            "type": "dropdown",
            "content": "Some content here",
            "title": "Click me",
            "line_number": 10,
            "file_path": Path("test.md"),
        }

        analyzer._validate_dropdown_directive(directive)

        assert "completeness_error" not in directive

    def test_dropdown_with_empty_content(self):
        """Test dropdown with empty content."""
        analyzer = DirectiveAnalyzer()
        directive = {
            "type": "dropdown",
            "content": "",
            "title": "Click me",
            "line_number": 10,
            "file_path": Path("test.md"),
        }

        analyzer._validate_dropdown_directive(directive)

        assert "completeness_error" in directive
        assert "no content" in directive["completeness_error"].lower()


class TestDirectiveValidation:
    """Test full directive validation."""

    def test_validate_with_no_directives(self, tmp_path):
        """Test validation when site has no directives."""
        # Create a simple markdown file with no directives
        content = """---
title: Simple Page
---

# Hello World

Just regular markdown content here.
"""
        source_file = tmp_path / "simple.md"
        source_file.write_text(content)

        output_file = tmp_path / "output" / "simple.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("<html><body>Hello World</body></html>")

        page = MockPage(title="Test", source_path=source_file, output_path=output_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # No issues = no results (silence is golden)
        # OR if there are results, none should be errors
        assert all(r.status != CheckStatus.ERROR for r in results)

    def test_validate_with_valid_directives(self, tmp_path):
        """Test validation with valid directives."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        # Use MyST-style nested tab-items instead of ### Tab: headers
        content = """---
title: Page with Directives
---

:::{note} Important Note
This is important information.
:::

::::{tab-set}
:::{tab-item} Option 1
First option content.
:::

:::{tab-item} Option 2
Second option content.
:::
::::
"""
        source_file = tmp_path / "with_directives.md"
        source_file.write_text(content)

        output_file = tmp_path / "output" / "with_directives.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("""
        <html>
        <body>
            <div class="admonition note">Important</div>
            <div class="tabs">Tabs rendered</div>
        </body>
        </html>
        """)

        page = MockPage(title="Test", source_path=source_file, output_path=output_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # With valid directives and no issues, validator follows "silence is golden"
        # principle - no results or only non-error results
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) == 0

    def test_validate_with_syntax_errors(self, tmp_path):
        """Test validation catches syntax errors."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        content = """
:::{unknown_type} Test
Content
:::

:::{note} Valid Note
This one is valid.
:::
"""
        source_file = tmp_path / "with_errors.md"
        source_file.write_text(content)

        output_file = tmp_path / "output" / "with_errors.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("<html><body>Content</body></html>")

        page = MockPage(title="Test", source_path=source_file, output_path=output_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Should have error results
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) > 0
        assert any("syntax error" in r.message.lower() for r in error_results)

    def test_validate_with_performance_warnings(self, tmp_path):
        """Test validation warns about performance issues."""
        # Create content with many directives (>10)
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        directives = [f":::{{note}} Note {i}\nContent {i}\n:::\n" for i in range(15)]
        content = "---\ntitle: Heavy Page\n---\n\n" + "\n".join(directives)

        source_file = tmp_path / "heavy.md"
        source_file.write_text(content)

        output_file = tmp_path / "output" / "heavy.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("<html><body>Content</body></html>")

        page = MockPage(title="Test", source_path=source_file, output_path=output_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Should have performance warning
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert len(warning_results) > 0
        assert any("heavy directive usage" in r.message.lower() for r in warning_results)

    def test_validate_unrendered_directive(self, tmp_path):
        """Test validation catches unrendered directives in output."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        content = """
:::{note} Test
Content
:::
"""
        source_file = tmp_path / "unrendered.md"
        source_file.write_text(content)

        # Output still has directive syntax (not rendered)
        output_file = tmp_path / "output" / "unrendered.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("""
        <html>
        <body>
            :::{note} Test
            Content
            :::
        </body>
        </html>
        """)

        page = MockPage(title="Test", source_path=source_file, output_path=output_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Should have error about unrendered directive
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) > 0
        assert any("rendering" in r.message.lower() for r in error_results)

    def test_validate_skips_generated_pages(self, tmp_path):
        """Test that generated pages are skipped in validation."""
        source_file = tmp_path / "generated.md"
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        source_file.write_text(":::{note} Test\nContent\n:::")

        output_file = tmp_path / "output" / "generated.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("<html><body>Content</body></html>")

        # Mark as generated page
        page = MockPage(
            title="Generated",
            source_path=source_file,
            output_path=output_file,
            metadata={"_generated": True},
        )
        site = MockSite(pages=[page])

        analyzer = DirectiveAnalyzer()
        data = analyzer.analyze(site)

        # Should have skipped the generated page
        assert data["total_directives"] == 0


class TestPerformanceChecks:
    """Test performance-related checks."""

    def test_warn_on_too_many_tabs(self, tmp_path):
        """Test warning when tabs block has too many tabs."""
        # Create tabs with >10 tabs
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        tabs = [f"### Tab: Tab {i}\nContent {i}\n" for i in range(15)]
        content = f":::{{tabs}}\n{''.join(tabs)}\n:::"

        source_file = tmp_path / "many_tabs.md"
        source_file.write_text(content)

        output_file = tmp_path / "output" / "many_tabs.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("<html><body>Tabs</body></html>")

        page = MockPage(title="Test", source_path=source_file, output_path=output_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # Should warn about too many tabs
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any(
            "too many tabs" in r.message.lower() or "many tabs" in r.message.lower()
            for r in warning_results
        )


class TestStatistics:
    """Test directive statistics reporting."""

    def test_statistics_with_mixed_directives(self, tmp_path):
        """Test statistics reporting with various directive types."""
        # Use colon fences (:::) - backtick fences are no longer supported for directives
        # Use MyST-style nested tab-items instead of ### Tab: headers
        content = """
:::{note} Note 1
Content
:::

:::{note} Note 2
Content
:::

:::{tip} Tip 1
Content
:::

::::{tab-set}
:::{tab-item} A
Content A
:::

:::{tab-item} B
Content B
:::
::::

:::{dropdown} Dropdown 1
Content
:::
"""
        source_file = tmp_path / "mixed.md"
        source_file.write_text(content)

        output_file = tmp_path / "output" / "mixed.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("<html><body>Content</body></html>")

        page = MockPage(title="Test", source_path=source_file, output_path=output_file)
        site = MockSite(pages=[page])

        validator = DirectiveValidator()
        results = validator.validate(site)

        # With valid directives and no issues, validator follows "silence is golden"
        # principle - no error results for well-formed content
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) == 0

        # Verify analyzer correctly counts directives (internal check)
        # Note: nested tab-items count as separate directives (1 tab-set + 2 tab-items = 3)
        analyzer = DirectiveAnalyzer()
        data = analyzer.analyze(site)
        assert data["total_directives"] == 7  # 2 note + 1 tip + 1 tab-set + 2 tab-item + 1 dropdown
        assert data["by_type"]["note"] == 2
        assert data["by_type"]["tip"] == 1
        assert data["by_type"]["tab-set"] == 1
        assert data["by_type"]["tab-item"] == 2
        assert data["by_type"]["dropdown"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
