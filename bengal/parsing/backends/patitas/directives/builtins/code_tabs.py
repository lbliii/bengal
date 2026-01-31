"""Code tabs directive for multi-language code examples.

Provides tabbed code blocks for easy comparison across programming languages.

Features:
- Tab labels derived from code fence language
- Filename badges in info string
- Title override with title="..."
- Auto sync by language across page
- Pygments syntax highlighting
- Copy button per pane
- Line highlighting

Syntax (v2 simplified):
:::{code-tabs}

    ```python app.py {3-4}
    def hello():
        print("Hello!")
    ```

    ```javascript index.js
    console.log("Hello!");
    ```

:::

Thread Safety:
Stateless handler. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's code-tabs directive exactly for parity.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract
from bengal.utils.primitives.code import parse_hl_lines

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = ["CodeTabsDirective"]


# =============================================================================
# Regex Patterns
# =============================================================================

# Code block pattern: captures language, info string, and code
CODE_BLOCK_PATTERN = re.compile(
    r"```(\w+)?(?:[ \t]+([^\n]*))?\n(.*?)```",
    re.DOTALL,
)

# Info string pattern for v2 simplified syntax
INFO_STRING_PATTERN = re.compile(
    r"^"
    r"(?:(?P<filename>[\w][\w.-]*\.\w+)\s*)?"  # Optional filename (basename.ext)
    r'(?:title="(?P<title>[^"]*)"\s*)?'  # Optional title override
    r"(?:\{(?P<hl>[0-9,\s-]+)\})?"  # Optional highlights
    r"$"
)

# Line highlight extraction
HL_LINES_PATTERN = re.compile(r"\{([0-9,\s-]+)\}")

# Legacy ### marker syntax
LEGACY_TAB_SPLIT_PATTERN = re.compile(r"^### (?:Tab: )?(.+)$", re.MULTILINE)


# =============================================================================
# Language Display Names
# =============================================================================

LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "nodejs": "Node.js",
    "jsx": "JSX",
    "tsx": "TSX",
    "cpp": "C++",
    "cxx": "C++",
    "csharp": "C#",
    "cs": "C#",
    "objectivec": "Objective-C",
    "objc": "Objective-C",
    "fsharp": "F#",
    "haskell": "Haskell",
    "ocaml": "OCaml",
    "graphql": "GraphQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "sqlite": "SQLite",
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "cmake": "CMake",
    "powershell": "PowerShell",
    "zsh": "Zsh",
    "html": "HTML",
    "css": "CSS",
    "scss": "SCSS",
    "sass": "Sass",
    "less": "Less",
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

LANGUAGE_ICONS: dict[str, str] = {
    "bash": "terminal",
    "shell": "terminal",
    "sh": "terminal",
    "zsh": "terminal",
    "powershell": "terminal",
    "console": "terminal",
    "cmd": "terminal",
    "fish": "terminal",
    "sql": "database",
    "mysql": "database",
    "postgresql": "database",
    "sqlite": "database",
    "mongodb": "database",
    "json": "file-code",
    "yaml": "file-code",
    "toml": "file-code",
    "xml": "file-code",
    "ini": "file-code",
    "env": "file-code",
    "_default": "code",
}


def get_display_name(lang: str) -> str:
    """Get human-readable display name for a language."""
    normalized = lang.lower().strip()
    if normalized in LANGUAGE_DISPLAY_NAMES:
        return LANGUAGE_DISPLAY_NAMES[normalized]
    return lang.capitalize() if lang else "Text"


# parse_hl_lines imported from bengal.utils.primitives.code


def parse_info_string(info_string: str) -> tuple[str | None, str | None, list[int]]:
    """Parse code fence info string to extract filename, title, and highlights."""
    if not info_string:
        return None, None, []

    info_string = info_string.strip()
    match = INFO_STRING_PATTERN.match(info_string)

    if match:
        filename = match.group("filename")
        title = match.group("title")
        hl_spec = match.group("hl")
        hl_lines = parse_hl_lines(hl_spec) if hl_spec else []
        return filename, title, hl_lines

    # Fallback: try to extract just highlights
    hl_match = HL_LINES_PATTERN.search(info_string)
    if hl_match:
        return None, None, parse_hl_lines(hl_match.group(1))

    return None, None, []


# =============================================================================
# Code Tab Item (internal representation)
# =============================================================================


@dataclass(frozen=True, slots=True)
class CodeTabItem:
    """Single code tab with its metadata."""

    lang: str  # Display label
    code: str  # Source code
    filename: str  # Optional filename
    hl_lines: tuple[int, ...]  # Lines to highlight
    code_lang: str  # Actual language for highlighting


# =============================================================================
# Code Tabs Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class CodeTabsOptions(DirectiveOptions):
    """Options for code-tabs directive.

    Attributes:
        sync: Sync key for tab synchronization (default: "language")
        linenos: Force line numbers on/off (None = auto for 3+ lines)
        tabs: Parsed tab items (injected by parse method)

    """

    sync: str = "language"
    linenos: bool | None = None
    tabs: tuple[CodeTabItem, ...] | None = None  # Injected by parse()


class CodeTabsDirective:
    """
    Code tabs for multi-language code examples.

    Syntax (v2 simplified):
        :::{code-tabs}

            ```python app.py {3-4}
            def greet(name):
                print(f"Hello, {name}!")
            ```

            ```javascript index.js {2-3}
            function greet(name) {
                console.log(`Hello, ${name}!`);
            }
            ```

        :::

    Legacy syntax (still supported):
        :::{code-tabs}
        ### Python (main.py)
            ```python
            def greet(name):
                print(f"Hello, {name}!")
            ```
        :::

    Options:
        :sync: Sync key for tab synchronization (default: "language")
        :linenos: Force line numbers on/off (default: auto for 3+ lines)

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("code-tabs", "code_tabs")
    token_type: ClassVar[str] = "code_tabs"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[CodeTabsOptions]] = CodeTabsOptions
    preserves_raw_content: ClassVar[bool] = True

    def parse(
        self,
        name: str,
        title: str | None,
        options: CodeTabsOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build code-tabs AST node."""
        # Try v2 syntax first, then legacy
        tabs = self._parse_v2_syntax(content)
        if not tabs:
            tabs = self._parse_legacy_syntax(content)

        # Store tabs in options
        computed_opts = replace(options, tabs=tabs)

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,
            children=(),
            raw_content=content,
        )

    def _parse_v2_syntax(self, content: str) -> tuple[CodeTabItem, ...]:
        """Parse v2 simplified syntax: code fences without ### markers."""
        # Check if this uses legacy ### markers
        if LEGACY_TAB_SPLIT_PATTERN.search(content):
            return ()

        tabs: list[CodeTabItem] = []

        for match in CODE_BLOCK_PATTERN.finditer(content):
            lang = match.group(1) or "text"
            info_string = match.group(2) or ""
            code = match.group(3).strip()

            filename, custom_title, hl_lines = parse_info_string(info_string)
            label = custom_title or get_display_name(lang)

            tabs.append(
                CodeTabItem(
                    lang=label,
                    code=code,
                    filename=filename or "",
                    hl_lines=tuple(hl_lines),
                    code_lang=lang,
                )
            )

        return tuple(tabs)

    def _parse_legacy_syntax(self, content: str) -> tuple[CodeTabItem, ...]:
        """Parse legacy ### marker syntax for backward compatibility."""
        parts = LEGACY_TAB_SPLIT_PATTERN.split(content)
        tabs: list[CodeTabItem] = []

        if len(parts) > 1:
            start_idx = 1 if not parts[0].strip() else 0

            for i in range(start_idx, len(parts), 2):
                if i + 1 < len(parts):
                    raw_marker = parts[i].strip()
                    code_content = parts[i + 1].strip()

                    # Parse tab marker for language and filename
                    lang, filename = self._parse_tab_marker(raw_marker)

                    # Extract code block
                    code_match = CODE_BLOCK_PATTERN.search(code_content)
                    if code_match:
                        code_lang = code_match.group(1) or lang.lower()
                        info_string = code_match.group(2) or ""
                        code = code_match.group(3).strip()
                        _, _, tab_hl_lines = parse_info_string(info_string)
                    else:
                        code = code_content
                        code_lang = lang.lower()
                        tab_hl_lines = []

                    tabs.append(
                        CodeTabItem(
                            lang=lang,
                            code=code,
                            filename=filename or "",
                            hl_lines=tuple(tab_hl_lines),
                            code_lang=code_lang,
                        )
                    )

        return tuple(tabs)

    def _parse_tab_marker(self, marker: str) -> tuple[str, str | None]:
        """Parse a legacy ### tab marker."""
        filename_pattern = re.compile(r"^(.+?)\s+\((\w[\w.-]*\.[a-z]+)\)$")
        match = filename_pattern.match(marker.strip())
        if match:
            return match.group(1).strip(), match.group(2)
        return marker.strip(), None

    def render(
        self,
        node: Directive[CodeTabsOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render code tabs to HTML."""
        opts = node.options
        tabs: tuple[CodeTabItem, ...] = opts.tabs or ()

        if not tabs:
            sb.append(f'<div class="code-tabs" data-bengal="tabs">{rendered_children}</div>')
            return

        sync_key = opts.sync
        linenos = opts.linenos

        # Generate stable ID
        try:
            from bengal.utils.primitives.hashing import hash_str

            content_hash = hash_str(node.raw_content or "", truncate=12)
        except ImportError:
            import hashlib

            content_hash = hashlib.sha256((node.raw_content or "").encode()).hexdigest()[:12]

        tab_id = f"code-tabs-{content_hash}"

        # Build sync attributes
        sync_attr = ""
        if sync_key and sync_key.lower() != "none":
            sync_attr = f' data-sync="{html_escape(sync_key)}"'

        # Build navigation
        sb.append(f'<div class="code-tabs" id="{tab_id}" data-bengal="tabs"{sync_attr}>\n')
        sb.append('  <ul class="tab-nav" role="tablist">\n')

        for i, tab in enumerate(tabs):
            active_class = ' class="active"' if i == 0 else ""
            aria_selected = "true" if i == 0 else "false"

            sync_value = tab.lang.lower().replace(" ", "-")
            sync_value_attr = (
                f' data-sync-value="{html_escape(sync_value)}"'
                if sync_key and sync_key.lower() != "none"
                else ""
            )

            # Build tab label with optional icon
            icon_html = self._get_language_icon(tab.code_lang)
            if icon_html:
                icon_html = f'<span class="tab-icon" aria-hidden="true">{icon_html}</span>'

            filename_html = ""
            if tab.filename:
                filename_html = f'<span class="tab-filename">{html_escape(tab.filename)}</span>'

            sb.append(f'    <li{active_class} role="presentation">\n')
            sb.append(
                f'      <a href="#" role="tab" aria-selected="{aria_selected}" '
                f'aria-controls="{tab_id}-{i}" '
                f'data-tab-target="{tab_id}-{i}"{sync_value_attr}>\n'
            )
            sb.append(f"        {icon_html}")
            sb.append(f'<span class="tab-label">{html_escape(tab.lang)}</span>')
            sb.append(f"{filename_html}\n")
            sb.append("      </a>\n")
            sb.append("    </li>\n")

        sb.append("  </ul>\n")

        # Build content panes
        sb.append('  <div class="tab-content">\n')

        for i, tab in enumerate(tabs):
            active = " active" if i == 0 else ""
            code_id = f"{tab_id}-{i}-code"

            # Render code with highlighting
            highlighted_html = self._render_code(
                tab.code, tab.code_lang, list(tab.hl_lines), linenos
            )

            # Build copy button
            copy_icon = self._get_copy_icon()
            copy_btn_html = (
                f'<div class="code-toolbar">\n'
                f'  <button class="copy-btn" '
                f'data-copy-target="{code_id}" '
                f'aria-label="Copy code to clipboard">\n'
                f"    {copy_icon}\n"
                f'    <span class="copy-label visually-hidden">Copy</span>\n'
                f"  </button>\n"
                f"</div>\n"
            )

            # Inject ID into code element
            if "<code" in highlighted_html:
                highlighted_html = highlighted_html.replace("<code", f'<code id="{code_id}"', 1)

            sb.append(
                f'    <div id="{tab_id}-{i}" class="tab-pane{active}" '
                f'role="tabpanel" aria-labelledby="{tab_id}-{i}-tab">\n'
            )
            sb.append(f"      {copy_btn_html}")
            sb.append(f"      {highlighted_html}\n")
            sb.append("    </div>\n")

        sb.append("  </div>\n</div>\n")

    def _render_code(
        self,
        code: str,
        language: str,
        hl_lines: list[int],
        linenos: bool | None,
    ) -> str:
        """Render code with syntax highlighting."""
        try:
            from bengal.rendering.highlighting import highlight as highlight_code

            line_count = code.count("\n") + 1
            show_linenos = linenos if linenos is not None else (line_count >= 3)
            return highlight_code(
                code=code,
                language=language,
                hl_lines=hl_lines or None,
                show_linenos=show_linenos,
            )
        except ImportError:
            # Fallback: simple code block
            lang_class = f' class="language-{html_escape(language)}"' if language else ""
            return f"<pre><code{lang_class}>{html_escape(code)}</code></pre>"

    def _get_language_icon(self, lang: str, size: int = 16) -> str:
        """Get icon HTML for a language."""
        try:
            from bengal.directives._icons import icon_exists, render_svg_icon

            normalized = lang.lower().strip()
            icon_name = LANGUAGE_ICONS.get(normalized, LANGUAGE_ICONS["_default"])
            if not icon_exists(icon_name):
                return ""
            return render_svg_icon(icon_name, size=size, css_class="tab-icon")
        except ImportError:
            return ""

    def _get_copy_icon(self, size: int = 16) -> str:
        """Get copy icon HTML."""
        try:
            from bengal.directives._icons import render_svg_icon

            return render_svg_icon("copy", size=size, css_class="copy-icon")
        except ImportError:
            return "📋"
