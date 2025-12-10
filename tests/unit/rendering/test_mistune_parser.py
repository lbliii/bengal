"""
Tests for Mistune parser and plugins.
"""

import pytest

from bengal.rendering.parsers import BaseMarkdownParser, MistuneParser, create_markdown_parser

# python-markdown is optional (mistune is default)
try:
    import importlib.util

    HAS_MARKDOWN = importlib.util.find_spec("markdown") is not None
except ImportError:
    HAS_MARKDOWN = False


class TestParserFactory:
    """Test the parser factory function."""

    def test_create_mistune_parser(self, parser):
        """Test creating a Mistune parser."""
        parser = create_markdown_parser("mistune")
        assert isinstance(parser, MistuneParser)
        assert isinstance(parser, BaseMarkdownParser)

    @pytest.mark.skipif(
        not HAS_MARKDOWN, reason="python-markdown not installed (optional dependency)"
    )
    def test_create_python_markdown_parser(self, parser):
        """Test creating a python-markdown parser."""
        parser = create_markdown_parser("python-markdown")
        assert isinstance(parser, BaseMarkdownParser)

    def test_create_default_parser(self, parser):
        """Test creating a parser with default engine."""
        parser = create_markdown_parser(None)
        assert isinstance(parser, BaseMarkdownParser)

    def test_invalid_engine_raises_error(self, parser):
        """Test that invalid engine raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported markdown engine"):
            create_markdown_parser("invalid-engine")


class TestMistuneParser:
    """Test the Mistune parser implementation."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_basic_markdown(self, parser):
        """Test parsing basic markdown."""
        content = "# Hello\n\nThis is **bold** text."
        result = parser.parse(content, {})

        assert "<h1" in result
        assert "Hello" in result
        assert "<strong>bold</strong>" in result

    def test_tables(self, parser):
        """Test GFM table support."""
        content = """
| Name | Age |
|------|-----|
| John | 30  |
"""
        result = parser.parse(content, {})
        assert "<table>" in result
        assert "<th>Name</th>" in result
        assert "<td>John</td>" in result

    def test_footnotes(self, parser):
        """Test footnote support."""
        content = """
Here is a footnote[^1].

[^1]: This is the footnote content.
"""
        result = parser.parse(content, {})
        assert "footnote" in result.lower()

    def test_definition_lists(self, parser):
        """Test definition list support."""
        content = """
Term
:   Definition
"""
        result = parser.parse(content, {})
        assert "<dl>" in result
        assert "<dt>Term</dt>" in result
        assert "<dd>Definition</dd>" in result

    def test_task_lists(self, parser):
        """Test task list support."""
        content = """
- [x] Completed task
- [ ] Incomplete task
"""
        result = parser.parse(content, {})
        assert "task-list" in result or "checkbox" in result

    def test_strikethrough(self, parser):
        """Test strikethrough support."""
        content = "~~strikethrough~~"
        result = parser.parse(content, {})
        assert "<del>" in result or "<s>" in result

    def test_code_blocks(self, parser):
        """Test code block support with syntax highlighting."""
        content = """
```python
print("hello")
```
"""
        result = parser.parse(content, {})
        assert "<pre>" in result
        assert "<code" in result
        # Check for Pygments highlighting (language class may not be present)
        assert '<div class="highlight">' in result or '<span class="nb">print</span>' in result

    def test_parse_with_toc(self, parser):
        """Test TOC generation."""
        content = """
# Main Title

## Section 1

Some content here.

## Section 2

More content.

### Subsection 2.1

Details.
"""
        html, toc = parser.parse_with_toc(content, {})

        # Check HTML has headings (now with IDs)
        assert "Section 1" in html
        assert "Section 2" in html
        assert 'id="section-1"' in html
        assert 'class="headerlink"' not in html

        # Check TOC structure (if generated)
        if toc:
            assert "Section 1" in toc or "Section 2" in toc


class TestAdmonitions:
    """Test custom admonition plugin."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_note_admonition(self, parser):
        """Test note admonition using colon-fenced directive syntax."""
        content = """:::{note} Important Note
This is a note with **markdown** support.
:::
"""
        result = parser.parse(content, {})

        assert "admonition" in result
        assert "note" in result
        assert "Important Note" in result
        assert "<strong>markdown</strong>" in result

    def test_warning_admonition(self, parser):
        """Test warning admonition."""
        content = """:::{warning} Be Careful
This is a warning.
:::
"""
        result = parser.parse(content, {})

        assert "admonition" in result
        assert "warning" in result
        assert "Be Careful" in result

    def test_admonition_without_title(self, parser):
        """Test admonition without explicit title."""
        content = """:::{tip}
Here's a tip!
:::
"""
        result = parser.parse(content, {})

        assert "admonition" in result
        assert "tip" in result or "Tip" in result

    def test_admonition_types(self, parser):
        """Test various admonition types."""
        types = ["note", "warning", "danger", "tip", "info", "example", "success"]

        for admon_type in types:
            content = f""":::{{{admon_type}}} Title
Content here.
:::
"""
            result = parser.parse(content, {})
            assert "admonition" in result
            assert admon_type in result


class TestDirectives:
    """Test custom directives (tabs, dropdowns)."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_dropdown_directive(self, parser):
        """Test dropdown directive."""
        content = """
:::{dropdown} Click to expand
:open: false

Hidden content with **markdown**.
:::
"""
        result = parser.parse(content, {})

        assert "<details" in result
        assert "dropdown" in result
        assert "<summary>Click to expand</summary>" in result
        assert "<strong>markdown</strong>" in result

    def test_dropdown_open_state(self, parser):
        """Test dropdown with open state."""
        content = """
:::{dropdown} Already open
:open: true

Visible content.
:::
"""
        result = parser.parse(content, {})

        assert "<details" in result
        assert "open" in result  # open attribute

    def test_tabs_directive(self, parser):
        """Test tabs directive."""
        content = """
:::{tabs}
:id: example

### Tab: First

Content in first tab.

### Tab: Second

Content in second tab.
:::
"""
        result = parser.parse(content, {})

        assert "tabs" in result
        assert "tab-nav" in result or "tab-title" in result
        assert "First" in result
        assert "Second" in result

    def test_nested_markdown_in_dropdown(self, parser):
        """Test markdown nesting in dropdown."""
        content = """
:::{dropdown} Details

- List item 1
- List item 2

**Bold text**

:::
"""
        result = parser.parse(content, {})

        assert "<details" in result
        assert "<li>" in result  # Lists work
        assert "<strong>" in result  # Bold works


class TestErrorHandling:
    """Test error handling in parser."""

    def test_empty_content(self, parser):
        """Test parsing empty content."""
        result = parser.parse("", {})
        assert result == "" or result.strip() == ""

    def test_invalid_markdown(self, parser):
        """Test parsing malformed markdown."""
        # Should not raise, just render as best as possible
        content = "# Heading\n\n[invalid link syntax"
        result = parser.parse(content, {})
        assert "<h1" in result

    def test_parser_reuse(self, parser):
        """Test that parser can be reused multiple times."""

        content1 = "# First"
        content2 = "# Second"

        result1 = parser.parse(content1, {})
        result2 = parser.parse(content2, {})

        assert "First" in result1
        assert "Second" in result2
        assert "Second" not in result1

    def test_missing_mistune_raises_import_error(self, monkeypatch):
        """Test that missing mistune raises clear error."""
        # Mock mistune import to fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "mistune":
                raise ImportError("No module named 'mistune'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(ImportError, match="mistune is not installed"):
            MistuneParser()


class TestPerformance:
    """Test performance characteristics."""

    def test_large_document(self, parser):
        """Test parsing a large document."""

        # Create a document with many headings and paragraphs
        content = "\n\n".join(
            [f"## Section {i}\n\nParagraph {i} with some **bold** text." for i in range(100)]
        )

        result = parser.parse(content, {})

        # Should complete without error
        assert "<h2" in result
        assert "Section 99" in result

    def test_toc_extraction_large_doc(self, parser):
        """Test TOC extraction from large document."""

        content = "\n\n".join([f"## Heading {i}" for i in range(50)])

        html, toc = parser.parse_with_toc(content, {})

        assert "Heading 0" in toc
        assert "Heading 49" in toc


class TestHeadingAnchors:
    """Test heading anchor injection and TOC extraction."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_heading_ids_injected(self, parser):
        """Test that heading IDs are properly injected."""
        content = "## Test Heading\n\nSome content."
        html, toc = parser.parse_with_toc(content, {})

        assert 'id="test-heading"' in html

    def test_headerlink_not_injected(self, parser):
        """Test that headerlink anchors (¶) are not injected by parser."""
        content = "## Test Heading\n\nSome content."
        html, toc = parser.parse_with_toc(content, {})

        assert 'class="headerlink"' not in html
        assert 'href="#test-heading"' not in html
        assert "¶" not in html

    def test_toc_extracted_correctly(self, parser):
        """Test that TOC is properly extracted from headings."""
        content = """
## First Section

Content here.

### Subsection

More content.

## Second Section

Final content.
        """

        html, toc = parser.parse_with_toc(content, {})

        # Check TOC structure
        assert '<div class="toc">' in toc
        assert "<ul>" in toc

        # Check TOC links
        assert 'href="#first-section"' in toc
        assert 'href="#subsection"' in toc
        assert 'href="#second-section"' in toc

        # Check TOC doesn't include ¶ symbol
        assert "¶" not in toc

    def test_special_characters_in_headings(self, parser):
        """Test that special characters are handled in slugs."""
        content = "## Test & Code: A Guide\n\nContent."
        html, toc = parser.parse_with_toc(content, {})

        # Should have a slug
        assert 'id="test-code-a-guide"' in html or 'id="test--code-a-guide"' in html

        # TOC should link to it
        assert 'href="#' in toc

    def test_html_entities_in_headings(self, parser):
        """Test that HTML entities in headings are properly decoded in TOC."""
        content = '## Strategy 3: The "Include" Directive (Advanced)\n\nContent.'
        html, toc = parser.parse_with_toc(content, {})

        # Should have a slug
        assert 'id="strategy-3-the-include-directive-advanced"' in html

        # TOC should contain decoded entities (not &quot;)
        assert 'Strategy 3: The "Include" Directive (Advanced)' in toc
        assert "&quot;" not in toc or '"' in toc  # Either decoded or both present

    def test_long_header_with_code_truncated(self, parser):
        """Test that headers with long code snippets are truncated in slugs and TOC."""
        # Create a header with a very long code snippet
        long_code = "a" * 200  # 200 characters
        content = f"## Using `{long_code}` in Your Code\n\nContent here."
        html, toc = parser.parse_with_toc(content, {})

        # Slug should be truncated to max 100 characters
        # Find the heading ID
        import re

        id_match = re.search(r'id="([^"]+)"', html)
        assert id_match, "Should have a heading ID"
        heading_id = id_match.group(1)
        assert len(heading_id) <= 100, f"Slug should be <= 100 chars, got {len(heading_id)}"

        # TOC title should be truncated to 80 characters with ellipsis
        toc_title_match = re.search(r'<a href="#[^"]+">([^<]+)</a>', toc)
        assert toc_title_match, "Should have TOC title"
        toc_title = toc_title_match.group(1)
        assert len(toc_title) <= 50, f"TOC title should be <= 50 chars, got {len(toc_title)}"
        if len(toc_title) == 50:
            assert toc_title.endswith("..."), "Long titles should end with ellipsis"

    def test_header_with_long_inline_code(self, parser):
        """Test that headers with long inline code are handled properly."""
        # Header with inline code that's very long
        long_function = "very_long_function_name_that_goes_on_and_on_and_on_and_on_and_on"
        content = f"## Calling `{long_function}` and `another_very_long_function_name`\n\nContent."
        html, toc = parser.parse_with_toc(content, {})

        # Should still generate valid slug (truncated if needed)
        import re

        id_match = re.search(r'id="([^"]+)"', html)
        assert id_match, "Should have a heading ID"
        heading_id = id_match.group(1)
        assert len(heading_id) <= 100, f"Slug should be <= 100 chars, got {len(heading_id)}"

        # TOC should have truncated title
        toc_title_match = re.search(r'<a href="#[^"]+">([^<]+)</a>', toc)
        assert toc_title_match, "Should have TOC title"
        toc_title = toc_title_match.group(1)
        assert len(toc_title) <= 50, f"TOC title should be <= 50 chars, got {len(toc_title)}"

    def test_multiple_long_headers(self, parser):
        """Test that multiple headers with long code are all handled correctly."""
        content = """
## Using `very_long_function_name_that_exceeds_normal_length_limits` in Production

Content here.

### Another `extremely_long_class_name_that_should_be_truncated_properly` Example

More content.

## Final `short_code` Header

Final content.
        """
        html, toc = parser.parse_with_toc(content, {})

        # All slugs should be <= 100 chars
        import re

        ids = re.findall(r'id="([^"]+)"', html)
        for heading_id in ids:
            assert len(heading_id) <= 100, (
                f"Slug '{heading_id}' should be <= 100 chars, got {len(heading_id)}"
            )

        # All TOC titles should be <= 50 chars (for 280px sidebar)
        titles = re.findall(r'<a href="#[^"]+">([^<]+)</a>', toc)
        for title in titles:
            assert len(title) <= 50, f"TOC title '{title}' should be <= 50 chars, got {len(title)}"

    def test_multiple_heading_levels(self, parser):
        """Test h2, h3, h4 all get anchors."""
        content = """
## Level 2
### Level 3
#### Level 4
        """

        html, toc = parser.parse_with_toc(content, {})

        # All should have IDs
        assert 'id="level-2"' in html
        assert 'id="level-3"' in html
        assert 'id="level-4"' in html

        # All should be in TOC
        assert 'href="#level-2"' in toc
        assert 'href="#level-3"' in toc
        assert 'href="#level-4"' in toc

    def test_empty_content_no_crash(self, parser):
        """Test that empty content doesn't crash."""
        content = "Just text, no headings."
        html, toc = parser.parse_with_toc(content, {})

        assert "Just text" in html
        assert toc == "" or '<div class="toc">' not in toc

    def test_existing_ids_preserved(self, parser):
        """Test that if Mistune adds IDs, we don't duplicate."""
        # This is future-proofing in case Mistune starts adding IDs
        content = "## Test Heading"
        html, toc = parser.parse_with_toc(content, {})

        # Should have exactly one ID per heading
        assert html.count('id="test-heading"') == 1

    def test_toc_indentation(self, parser):
        """Test that TOC has correct indentation for nested headings."""
        content = """
## H2 First
### H3 Nested
## H2 Second
        """

        html, toc = parser.parse_with_toc(content, {})

        # h3 should be indented (2 spaces)
        lines = toc.split("\n")
        h3_line = [line for line in lines if "H3 Nested" in line][0]
        assert h3_line.startswith("  <li>")  # 2 space indent


class TestExplicitAnchorSyntax:
    """Test MyST-compatible {#custom-id} explicit anchor syntax."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_explicit_id_creates_custom_anchor(self, parser):
        """Test that {#custom-id} syntax creates custom anchor ID."""
        content = "## Installation {#install}\n\nContent here."
        html, toc = parser.parse_with_toc(content, {})

        # Should have custom ID, not auto-generated
        assert 'id="install"' in html
        assert 'id="installation"' not in html

    def test_explicit_id_stripped_from_display(self, parser):
        """Test that {#id} is removed from displayed heading text."""
        content = "## Installation {#install}\n\nContent here."
        html, toc = parser.parse_with_toc(content, {})

        # {#install} should not appear in visible content
        assert "{#install}" not in html
        # But heading text should still be there
        assert "Installation" in html

    def test_explicit_id_stripped_from_toc(self, parser):
        """Test that {#id} is removed from TOC display."""
        content = "## Installation {#install}\n\nContent here."
        html, toc = parser.parse_with_toc(content, {})

        # TOC should show "Installation" without {#install}
        assert "{#install}" not in toc
        assert "Installation" in toc
        # TOC should link to the explicit ID
        assert 'href="#install"' in toc

    def test_explicit_id_with_complex_syntax(self, parser):
        """Test {#id} with hyphens and underscores in ID."""
        content = "## Getting Started Guide {#getting-started_guide}\n\nContent."
        html, toc = parser.parse_with_toc(content, {})

        assert 'id="getting-started_guide"' in html
        assert "{#getting-started_guide}" not in html
        assert 'href="#getting-started_guide"' in toc

    def test_mixed_explicit_and_auto_anchors(self, parser):
        """Test that explicit and auto-generated anchors coexist."""
        content = """
## With Explicit ID {#explicit}

Content here.

## Without Explicit ID

More content.

## Another Explicit {#another-explicit}

Final content.
        """
        html, toc = parser.parse_with_toc(content, {})

        # Explicit IDs used where specified
        assert 'id="explicit"' in html
        assert 'id="another-explicit"' in html

        # Auto-generated for the one without explicit ID
        assert 'id="without-explicit-id"' in html

        # No {#...} in visible output
        assert "{#explicit}" not in html
        assert "{#another-explicit}" not in html

    def test_explicit_id_preserves_heading_content(self, parser):
        """Test that heading content with code and formatting is preserved."""
        content = "## Using `config.yaml` for Setup {#config-setup}\n\nContent."
        html, toc = parser.parse_with_toc(content, {})

        assert 'id="config-setup"' in html
        assert "<code>config.yaml</code>" in html
        assert "{#config-setup}" not in html

    def test_explicit_id_case_sensitive(self, parser):
        """Test that explicit ID is used exactly as specified (case preserved)."""
        content = "## API Reference {#APIRef}\n\nContent."
        html, toc = parser.parse_with_toc(content, {})

        # ID should be exactly as specified
        assert 'id="APIRef"' in html
        assert 'href="#APIRef"' in toc

    def test_explicit_id_with_multiple_levels(self, parser):
        """Test explicit IDs work across different heading levels."""
        content = """
## Level 2 {#lvl2}
### Level 3 {#lvl3}
#### Level 4 {#lvl4}
        """
        html, toc = parser.parse_with_toc(content, {})

        assert 'id="lvl2"' in html
        assert 'id="lvl3"' in html
        assert 'id="lvl4"' in html

        assert 'href="#lvl2"' in toc
        assert 'href="#lvl3"' in toc
        assert 'href="#lvl4"' in toc

    def test_explicit_id_pattern_requirements(self, parser):
        """Test that ID must start with letter."""
        # Valid: starts with letter
        content = "## Valid {#a123}\n\nContent."
        html, toc = parser.parse_with_toc(content, {})
        assert 'id="a123"' in html

        # The pattern requires ID to start with letter, so {#123abc} won't match
        # and falls back to auto-generated slug
        content2 = "## Invalid Start {#123abc}\n\nContent."
        html2, toc2 = parser.parse_with_toc(content2, {})
        # Should fall back to auto-generated since pattern doesn't match
        # The {#123abc} stays in content and auto-slug is generated
        assert 'id="invalid-start-123abc"' in html2 or "{#123abc}" in html2

    def test_blockquote_headings_without_explicit_id(self, parser):
        """Test that blockquote headings work without getting IDs."""
        content = """
## Regular Heading {#regular}

> ## Quoted Heading {#quoted}
> This is inside a blockquote

## Another Regular {#another}
        """
        html, toc = parser.parse_with_toc(content, {})

        # Regular headings should have explicit IDs
        assert 'id="regular"' in html
        assert 'id="another"' in html

        # Blockquote headings should NOT get IDs
        # (they're inside <blockquote> so we skip them)
        # The {#quoted} should remain in the blockquote content
        assert 'href="#quoted"' not in toc
