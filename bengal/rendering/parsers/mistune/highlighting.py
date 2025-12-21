"""
Syntax highlighting plugin for Mistune parser.

Provides Pygments-based syntax highlighting for code blocks with support for:
- Language detection
- Line highlighting ({1,3-5} syntax)
- Code block titles (title="filename.py")
- Line numbers (for blocks with 3+ lines)
- Special handling for Mermaid diagrams
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bengal.rendering.parsers.mistune.patterns import (
    CODE_INFO_PATTERN,
    HL_LINES_PATTERN,
)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


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
            # Range: "3-5" -> 3, 4, 5
            try:
                start, end = part.split("-", 1)
                lines.update(range(int(start), int(end) + 1))
            except ValueError:
                continue
        else:
            # Single line
            try:
                lines.add(int(part))
            except ValueError:
                continue
    return sorted(lines)


def create_syntax_highlighting_plugin() -> Callable[[Any], None]:
    """
    Create a Mistune plugin that adds Pygments syntax highlighting to code blocks.

    Returns:
        Plugin function that modifies the renderer to add syntax highlighting
    """
    from pygments import highlight
    from pygments.formatters.html import HtmlFormatter

    from bengal.rendering.pygments_cache import get_lexer_cached

    def plugin_syntax_highlighting(md: Any) -> None:
        """Plugin function to add syntax highlighting to Mistune renderer."""
        # Get the original block_code renderer
        original_block_code = md.renderer.block_code

        def highlighted_block_code(code: str, info: str | None = None) -> str:
            """Render code block with syntax highlighting."""
            # If no language specified, use original renderer
            if not info:
                return original_block_code(code, info)

            # Skip directive blocks (e.g., {info}, {rubric}, {note}, etc.)
            # These should be handled by the FencedDirective plugin
            info_stripped = info.strip()
            if info_stripped.startswith("{") and "}" in info_stripped:
                return original_block_code(code, info)

            # Parse language, optional title, and line highlights
            # Supports: python, python title="file.py", python {1,3}, python title="file.py" {1,3}
            language = info_stripped
            title: str | None = None
            hl_lines: list[int] = []

            # Try new pattern first (supports title)
            info_match = CODE_INFO_PATTERN.match(info_stripped)
            if info_match:
                language = info_match.group("lang")
                title = info_match.group("title")  # None if not present
                hl_spec = info_match.group("hl")
                if hl_spec:
                    hl_lines = parse_hl_lines(hl_spec)
            else:
                # Fall back to old pattern (line highlights only, no title)
                hl_match = HL_LINES_PATTERN.match(info_stripped)
                if hl_match:
                    language = hl_match.group(1)
                    hl_lines = parse_hl_lines(hl_match.group(2))

            # Special handling: client-side rendered languages (e.g., Mermaid)
            lang_lower = language.lower()
            if lang_lower == "mermaid":
                # Escape HTML so browsers don't interpret it; Mermaid will read textContent
                escaped_code = (
                    code.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                return f'<div class="mermaid">{escaped_code}</div>\n'

            try:
                # Get cached lexer for the language
                lexer = get_lexer_cached(language=language)

                # Count lines to decide on line numbers
                line_count = code.count("\n") + 1

                # Format with Pygments using 'highlight' CSS class (matches python-markdown)
                # Add line numbers for code blocks with 3+ lines (Supabase-style)
                formatter = HtmlFormatter(
                    cssclass="highlight",
                    wrapcode=True,
                    noclasses=False,  # Use CSS classes instead of inline styles
                    linenos="table" if line_count >= 3 else False,
                    linenostart=1,
                    hl_lines=hl_lines,  # Line highlighting (empty list is valid)
                )

                # Highlight the code
                highlighted = highlight(code, lexer, formatter)

                # Fix Pygments .hll output: remove newlines from inside the span
                # Pygments outputs: <span class="hll">content\n</span>
                # We need: <span class="hll">content</span>
                # Since .hll uses display:block (for full-width background), the
                # block element already creates a line break. Keeping the newline
                # after </span> would create double spacing in <pre> elements.
                # The \n</span> pattern only appears inside .hll spans (token spans
                # don't have newlines inside them), so we can safely replace all.
                if hl_lines:
                    highlighted = highlighted.replace("\n</span>", "</span>")

                # Wrap with title if present
                if title:
                    import html as html_mod

                    safe_title = html_mod.escape(title)
                    return (
                        f'<div class="code-block-titled">\n'
                        f'<div class="code-block-title">{safe_title}</div>\n'
                        f"{highlighted}"
                        f"</div>\n"
                    )

                return highlighted

            except Exception as e:
                # If highlighting fails, return plain code block
                logger.warning("pygments_highlight_failed", language=language, error=str(e))
                # Escape HTML and return plain code block
                escaped_code = (
                    code.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                plain_block = (
                    f'<pre><code class="language-{language}">{escaped_code}</code></pre>\n'
                )

                # Wrap with title if present
                if title:
                    import html as html_mod

                    safe_title = html_mod.escape(title)
                    return (
                        f'<div class="code-block-titled">\n'
                        f'<div class="code-block-title">{safe_title}</div>\n'
                        f"{plain_block}"
                        f"</div>\n"
                    )

                return plain_block

        # Replace the block_code method
        md.renderer.block_code = highlighted_block_code

    return plugin_syntax_highlighting
