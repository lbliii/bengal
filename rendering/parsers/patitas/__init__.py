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
    >>> html = md("# Hello\\n\\n| A | B |\\n|---|---|\\n| 1 | 2 |")

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
    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

__all__ = [
    # Public API
    "parse",
    "parse_many",
    "parse_to_ast",
    "render_ast",
    "create_markdown",
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
    """Module-level getattr for free-threading declaration.

    Declares this module safe for free-threaded Python (PEP 703/779).
    The interpreter queries _Py_mod_gil to determine if the module
    needs the GIL.
    """
    if name == "_Py_mod_gil":
        # Signal: this module is safe for free-threading
        # 0 = Py_MOD_GIL_NOT_USED
        return 0
    raise AttributeError(f"module 'patitas' has no attribute {name!r}")


def parse(source: str, *, highlight: bool = False) -> str:
    """Parse Markdown source to HTML.

    Simple one-shot parsing function for common use cases.

    Args:
        source: Markdown source text
        highlight: Enable syntax highlighting for code blocks

    Returns:
        Rendered HTML string

    Examples:
        >>> parse("# Hello **World**")
        '<h1>Hello <strong>World</strong></h1>\\n'

        >>> parse("```python\\nprint('hi')\\n```", highlight=True)
        '<pre><code class="language-python">print(&#x27;hi&#x27;)</code></pre>\\n'

    Thread Safety:
        This function is fully thread-safe. Each call creates independent
        parser and renderer instances with no shared state.
    """
    ast = parse_to_ast(source)
    return render_ast(ast, highlight=highlight)


def parse_many(
    sources: Sequence[str],
    *,
    highlight: bool = False,
    workers: int | Literal["auto"] = "auto",
) -> list[str]:
    """Parse multiple Markdown documents in parallel.

    Leverages Python 3.14t free-threading for true parallel execution.
    Auto-tunes worker count based on document sizes and CPU cores.

    Args:
        sources: Sequence of Markdown source strings
        highlight: Enable syntax highlighting for code blocks
        workers: Number of parallel workers, or "auto" for optimal selection

    Returns:
        List of rendered HTML strings (order preserved)

    Examples:
        >>> docs = ["# Doc 1", "# Doc 2", "# Doc 3"]
        >>> htmls = parse_many(docs)
        >>> len(htmls)
        3

        >>> # With explicit workers
        >>> htmls = parse_many(docs, workers=4)

    Thread Safety:
        Fully thread-safe. Uses ThreadPoolExecutor for parallel execution.
        On Python 3.14t with GIL disabled, achieves true parallelism.

    Performance Notes:
        - Auto mode targets ~2x speedup (sweet spot for memory-bound parsing)
        - Small docs (<1KB): Sequential may be faster due to thread overhead
        - Large docs (>10KB): Benefits most from parallelism
    """
    n_docs = len(sources)

    # Fast path: single doc or empty
    if n_docs <= 1:
        return [parse(s, highlight=highlight) for s in sources]

    # Calculate total work
    total_chars = sum(len(s) for s in sources)
    avg_size = total_chars / n_docs

    # Determine optimal worker count
    if workers == "auto":
        # Fast path: skip parallelism for small workloads
        # Thread overhead (~1-2ms) only pays off for larger batches
        if total_chars < 5000:  # < 5KB total
            return [parse(s, highlight=highlight) for s in sources]

        # Heuristics for sweet spot:
        # - Cap at 4 workers (diminishing returns beyond this)
        # - Cap at n_docs (no point having more workers than docs)
        # - Cap at CPU count // 2 (leave headroom for system)
        cpu_count = os.cpu_count() or 4
        max_workers = min(4, n_docs, max(2, cpu_count // 2))

        # For small docs, reduce parallelism (overhead dominates)
        if avg_size < 1000:  # < 1KB average per doc
            max_workers = min(2, max_workers)
    else:
        max_workers = workers

    # Sequential fallback if only 1 worker
    if max_workers <= 1:
        return [parse(s, highlight=highlight) for s in sources]

    # Parallel execution
    def _parse_one(source: str) -> str:
        return parse(source, highlight=highlight)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_parse_one, sources))


def parse_to_ast(
    source: str, text_transformer: Callable[[str], str] | None = None
) -> Sequence[Block]:
    """Parse Markdown source to typed AST.

    Returns a sequence of typed Block nodes that can be inspected,
    transformed, or rendered.

    Args:
        source: Markdown source text
        text_transformer: Optional callback to transform plain text lines

    Returns:
        Sequence of Block AST nodes

    Examples:
        >>> ast = parse_to_ast("# Hello")
        >>> ast[0]
        Heading(level=1, children=(Text(content='Hello'),), style='atx', ...)

        >>> from dataclasses import asdict
        >>> asdict(ast[0])
        {'location': ..., 'level': 1, 'children': (...,), 'style': 'atx'}

    Thread Safety:
        Returns immutable AST (frozen dataclasses). Safe to share across threads.
    """
    from bengal.rendering.parsers.patitas.parser import Parser

    parser = Parser(source, text_transformer=text_transformer)
    return parser.parse()


def render_ast(
    ast: Sequence[Block],
    *,
    highlight: bool = False,
    highlight_style: str = "semantic",
    text_transformer: Callable[[str], str] | None = None,
) -> str:
    """Render AST nodes to HTML.

    Args:
        ast: Sequence of Block AST nodes from parse_to_ast()
        highlight: Enable syntax highlighting for code blocks
        highlight_style: Highlighting style ("semantic" or "pygments")
        text_transformer: Optional callback to transform plain text nodes

    Returns:
        Rendered HTML string

    Examples:
        >>> ast = parse_to_ast("# Hello **World**")
        >>> render_ast(ast)
        '<h1>Hello <strong>World</strong></h1>\\n'

    Thread Safety:
        Uses StringBuilder local to each call. Safe for concurrent use.
    """
    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

    renderer = HtmlRenderer(
        highlight=highlight,
        highlight_style=highlight_style,
        text_transformer=text_transformer,
    )
    return renderer.render(ast)


def create_markdown(
    *,
    plugins: list[str] | None = None,
    highlight: bool = True,
    highlight_style: str = "semantic",
) -> Markdown:
    """Create a configured Markdown parser/renderer.

    Factory function for creating reusable Markdown instances with
    specific configuration.

    Args:
        plugins: List of plugin names to enable (e.g., ["table", "footnotes"])
        highlight: Enable syntax highlighting for code blocks
        highlight_style: Highlighting style ("semantic" or "pygments")

    Returns:
        Markdown instance that can be called to parse/render content

    Examples:
        >>> md = create_markdown(plugins=["table"])
        >>> md("| A | B |\\n|---|---|\\n| 1 | 2 |")
        '<table>...'

    Thread Safety:
        The returned Markdown instance is thread-safe. Multiple threads
        can call the same instance concurrently.
    """
    return Markdown(
        plugins=plugins or [],
        highlight=highlight,
        highlight_style=highlight_style,
    )


class Markdown:
    """Configured Markdown parser/renderer.

    Thread-safe: can be shared across threads. Each __call__ creates
    independent parser/renderer instances.

    Plugins:
        Plugins are applied at construction time and modify the parser behavior:
        - "table": GFM-style pipe tables
        - "strikethrough": ~~deleted~~ syntax
        - "task_lists": - [ ] checkbox syntax
        - "footnotes": [^1] footnote references
        - "math": $inline$ and $$block$$ math
        - "autolinks": automatic URL and email detection
        - "all": enable all plugins
    """

    __slots__ = (
        "_plugins",
        "_highlight",
        "_highlight_style",
        "_plugins_enabled",
        "_directive_registry",
    )

    # Available plugins and their enabled flags
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
    ) -> None:
        self._plugins = tuple(plugins)  # Immutable
        self._highlight = highlight
        self._highlight_style = highlight_style

        # Determine which plugins are enabled
        if "all" in plugins:
            self._plugins_enabled = frozenset(self.AVAILABLE_PLUGINS)
        else:
            enabled = set()
            for plugin in plugins:
                if plugin in self.AVAILABLE_PLUGINS:
                    enabled.add(plugin)
                elif plugin != "all":
                    # Unknown plugin - warn but continue
                    import warnings

                    warnings.warn(
                        f"Unknown plugin: {plugin!r}. Available: {sorted(self.AVAILABLE_PLUGINS)}",
                        stacklevel=3,
                    )
            self._plugins_enabled = frozenset(enabled)

        # Create default directive registry with all builtins
        from bengal.rendering.parsers.patitas.directives.registry import (
            create_default_registry,
        )

        self._directive_registry = create_default_registry()

    def __call__(self, source: str, text_transformer: Callable[[str], str] | None = None) -> str:
        """Parse and render Markdown source to HTML.

        Args:
            source: Markdown source text
            text_transformer: Optional callback to transform plain text lines

        Returns:
            Rendered HTML string
        """
        ast = self._parse_to_ast(source, text_transformer=text_transformer)
        return self._render_ast(ast, text_transformer=text_transformer)

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

        # Apply plugin-specific flags
        parser._tables_enabled = "table" in self._plugins_enabled
        parser._strikethrough_enabled = "strikethrough" in self._plugins_enabled
        parser._task_lists_enabled = "task_lists" in self._plugins_enabled
        parser._footnotes_enabled = "footnotes" in self._plugins_enabled
        parser._math_enabled = "math" in self._plugins_enabled
        parser._autolinks_enabled = "autolinks" in self._plugins_enabled

        return parser.parse()

    def _render_ast(
        self, ast: Sequence[Block], text_transformer: Callable[[str], str] | None = None
    ) -> str:
        """Render AST with configured options."""
        from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

        renderer = HtmlRenderer(
            highlight=self._highlight,
            highlight_style=self._highlight_style,
            directive_registry=self._directive_registry,
            text_transformer=text_transformer,
        )
        return renderer.render(ast)

    def parse_to_ast(
        self, source: str, text_transformer: Callable[[str], str] | None = None
    ) -> Sequence[Block]:
        """Parse source to AST without rendering."""
        return self._parse_to_ast(source, text_transformer=text_transformer)

    def render_ast(
        self, ast: Sequence[Block], text_transformer: Callable[[str], str] | None = None
    ) -> str:
        """Render AST to HTML."""
        return self._render_ast(ast, text_transformer=text_transformer)

    @property
    def plugins(self) -> frozenset[str]:
        """Get enabled plugins."""
        return self._plugins_enabled
