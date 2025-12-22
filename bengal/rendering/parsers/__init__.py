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

Public API:
    - create_markdown_parser(): Factory function (recommended)
    - BaseMarkdownParser: Protocol for custom parser implementations
    - MistuneParser: Fast Mistune-based parser
    - PythonMarkdownParser: Python-Markdown based parser

Configuration:
    Set the parser in bengal.yaml:

    .. code-block:: yaml

        markdown:
          parser: mistune  # or 'python-markdown'

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

Thread Safety:
    Parser instances are NOT thread-safe. The rendering pipeline uses
    thread-local caching (see pipeline.thread_local) to provide one
    parser per worker thread.

Related Modules:
    - bengal.rendering.pipeline.thread_local: Thread-local parser management
    - bengal.rendering.plugins: Mistune plugins for enhanced parsing
    - bengal.directives: Documentation directive support

See Also:
    - architecture/performance.md: Parser benchmarks and optimization
"""

from __future__ import annotations

from bengal.rendering.parsers.base import BaseMarkdownParser
from bengal.rendering.parsers.mistune import MistuneParser
from bengal.rendering.parsers.python_markdown import PythonMarkdownParser

try:
    # Auto-apply Pygments performance patch for tests and default behavior
    from bengal.rendering.parsers.pygments_patch import PygmentsPatch

    PygmentsPatch.apply()
except Exception:
    pass

# Alias for convenience
MarkdownParser = PythonMarkdownParser

__all__ = [
    "BaseMarkdownParser",
    "PythonMarkdownParser",
    "MistuneParser",
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
    """
    engine = (engine or "mistune").lower()

    if engine == "mistune":
        return MistuneParser()
    elif engine in ("python-markdown", "python_markdown", "markdown"):
        try:
            return PythonMarkdownParser()
        except ImportError:
            raise ImportError(
                "python-markdown parser requested but not installed. "
                "Install with: pip install markdown"
            ) from None
    else:
        from bengal.errors import BengalConfigError

        raise BengalConfigError(
            f"Unsupported markdown engine: {engine}. Choose from: 'python-markdown', 'mistune'",
            suggestion="Set markdown.engine to 'python-markdown' or 'mistune' in config",
        )
