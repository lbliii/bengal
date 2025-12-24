"""
Unit tests for Enhanced Code Tabs (RFC: Enhanced Code Tabs).

Tests:
- Tab marker parsing (language, filename)
- Code block info parsing (highlights)
- Pygments integration
- Sync attributes
- Language icons
- Backward compatibility
"""

from __future__ import annotations

import pytest

from bengal.directives.code_tabs import (
    CodeTabsDirective,
    CodeTabsOptions,
    LANGUAGE_ICONS,
    get_language_icon,
    parse_code_block_info,
    parse_hl_lines,
    parse_tab_marker,
    render_code_tab_item,
    render_code_with_pygments,
)


class TestParseTabMarker:
    """Tests for tab marker parsing."""

    def test_simple_language(self):
        """Tab markers parse simple language names."""
        lang, filename = parse_tab_marker("Python")
        assert lang == "Python"
        assert filename is None

    def test_language_with_filename(self):
        """Tab markers parse language with filename."""
        lang, filename = parse_tab_marker("Python (main.py)")
        assert lang == "Python"
        assert filename == "main.py"

    def test_tab_prefix(self):
        """Tab markers work with Tab: prefix."""
        lang, filename = parse_tab_marker("Tab: Go")
        # Note: The split pattern handles this, but parse_tab_marker gets the cleaned string
        assert lang == "Tab: Go"  # The Tab: prefix would be stripped by the regex split
        assert filename is None

    def test_filename_with_dots(self):
        """Filenames with dots in the name are parsed correctly."""
        lang, filename = parse_tab_marker("Rust (lib.rs)")
        assert lang == "Rust"
        assert filename == "lib.rs"

    def test_filename_with_hyphen(self):
        """Filenames with hyphens are parsed correctly."""
        lang, filename = parse_tab_marker("Config (my-config.yaml)")
        assert lang == "Config"
        assert filename == "my-config.yaml"

    def test_version_annotation_not_filename(self):
        """Version annotations like (v3.12+) are NOT parsed as filenames."""
        lang, filename = parse_tab_marker("Python (v3.12+)")
        assert lang == "Python (v3.12+)"
        assert filename is None

    def test_node_version_not_filename(self):
        """Node.js version annotations are NOT parsed as filenames."""
        lang, filename = parse_tab_marker("Node.js (v18)")
        assert lang == "Node.js (v18)"
        assert filename is None

    def test_whitespace_handling(self):
        """Whitespace is handled correctly."""
        lang, filename = parse_tab_marker("  Python  ")
        assert lang == "Python"
        assert filename is None


class TestParseHlLines:
    """Tests for line highlight parsing."""

    def test_single_line(self):
        """Single line number is parsed."""
        assert parse_hl_lines("5") == [5]

    def test_multiple_lines(self):
        """Multiple comma-separated lines are parsed."""
        assert parse_hl_lines("1,3,5") == [1, 3, 5]

    def test_range(self):
        """Ranges are expanded correctly."""
        assert parse_hl_lines("1-3") == [1, 2, 3]

    def test_mixed(self):
        """Mixed single lines and ranges work together."""
        assert parse_hl_lines("1,3-5,7") == [1, 3, 4, 5, 7]

    def test_with_spaces(self):
        """Spaces in the specification are handled."""
        assert parse_hl_lines("1, 3-5, 7") == [1, 3, 4, 5, 7]

    def test_empty_string(self):
        """Empty string returns empty list."""
        assert parse_hl_lines("") == []

    def test_invalid_values(self):
        """Invalid values are skipped."""
        assert parse_hl_lines("a,2,b") == [2]

    def test_deduplication(self):
        """Duplicate line numbers are deduplicated."""
        assert parse_hl_lines("1,1,2,2-3") == [1, 2, 3]


class TestParseCodeBlockInfo:
    """Tests for code block info string parsing."""

    def test_highlight_braces(self):
        """Highlights in braces are parsed."""
        title, hl_lines = parse_code_block_info("{1,3-5}")
        assert title is None
        assert hl_lines == [1, 3, 4, 5]

    def test_single_line_highlight(self):
        """Single line highlight works."""
        title, hl_lines = parse_code_block_info("{5}")
        assert hl_lines == [5]

    def test_empty_info(self):
        """Empty info string returns empty results."""
        title, hl_lines = parse_code_block_info("")
        assert title is None
        assert hl_lines == []

    def test_none_info(self):
        """None info string returns empty results."""
        title, hl_lines = parse_code_block_info(None)
        assert title is None
        assert hl_lines == []


class TestRenderCodeWithPygments:
    """Tests for Pygments rendering."""

    def test_basic_highlighting(self):
        """Code is highlighted with Pygments."""
        html, plain = render_code_with_pygments("print('hello')", "python")
        assert 'class="highlight"' in html
        assert "hello" in html
        assert plain == "print('hello')"

    def test_plain_code_preserved(self):
        """Plain code is returned unchanged for copy."""
        code = "def foo():\n    pass"
        html, plain = render_code_with_pygments(code, "python")
        assert plain == code

    def test_line_numbers_auto(self):
        """Line numbers appear for 3+ line code by default."""
        short_code = "x = 1"
        long_code = "x = 1\ny = 2\nz = 3"

        short_html, _ = render_code_with_pygments(short_code, "python")
        long_html, _ = render_code_with_pygments(long_code, "python")

        # Short code shouldn't have line numbers table
        assert "linenos" not in short_html or "highlighttable" not in short_html

        # Long code should have line numbers (highlighttable)
        assert "highlighttable" in long_html

    def test_line_numbers_forced(self):
        """Line numbers can be forced on."""
        code = "x = 1"
        html, _ = render_code_with_pygments(code, "python", line_numbers=True)
        assert "highlighttable" in html

    def test_line_numbers_disabled(self):
        """Line numbers can be forced off."""
        code = "x = 1\ny = 2\nz = 3\na = 4"
        html, _ = render_code_with_pygments(code, "python", line_numbers=False)
        assert "highlighttable" not in html

    def test_line_highlighting(self):
        """Highlighted lines get .hll class."""
        code = "line1\nline2\nline3"
        html, _ = render_code_with_pygments(code, "text", hl_lines=[2])
        assert "hll" in html

    def test_unknown_language_fallback(self):
        """Unknown languages fall back to text."""
        html, plain = render_code_with_pygments("hello", "unknownlang123")
        assert plain == "hello"
        assert 'class="highlight"' in html


class TestLanguageIcons:
    """Tests for language icon mapping."""

    def test_bash_terminal_icon(self):
        """Shell languages map to terminal icon."""
        assert LANGUAGE_ICONS["bash"] == "terminal"
        assert LANGUAGE_ICONS["shell"] == "terminal"
        assert LANGUAGE_ICONS["zsh"] == "terminal"

    def test_sql_database_icon(self):
        """SQL languages map to database icon."""
        assert LANGUAGE_ICONS["sql"] == "database"
        assert LANGUAGE_ICONS["mysql"] == "database"
        assert LANGUAGE_ICONS["postgresql"] == "database"

    def test_config_file_code_icon(self):
        """Config formats map to file-code icon."""
        assert LANGUAGE_ICONS["json"] == "file-code"
        assert LANGUAGE_ICONS["yaml"] == "file-code"
        assert LANGUAGE_ICONS["toml"] == "file-code"

    def test_default_icon(self):
        """Default icon is 'code'."""
        assert LANGUAGE_ICONS["_default"] == "code"

    def test_get_language_icon_known(self):
        """get_language_icon returns icon for known languages."""
        # Note: This may return empty string if icon doesn't exist
        icon = get_language_icon("bash")
        # Just verify it doesn't error; actual content depends on icon library
        assert isinstance(icon, str)

    def test_get_language_icon_unknown(self):
        """get_language_icon handles unknown languages gracefully."""
        icon = get_language_icon("unknownlang123")
        # Should return default icon or empty string
        assert isinstance(icon, str)


class TestCodeTabsOptions:
    """Tests for CodeTabsOptions dataclass."""

    def test_default_values(self):
        """Default options have expected values."""
        opts = CodeTabsOptions()
        assert opts.sync == "language"
        assert opts.line_numbers is None
        assert opts.highlight == ""
        assert opts.icons is True

    def test_sync_none(self):
        """Sync can be set to 'none' to disable."""
        opts = CodeTabsOptions(sync="none")
        assert opts.sync == "none"

    def test_line_numbers_explicit(self):
        """Line numbers can be explicitly set."""
        opts = CodeTabsOptions(line_numbers=True)
        assert opts.line_numbers is True

    def test_highlight_lines(self):
        """Global highlight lines can be set."""
        opts = CodeTabsOptions(highlight="1,3-5")
        assert opts.highlight == "1,3-5"


class TestRenderCodeTabItem:
    """Tests for internal tab item rendering."""

    def test_basic_render(self):
        """Basic tab item renders with all attributes."""
        html = render_code_tab_item(None, lang="Python", code="print('hi')")
        assert 'data-lang="Python"' in html
        assert 'data-code="print(&#x27;hi&#x27;)"' in html

    def test_with_filename(self):
        """Filename is included in output."""
        html = render_code_tab_item(
            None, lang="Python", code="pass", filename="main.py"
        )
        assert 'data-filename="main.py"' in html

    def test_with_hl_lines(self):
        """Highlight lines are serialized."""
        html = render_code_tab_item(
            None, lang="Python", code="pass", hl_lines=[1, 3, 5]
        )
        assert 'data-hl-lines="1,3,5"' in html

    def test_html_escaping(self):
        """HTML in code is escaped."""
        html = render_code_tab_item(None, lang="HTML", code="<div>test</div>")
        assert "&lt;div&gt;" in html


class TestCodeTabsDirectiveRender:
    """Tests for CodeTabsDirective.render() method."""

    def setup_method(self):
        """Set up test fixture."""
        self.directive = CodeTabsDirective()

    def test_sync_attributes_present(self):
        """Sync attributes are added to output."""
        # Create internal tab item markers
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            '</div>'
        )
        html = self.directive.render(None, text, sync="language")
        assert 'data-sync="language"' in html
        assert 'data-sync-value="python"' in html

    def test_sync_none_disables(self):
        """sync: none disables sync attributes."""
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            '</div>'
        )
        html = self.directive.render(None, text, sync="none")
        assert 'data-sync=' not in html
        assert 'data-sync-value=' not in html

    def test_aria_attributes(self):
        """ARIA attributes are present for accessibility."""
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            '</div>'
        )
        html = self.directive.render(None, text, sync="language")
        assert 'role="tab"' in html
        assert 'aria-selected=' in html
        assert 'role="tabpanel"' in html

    def test_copy_button_present(self):
        """Copy button is added to each pane."""
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            '</div>'
        )
        html = self.directive.render(None, text, sync="language")
        assert 'class="copy-btn"' in html
        assert 'data-copy-target=' in html

    def test_filename_badge(self):
        """Filename badge appears when filename is present."""
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="main.py" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            '</div>'
        )
        html = self.directive.render(None, text, sync="language")
        assert 'class="tab-filename"' in html
        assert "main.py" in html

    def test_backward_compat_legacy_format(self):
        """Legacy tab item format still works."""
        # Old format without enhanced attributes
        text = '<div class="code-tab-item" data-lang="Python" data-code="pass"></div>'
        html = self.directive.render(None, text, sync="language")
        # Should still render, even if with defaults
        assert 'class="code-tabs"' in html
        assert "Python" in html

    def test_bengal_tabs_attribute(self):
        """data-bengal='tabs' attribute is present for JS enhancement."""
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            '</div>'
        )
        html = self.directive.render(None, text, sync="language")
        assert 'data-bengal="tabs"' in html


class TestCodeTabsDirectiveParse:
    """Tests for CodeTabsDirective.parse_directive() method."""

    def setup_method(self):
        """Set up test fixture."""
        self.directive = CodeTabsDirective()

    def test_parses_simple_tabs(self):
        """Simple tab structure is parsed."""
        content = """
### Python
```python
print("hello")
```

### JavaScript
```javascript
console.log("hello");
```
"""
        result = self.directive.parse_directive(
            title="",
            options=CodeTabsOptions(),
            content=content,
            children=[],
            state=None,
        )

        assert result["type"] == "code_tabs"
        assert len(result["children"]) == 2
        assert result["children"][0]["attrs"]["lang"] == "Python"
        assert result["children"][1]["attrs"]["lang"] == "JavaScript"

    def test_extracts_code(self):
        """Code is extracted from fenced blocks."""
        content = """
### Python
```python
def hello():
    print("hello")
```
"""
        result = self.directive.parse_directive(
            title="",
            options=CodeTabsOptions(),
            content=content,
            children=[],
            state=None,
        )

        code = result["children"][0]["attrs"]["code"]
        # Code should contain the function definition
        assert 'print("hello")' in code

    def test_filename_extraction(self):
        """Filenames are extracted from tab markers."""
        content = """
### Python (main.py)
```python
pass
```
"""
        result = self.directive.parse_directive(
            title="",
            options=CodeTabsOptions(),
            content=content,
            children=[],
            state=None,
        )

        assert result["children"][0]["attrs"]["filename"] == "main.py"

    def test_per_tab_highlights(self):
        """Per-tab highlights are extracted from info string."""
        content = """
### Python
```python {2-3}
line1
line2
line3
```
"""
        result = self.directive.parse_directive(
            title="",
            options=CodeTabsOptions(),
            content=content,
            children=[],
            state=None,
        )

        assert result["children"][0]["attrs"]["hl_lines"] == [2, 3]

    def test_global_highlights_merged(self):
        """Global highlights are merged with per-tab highlights."""
        content = """
### Python
```python {3}
line1
line2
line3
```
"""
        opts = CodeTabsOptions(highlight="1")
        result = self.directive.parse_directive(
            title="",
            options=opts,
            content=content,
            children=[],
            state=None,
        )

        # Should have both line 1 (global) and line 3 (per-tab)
        assert 1 in result["children"][0]["attrs"]["hl_lines"]
        assert 3 in result["children"][0]["attrs"]["hl_lines"]

    def test_options_stored_in_attrs(self):
        """Options are stored in attrs for render phase."""
        content = """
### Python
```python
pass
```
"""
        opts = CodeTabsOptions(sync="api-examples", icons=False)
        result = self.directive.parse_directive(
            title="",
            options=opts,
            content=content,
            children=[],
            state=None,
        )

        assert result["attrs"]["sync"] == "api-examples"
        assert result["attrs"]["icons"] is False

