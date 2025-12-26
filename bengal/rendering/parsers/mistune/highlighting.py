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
- Parallel batch highlighting for 3.14t free-threading

Backend Selection:
    By default, uses the Pygments backend. To use tree-sitter:

    >>> from bengal.rendering.highlighting import get_highlighter
    >>> backend = get_highlighter("tree-sitter")

    Or configure in bengal.yaml:

    .. code-block:: yaml

        rendering:
          syntax_highlighting:
            backend: tree-sitter

Parallel Processing (3.14t):
    For batch processing of pages, use the deferred highlighting mode:

    >>> collector = CodeBlockCollector()
    >>> # Parse pages, collecting code blocks...
    >>> collector.flush()  # Batch highlight all collected blocks
"""

from __future__ import annotations

import html as html_mod
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from bengal.rendering.highlighting import highlight, highlight_many
from bengal.rendering.parsers.mistune.patterns import (
    CODE_INFO_PATTERN,
    HL_LINES_PATTERN,
)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Parallel Batch Highlighting (3.14t optimized)
# =============================================================================


@dataclass
class PendingCodeBlock:
    """A code block pending highlighting."""

    code: str
    language: str
    hl_lines: list[int]
    show_linenos: bool
    title: str | None
    placeholder_id: str


@dataclass
class CodeBlockCollector:
    """Collects code blocks for batch parallel highlighting.

    On Python 3.14t free-threaded, this provides significant speedups
    when a page has many code blocks.

    Usage:
        collector = CodeBlockCollector()

        # During markdown parsing, register blocks
        placeholder = collector.add(code, language, ...)

        # After parsing, batch highlight all blocks
        results = collector.flush()

        # Replace placeholders with highlighted HTML
        for block_id, html in results.items():
            content = content.replace(f"<!--code:{block_id}-->", html)
    """

    _pending: list[PendingCodeBlock] = field(default_factory=list)
    _counter: int = 0

    def add(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
        title: str | None = None,
    ) -> str:
        """Add a code block to the batch and return a placeholder.

        Args:
            code: Source code to highlight
            language: Programming language
            hl_lines: Lines to highlight
            show_linenos: Whether to show line numbers
            title: Optional title for the code block

        Returns:
            Placeholder string to insert in HTML
        """
        self._counter += 1
        block_id = f"cb{self._counter}"

        self._pending.append(
            PendingCodeBlock(
                code=code,
                language=language,
                hl_lines=hl_lines or [],
                show_linenos=show_linenos,
                title=title,
                placeholder_id=block_id,
            )
        )

        return f"<!--code:{block_id}-->"

    def flush(self) -> dict[str, str]:
        """Batch highlight all pending code blocks.

        Uses parallel highlighting on 3.14t for speedup.

        Returns:
            Mapping of placeholder_id -> highlighted HTML
        """
        if not self._pending:
            return {}

        # Prepare batch for parallel processing
        # Note: highlight_many doesn't support hl_lines yet, so we fall back
        # to sequential for blocks with line highlighting
        simple_blocks: list[tuple[str, str, PendingCodeBlock]] = []
        complex_blocks: list[PendingCodeBlock] = []

        for block in self._pending:
            if block.hl_lines:
                # Has line highlighting - needs individual processing
                complex_blocks.append(block)
            else:
                simple_blocks.append((block.code, block.language, block))

        results: dict[str, str] = {}

        # Batch process simple blocks in parallel
        if simple_blocks:
            items = [(code, lang) for code, lang, _ in simple_blocks]
            highlighted = highlight_many(items)

            for (_, _, block), html in zip(simple_blocks, highlighted, strict=True):
                results[block.placeholder_id] = _wrap_with_title(html, block.title)

        # Process complex blocks sequentially (they have line highlighting)
        for block in complex_blocks:
            try:
                html = highlight(
                    code=block.code,
                    language=block.language,
                    hl_lines=block.hl_lines,
                    show_linenos=block.show_linenos,
                )
                results[block.placeholder_id] = _wrap_with_title(html, block.title)
            except Exception as e:
                logger.warning("highlight_failed", language=block.language, error=str(e))
                results[block.placeholder_id] = _fallback_code_block(
                    block.code, block.language, block.title
                )

        # Reset state
        self._pending = []

        return results

    def __len__(self) -> int:
        """Number of pending code blocks."""
        return len(self._pending)


def _wrap_with_title(html: str, title: str | None) -> str:
    """Wrap highlighted code with optional title."""
    if not title:
        return html

    safe_title = html_mod.escape(title)
    return (
        f'<div class="code-block-titled">\n'
        f'<div class="code-block-title">{safe_title}</div>\n'
        f"{html}"
        f"</div>\n"
    )


def _fallback_code_block(code: str, language: str, title: str | None) -> str:
    """Create a plain code block when highlighting fails."""
    escaped_code = (
        code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
    plain_block = f'<pre><code class="language-{language}">{escaped_code}</code></pre>\n'

    return _wrap_with_title(plain_block, title)


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
