"""
Unit tests for Code Tabs (RFC: Simplified Code Tabs Syntax v2).

Tests:
- v2 simplified syntax (info string parsing)
- Language display names
- Pygments integration
- Sync attributes
- Language icons
- Legacy ### marker syntax (backward compatibility)
"""

from __future__ import annotations

from bengal.directives.code_tabs import (
    LANGUAGE_DISPLAY_NAMES,
    LANGUAGE_ICONS,
    CodeTabsDirective,
    CodeTabsOptions,
    get_display_name,
    get_language_icon,
    parse_hl_lines,
    parse_info_string,
    parse_tab_marker,
    render_code_tab_item,
    render_code_with_pygments,
)

# ============================================================================
# v2 Simplified Syntax Tests
# ============================================================================


class TestParseInfoString:
    """Tests for v2 info string parsing."""

    def test_empty_string(self):
        """Empty info string returns all None/empty."""
        filename, title, hl_lines = parse_info_string("")
        assert filename is None
        assert title is None
        assert hl_lines == []

    def test_filename_only(self):
        """Just a filename is parsed."""
        filename, title, hl_lines = parse_info_string("app.py")
        assert filename == "app.py"
        assert title is None
        assert hl_lines == []

    def test_filename_with_dots(self):
        """Filenames with multiple dots work."""
        filename, title, hl_lines = parse_info_string("config.local.py")
        assert filename == "config.local.py"
        assert title is None
        assert hl_lines == []

    def test_filename_with_hyphen(self):
        """Filenames with hyphens work."""
        filename, title, hl_lines = parse_info_string("my-app.config.ts")
        assert filename == "my-app.config.ts"
        assert title is None
        assert hl_lines == []

    def test_highlights_only(self):
        """Just highlights are parsed."""
        filename, title, hl_lines = parse_info_string("{3-4}")
        assert filename is None
        assert title is None
        assert hl_lines == [3, 4]

    def test_title_only(self):
        """Just a title override is parsed."""
        filename, title, hl_lines = parse_info_string('title="Flask App"')
        assert filename is None
        assert title == "Flask App"
        assert hl_lines == []

    def test_filename_and_highlights(self):
        """Filename with highlights works."""
        filename, title, hl_lines = parse_info_string("app.py {3-4}")
        assert filename == "app.py"
        assert title is None
        assert hl_lines == [3, 4]

    def test_title_and_highlights(self):
        """Title with highlights works."""
        filename, title, hl_lines = parse_info_string('title="Flask" {5-7}')
        assert filename is None
        assert title == "Flask"
        assert hl_lines == [5, 6, 7]

    def test_full_combo(self):
        """Filename, title, and highlights together."""
        filename, title, hl_lines = parse_info_string('app.py title="Flask App" {5-7}')
        assert filename == "app.py"
        assert title == "Flask App"
        assert hl_lines == [5, 6, 7]

    def test_filename_underscore(self):
        """Filenames with underscores work."""
        filename, title, hl_lines = parse_info_string("test_utils.py")
        assert filename == "test_utils.py"

    def test_invalid_filename_no_extension(self):
        """Files without extension don't match as filename."""
        # Dockerfile has no extension, so it won't match the filename pattern
        filename, title, hl_lines = parse_info_string("Dockerfile")
        # This won't match the strict filename pattern, falls through
        assert filename is None

    def test_complex_highlights(self):
        """Complex highlight specs are parsed."""
        filename, title, hl_lines = parse_info_string("{1,3-5,7}")
        assert hl_lines == [1, 3, 4, 5, 7]


class TestGetDisplayName:
    """Tests for language display name resolution."""

    def test_javascript(self):
        """JavaScript has proper casing."""
        assert get_display_name("javascript") == "JavaScript"
        assert get_display_name("js") == "JavaScript"

    def test_typescript(self):
        """TypeScript has proper casing."""
        assert get_display_name("typescript") == "TypeScript"
        assert get_display_name("ts") == "TypeScript"

    def test_cpp(self):
        """C++ has proper symbol."""
        assert get_display_name("cpp") == "C++"
        assert get_display_name("cxx") == "C++"

    def test_csharp(self):
        """C# has proper symbol."""
        assert get_display_name("csharp") == "C#"
        assert get_display_name("cs") == "C#"

    def test_golang(self):
        """Go language display name."""
        assert get_display_name("golang") == "Go"

    def test_unknown_fallback(self):
        """Unknown languages get capitalized."""
        assert get_display_name("rust") == "Rust"
        assert get_display_name("python") == "Python"
        assert get_display_name("ruby") == "Ruby"

    def test_case_insensitive(self):
        """Display name lookup is case-insensitive."""
        assert get_display_name("JAVASCRIPT") == "JavaScript"
        assert get_display_name("JavaScript") == "JavaScript"

    def test_empty_string(self):
        """Empty string returns 'Text'."""
        assert get_display_name("") == "Text"


class TestLanguageDisplayNames:
    """Tests for LANGUAGE_DISPLAY_NAMES constant."""

    def test_common_languages_present(self):
        """Common languages with special formatting are present."""
        assert "javascript" in LANGUAGE_DISPLAY_NAMES
        assert "typescript" in LANGUAGE_DISPLAY_NAMES
        assert "cpp" in LANGUAGE_DISPLAY_NAMES
        assert "csharp" in LANGUAGE_DISPLAY_NAMES

    def test_aliases_present(self):
        """Common aliases are present."""
        assert "js" in LANGUAGE_DISPLAY_NAMES
        assert "ts" in LANGUAGE_DISPLAY_NAMES
        assert "cs" in LANGUAGE_DISPLAY_NAMES


# ============================================================================
# v2 Syntax Parsing Tests
# ============================================================================


class TestV2SyntaxParsing:
    """Tests for v2 simplified syntax in parse_directive."""

    def setup_method(self):
        """Set up test fixture."""
        self.directive = CodeTabsDirective()

    def test_simple_two_tabs(self):
        """Simple v2 syntax with two code fences."""
        content = """
```python
print("hello")
```

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
        # v2 derives label from language
        assert result["children"][0]["attrs"]["lang"] == "Python"
        assert result["children"][1]["attrs"]["lang"] == "JavaScript"
        assert result["children"][0]["attrs"]["code_lang"] == "python"
        assert result["children"][1]["attrs"]["code_lang"] == "javascript"

    def test_with_filenames(self):
        """v2 syntax with filenames in info string."""
        content = """
```python main.py
print("hello")
```

```javascript index.js
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

        assert result["children"][0]["attrs"]["filename"] == "main.py"
        assert result["children"][1]["attrs"]["filename"] == "index.js"

    def test_with_title_override(self):
        """v2 syntax with title= overrides tab label."""
        content = """
```javascript title="React"
const [count, setCount] = useState(0);
```

```javascript title="Vue"
const count = ref(0);
```
"""
        result = self.directive.parse_directive(
            title="",
            options=CodeTabsOptions(),
            content=content,
            children=[],
            state=None,
        )

        # title= overrides the language-derived label
        assert result["children"][0]["attrs"]["lang"] == "React"
        assert result["children"][1]["attrs"]["lang"] == "Vue"
        # But code_lang is still javascript for highlighting
        assert result["children"][0]["attrs"]["code_lang"] == "javascript"
        assert result["children"][1]["attrs"]["code_lang"] == "javascript"

    def test_with_highlights(self):
        """v2 syntax with line highlights."""
        content = """
```python {2-3}
def hello():
    print("hello")
    return True
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

    def test_full_featured(self):
        """v2 syntax with filename, title, and highlights."""
        content = """
```python app.py title="Flask App" {5-7}
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello!"
```
"""
        result = self.directive.parse_directive(
            title="",
            options=CodeTabsOptions(),
            content=content,
            children=[],
            state=None,
        )

        tab = result["children"][0]["attrs"]
        assert tab["lang"] == "Flask App"  # title override
        assert tab["filename"] == "app.py"
        assert tab["code_lang"] == "python"
        assert tab["hl_lines"] == [5, 6, 7]

    def test_cpp_display_name(self):
        """C++ gets proper display name in v2 syntax."""
        content = """
```cpp
int main() { return 0; }
```
"""
        result = self.directive.parse_directive(
            title="",
            options=CodeTabsOptions(),
            content=content,
            children=[],
            state=None,
        )

        assert result["children"][0]["attrs"]["lang"] == "C++"


# ============================================================================
# Legacy Syntax Tests (Backward Compatibility)
# ============================================================================


class TestLegacySyntaxParsing:
    """Tests for legacy ### marker syntax (backward compatibility)."""

    def setup_method(self):
        """Set up test fixture."""
        self.directive = CodeTabsDirective()

    def test_parses_simple_tabs(self):
        """Legacy ### markers are still parsed."""
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
        """Code is extracted from legacy fenced blocks."""
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
        assert 'print("hello")' in code

    def test_filename_extraction(self):
        """Filenames are extracted from legacy tab markers."""
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
        """Per-tab highlights work in legacy syntax."""
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


# ============================================================================
# Legacy Helper Tests (parse_tab_marker)
# ============================================================================


class TestParseTabMarker:
    """Tests for legacy tab marker parsing."""

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

    def test_whitespace_handling(self):
        """Whitespace is handled correctly."""
        lang, filename = parse_tab_marker("  Python  ")
        assert lang == "Python"
        assert filename is None


# ============================================================================
# Line Highlight Parsing Tests
# ============================================================================


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


# ============================================================================
# Pygments Rendering Tests
# ============================================================================


class TestRenderCodeWithPygments:
    """Tests for syntax highlighting rendering.

    Note: Uses render_code_with_pygments which is aliased to
    render_code_with_highlighting, which uses the Rosettes backend.
    Rosettes has a simpler output format without table-based line numbers.
    """

    def test_basic_highlighting(self):
        """Code is highlighted with syntax spans."""
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
        """Line number behavior for different code lengths."""
        short_code = "x = 1"
        long_code = "x = 1\ny = 2\nz = 3"

        short_html, _ = render_code_with_pygments(short_code, "python")
        long_html, _ = render_code_with_pygments(long_code, "python")

        # Short code shouldn't have line numbers
        # Note: Rosettes doesn't use table-based line numbers
        assert "linenos" not in short_html

        # Long code should have highlight wrapper
        assert 'class="highlight"' in long_html

    def test_line_numbers_forced(self):
        """Line numbers can be requested (behavior depends on backend)."""
        code = "x = 1"
        html, _ = render_code_with_pygments(code, "python", line_numbers=True)
        # Rosettes wraps in highlight div regardless
        assert 'class="highlight"' in html

    def test_line_numbers_disabled(self):
        """Line numbers can be disabled."""
        code = "x = 1\ny = 2\nz = 3\na = 4"
        html, _ = render_code_with_pygments(code, "python", line_numbers=False)
        # Should not have table structure
        assert "highlighttable" not in html

    def test_line_highlighting(self):
        """Highlighted lines get .hll class."""
        code = "line1\nline2\nline3"
        html, _ = render_code_with_pygments(code, "python", hl_lines=[2])
        # Rosettes uses .hll class for highlighted lines
        assert "hll" in html

    def test_unknown_language_fallback(self):
        """Unknown languages fall back to text."""
        html, plain = render_code_with_pygments("hello", "unknownlang123")
        assert plain == "hello"
        assert 'class="highlight"' in html


# ============================================================================
# Language Icon Tests
# ============================================================================


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
        icon = get_language_icon("bash")
        assert isinstance(icon, str)

    def test_get_language_icon_unknown(self):
        """get_language_icon handles unknown languages gracefully."""
        icon = get_language_icon("unknownlang123")
        assert isinstance(icon, str)


# ============================================================================
# Options Tests
# ============================================================================


class TestCodeTabsOptions:
    """Tests for CodeTabsOptions dataclass."""

    def test_default_values(self):
        """Default options have expected values."""
        opts = CodeTabsOptions()
        assert opts.sync == "language"
        assert opts.linenos is None

    def test_sync_none(self):
        """Sync can be set to 'none' to disable."""
        opts = CodeTabsOptions(sync="none")
        assert opts.sync == "none"

    def test_linenos_explicit(self):
        """Line numbers can be explicitly set."""
        opts = CodeTabsOptions(linenos=True)
        assert opts.linenos is True


# ============================================================================
# Render Tests
# ============================================================================


class TestRenderCodeTabItem:
    """Tests for internal tab item rendering."""

    def test_basic_render(self):
        """Basic tab item renders with all attributes."""
        html = render_code_tab_item(None, lang="Python", code="print('hi')")
        assert 'data-lang="Python"' in html
        assert 'data-code="print(&#x27;hi&#x27;)"' in html

    def test_with_filename(self):
        """Filename is included in output."""
        html = render_code_tab_item(None, lang="Python", code="pass", filename="main.py")
        assert 'data-filename="main.py"' in html

    def test_with_hl_lines(self):
        """Highlight lines are serialized."""
        html = render_code_tab_item(None, lang="Python", code="pass", hl_lines=[1, 3, 5])
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
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            "</div>"
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
            "</div>"
        )
        html = self.directive.render(None, text, sync="none")
        assert "data-sync=" not in html
        assert "data-sync-value=" not in html

    def test_aria_attributes(self):
        """ARIA attributes are present for accessibility."""
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            "</div>"
        )
        html = self.directive.render(None, text, sync="language")
        assert 'role="tab"' in html
        assert "aria-selected=" in html
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
            "</div>"
        )
        html = self.directive.render(None, text, sync="language")
        assert 'class="copy-btn"' in html
        assert "data-copy-target=" in html

    def test_filename_badge(self):
        """Filename badge appears when filename is present."""
        text = (
            '<div class="code-tab-item" '
            'data-lang="Python" '
            'data-code="pass" '
            'data-filename="main.py" '
            'data-hl-lines="" '
            'data-code-lang="python">'
            "</div>"
        )
        html = self.directive.render(None, text, sync="language")
        assert 'class="tab-filename"' in html
        assert "main.py" in html

    def test_backward_compat_legacy_format(self):
        """Legacy tab item format still works."""
        text = '<div class="code-tab-item" data-lang="Python" data-code="pass"></div>'
        html = self.directive.render(None, text, sync="language")
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
            "</div>"
        )
        html = self.directive.render(None, text, sync="language")
        assert 'data-bengal="tabs"' in html

    def test_options_stored_in_attrs(self):
        """Options are stored in attrs for render phase."""
        content = """
### Python
```python
pass
```
"""
        directive = CodeTabsDirective()
        opts = CodeTabsOptions(sync="api-examples")
        result = directive.parse_directive(
            title="",
            options=opts,
            content=content,
            children=[],
            state=None,
        )

        assert result["attrs"]["sync"] == "api-examples"
