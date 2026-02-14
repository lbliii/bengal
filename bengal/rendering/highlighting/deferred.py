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

from bengal.rendering.highlighting.cache import HighlightCache
from bengal.rendering.highlighting.rosettes import RosettesBackend
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.code import parse_hl_lines

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


def _cache_key(block: PendingCodeBlock) -> str:
    """Compute cache key for a block. Uses rosettes.content_hash."""
    import rosettes

    return rosettes.content_hash(
        block.code,
        block.language,
        hl_lines=frozenset(block.hl_lines) if block.hl_lines else None,
        show_linenos=block.show_linenos,
    )


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

        Uses parallel highlighting on 3.14t for speedup. When cache is provided,
        checks cache first; cache misses are highlighted and stored.
        """
        if not self._pending:
            return {}

        cache: HighlightCache | None = getattr(_thread_local, "highlight_cache", None)
        results: dict[str, str] = {}

        import rosettes

        # Use cache only when rosettes has content_hash (rosettes>=0.2.0)
        if cache and not hasattr(rosettes, "content_hash"):
            cache = None

        # Cache lookup: split into cached vs uncached
        uncached: list[tuple[PendingCodeBlock, str]] = []
        for block in self._pending:
            if cache:
                key = _cache_key(block)
                cached = cache.get(key)
                if cached is not None:
                    results[block.placeholder_id] = _wrap_with_title(cached, block.title)
                    continue
                uncached.append((block, key))
            else:
                uncached.append((block, ""))

        if not uncached:
            self._pending = []
            return results

        uncached_blocks = [b for b, _ in uncached]

        HighlightItem = getattr(rosettes, "HighlightItem", None)
        has_highlight_item = HighlightItem is not None

        if has_highlight_item:
            items: list[object] = []
            for block in uncached_blocks:
                if block.hl_lines or block.show_linenos:
                    items.append(
                        HighlightItem(
                            code=block.code,
                            language=block.language,
                            hl_lines=frozenset(block.hl_lines) if block.hl_lines else None,
                            show_linenos=block.show_linenos,
                        )
                    )
                else:
                    items.append((block.code, block.language))

            try:
                highlighted = rosettes.highlight_many(items)
            except Exception as e:
                logger.warning("highlight_batch_failed", error=str(e))
                for block in uncached_blocks:
                    results[block.placeholder_id] = _fallback_code_block(
                        block.code, block.language, block.title
                    )
                self._pending = []
                return results

            for (block, key), html in zip(uncached, highlighted, strict=True):
                if cache and key:
                    cache.set(key, html)
                results[block.placeholder_id] = _wrap_with_title(html, block.title)
        else:
            # Fallback for rosettes < 0.2.0: simple blocks parallel, complex sequential
            simple_blocks: list[tuple[str, str, PendingCodeBlock, str]] = []
            complex_blocks: list[tuple[PendingCodeBlock, str]] = []
            for block, key in uncached:
                if block.hl_lines or block.show_linenos:
                    complex_blocks.append((block, key))
                else:
                    simple_blocks.append((block.code, block.language, block, key))

            if simple_blocks:
                items = [(code, lang) for code, lang, _, _ in simple_blocks]
                highlighted = rosettes.highlight_many(items)
                for (_, _, block, key), html in zip(simple_blocks, highlighted, strict=True):
                    if cache and key:
                        cache.set(key, html)
                    results[block.placeholder_id] = _wrap_with_title(html, block.title)

            backend = RosettesBackend()
            for block, key in complex_blocks:
                try:
                    html = backend.highlight(
                        code=block.code,
                        language=block.language,
                        hl_lines=block.hl_lines,
                        show_linenos=block.show_linenos,
                    )
                    if cache and key:
                        cache.set(key, html)
                    results[block.placeholder_id] = _wrap_with_title(html, block.title)
                except Exception as e:
                    logger.warning("highlight_failed", language=block.language, error=str(e))
                    results[block.placeholder_id] = _fallback_code_block(
                        block.code, block.language, block.title
                    )

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


def enable_deferred_highlighting(cache: HighlightCache | None = None) -> None:
    """Enable deferred highlighting for the current thread.

    When enabled, code blocks are collected instead of highlighted immediately.
    Call flush_deferred_highlighting() after parsing to batch process them.

    Args:
        cache: Optional HighlightCache for block-level caching across pages.
    """
    _thread_local.collector = CodeBlockCollector()
    _thread_local.highlight_cache = cache
    _thread_local.deferred_enabled = True


def disable_deferred_highlighting() -> None:
    """Disable deferred highlighting for the current thread."""
    _thread_local.deferred_enabled = False
    _thread_local.collector = None
    _thread_local.highlight_cache = None


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


# Re-export for backward compatibility
__all__ = [
    "disable_deferred_highlighting",
    "enable_deferred_highlighting",
    "flush_deferred_highlighting",
    "is_deferred_highlighting_enabled",
    "parse_hl_lines",
]
