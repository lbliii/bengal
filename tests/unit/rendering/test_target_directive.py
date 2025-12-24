"""
Tests for the target directive (explicit anchor targets).

The target directive creates invisible anchor elements that can be
referenced via [[#anchor-id]] cross-reference syntax.

Related: bengal/rendering/plugins/directives/target.py
"""

import pytest

from bengal.rendering.parsers import MistuneParser


class TestTargetDirective:
    """Test the target directive for explicit anchor targets."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_basic_target_creates_anchor(self, parser):
        """Test that :::{target} creates an anchor element."""
        content = """
:::{target} my-anchor
:::

Some content after the anchor.
        """
        result = parser.parse(content, {})

        assert 'id="my-anchor"' in result
        assert 'class="target-anchor"' in result

    def test_target_is_invisible_span(self, parser):
        """Test that target renders as a span element."""
        content = """
:::{target} invisible-anchor
:::
        """
        result = parser.parse(content, {})

        assert '<span id="invisible-anchor"' in result
        assert "</span>" in result

    def test_target_with_hyphenated_id(self, parser):
        """Test target with hyphenated ID."""
        content = """
:::{target} my-complex-anchor-id
:::
        """
        result = parser.parse(content, {})

        assert 'id="my-complex-anchor-id"' in result

    def test_target_with_underscored_id(self, parser):
        """Test target with underscored ID."""
        content = """
:::{target} my_anchor_id
:::
        """
        result = parser.parse(content, {})

        assert 'id="my_anchor_id"' in result

    def test_target_with_numbers_in_id(self, parser):
        """Test target with numbers in ID."""
        content = """
:::{target} step3-config
:::
        """
        result = parser.parse(content, {})

        assert 'id="step3-config"' in result

    def test_target_alias_anchor(self, parser):
        """Test that :::{anchor} works as alias for :::{target}."""
        content = """
:::{anchor} my-alias-anchor
:::
        """
        result = parser.parse(content, {})

        assert 'id="my-alias-anchor"' in result
        assert 'class="target-anchor"' in result

    def test_target_content_is_ignored(self, parser):
        """Test that content inside target directive is ignored."""
        content = """
:::{target} ignore-content
This content should not appear in output.
:::
        """
        result = parser.parse(content, {})

        assert 'id="ignore-content"' in result
        # Content should NOT be in output (targets are point anchors)
        assert "This content should not appear" not in result

    def test_target_invalid_id_starting_with_number(self, parser):
        """Test that ID starting with number shows error."""
        content = """
:::{target} 123invalid
:::
        """
        result = parser.parse(content, {})

        # Should show error message
        assert "directive-error" in result or "error" in result.lower()

    def test_target_empty_id_shows_error(self, parser):
        """Test that empty ID shows error."""
        content = """
:::{target}
:::
        """
        result = parser.parse(content, {})

        # Should show error message
        assert "directive-error" in result or "error" in result.lower()

    def test_multiple_targets_in_document(self, parser):
        """Test multiple targets in the same document."""
        content = """
:::{target} first-anchor
:::

Some content here.

:::{target} second-anchor
:::

More content.

:::{target} third-anchor
:::
        """
        result = parser.parse(content, {})

        assert 'id="first-anchor"' in result
        assert 'id="second-anchor"' in result
        assert 'id="third-anchor"' in result

    def test_target_before_admonition(self, parser):
        """Test target placed before an admonition (common use case)."""
        content = """
:::{target} important-note
:::

:::{note}
This is an important note that can be linked to directly.
:::
        """
        result = parser.parse(content, {})

        assert 'id="important-note"' in result
        assert "admonition" in result
        assert "important note" in result.lower()

    def test_target_id_case_preserved(self, parser):
        """Test that ID casing is preserved in output."""
        content = """
:::{target} CamelCaseAnchor
:::
        """
        result = parser.parse(content, {})

        # ID should be exactly as specified
        assert 'id="CamelCaseAnchor"' in result


class TestTargetDirectiveValidation:
    """Test validation rules for target directive."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_valid_id_starts_with_letter(self, parser):
        """Test that ID starting with letter is valid."""
        content = """
:::{target} valid-id
:::
        """
        result = parser.parse(content, {})

        assert 'id="valid-id"' in result
        assert "directive-error" not in result

    def test_valid_id_starts_with_uppercase(self, parser):
        """Test that ID starting with uppercase letter is valid."""
        content = """
:::{target} ValidId
:::
        """
        result = parser.parse(content, {})

        assert 'id="ValidId"' in result
        assert "directive-error" not in result

    def test_invalid_id_with_special_chars(self, parser):
        """Test that ID with special characters shows error."""
        content = """
:::{target} invalid@id
:::
        """
        result = parser.parse(content, {})

        # Should show error
        assert "directive-error" in result or "error" in result.lower()

    def test_invalid_id_with_spaces(self, parser):
        """Test that ID with spaces uses only first word or shows error."""
        content = """
:::{target} invalid id with spaces
:::
        """
        result = parser.parse(content, {})

        # Either uses first part or shows error
        # The regex validates the stripped title, so "invalid id with spaces" would fail
        assert "directive-error" in result or 'id="invalid"' in result


class TestTargetDirectiveIntegration:
    """Integration tests for target directive with other features."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_target_doesnt_affect_toc(self, parser):
        """Test that targets don't appear in TOC."""
        content = """
## Introduction

:::{target} important-section
:::

### Details

Content here.
        """
        html, toc = parser.parse_with_toc(content, {})

        # Target should be in HTML
        assert 'id="important-section"' in html

        # TOC should NOT include target
        assert "important-section" not in toc
        # But should include actual headings
        assert "Introduction" in toc
        assert "Details" in toc

    def test_target_with_explicit_heading_anchors(self, parser):
        """Test that targets work alongside explicit heading anchors."""
        content = """
## Introduction {#intro}

:::{target} intro-detail
:::

More details about the introduction.
        """
        html, toc = parser.parse_with_toc(content, {})

        # Both should be present
        assert 'id="intro"' in html  # Explicit heading anchor
        assert 'id="intro-detail"' in html  # Target directive

        # TOC should use explicit heading anchor
        assert 'href="#intro"' in toc


