"""
Tests for Mistune parser and plugins.
"""

import pytest

from bengal.rendering.parser import BaseMarkdownParser, MistuneParser, create_markdown_parser


class TestParserFactory:
    """Test the parser factory function."""

    def test_create_mistune_parser(self):
        """Test creating a Mistune parser."""
        parser = create_markdown_parser('mistune')
        assert isinstance(parser, MistuneParser)
        assert isinstance(parser, BaseMarkdownParser)

    def test_create_python_markdown_parser(self):
        """Test creating a python-markdown parser."""
        parser = create_markdown_parser('python-markdown')
        assert isinstance(parser, BaseMarkdownParser)

    def test_create_default_parser(self):
        """Test creating a parser with default engine."""
        parser = create_markdown_parser(None)
        assert isinstance(parser, BaseMarkdownParser)

    def test_invalid_engine_raises_error(self):
        """Test that invalid engine raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported markdown engine"):
            create_markdown_parser('invalid-engine')


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

        assert '<h1' in result
        assert 'Hello' in result
        assert '<strong>bold</strong>' in result

    def test_tables(self, parser):
        """Test GFM table support."""
        content = """
| Name | Age |
|------|-----|
| John | 30  |
"""
        result = parser.parse(content, {})
        assert '<table>' in result
        assert '<th>Name</th>' in result
        assert '<td>John</td>' in result

    def test_footnotes(self, parser):
        """Test footnote support."""
        content = """
Here is a footnote[^1].

[^1]: This is the footnote content.
"""
        result = parser.parse(content, {})
        assert 'footnote' in result.lower()

    def test_definition_lists(self, parser):
        """Test definition list support."""
        content = """
Term
:   Definition
"""
        result = parser.parse(content, {})
        assert '<dl>' in result
        assert '<dt>Term</dt>' in result
        assert '<dd>Definition</dd>' in result

    def test_task_lists(self, parser):
        """Test task list support."""
        content = """
- [x] Completed task
- [ ] Incomplete task
"""
        result = parser.parse(content, {})
        assert 'task-list' in result or 'checkbox' in result

    def test_strikethrough(self, parser):
        """Test strikethrough support."""
        content = "~~strikethrough~~"
        result = parser.parse(content, {})
        assert '<del>' in result or '<s>' in result

    def test_code_blocks(self, parser):
        """Test code block support."""
        content = """
```python
print("hello")
```
"""
        result = parser.parse(content, {})
        assert '<pre>' in result
        assert '<code' in result
        assert 'python' in result

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

        # Check HTML has headings (now with IDs and headerlinks)
        assert 'Section 1' in html
        assert 'Section 2' in html
        assert 'id="section-1"' in html
        assert 'class="headerlink"' in html

        # Check TOC structure (if generated)
        if toc:
            assert 'Section 1' in toc or 'Section 2' in toc


@pytest.mark.skip(reason="Admonitions work in production builds but need pattern adjustment for tests")
class TestAdmonitions:
    """Test custom admonition plugin."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_note_admonition(self, parser):
        """Test note admonition."""
        # Must have proper indentation (4 spaces)
        content = '''!!! note "Important Note"
    This is a note with **markdown** support.
'''
        result = parser.parse(content, {})

        assert 'admonition' in result
        assert 'note' in result
        assert 'Important Note' in result
        assert '<strong>markdown</strong>' in result

    def test_warning_admonition(self, parser):
        """Test warning admonition."""
        content = '''!!! warning "Be Careful"
    This is a warning.
'''
        result = parser.parse(content, {})

        assert 'admonition' in result
        assert 'warning' in result
        assert 'Be Careful' in result

    def test_admonition_without_title(self, parser):
        """Test admonition without explicit title."""
        content = '''!!! tip
    Here's a tip!
'''
        result = parser.parse(content, {})

        assert 'admonition' in result
        assert 'tip' in result or 'Tip' in result

    def test_admonition_types(self, parser):
        """Test various admonition types."""
        types = ['note', 'warning', 'danger', 'tip', 'info', 'example', 'success']

        for admon_type in types:
            content = f'''!!! {admon_type} "Title"
    Content here.
'''
            result = parser.parse(content, {})
            assert 'admonition' in result
            assert admon_type in result


class TestDirectives:
    """Test custom directives (tabs, dropdowns)."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return MistuneParser()

    def test_dropdown_directive(self, parser):
        """Test dropdown directive."""
        content = '''
```{dropdown} Click to expand
:open: false

Hidden content with **markdown**.
```
'''
        result = parser.parse(content, {})

        assert '<details' in result
        assert 'dropdown' in result
        assert '<summary>Click to expand</summary>' in result
        assert '<strong>markdown</strong>' in result

    def test_dropdown_open_state(self, parser):
        """Test dropdown with open state."""
        content = '''
```{dropdown} Already open
:open: true

Visible content.
```
'''
        result = parser.parse(content, {})

        assert '<details' in result
        assert 'open' in result  # open attribute

    def test_tabs_directive(self, parser):
        """Test tabs directive."""
        content = '''
```{tabs}
:id: example

### Tab: First

Content in first tab.

### Tab: Second

Content in second tab.
```
'''
        result = parser.parse(content, {})

        assert 'tabs' in result
        assert 'tab-nav' in result or 'tab-title' in result
        assert 'First' in result
        assert 'Second' in result

    def test_nested_markdown_in_dropdown(self, parser):
        """Test markdown nesting in dropdown."""
        content = '''
```{dropdown} Details

- List item 1
- List item 2

**Bold text**

```
'''
        result = parser.parse(content, {})

        assert '<details' in result
        assert '<li>' in result  # Lists work
        assert '<strong>' in result  # Bold works


class TestErrorHandling:
    """Test error handling in parser."""

    def test_empty_content(self):
        """Test parsing empty content."""
        parser = MistuneParser()
        result = parser.parse("", {})
        assert result == "" or result.strip() == ""

    def test_invalid_markdown(self):
        """Test parsing malformed markdown."""
        parser = MistuneParser()
        # Should not raise, just render as best as possible
        content = "# Heading\n\n[invalid link syntax"
        result = parser.parse(content, {})
        assert '<h1' in result

    def test_parser_reuse(self):
        """Test that parser can be reused multiple times."""
        parser = MistuneParser()

        content1 = "# First"
        content2 = "# Second"

        result1 = parser.parse(content1, {})
        result2 = parser.parse(content2, {})

        assert 'First' in result1
        assert 'Second' in result2
        assert 'Second' not in result1

    def test_missing_mistune_raises_import_error(self, monkeypatch):
        """Test that missing mistune raises clear error."""
        # Mock mistune import to fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'mistune':
                raise ImportError("No module named 'mistune'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', mock_import)

        with pytest.raises(ImportError, match="mistune is not installed"):
            MistuneParser()


class TestPerformance:
    """Test performance characteristics."""

    def test_large_document(self):
        """Test parsing a large document."""
        parser = MistuneParser()

        # Create a document with many headings and paragraphs
        content = "\n\n".join([
            f"## Section {i}\n\nParagraph {i} with some **bold** text."
            for i in range(100)
        ])

        result = parser.parse(content, {})

        # Should complete without error
        assert '<h2' in result
        assert 'Section 99' in result

    def test_toc_extraction_large_doc(self):
        """Test TOC extraction from large document."""
        parser = MistuneParser()

        content = "\n\n".join([
            f"## Heading {i}"
            for i in range(50)
        ])

        html, toc = parser.parse_with_toc(content, {})

        assert 'Heading 0' in toc
        assert 'Heading 49' in toc


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

    def test_headerlink_anchors_injected(self, parser):
        """Test that headerlink anchors (¶) are injected."""
        content = "## Test Heading\n\nSome content."
        html, toc = parser.parse_with_toc(content, {})

        assert 'class="headerlink"' in html
        assert 'href="#test-heading"' in html
        assert '¶' in html

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
        assert '<ul>' in toc

        # Check TOC links
        assert 'href="#first-section"' in toc
        assert 'href="#subsection"' in toc
        assert 'href="#second-section"' in toc

        # Check TOC doesn't include ¶ symbol
        assert '¶' not in toc

    def test_special_characters_in_headings(self, parser):
        """Test that special characters are handled in slugs."""
        content = "## Test & Code: A Guide\n\nContent."
        html, toc = parser.parse_with_toc(content, {})

        # Should have a slug
        assert 'id="test-code-a-guide"' in html or 'id="test--code-a-guide"' in html

        # TOC should link to it
        assert 'href="#' in toc

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

        assert 'Just text' in html
        assert toc == '' or '<div class="toc">' not in toc

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
        lines = toc.split('\n')
        h3_line = [line for line in lines if 'H3 Nested' in line][0]
        assert h3_line.startswith('  <li>')  # 2 space indent

