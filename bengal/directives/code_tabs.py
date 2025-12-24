"""
Code tabs directive for Mistune.

Provides multi-language code examples with tabbed interface for easy
comparison across programming languages.

Enhanced features (RFC: Enhanced Code Tabs):
- Auto language sync: All code-tabs on a page sync when user picks a language
- Language icons: Automatic icons from language category
- Pygments integration: Line numbers, highlighting, proper syntax coloring
- Copy button: One-click copy per tab
- Filename display: `### Python (main.py)` shows filename badge

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

__all__ = ["CodeTabsDirective", "CodeTabsOptions", "render_code_tab_item"]

logger = get_logger(__name__)

# ============================================================================
# Pre-compiled regex patterns
# ============================================================================

# Tab marker: ### Python or ### Tab: Python or ### Python (main.py)
# Filename pattern only matches: word chars, dots, hyphens ending with .ext
_TAB_MARKER_PATTERN = re.compile(
    r"^### (?:Tab: )?(.+?)(?:\s+\((\w[\w.-]*\.[a-z]+)\))?$",
    re.MULTILINE,
)

# Simple split pattern for backward compatibility
_CODE_TAB_SPLIT_PATTERN = re.compile(r"^### (?:Tab: )?(.+)$", re.MULTILINE)

# Enhanced code block pattern: captures language, info string, and code
# Matches: ```python, ```python {1,3-5}, ```python title="file.py" {1,3}
_CODE_BLOCK_PATTERN = re.compile(
    r"```(\w+)?(?:\s+(.+?))?\n(.*?)```",
    re.DOTALL,
)

# Legacy pattern for backward compatibility
_CODE_BLOCK_EXTRACT_PATTERN = re.compile(r"```\w*\n(.*?)```", re.DOTALL)

# Line highlight extraction from info string: {1,3-5}
_HL_LINES_PATTERN = re.compile(r"\{([0-9,\s-]+)\}")

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

    Attributes:
        sync: Sync key for tab synchronization (default: "language").
              Use "none" to disable sync.
        line_numbers: Force line numbers on/off (None = auto for 3+ lines)
        highlight: Global line highlights for all tabs (e.g., "1,3-5")
        icons: Show language icons in tab labels (default: True)
    """

    sync: str = "language"
    line_numbers: bool | None = None
    highlight: str = ""
    icons: bool = True

    _field_aliases: ClassVar[dict[str, str]] = {
        "linenos": "line_numbers",
        "line-numbers": "line_numbers",
        "hl": "highlight",
        "hl-lines": "highlight",
    }


# ============================================================================
# Tab parsing helpers
# ============================================================================


def parse_tab_marker(marker: str) -> tuple[str, str | None]:
    """
    Parse a tab marker to extract language and optional filename.

    Args:
        marker: Tab marker text (e.g., "Python", "Python (main.py)")

    Returns:
        Tuple of (language, filename or None)

    Examples:
        >>> parse_tab_marker("Python")
        ("Python", None)
        >>> parse_tab_marker("Python (main.py)")
        ("Python", "main.py")
        >>> parse_tab_marker("Python (v3.12+)")  # Not a filename
        ("Python (v3.12+)", None)
    """
    # Strict filename pattern: must end with .ext (lowercase extension)
    # This avoids false positives on version annotations like (v3.12+)
    filename_pattern = re.compile(r"^(.+?)\s+\((\w[\w.-]*\.[a-z]+)\)$")
    match = filename_pattern.match(marker.strip())
    if match:
        return match.group(1).strip(), match.group(2)
    return marker.strip(), None


def parse_code_block_info(info_string: str) -> tuple[str | None, list[int]]:
    """
    Parse code block info string to extract highlights.

    Args:
        info_string: Info string after language (e.g., "{1,3-5}", "title='x' {1,3}")

    Returns:
        Tuple of (title or None, list of highlight line numbers)
    """
    if not info_string:
        return None, []

    hl_lines: list[int] = []

    # Extract highlight lines from {1,3-5} syntax
    hl_match = _HL_LINES_PATTERN.search(info_string)
    if hl_match:
        hl_lines = parse_hl_lines(hl_match.group(1))

    # Title extraction could be added here if needed
    # For now, we don't support title= in code-tabs (use tab marker instead)

    return None, hl_lines


# ============================================================================
# Directive
# ============================================================================


class CodeTabsDirective(BengalDirective):
    """
    Code tabs for multi-language examples.

    Enhanced with Pygments highlighting, auto-sync, and language icons.

    Syntax:
        ````{code-tabs}
        :sync: language
        :line-numbers: true
        :highlight: 3-5

        ### Python (main.py)
        ```python
        def greet(name):
            print(f"Hello, {name}!")
        ```

        ### JavaScript (index.js)
        ```javascript {2-3}
        function greet(name) {
            console.log(`Hello, ${name}!`);
        }
        ```
        ````

    Aliases: code-tabs, code_tabs
    """

    NAMES: ClassVar[list[str]] = ["code-tabs", "code_tabs"]
    TOKEN_TYPE: ClassVar[str] = "code_tabs"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = CodeTabsOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["code-tabs", "code_tabs"]

    def parse_directive(
        self,
        title: str,
        options: CodeTabsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> dict[str, Any]:
        """
        Build code tabs token by parsing tab markers in content.

        Enhanced to extract:
        - Language and filename from tab markers
        - Code block language and info string
        - Per-tab line highlights

        Returns dict instead of DirectiveToken because children
        are custom code_tab_item tokens, not parsed markdown.
        """
        # Parse global options
        global_hl_lines = parse_hl_lines(options.highlight) if options.highlight else []

        # Split by tab markers
        parts = _CODE_TAB_SPLIT_PATTERN.split(content)

        tabs: list[dict[str, Any]] = []
        if len(parts) > 1:
            start_idx = 1 if not parts[0].strip() else 0

            for i in range(start_idx, len(parts), 2):
                if i + 1 < len(parts):
                    raw_marker = parts[i].strip()
                    code_content = parts[i + 1].strip()

                    # Parse tab marker for language and filename
                    lang, filename = parse_tab_marker(raw_marker)

                    # Extract code block with enhanced pattern
                    code_match = _CODE_BLOCK_PATTERN.search(code_content)
                    if code_match:
                        code_lang = code_match.group(1) or lang.lower()
                        info_string = code_match.group(2) or ""
                        code = code_match.group(3).strip()

                        # Parse info string for highlights
                        _, tab_hl_lines = parse_code_block_info(info_string)
                    else:
                        # Fallback to legacy extraction
                        legacy_match = _CODE_BLOCK_EXTRACT_PATTERN.search(code_content)
                        code = (
                            legacy_match.group(1).strip()
                            if legacy_match
                            else code_content
                        )
                        code_lang = lang.lower()
                        tab_hl_lines = []

                    # Merge global and per-tab highlights
                    combined_hl = sorted(set(global_hl_lines + tab_hl_lines))

                    tabs.append(
                        {
                            "type": "code_tab_item",
                            "attrs": {
                                "lang": lang,
                                "code": code,
                                "filename": filename or "",
                                "hl_lines": combined_hl,
                                "code_lang": code_lang,
                            },
                        }
                    )

        # Store options for render phase
        return {
            "type": "code_tabs",
            "children": tabs,
            "attrs": {
                "sync": options.sync,
                "line_numbers": options.line_numbers,
                "icons": options.icons,
            },
        }

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render code tabs to HTML with Pygments highlighting.

        Enhanced output includes:
        - data-sync for auto-sync across tabs
        - Language icons in tab navigation
        - Filename badges
        - Copy button per pane
        - Pygments-highlighted code
        """
        # Extract options from attrs
        sync_key = attrs.get("sync", "language")
        line_numbers = attrs.get("line_numbers")
        show_icons = attrs.get("icons", True)

        # Stable IDs are critical for deterministic builds
        tab_id = f"code-tabs-{hash_str(text or '', truncate=12)}"

        # Try enhanced pattern first, fall back to legacy
        matches = _CODE_TAB_ITEM_PATTERN.findall(text)
        use_legacy = False

        if not matches:
            # Try legacy pattern for backward compatibility
            legacy_matches = _LEGACY_CODE_TAB_ITEM_PATTERN.findall(text)
            if legacy_matches:
                # Convert legacy format to enhanced format
                matches = [
                    (lang, code, "", "", lang.lower())
                    for lang, code in legacy_matches
                ]
                use_legacy = True

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
                filename_html = (
                    f'<span class="tab-filename">{html_lib.escape(filename)}</span>'
                )

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
                plain_code = code

            # Build pane with copy button
            code_id = f"{tab_id}-{i}-code"
            copy_btn_html = (
                f'<div class="code-toolbar">\n'
                f'  <button class="copy-btn" '
                f'data-copy-target="{code_id}" '
                f'aria-label="Copy code to clipboard">\n'
                f'    {render_svg_icon("copy", size=16, css_class="copy-icon")}\n'
                f'    <span class="copy-label visually-hidden">Copy</span>\n'
                f"  </button>\n"
                f"</div>\n"
            )

            # Wrap highlighted code with ID for copy functionality
            # Inject id into the code element for copy targeting
            if "<code" in highlighted_html:
                highlighted_html = highlighted_html.replace(
                    "<code", f'<code id="{code_id}"', 1
                )

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
