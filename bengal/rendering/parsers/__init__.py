"""
Markdown parser implementations for Bengal SSG.

This package provides pluggable Markdown parser engines with a unified interface.
Choose the parser that best fits your needs:

Parser Engines:
    PatitasParser (Recommended for Python 3.14+):
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

    MistuneParser (Legacy, still default):
        Fast, modern parser with excellent performance. Supports all Bengal
        features including TOC extraction, cross-references, and variable
        substitution. Will be deprecated in Bengal 3.0.

        Performance: ~100 pages in 1.2s

    PythonMarkdownParser:
        Full-featured parser with extensive extension support. Better
        compatibility with complex Markdown edge cases but slower.

        Performance: ~100 pages in 3.8s (3.2x slower)

Public API:
    - create_markdown_parser(): Factory function (recommended)
    - BaseMarkdownParser: Protocol for custom parser implementations
    - PatitasParser: Modern typed-AST parser (production-ready)
    - MistuneParser: Fast Mistune-based parser (legacy)
    - PythonMarkdownParser: Python-Markdown based parser

Configuration:
    Set the parser in bengal.yaml:

    .. code-block:: yaml

        markdown:
          parser: patitas  # Recommended for Python 3.14+
          # parser: mistune  # Legacy (default until Bengal 3.0)
          # parser: python-markdown  # Full-featured but slower

Usage:
    >>> from bengal.rendering.parsers import create_markdown_parser
    >>>
    >>> # Default parser (mistune, but patitas recommended)
    >>> parser = create_markdown_parser()
    >>>
    >>> # Modern parser (recommended for Python 3.14+)
    >>> parser = create_markdown_parser('patitas')
    >>>
    >>> # Parse content
    >>> html = parser.parse("# Hello World", metadata={})
    >>>
    >>> # Parse with TOC extraction
    >>> html, toc = parser.parse_with_toc("## Section 1\\n## Section 2", {})

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
    - plan/drafted/rfc-patitas-bengal-directive-migration.md: Directive migration
"""

from __future__ import annotations

import os
import warnings

from bengal.rendering.parsers.base import BaseMarkdownParser
from bengal.rendering.parsers.mistune import MistuneParser
from bengal.rendering.parsers.patitas.wrapper import PatitasParser
from bengal.rendering.parsers.python_markdown import PythonMarkdownParser

# Alias for convenience
MarkdownParser = PythonMarkdownParser

# Environment variable to opt-in to deprecation warnings
_SHOW_DEPRECATION = os.environ.get("BENGAL_PARSER_DEPRECATION_WARNINGS", "0") == "1"

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
            - 'mistune' (default): Legacy parser, will be deprecated in Bengal 3.0
            - 'patitas': Modern parser with typed AST (recommended for Python 3.14+)
            - 'python-markdown' / 'markdown': Full-featured, slower

    Returns:
        Parser instance implementing BaseMarkdownParser protocol.

    Raises:
        BengalConfigError: If engine name is not recognized.
        ImportError: If python-markdown is requested but not installed.

    Examples:
        >>> # Modern parser (recommended for Python 3.14+)
        >>> parser = create_markdown_parser('patitas')
        >>>
        >>> # Default parser (mistune, legacy)
        >>> parser = create_markdown_parser()
        >>>
        >>> # Explicit engine selection
        >>> parser = create_markdown_parser('python-markdown')

    Note:
        Set BENGAL_PARSER_DEPRECATION_WARNINGS=1 to see deprecation warnings
        for mistune parser usage.
    """
    engine = (engine or "mistune").lower()

    if engine == "mistune":
        if _SHOW_DEPRECATION:
            warnings.warn(
                "MistuneParser will be deprecated in Bengal 3.0. "
                "Consider switching to PatitasParser for Python 3.14+ "
                "(set markdown.parser: patitas in bengal.yaml). "
                "PatitasParser offers thread-safety, typed AST, and O(n) parsing.",
                DeprecationWarning,
                stacklevel=2,
            )
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
            f"Unsupported markdown engine: {engine}. Choose from: 'patitas', 'mistune', 'python-markdown'",
            suggestion="Set markdown.parser to 'patitas' (recommended), 'mistune', or 'python-markdown' in config",
            code=ErrorCode.C003,
        )
