"""
Syntax highlighting plugin for Mistune parser.

Provides syntax highlighting for code blocks with support for:
- Language detection
- Line highlighting ({1,3-5} syntax)
- Code block titles (title="filename.py")
- Line numbers (for blocks with 3+ lines)
- Special handling for Mermaid diagrams
- Example flag ({example}) to suppress unknown language warnings
- Pluggable backends via bengal.rendering.highlighting

Backend Selection:
    By default, uses the Pygments backend. To use tree-sitter:

    >>> from bengal.rendering.highlighting import get_highlighter
    >>> backend = get_highlighter("tree-sitter")

    Or configure in bengal.yaml:

    .. code-block:: yaml

        rendering:
          syntax_highlighting:
            backend: tree-sitter
"""

from __future__ import annotations

import html as html_mod
import re
from collections.abc import Callable
from typing import Any

from bengal.rendering.highlighting import highlight
from bengal.rendering.parsers.mistune.patterns import (
    CODE_INFO_PATTERN,
    HL_LINES_PATTERN,
)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Pattern to detect {example} flag in info string
# Can appear anywhere: "python {example}", "jsx {example} {1,3}", etc.
EXAMPLE_FLAG_PATTERN = re.compile(r"\{example\}", re.IGNORECASE)


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
    Create a Mistune plugin that adds syntax highlighting to code blocks.

    Uses the highlighting backend registry (bengal.rendering.highlighting)
    which defaults to Pygments but can be configured to use tree-sitter
    or other backends.

    Returns:
        Plugin function that modifies the renderer to add syntax highlighting
    """

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

            # Check for {example} flag - suppresses warnings for intentional foreign syntax
            is_example = bool(EXAMPLE_FLAG_PATTERN.search(info_stripped))
            if is_example:
                # Remove the {example} flag from the info string for further parsing
                info_stripped = EXAMPLE_FLAG_PATTERN.sub("", info_stripped).strip()

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
                # Count lines to decide on line numbers
                line_count = code.count("\n") + 1
                show_linenos = line_count >= 3

                # Highlight using the configured backend (via registry)
                # The highlight() function handles backend selection and fallback
                highlighted = highlight(
                    code=code,
                    language=language,
                    hl_lines=hl_lines if hl_lines else None,
                    show_linenos=show_linenos,
                )

                # Wrap with title if present
                if title:
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
                logger.warning("highlight_failed", language=language, error=str(e))
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
