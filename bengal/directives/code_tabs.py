"""
Code tabs directive for Mistune.

Provides multi-language code examples with tabbed interface for easy
comparison across programming languages.

Simplified syntax (RFC: Simplified Code Tabs Syntax v2):
- Tab labels derived from code fence language (no ### markers needed)
- Filename in info string: ```python app.py {3-4}
- Title override: ```python title="Flask" for custom labels
- Auto sync by language across page
- Language icons, Pygments highlighting, copy button

Syntax:
    :::{code-tabs}

    ```python app.py {3-4}
    def hello():
        print("Hello!")
    ```

    ```javascript index.js
    console.log("Hello!");
    ```

    :::

"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from pygments import highlight
from pygments.formatters.html import HtmlFormatter

from bengal.directives._icons import icon_exists, render_svg_icon
from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.rendering.pygments_cache import get_lexer_cached
from bengal.utils.hashing import hash_str
from bengal.utils.logger import get_logger

__all__ = [
    "CodeTabsDirective",
    "CodeTabsOptions",
    "render_code_tab_item",
    "get_display_name",
    "parse_info_string",
    "LANGUAGE_DISPLAY_NAMES",
]

logger = get_logger(__name__)

# ============================================================================
# Pre-compiled regex patterns
# ============================================================================

# Code block pattern: captures language, info string, and code
# Matches: ```python, ```python app.py {1,3-5}, ```python title="Flask" {1,3}
_CODE_BLOCK_PATTERN = re.compile(
    r"```(\w+)?(?:[ \t]+([^\n]*))?\n(.*?)```",
    re.DOTALL,
)

# Info string pattern for v2 simplified syntax
# Strict ordering: filename → title → highlights
# Examples:
#   ""                           → filename=None, title=None, hl=None
#   "app.py"                     → filename="app.py", title=None, hl=None
#   "{3-4}"                      → filename=None, title=None, hl="3-4"
#   "app.py {3-4}"               → filename="app.py", title=None, hl="3-4"
#   'title="Flask"'              → filename=None, title="Flask", hl=None
#   'app.py title="Flask" {5-7}' → filename="app.py", title="Flask", hl="5-7"
_INFO_STRING_PATTERN = re.compile(
    r"^"
    r"(?:(?P<filename>[\w][\w.-]*\.\w+)\s*)?"  # Optional filename (basename.ext)
    r'(?:title="(?P<title>[^"]*)"\s*)?'  # Optional title override
    r"(?:\{(?P<hl>[0-9,\s-]+)\})?"  # Optional highlights
    r"$"
)

# Line highlight extraction from info string: {1,3-5}
_HL_LINES_PATTERN = re.compile(r"\{([0-9,\s-]+)\}")

# Legacy patterns for backward compatibility with ### marker syntax
_LEGACY_TAB_SPLIT_PATTERN = re.compile(r"^### (?:Tab: )?(.+)$", re.MULTILINE)
_LEGACY_CODE_BLOCK_PATTERN = re.compile(r"```\w*\n(.*?)```", re.DOTALL)

# Internal marker pattern for render phase
_CODE_TAB_ITEM_PATTERN = re.compile(
    r'<div class="code-tab-item" '
    r'data-lang="(.*?)" '
    r'data-code="(.*?)" '
    r'data-filename="(.*?)" '
    r'data-hl-lines="(.*?)" '
    r'data-code-lang="(.*?)"'
    r"></div>",
    re.DOTALL,
)

# Legacy pattern for backward compatibility
_LEGACY_CODE_TAB_ITEM_PATTERN = re.compile(
    r'<div class="code-tab-item" data-lang="(.*?)" data-code="(.*?)"></div>',
    re.DOTALL,
)

# ============================================================================
# Language display names (proper capitalization/formatting)
# ============================================================================

# Map language identifiers to human-readable display names
# Used for tab labels when no title= override is provided
LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    # JavaScript ecosystem
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "nodejs": "Node.js",
    "jsx": "JSX",
    "tsx": "TSX",
    # C family
    "cpp": "C++",
    "cxx": "C++",
    "csharp": "C#",
    "cs": "C#",
    "objectivec": "Objective-C",
    "objc": "Objective-C",
    # Functional
    "fsharp": "F#",
    "haskell": "Haskell",
    "ocaml": "OCaml",
    # Query languages
    "graphql": "GraphQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "sqlite": "SQLite",
    # Config/Data
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "cmake": "CMake",
    # Shell
    "powershell": "PowerShell",
    "zsh": "Zsh",
    # Web
    "html": "HTML",
    "css": "CSS",
    "scss": "SCSS",
    "sass": "Sass",
    "less": "Less",
    # Other
    "golang": "Go",
    "yaml": "YAML",
    "yml": "YAML",
    "json": "JSON",
    "toml": "TOML",
    "ini": "INI",
    "xml": "XML",
    "php": "PHP",
    "sql": "SQL",
}

# ============================================================================
# Language icon mapping
# ============================================================================

# Map languages to existing icons in Bengal's Phosphor icon library
# Only use icons verified to exist
LANGUAGE_ICONS: dict[str, str] = {
    # Shell/Terminal
    "bash": "terminal",
    "shell": "terminal",
    "sh": "terminal",
    "zsh": "terminal",
    "powershell": "terminal",
    "console": "terminal",
    "cmd": "terminal",
    "fish": "terminal",
    # Data/Database
    "sql": "database",
    "mysql": "database",
    "postgresql": "database",
    "sqlite": "database",
    "mongodb": "database",
    # Config/Data formats
    "json": "file-code",
    "yaml": "file-code",
    "toml": "file-code",
    "xml": "file-code",
    "ini": "file-code",
    "env": "file-code",
    # Generic code fallback
    "_default": "code",
}


def get_language_icon(lang: str, size: int = 16) -> str:
    """
    Get icon HTML for a programming language.

    Returns empty string if no icon available (graceful degradation).

    Args:
        lang: Language name (e.g., "python", "bash")
        size: Icon size in pixels

    Returns:
        Inline SVG HTML string, or empty string if not found
    """
    normalized = lang.lower().strip()
    icon_name = LANGUAGE_ICONS.get(normalized, LANGUAGE_ICONS["_default"])

    # Verify icon exists before rendering
    if not icon_exists(icon_name):
        return ""

    return render_svg_icon(icon_name, size=size, css_class="tab-icon")


def get_display_name(lang: str) -> str:
    """
    Get human-readable display name for a programming language.

    Uses LANGUAGE_DISPLAY_NAMES for special cases (JavaScript, C++, etc.),
    falls back to simple capitalization for unknown languages.

    Args:
        lang: Language identifier (e.g., "python", "javascript", "cpp")

    Returns:
        Display name (e.g., "Python", "JavaScript", "C++")

    Examples:
        >>> get_display_name("javascript")
        "JavaScript"
        >>> get_display_name("cpp")
        "C++"
        >>> get_display_name("rust")
        "Rust"
    """
    normalized = lang.lower().strip()
    if normalized in LANGUAGE_DISPLAY_NAMES:
        return LANGUAGE_DISPLAY_NAMES[normalized]
    # Fallback: capitalize first letter
    return lang.capitalize() if lang else "Text"


# ============================================================================
# Line highlight parsing (reused from highlighting.py)
# ============================================================================


def parse_hl_lines(hl_spec: str) -> list[int]:
    """
    Parse line highlight specification into list of line numbers.

    Supports:
    - Single line: "5" -> [5]
    - Multiple lines: "1,3,5" -> [1, 3, 5]
    - Ranges: "1-3" -> [1, 2, 3]
    - Mixed: "1,3-5,7" -> [1, 3, 4, 5, 7]

    Args:
        hl_spec: Line specification string (e.g., "1,3-5,7")

    Returns:
        Sorted list of unique line numbers
    """
    lines: set[int] = set()
    for part in hl_spec.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                lines.update(range(int(start), int(end) + 1))
            except ValueError:
                continue
        else:
            try:
                lines.add(int(part))
            except ValueError:
                continue
    return sorted(lines)


# ============================================================================
# Pygments rendering
# ============================================================================


def render_code_with_pygments(
    code: str,
    language: str,
    hl_lines: list[int] | None = None,
    line_numbers: bool | None = None,
) -> tuple[str, str]:
    """
    Render code with Pygments highlighting.

    Args:
        code: Source code to highlight
        language: Programming language
        hl_lines: Optional list of line numbers to highlight
        line_numbers: Force line numbers on/off (None = auto for 3+ lines)

    Returns:
        Tuple of (highlighted_html, plain_code_for_copy)
    """
    # Get cached lexer (fast path for known languages)
    try:
        lexer = get_lexer_cached(language=language)
    except Exception:
        lexer = get_lexer_cached(language="text")

    line_count = code.count("\n") + 1

    # Auto line numbers for 3+ lines unless explicitly disabled
    show_linenos = line_numbers if line_numbers is not None else (line_count >= 3)

    formatter = HtmlFormatter(
        cssclass="highlight",
        wrapcode=True,
        noclasses=False,
        linenos="table" if show_linenos else False,
        linenostart=1,
        hl_lines=hl_lines or [],
    )

    highlighted = highlight(code, lexer, formatter)

    # Fix Pygments .hll newline issue (same as highlighting.py)
    if hl_lines:
        highlighted = highlighted.replace("\n</span>", "</span>")

    return highlighted, code


# ============================================================================
# Options
# ============================================================================


@dataclass
class CodeTabsOptions(DirectiveOptions):
    """
    Options for code-tabs directive.

    v2 simplified syntax requires minimal options - most behavior is automatic:
    - Sync: enabled by default (syncs by language across page)
    - Line numbers: auto for 3+ lines
    - Icons: always shown

    Attributes:
        sync: Sync key for tab synchronization (default: "language").
              Use "none" to disable sync for this specific block.
        linenos: Force line numbers on/off (None = auto for 3+ lines)
    """

    sync: str = "language"
    linenos: bool | None = None

    _field_aliases: ClassVar[dict[str, str]] = {
        "line-numbers": "linenos",
        "line_numbers": "linenos",
    }


# ============================================================================
# Info string parsing (v2 simplified syntax)
# ============================================================================


def parse_info_string(info_string: str) -> tuple[str | None, str | None, list[int]]:
    """
    Parse code fence info string to extract filename, title, and highlights.

    Strict ordering: filename → title → highlights

    Args:
        info_string: Info string after language
            (e.g., "app.py", "{3-4}", 'app.py title="Flask" {5-7}')

    Returns:
        Tuple of (filename or None, title or None, list of highlight line numbers)

    Examples:
        >>> parse_info_string("")
        (None, None, [])
        >>> parse_info_string("app.py")
        ("app.py", None, [])
        >>> parse_info_string("{3-4}")
        (None, None, [3, 4])
        >>> parse_info_string("app.py {3-4}")
        ("app.py", None, [3, 4])
        >>> parse_info_string('title="Flask"')
        (None, "Flask", [])
        >>> parse_info_string('app.py title="Flask" {5-7}')
        ("app.py", "Flask", [5, 6, 7])
    """
    if not info_string:
        return None, None, []

    info_string = info_string.strip()
    match = _INFO_STRING_PATTERN.match(info_string)

    if match:
        filename = match.group("filename")
        title = match.group("title")
        hl_spec = match.group("hl")
        hl_lines = parse_hl_lines(hl_spec) if hl_spec else []
        return filename, title, hl_lines

    # Fallback: try to extract just highlights if pattern doesn't match
    hl_match = _HL_LINES_PATTERN.search(info_string)
    if hl_match:
        return None, None, parse_hl_lines(hl_match.group(1))

    # Pattern didn't match - log warning and continue gracefully
    logger.debug(
        "code_tabs_info_parse_fallback",
        info=info_string,
        hint='Expected: [filename] [title="..."] [{lines}]',
    )
    return None, None, []


# Legacy helper for backward compatibility
def parse_tab_marker(marker: str) -> tuple[str, str | None]:
    """
    Parse a legacy ### tab marker to extract language and optional filename.

    DEPRECATED: Use parse_info_string() for v2 syntax.

    Args:
        marker: Tab marker text (e.g., "Python", "Python (main.py)")

    Returns:
        Tuple of (language, filename or None)
    """
    # Strict filename pattern: must end with .ext (lowercase extension)
    filename_pattern = re.compile(r"^(.+?)\s+\((\w[\w.-]*\.[a-z]+)\)$")
    match = filename_pattern.match(marker.strip())
    if match:
        return match.group(1).strip(), match.group(2)
    return marker.strip(), None


# ============================================================================
# Directive
# ============================================================================


class CodeTabsDirective(BengalDirective):
    """
    Code tabs for multi-language examples.

    Enhanced with Pygments highlighting, auto-sync, and language icons.

    v2 Simplified Syntax (preferred):
        ````{code-tabs}

        ```python app.py {3-4}
        def greet(name):
            print(f"Hello, {name}!")
        ```

        ```javascript index.js {2-3}
        function greet(name) {
            console.log(`Hello, ${name}!`);
        }
        ```
        ````

    Legacy Syntax (still supported):
        ````{code-tabs}
        ### Python (main.py)
        ```python
        def greet(name):
            print(f"Hello, {name}!")
        ```
        ````

    Aliases: code-tabs, code_tabs
    """

    NAMES: ClassVar[list[str]] = ["code-tabs", "code_tabs"]
    TOKEN_TYPE: ClassVar[str] = "code_tabs"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = CodeTabsOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["code-tabs", "code_tabs"]

    def __call__(self, directive: Any, md: Any) -> None:
        """Register directive with Mistune, including code_tab_item renderer."""
        # Call parent registration
        super().__call__(directive, md)

        # Also register the internal code_tab_item renderer
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("code_tab_item", render_code_tab_item)

    def parse_directive(
        self,
        title: str,
        options: CodeTabsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> dict[str, Any]:
        """
        Build code tabs token by parsing code fences in content.

        v2 syntax: Directly parses code fences, deriving tab labels from language.
        Legacy syntax: Falls back to ### marker parsing if no direct fences found.

        Returns dict instead of DirectiveToken because children
        are custom code_tab_item tokens, not parsed markdown.
        """
        # Try v2 syntax first: direct code fence parsing
        tabs = self._parse_v2_syntax(content)

        # Fall back to legacy ### marker syntax if no tabs found
        if not tabs:
            tabs = self._parse_legacy_syntax(content)

        # Store options for render phase
        return {
            "type": "code_tabs",
            "children": tabs,
            "attrs": {
                "sync": options.sync,
                "line_numbers": options.linenos,
            },
        }

    def _parse_v2_syntax(self, content: str) -> list[dict[str, Any]]:
        """
        Parse v2 simplified syntax: code fences without ### markers.

        Tab labels are derived from code fence language.
        Filename, title, and highlights are extracted from info string.

        Args:
            content: Directive content

        Returns:
            List of code_tab_item tokens, or empty list if not v2 syntax
        """
        # Check if this uses legacy ### markers
        if _LEGACY_TAB_SPLIT_PATTERN.search(content):
            return []  # Fall back to legacy parsing

        tabs: list[dict[str, Any]] = []

        for match in _CODE_BLOCK_PATTERN.finditer(content):
            lang = match.group(1) or "text"
            info_string = match.group(2) or ""
            code = match.group(3).strip()

            # Parse info string for filename, title, highlights
            filename, custom_title, hl_lines = parse_info_string(info_string)

            # Derive tab label: title override > display name
            label = custom_title or get_display_name(lang)

            tabs.append(
                {
                    "type": "code_tab_item",
                    "attrs": {
                        "lang": label,  # Display label for tab
                        "code": code,
                        "filename": filename or "",
                        "hl_lines": hl_lines,
                        "code_lang": lang,  # Actual language for highlighting
                    },
                }
            )

        return tabs

    def _parse_legacy_syntax(self, content: str) -> list[dict[str, Any]]:
        """
        Parse legacy ### marker syntax for backward compatibility.

        Args:
            content: Directive content with ### Language markers

        Returns:
            List of code_tab_item tokens
        """
        parts = _LEGACY_TAB_SPLIT_PATTERN.split(content)
        tabs: list[dict[str, Any]] = []

        if len(parts) > 1:
            start_idx = 1 if not parts[0].strip() else 0

            for i in range(start_idx, len(parts), 2):
                if i + 1 < len(parts):
                    raw_marker = parts[i].strip()
                    code_content = parts[i + 1].strip()

                    # Parse tab marker for language and filename
                    lang, filename = parse_tab_marker(raw_marker)

                    # Extract code block
                    code_match = _CODE_BLOCK_PATTERN.search(code_content)
                    if code_match:
                        code_lang = code_match.group(1) or lang.lower()
                        info_string = code_match.group(2) or ""
                        code = code_match.group(3).strip()

                        # Parse info string for highlights only
                        _, _, tab_hl_lines = parse_info_string(info_string)
                    else:
                        # Fallback to simple extraction
                        legacy_match = _LEGACY_CODE_BLOCK_PATTERN.search(code_content)
                        code = legacy_match.group(1).strip() if legacy_match else code_content
                        code_lang = lang.lower()
                        tab_hl_lines = []

                    tabs.append(
                        {
                            "type": "code_tab_item",
                            "attrs": {
                                "lang": lang,
                                "code": code,
                                "filename": filename or "",
                                "hl_lines": tab_hl_lines,
                                "code_lang": code_lang,
                            },
                        }
                    )

        return tabs

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render code tabs to HTML with Pygments highlighting.

        Enhanced output includes:
        - data-sync for auto-sync across tabs
        - Language icons in tab navigation (always enabled)
        - Filename badges
        - Copy button per pane
        - Pygments-highlighted code
        """
        # Extract options from attrs
        sync_key = attrs.get("sync", "language")
        line_numbers = attrs.get("line_numbers")
        # Icons are always shown in v2 (removed from options)
        show_icons = True

        # Stable IDs are critical for deterministic builds
        tab_id = f"code-tabs-{hash_str(text or '', truncate=12)}"

        # Try enhanced pattern first, fall back to legacy
        matches = _CODE_TAB_ITEM_PATTERN.findall(text)

        if not matches:
            # Try legacy pattern for backward compatibility
            legacy_matches = _LEGACY_CODE_TAB_ITEM_PATTERN.findall(text)
            if legacy_matches:
                # Convert legacy format to enhanced format
                matches = [(lang, code, "", "", lang.lower()) for lang, code in legacy_matches]

        if not matches:
            return f'<div class="code-tabs" data-bengal="tabs">{text}</div>'

        # Build sync attributes
        sync_attr = ""
        if sync_key and sync_key.lower() != "none":
            sync_attr = f' data-sync="{html_lib.escape(sync_key)}"'

        # Build navigation with icons and filename badges
        nav_html = (
            f'<div class="code-tabs" id="{tab_id}" data-bengal="tabs"{sync_attr}>\n'
            f'  <ul class="tab-nav" role="tablist">\n'
        )

        for i, match in enumerate(matches):
            lang, _, filename, _, code_lang = match
            active_class = ' class="active"' if i == 0 else ""
            aria_selected = "true" if i == 0 else "false"

            # Normalize sync value (lowercase for matching)
            sync_value = lang.lower().replace(" ", "-")
            sync_value_attr = (
                f' data-sync-value="{html_lib.escape(sync_value)}"'
                if sync_key and sync_key.lower() != "none"
                else ""
            )

            # Build tab label with optional icon and filename
            icon_html = ""
            if show_icons:
                icon_html = get_language_icon(code_lang or lang, size=16)
                if icon_html:
                    icon_html = f'<span class="tab-icon" aria-hidden="true">{icon_html}</span>'

            filename_html = ""
            if filename:
                filename_html = f'<span class="tab-filename">{html_lib.escape(filename)}</span>'

            nav_html += (
                f'    <li{active_class} role="presentation">\n'
                f'      <a href="#" role="tab" aria-selected="{aria_selected}" '
                f'aria-controls="{tab_id}-{i}" '
                f'data-tab-target="{tab_id}-{i}"{sync_value_attr}>\n'
                f"        {icon_html}"
                f'<span class="tab-label">{html_lib.escape(lang)}</span>'
                f"{filename_html}\n"
                f"      </a>\n"
                f"    </li>\n"
            )

        nav_html += "  </ul>\n"

        # Build content panes with Pygments highlighting and copy button
        content_html = '  <div class="tab-content">\n'

        for i, match in enumerate(matches):
            lang, code_escaped, filename, hl_lines_str, code_lang = match
            active = " active" if i == 0 else ""

            # Unescape code for processing
            code = html_lib.unescape(code_escaped)

            # Parse highlight lines
            hl_lines = parse_hl_lines(hl_lines_str) if hl_lines_str else []

            # Render with Pygments
            try:
                highlighted_html, plain_code = render_code_with_pygments(
                    code,
                    code_lang or lang.lower(),
                    hl_lines=hl_lines,
                    line_numbers=line_numbers,
                )
            except Exception as e:
                logger.warning(
                    "code_tabs_highlight_failed",
                    language=code_lang or lang,
                    error=str(e),
                )
                # Fallback to escaped code
                highlighted_html = (
                    f'<pre><code class="language-{html_lib.escape(code_lang or lang)}">'
                    f"{html_lib.escape(code)}</code></pre>"
                )

            # Build pane with copy button
            code_id = f"{tab_id}-{i}-code"
            copy_btn_html = (
                f'<div class="code-toolbar">\n'
                f'  <button class="copy-btn" '
                f'data-copy-target="{code_id}" '
                f'aria-label="Copy code to clipboard">\n'
                f"    {render_svg_icon('copy', size=16, css_class='copy-icon')}\n"
                f'    <span class="copy-label visually-hidden">Copy</span>\n'
                f"  </button>\n"
                f"</div>\n"
            )

            # Wrap highlighted code with ID for copy functionality
            # Inject id into the code element for copy targeting
            if "<code" in highlighted_html:
                highlighted_html = highlighted_html.replace("<code", f'<code id="{code_id}"', 1)

            content_html += (
                f'    <div id="{tab_id}-{i}" class="tab-pane{active}" '
                f'role="tabpanel" aria-labelledby="{tab_id}-{i}-tab">\n'
                f"      {copy_btn_html}"
                f"      {highlighted_html}\n"
                f"    </div>\n"
            )

        content_html += "  </div>\n</div>\n"

        return nav_html + content_html


# ============================================================================
# Backward compatibility render functions
# ============================================================================


def render_code_tab_item(renderer: Any, **attrs: Any) -> str:
    """
    Render code tab item marker (used internally).

    Enhanced to include filename, highlight lines, and code language.
    """
    lang = attrs.get("lang", "text")
    code = attrs.get("code", "")
    filename = attrs.get("filename", "")
    hl_lines = attrs.get("hl_lines", [])
    code_lang = attrs.get("code_lang", lang.lower())

    code_escaped = html_lib.escape(code)
    hl_lines_str = ",".join(str(n) for n in hl_lines) if hl_lines else ""

    return (
        f'<div class="code-tab-item" '
        f'data-lang="{html_lib.escape(lang)}" '
        f'data-code="{code_escaped}" '
        f'data-filename="{html_lib.escape(filename)}" '
        f'data-hl-lines="{hl_lines_str}" '
        f'data-code-lang="{html_lib.escape(code_lang)}"'
        f"></div>"
    )
