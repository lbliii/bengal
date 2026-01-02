"""
Patitas - A Modern Markdown Parser for Python 3.14+.

Patitas ("little paws" 🐾) is a pure-Python Markdown parser designed for the
free-threaded Python era. It provides:

- O(n) guaranteed parsing — No regex backtracking, no ReDoS vulnerabilities
- Thread-safe by design — Zero shared mutable state, free-threading ready
- Typed AST — @dataclass(frozen=True, slots=True) nodes, not Dict[str, Any]
- StringBuilder rendering — O(n) output vs O(n²) string concatenation

Part of the Bengal cat family:
- Bengal — Static site generator (the breed)
- Kida — Template engine (the cat's name)
- Rosettes — Syntax highlighter (the spots)
- Patitas — Markdown parser (the paws)

Usage:
    >>> from bengal.rendering.parsers.patitas import parse, create_markdown
    >>>
    >>> # Simple parsing
    >>> html = parse("# Hello **World**")
    >>>
    >>> # With options
    >>> md = create_markdown(plugins=["table", "footnotes"])
    >>> html = md("# Hello\n\n| A | B |\n|---|---|\n| 1 | 2 |")

Thread Safety:
    Patitas is designed for Python 3.14t free-threaded builds:
    - Lexer: Single-use, instance-local state only
    - Parser: Produces immutable AST (frozen dataclasses)
    - Renderer: StringBuilder is local to each render() call
    - No global state: No module-level mutable variables

See Also:
    - RFC: plan/drafted/rfc-patitas-markdown-parser.md
    - Mistune (being replaced): bengal/rendering/parsers/mistune/
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Literal

from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.nodes import (
    Block,
    BlockQuote,
    CodeSpan,
    Directive,
    Document,
    Emphasis,
    FencedCode,
    FootnoteDef,
    FootnoteRef,
    Heading,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    Inline,
    LineBreak,
    Link,
    List,
    ListItem,
    Math,
    MathBlock,
    Node,
    Paragraph,
    Role,
    Strikethrough,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    ThematicBreak,
)
from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.parser import Parser
    from bengal.rendering.parsers.patitas.protocols import LexerDelegate
    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

__all__ = [
    # Public API
    "parse",
    "parse_many",
    "parse_to_ast",
    "render_ast",
    "create_markdown",
    # Wrapper for BaseMarkdownParser interface
    "PatitasParser",
    # Types
    "SourceLocation",
    "Token",
    "TokenType",
    "StringBuilder",
    # AST Nodes - Core
    "Node",
    "Block",
    "Inline",
    "Document",
    "Heading",
    "Paragraph",
    "FencedCode",
    "IndentedCode",
    "BlockQuote",
    "List",
    "ListItem",
    "ThematicBreak",
    "HtmlBlock",
    "Text",
    "Emphasis",
    "Strong",
    "Link",
    "Image",
    "CodeSpan",
    "LineBreak",
    "HtmlInline",
    # Directive and Role nodes
    "Directive",
    "Role",
    # Plugin AST Nodes
    "Strikethrough",
    "Table",
    "TableRow",
    "TableCell",
    "Math",
    "MathBlock",
    "FootnoteRef",
    "FootnoteDef",
]

# Version
__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    """Module-level getattr for free-threading declaration and lazy imports.

    Declares this module safe for free-threaded Python (PEP 703/779).
    The interpreter queries _Py_mod_gil to determine if the module
    needs the GIL.

    Also provides lazy import of PatitasParser to avoid circular imports
    (wrapper.py imports from this module).
    """
    if name == "_Py_mod_gil":
        # Signal: this module is safe for free-threading
        # 0 = Py_MOD_GIL_NOT_USED
        return 0
    if name == "PatitasParser":
        from bengal.rendering.parsers.patitas.wrapper import PatitasParser

        return PatitasParser
    raise AttributeError(f"module 'patitas' has no attribute {name!r}")


def parse(source: str, *, highlight: bool = False, delegate: LexerDelegate | None = None) -> str:
    """Parse Markdown source to HTML.

    Simple one-shot parsing function for common use cases.

    Args:
        source: Markdown source text
        highlight: Enable syntax highlighting for code blocks
        delegate: Optional sub-lexer delegate for ZCLH handoff

    Returns:
        Rendered HTML string
    """
    ast = parse_to_ast(source)
    return render_ast(ast, source, highlight=highlight, delegate=delegate)


def parse_many(
    sources: Sequence[str],
    *,
    highlight: bool = False,
    delegate: LexerDelegate | None = None,
    workers: int | Literal["auto"] = "auto",
) -> list[str]:
    """Parse multiple Markdown documents in parallel.

    Leverages Python 3.14t free-threading for true parallel execution.
    """
    n_docs = len(sources)

    # Fast path: single doc or empty
    if n_docs <= 1:
        return [parse(s, highlight=highlight, delegate=delegate) for s in sources]

    # Calculate total work
    total_chars = sum(len(s) for s in sources)
    avg_size = total_chars / n_docs

    # Determine optimal worker count
    if workers == "auto":
        # Fast path: skip parallelism for small workloads
        if total_chars < 5000:  # < 5KB total
            return [parse(s, highlight=highlight, delegate=delegate) for s in sources]

        cpu_count = os.cpu_count() or 4
        max_workers = min(4, n_docs, max(2, cpu_count // 2))

        if avg_size < 1000:  # < 1KB average per doc
            max_workers = min(2, max_workers)
    else:
        max_workers = workers

    # Sequential fallback if only 1 worker
    if max_workers <= 1:
        return [parse(s, highlight=highlight, delegate=delegate) for s in sources]

    # Parallel execution
    def _parse_one(source: str) -> str:
        return parse(source, highlight=highlight, delegate=delegate)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_parse_one, sources))


def parse_to_ast(
    source: str,
    source_file: str | None = None,
    *,
    plugins: list[str] | None = None,
    text_transformer: Callable[[str], str] | None = None,
) -> Sequence[Block]:
    """Parse Markdown source into typed AST blocks."""
    from .parser import Parser

    parser = Parser(
        source,
        source_file,
        text_transformer=text_transformer,
    )

    # Enable plugins
    if plugins:
        if "table" in plugins:
            parser._tables_enabled = True
        if "strikethrough" in plugins:
            parser._strikethrough_enabled = True
        if "task_lists" in plugins:
            parser._task_lists_enabled = True
        if "footnotes" in plugins:
            parser._footnotes_enabled = True
        if "math" in plugins:
            parser._math_enabled = True
        if "autolinks" in plugins:
            parser._autolinks_enabled = True

    return parser.parse()


def render_ast(
    ast: Sequence[Block],
    source: str,
    *,
    highlight: bool = False,
    highlight_style: str = "semantic",
    text_transformer: Callable[[str], str] | None = None,
    delegate: LexerDelegate | None = None,
) -> str:
    """Render AST nodes to HTML.

    Note: The 'source' buffer is required because Patitas uses a Zero-Copy Lexer Handoff (ZCLH)
    where AST nodes like FencedCode store source offsets rather than content strings.
    """
    if source is None:
        raise TypeError(
            "render_ast() requires the 'source' buffer for Zero-Copy extraction. "
            "See rfc-zero-copy-lexer-handoff.md for details."
        )

    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

    renderer = HtmlRenderer(
        source,
        highlight=highlight,
        highlight_style=highlight_style,
        text_transformer=text_transformer,
        delegate=delegate,
    )
    return renderer.render(ast)


def create_markdown(
    *,
    plugins: list[str] | None = None,
    highlight: bool = True,
    highlight_style: str = "semantic",
    delegate: LexerDelegate | None = None,
) -> Markdown:
    """Create a configured Markdown parser/renderer."""
    return Markdown(
        plugins=plugins or [],
        highlight=highlight,
        highlight_style=highlight_style,
        delegate=delegate,
    )


class Markdown:
    """Configured Markdown parser/renderer.

    Thread-safe: can be shared across threads. Each __call__ creates
    independent parser/renderer instances.
    """

    __slots__ = (
        "_plugins",
        "_highlight",
        "_highlight_style",
        "_plugins_enabled",
        "_directive_registry",
        "_role_registry",
        "_delegate",
    )

    AVAILABLE_PLUGINS = frozenset(
        {
            "table",
            "strikethrough",
            "task_lists",
            "footnotes",
            "math",
            "autolinks",
        }
    )

    def __init__(
        self,
        plugins: list[str],
        highlight: bool,
        highlight_style: str,
        delegate: LexerDelegate | None = None,
    ) -> None:
        self._plugins = tuple(plugins)  # Immutable
        self._highlight = highlight
        self._highlight_style = highlight_style
        self._delegate = delegate

        # Determine which plugins are enabled
        if "all" in plugins:
            self._plugins_enabled = frozenset(self.AVAILABLE_PLUGINS)
        else:
            enabled = set()
            for plugin in plugins:
                if plugin in self.AVAILABLE_PLUGINS:
                    enabled.add(plugin)
                elif plugin != "all":
                    import warnings

                    warnings.warn(
                        f"Unknown plugin: {plugin!r}. Available: {sorted(self.AVAILABLE_PLUGINS)}",
                        stacklevel=3,
                    )
            self._plugins_enabled = frozenset(enabled)

        from bengal.rendering.parsers.patitas.directives.registry import (
            create_default_registry,
        )
        from bengal.rendering.parsers.patitas.roles.registry import (
            create_default_registry as create_default_role_registry,
        )

        self._directive_registry = create_default_registry()
        self._role_registry = create_default_role_registry()

    def __call__(
        self,
        source: str,
        text_transformer: Callable[[str], str] | None = None,
        page_context: Any | None = None,
    ) -> str:
        """Parse and render Markdown source to HTML."""
        ast = self._parse_to_ast(source, text_transformer=text_transformer)
        return self._render_ast(
            ast, source, text_transformer=text_transformer, page_context=page_context
        )

    def _parse_to_ast(
        self, source: str, text_transformer: Callable[[str], str] | None = None
    ) -> Sequence[Block]:
        """Parse source to AST with plugins applied."""
        from bengal.rendering.parsers.patitas.parser import Parser

        parser = Parser(
            source,
            directive_registry=self._directive_registry,
            text_transformer=text_transformer,
        )

        parser._tables_enabled = "table" in self._plugins_enabled
        parser._strikethrough_enabled = "strikethrough" in self._plugins_enabled
        parser._task_lists_enabled = "task_lists" in self._plugins_enabled
        parser._footnotes_enabled = "footnotes" in self._plugins_enabled
        parser._math_enabled = "math" in self._plugins_enabled
        parser._autolinks_enabled = "autolinks" in self._plugins_enabled

        return parser.parse()

    def _render_ast(
        self,
        ast: Sequence[Block],
        source: str,
        text_transformer: Callable[[str], str] | None = None,
        page_context: Any | None = None,
    ) -> str:
        """Render AST with configured options.

        Args:
            ast: Parsed AST blocks
            source: Original source buffer
            text_transformer: Optional callback to transform plain text
            page_context: Optional page object for directives that need page/section info
        """
        from bengal.directives.cache import get_cache
        from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

        # Use global directive cache if enabled (auto-enabled for versioned sites)
        directive_cache = get_cache()
        cache_enabled = directive_cache.stats().get("enabled", False)

        renderer = HtmlRenderer(
            source,
            highlight=self._highlight,
            highlight_style=self._highlight_style,
            directive_registry=self._directive_registry,
            directive_cache=directive_cache if cache_enabled else None,
            role_registry=self._role_registry,
            text_transformer=text_transformer,
            delegate=self._delegate,
            page_context=page_context,
        )
        return renderer.render(ast)

    def parse_to_ast(
        self, source: str, text_transformer: Callable[[str], str] | None = None
    ) -> Sequence[Block]:
        """Parse source to AST without rendering."""
        return self._parse_to_ast(source, text_transformer=text_transformer)

    def render_ast(
        self,
        ast: Sequence[Block],
        source: str,
        text_transformer: Callable[[str], str] | None = None,
        page_context: Any | None = None,
    ) -> str:
        """Render AST to HTML."""
        return self._render_ast(
            ast, source, text_transformer=text_transformer, page_context=page_context
        )

    def render_ast_with_toc(
        self,
        ast: Sequence[Block],
        source: str,
        text_transformer: Callable[[str], str] | None = None,
        page_context: Any | None = None,
    ) -> tuple[str, str, list[dict[str, Any]]]:
        """Render AST to HTML with single-pass TOC extraction.

        RFC: rfc-path-to-200-pgs (Single-Pass Heading Decoration)

        Headings are collected during rendering - no post-render regex pass needed.

        Args:
            ast: Parsed AST blocks
            source: Original source buffer
            text_transformer: Optional callback to transform plain text
            page_context: Optional page object for directives that need page/section info

        Returns:
            Tuple of (HTML with heading IDs, TOC HTML, TOC items list)
        """
        from bengal.directives.cache import get_cache
        from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

        # Use global directive cache if enabled
        directive_cache = get_cache()
        cache_enabled = directive_cache.stats().get("enabled", False)

        renderer = HtmlRenderer(
            source,
            highlight=self._highlight,
            highlight_style=self._highlight_style,
            directive_registry=self._directive_registry,
            directive_cache=directive_cache if cache_enabled else None,
            role_registry=self._role_registry,
            text_transformer=text_transformer,
            delegate=self._delegate,
            page_context=page_context,
        )

        # Render HTML - headings collected during this walk
        html = renderer.render(ast)

        # Get TOC data from renderer (no extra pass!)
        toc_html = renderer.get_toc_html()
        toc_items = renderer.get_toc_items()

        return html, toc_html, toc_items

    @property
    def plugins(self) -> frozenset[str]:
        """Get enabled plugins."""
        return self._plugins_enabled
