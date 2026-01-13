"""
Patitas - A Modern Markdown Parser for Python 3.14+.

Patitas ("little paws" 🐾) is a pure-Python Markdown parser designed for the
free-threaded Python era. It provides:

- O(n) guaranteed parsing — No regex backtracking, no ReDoS vulnerabilities
- Thread-safe by design — Zero shared mutable state, free-threading ready
- Typed AST — @dataclass(frozen=True, slots=True) nodes, not Dict[str, Any]
- StringBuilder rendering — O(n) output vs O(n²) string concatenation
- ContextVar configuration — Thread-local config for parallel parsing

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
    >>> html = md("# Hello

| A | B |
|---|---|
| 1 | 2 |")

Thread Safety:
Patitas is designed for Python 3.14t free-threaded builds:
- Lexer: Single-use, instance-local state only
- Parser: Produces immutable AST (frozen dataclasses)
- Renderer: StringBuilder is local to each render() call
- Configuration: ContextVar provides thread-local config (no global mutable state)

See Also:
- RFC: plan/drafted/rfc-patitas-markdown-parser.md
- RFC: plan/rfc-contextvar-config-implementation.md
- Mistune (being replaced): bengal/rendering/parsers/mistune/

"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Literal

from bengal.rendering.parsers.patitas.accumulator import (
    RenderMetadata,
    get_metadata,
    metadata_context,
    reset_metadata,
    set_metadata,
)
from bengal.rendering.parsers.patitas.config import (
    ParseConfig,
    get_parse_config,
    parse_config_context,
    reset_parse_config,
    set_parse_config,
)
from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.pool import ParserPool, RendererPool
from bengal.rendering.parsers.patitas.request_context import (
    RequestContext,
    RequestContextError,
    get_request_context,
    request_context,
    reset_request_context,
    set_request_context,
    try_get_request_context,
)
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
from bengal.rendering.parsers.patitas.render_config import (
    RenderConfig,
    get_render_config,
    render_config_context,
    reset_render_config,
    set_render_config,
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
    # Configuration (ContextVar pattern)
    "ParseConfig",
    "get_parse_config",
    "set_parse_config",
    "reset_parse_config",
    "parse_config_context",
    "RenderConfig",
    "get_render_config",
    "set_render_config",
    "reset_render_config",
    "render_config_context",
    # Metadata Accumulator (RFC: rfc-contextvar-downstream-patterns)
    "RenderMetadata",
    "get_metadata",
    "set_metadata",
    "reset_metadata",
    "metadata_context",
    # Request Context (RFC: rfc-contextvar-downstream-patterns)
    "RequestContext",
    "RequestContextError",
    "get_request_context",
    "try_get_request_context",
    "set_request_context",
    "reset_request_context",
    "request_context",
    # Instance Pooling (RFC: rfc-contextvar-downstream-patterns)
    "ParserPool",
    "RendererPool",
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
    """Parse Markdown source into typed AST blocks.

    Uses ContextVar pattern for configuration. Plugins are set via ParseConfig.
    """
    from .parser import Parser

    # Build config from plugins
    config = ParseConfig(
        tables_enabled="table" in (plugins or []),
        strikethrough_enabled="strikethrough" in (plugins or []),
        task_lists_enabled="task_lists" in (plugins or []),
        footnotes_enabled="footnotes" in (plugins or []),
        math_enabled="math" in (plugins or []),
        autolinks_enabled="autolinks" in (plugins or []),
        text_transformer=text_transformer,
    )

    # Set config and parse
    parse_token = set_parse_config(config)
    try:
        parser = Parser(source, source_file)
        return parser.parse()
    finally:
        reset_parse_config(parse_token)


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

    Uses ContextVar pattern for configuration.

    Note: The 'source' buffer is required because Patitas uses a Zero-Copy Lexer Handoff (ZCLH)
    where AST nodes like FencedCode store source offsets rather than content strings.

    """
    if source is None:
        raise TypeError(
            "render_ast() requires the 'source' buffer for Zero-Copy extraction. "
            "See rfc-zero-copy-lexer-handoff.md for details."
        )

    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

    # Build config
    config = RenderConfig(
        highlight=highlight,
        highlight_style=highlight_style,  # type: ignore[arg-type]
        text_transformer=text_transformer,
    )

    # Set config and render
    render_token = set_render_config(config)
    try:
        renderer = HtmlRenderer(source, delegate=delegate)
        return renderer.render(ast)
    finally:
        reset_render_config(render_token)


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
    independent parser/renderer instances using ContextVar configuration.

    Uses ContextVar pattern (RFC: rfc-contextvar-config-implementation) for
    thread-safe configuration. Parse and render configs are set before
    creating parser/renderer instances, then restored after.

    """

    __slots__ = (
        "_plugins",
        "_plugins_enabled",
        "_delegate",
        # Pre-built immutable configs (reused for all parses)
        "_parse_config",
        "_render_config",
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

        directive_registry = create_default_registry()
        role_registry = create_default_role_registry()

        # Build immutable configs once (reused for all parses)
        # text_transformer is set per-call, so we use None here as base
        self._parse_config = ParseConfig(
            tables_enabled="table" in self._plugins_enabled,
            strikethrough_enabled="strikethrough" in self._plugins_enabled,
            task_lists_enabled="task_lists" in self._plugins_enabled,
            footnotes_enabled="footnotes" in self._plugins_enabled,
            math_enabled="math" in self._plugins_enabled,
            autolinks_enabled="autolinks" in self._plugins_enabled,
            directive_registry=directive_registry,
        )

        self._render_config = RenderConfig(
            highlight=highlight,
            highlight_style=highlight_style,  # type: ignore[arg-type]
            directive_registry=directive_registry,
            role_registry=role_registry,
        )

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

    def _get_parse_config(
        self, text_transformer: Callable[[str], str] | None = None
    ) -> ParseConfig:
        """Get parse config, optionally with text_transformer override."""
        if text_transformer is None:
            return self._parse_config
        # Create new config with text_transformer (frozen dataclass, so we rebuild)
        from dataclasses import replace

        return replace(self._parse_config, text_transformer=text_transformer)

    def _get_render_config(
        self, text_transformer: Callable[[str], str] | None = None
    ) -> RenderConfig:
        """Get render config, optionally with text_transformer override."""
        if text_transformer is None:
            return self._render_config
        # Create new config with text_transformer (frozen dataclass, so we rebuild)
        from dataclasses import replace

        return replace(self._render_config, text_transformer=text_transformer)

    def _parse_to_ast(
        self, source: str, text_transformer: Callable[[str], str] | None = None
    ) -> Sequence[Block]:
        """Parse source to AST with plugins applied.

        Uses ContextVar pattern - sets config before creating parser.
        """
        from bengal.rendering.parsers.patitas.parser import Parser

        config = self._get_parse_config(text_transformer)
        parse_token = set_parse_config(config)
        try:
            parser = Parser(source)
            return parser.parse()
        finally:
            reset_parse_config(parse_token)

    def _render_ast(
        self,
        ast: Sequence[Block],
        source: str,
        text_transformer: Callable[[str], str] | None = None,
        page_context: Any | None = None,
    ) -> str:
        """Render AST with configured options.

        Uses ContextVar pattern - sets config before creating renderer.

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

        config = self._get_render_config(text_transformer)
        render_token = set_render_config(config)
        try:
            renderer = HtmlRenderer(
                source,
                delegate=self._delegate,
                directive_cache=directive_cache if cache_enabled else None,
                page_context=page_context,
            )
            return renderer.render(ast)
        finally:
            reset_render_config(render_token)

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

        Uses ContextVar pattern - sets config before creating renderer.
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

        config = self._get_render_config(text_transformer)
        render_token = set_render_config(config)
        try:
            renderer = HtmlRenderer(
                source,
                delegate=self._delegate,
                directive_cache=directive_cache if cache_enabled else None,
                page_context=page_context,
            )

            # Render HTML - headings collected during this walk
            html = renderer.render(ast)

            # Get TOC data from renderer (no extra pass!)
            toc_html = renderer.get_toc_html()
            toc_items = renderer.get_toc_items()

            return html, toc_html, toc_items
        finally:
            reset_render_config(render_token)

    @property
    def plugins(self) -> frozenset[str]:
        """Get enabled plugins."""
        return self._plugins_enabled
