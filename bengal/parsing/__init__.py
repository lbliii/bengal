"""
Markdown parser implementations for Bengal SSG.

This package provides pluggable Markdown parser engines with a unified interface.

Parser Engines:
PatitasParser (Default):
    Modern parser with typed AST, designed for Python 3.14+ free-threading.
    Features O(n) guaranteed parsing, immutable AST nodes, and StringBuilder
    rendering. Production-ready with full directive support.

    Key features:
    - O(n) parsing (no regex backtracking, no ReDoS)
    - Typed AST with frozen dataclasses
    - Thread-safe by design (free-threading ready)
    - StringBuilder O(n) rendering
    - Full directive support (40+ directives)

    See: plan/drafted/rfc-patitas-markdown-parser.md

PythonMarkdownParser:
    Full-featured parser with extensive extension support. Better
    compatibility with complex Markdown edge cases but slower.

    Performance: ~100 pages in 3.8s (3.2x slower than Patitas)

Public API:
- create_markdown_parser(): Factory function (recommended)
- BaseMarkdownParser: Protocol for custom parser implementations
- PatitasParser: Modern typed-AST parser (production-ready)
- PythonMarkdownParser: Python-Markdown based parser

Configuration:
Set the parser in bengal.toml:

.. code-block:: toml

    [markdown]
    parser = "patitas"  # Default (recommended)
    # parser = "python-markdown"  # Full-featured but slower

Usage:
    >>> from bengal.parsing import create_markdown_parser
    >>>
    >>> # Default parser (patitas)
    >>> parser = create_markdown_parser()
    >>>
    >>> # Parse content
    >>> html = parser.parse("# Hello World", metadata={})
    >>>
    >>> # Parse with TOC extraction
    >>> html, toc = parser.parse_with_toc("## Section 1\n## Section 2", {})

Thread Safety:
PythonMarkdownParser instances are NOT thread-safe.
The rendering pipeline uses thread-local caching (see pipeline.thread_local)
to provide one parser per worker thread.

PatitasParser is thread-safe by design - each parse() call creates
independent parser/renderer instances with no shared state.

Related Modules:
- bengal.rendering.pipeline.thread_local: Thread-local parser management
- bengal.directives: Documentation directive support

See Also:
- architecture/performance.md: Parser benchmarks and optimization
- plan/drafted/rfc-patitas-markdown-parser.md: Patitas RFC

"""

from __future__ import annotations

import warnings

from bengal.parsing.backends.patitas.wrapper import PatitasParser
from bengal.parsing.base import BaseMarkdownParser
from bengal.parsing.python_markdown import PythonMarkdownParser

# Alias for convenience
MarkdownParser = PythonMarkdownParser

__all__ = [
    "BaseMarkdownParser",
    "MarkdownParser",
    "PatitasParser",
    "PythonMarkdownParser",
    "create_markdown_parser",
]


def create_markdown_parser(engine: str | None = None) -> BaseMarkdownParser:
    """
    Create a markdown parser instance.

    Factory function to instantiate the appropriate parser based on engine
    selection. This is the recommended way to create parsers.

    Args:
        engine: Parser engine name. Options:
            - 'patitas' (default): Modern parser with typed AST
            - 'python-markdown' / 'markdown': Full-featured, slower

    Returns:
        Parser instance implementing BaseMarkdownParser protocol.

    Raises:
        BengalConfigError: If engine name is not recognized.
        ImportError: If python-markdown is requested but not installed.

    Examples:
            >>> # Default parser (patitas - recommended)
            >>> parser = create_markdown_parser()
            >>>
            >>> # Explicit engine selection
            >>> parser = create_markdown_parser('python-markdown')

    """
    engine = (engine or "patitas").lower()

    if engine == "mistune":
        # Graceful deprecation: mistune is removed, redirect to patitas
        warnings.warn(
            "MistuneParser has been removed. Using PatitasParser instead. "
            "Update your config to use parser = 'patitas'.",
            DeprecationWarning,
            stacklevel=2,
        )
        return PatitasParser()
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
            f"Unsupported markdown engine: {engine}. Choose from: 'patitas', 'python-markdown'",
            suggestion="Set markdown.parser to 'patitas' (default) or 'python-markdown' in config",
            code=ErrorCode.C003,
        )
