"""
Markdown parser implementations for Bengal SSG.

This package provides pluggable Markdown parser engines with a unified interface.
Choose the parser that best fits your needs:

Parser Engines:
    MistuneParser (Recommended):
        Fast, modern parser with excellent performance. Supports all Bengal
        features including TOC extraction, cross-references, and variable
        substitution. Default choice for production sites.

        Performance: ~100 pages in 1.2s

    PythonMarkdownParser:
        Full-featured parser with extensive extension support. Better
        compatibility with complex Markdown edge cases but slower.

        Performance: ~100 pages in 3.8s (3.2x slower)

    PatitasParser (Experimental):
        Modern parser with typed AST, designed for Python 3.14+ free-threading.
        Features O(n) guaranteed parsing, immutable AST nodes, and StringBuilder
        rendering. Still in development - use for testing/evaluation.

        Key features:
        - O(n) parsing (no regex backtracking, no ReDoS)
        - Typed AST with frozen dataclasses
        - Thread-safe by design
        - StringBuilder O(n) rendering

        See: plan/drafted/rfc-patitas-markdown-parser.md

Public API:
    - create_markdown_parser(): Factory function (recommended)
    - BaseMarkdownParser: Protocol for custom parser implementations
    - MistuneParser: Fast Mistune-based parser
    - PythonMarkdownParser: Python-Markdown based parser
    - PatitasParser: Modern typed-AST parser (experimental)

Configuration:
    Set the parser in bengal.yaml:

    .. code-block:: yaml

        markdown:
          parser: mistune  # or 'python-markdown' or 'patitas'

Usage:
    >>> from bengal.rendering.parsers import create_markdown_parser
    >>>
    >>> # Create parser (defaults to mistune)
    >>> parser = create_markdown_parser()
    >>>
    >>> # Parse content
    >>> html = parser.parse("# Hello World", metadata={})
    >>>
    >>> # Parse with TOC extraction
    >>> html, toc = parser.parse_with_toc("## Section 1\\n## Section 2", {})
    >>>
    >>> # Use experimental Patitas parser
    >>> parser = create_markdown_parser('patitas')

Thread Safety:
    MistuneParser and PythonMarkdownParser instances are NOT thread-safe.
    The rendering pipeline uses thread-local caching (see pipeline.thread_local)
    to provide one parser per worker thread.

    PatitasParser is thread-safe by design - each parse() call creates
    independent parser/renderer instances with no shared state.

Related Modules:
    - bengal.rendering.pipeline.thread_local: Thread-local parser management
    - bengal.rendering.plugins: Mistune plugins for enhanced parsing
    - bengal.directives: Documentation directive support

See Also:
    - architecture/performance.md: Parser benchmarks and optimization
    - plan/drafted/rfc-patitas-markdown-parser.md: Patitas RFC
"""

from __future__ import annotations

from bengal.rendering.parsers.base import BaseMarkdownParser
from bengal.rendering.parsers.mistune import MistuneParser
from bengal.rendering.parsers.patitas.wrapper import PatitasParser
from bengal.rendering.parsers.python_markdown import PythonMarkdownParser

# Alias for convenience
MarkdownParser = PythonMarkdownParser

__all__ = [
    "BaseMarkdownParser",
    "PythonMarkdownParser",
    "MistuneParser",
    "PatitasParser",
    "MarkdownParser",
    "create_markdown_parser",
]


def create_markdown_parser(engine: str | None = None) -> BaseMarkdownParser:
    """
    Create a markdown parser instance.

    Factory function to instantiate the appropriate parser based on engine
    selection. This is the recommended way to create parsers.

    Args:
        engine: Parser engine name. Options:
            - 'mistune' (default): Fast, recommended for production
            - 'python-markdown' / 'markdown': Full-featured, slower
            - 'patitas': Modern parser with typed AST (experimental)

    Returns:
        Parser instance implementing BaseMarkdownParser protocol.

    Raises:
        BengalConfigError: If engine name is not recognized.
        ImportError: If python-markdown is requested but not installed.

    Examples:
        >>> # Default parser (mistune)
        >>> parser = create_markdown_parser()
        >>>
        >>> # Explicit engine selection
        >>> parser = create_markdown_parser('python-markdown')
        >>>
        >>> # Experimental modern parser
        >>> parser = create_markdown_parser('patitas')
    """
    engine = (engine or "mistune").lower()

    if engine == "mistune":
        return MistuneParser()
    elif engine == "patitas":
        return PatitasParser()
    elif engine in ("python-markdown", "python_markdown", "markdown"):
        try:
            return PythonMarkdownParser()
        except ImportError:
            raise ImportError(
                "python-markdown parser requested but not installed. "
                "Install with: pip install markdown"
            ) from None
    else:
        from bengal.errors import BengalConfigError, ErrorCode

        raise BengalConfigError(
            f"Unsupported markdown engine: {engine}. Choose from: 'python-markdown', 'mistune', 'patitas'",
            suggestion="Set markdown.engine to 'python-markdown', 'mistune', or 'patitas' in config",
            code=ErrorCode.C003,
        )
