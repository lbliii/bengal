"""
Deferred syntax highlighting for parallel batch processing.

Provides syntax highlighting for code blocks with support for:
- Language detection
- Line highlighting ({1,3-5} syntax)
- Code block titles (title="filename.py")
- Line numbers (for blocks with 3+ lines)
- Parallel batch highlighting for 3.14t free-threading

Backend Selection:
Uses the Rosettes backend (Bengal's default, lock-free, 55 languages).

Parallel Processing (3.14t):
For batch processing of pages, use the deferred highlighting mode:

    >>> from bengal.rendering.highlighting.deferred import (
    ...     enable_deferred_highlighting,
    ...     flush_deferred_highlighting,
    ... )
    >>> enable_deferred_highlighting()
    >>> # Parse pages, collecting code blocks...
    >>> content = flush_deferred_highlighting(content)

"""

from __future__ import annotations

import html as html_mod
import re
import threading
from dataclasses import dataclass, field

from bengal.rendering.highlighting.rosettes import RosettesBackend
from bengal.utils.observability.logger import get_logger

# Pattern to extract line highlight syntax from code fence info string
# Matches: python {5} or yaml {1,3,5} or js {1-3,5,7-9}
HL_LINES_PATTERN = re.compile(r"^(\S+)\s*\{([^}]+)\}$")

# Pattern to parse code fence info with optional title and line highlights
# Matches: python, python title="file.py", python {1,3}, python title="file.py" {1,3}
CODE_INFO_PATTERN = re.compile(
    r"^(?P<lang>\S+)"  # Language (required, no spaces)
    r'(?:\s+title="(?P<title>[^"]*)")?'  # title="..." (optional)
    r"(?:\s*\{(?P<hl>[^}]+)\})?$"  # {1,3-5} line highlights (optional)
)

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
            import rosettes

            items = [(code, lang) for code, lang, _ in simple_blocks]
            highlighted = rosettes.highlight_many(items)

            for (_, _, block), html in zip(simple_blocks, highlighted, strict=True):
                results[block.placeholder_id] = _wrap_with_title(html, block.title)

        # Process complex blocks sequentially (they have line highlighting)
        backend = RosettesBackend()
        for block in complex_blocks:
            try:
                html = backend.highlight(
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


# =============================================================================
# Thread-Local Deferred Highlighting (for pipeline integration)
# =============================================================================

# Thread-local collector for parallel batch highlighting
_thread_local = threading.local()


def enable_deferred_highlighting() -> None:
    """Enable deferred highlighting for the current thread.

    When enabled, code blocks are collected instead of highlighted immediately.
    Call flush_deferred_highlighting() after parsing to batch process them.

    """
    _thread_local.collector = CodeBlockCollector()
    _thread_local.deferred_enabled = True


def disable_deferred_highlighting() -> None:
    """Disable deferred highlighting for the current thread."""
    _thread_local.deferred_enabled = False
    _thread_local.collector = None


def is_deferred_highlighting_enabled() -> bool:
    """Check if deferred highlighting is enabled for the current thread."""
    return getattr(_thread_local, "deferred_enabled", False)


def get_deferred_collector() -> CodeBlockCollector | None:
    """Get the current thread's code block collector."""
    return getattr(_thread_local, "collector", None)


def flush_deferred_highlighting(content: str) -> str:
    """Batch highlight all collected code blocks and replace placeholders.

    Args:
        content: HTML content with code block placeholders

    Returns:
        Content with placeholders replaced by highlighted code

    """
    collector = get_deferred_collector()
    if not collector or len(collector) == 0:
        return content

    # Batch highlight all collected blocks
    results = collector.flush()

    # Replace placeholders with highlighted HTML
    for block_id, highlighted_html in results.items():
        placeholder = f"<!--code:{block_id}-->"
        content = content.replace(placeholder, highlighted_html)

    return content


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
