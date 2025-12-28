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

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.nodes import (
    Block,
    BlockQuote,
    CodeSpan,
    Document,
    Emphasis,
    FencedCode,
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
    Node,
    Paragraph,
    Strong,
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
    "parse_to_ast",
    "render_ast",
    "create_markdown",
    # Types
    "SourceLocation",
    "Token",
    "TokenType",
    "StringBuilder",
    # AST Nodes
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


def parse_to_ast(source: str) -> Sequence[Block]:
    """Parse Markdown source to typed AST.

    Returns a sequence of typed Block nodes that can be inspected,
    transformed, or rendered.

    Args:
        source: Markdown source text

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

    parser = Parser(source)
    return parser.parse()


def render_ast(
    ast: Sequence[Block],
    *,
    highlight: bool = False,
    highlight_style: str = "semantic",
) -> str:
    """Render AST nodes to HTML.

    Args:
        ast: Sequence of Block AST nodes from parse_to_ast()
        highlight: Enable syntax highlighting for code blocks
        highlight_style: Highlighting style ("semantic" or "pygments")

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

    renderer = HtmlRenderer(highlight=highlight, highlight_style=highlight_style)
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
    """

    __slots__ = ("_plugins", "_highlight", "_highlight_style")

    def __init__(
        self,
        plugins: list[str],
        highlight: bool,
        highlight_style: str,
    ) -> None:
        self._plugins = tuple(plugins)  # Immutable
        self._highlight = highlight
        self._highlight_style = highlight_style

    def __call__(self, source: str) -> str:
        """Parse and render Markdown source to HTML.

        Args:
            source: Markdown source text

        Returns:
            Rendered HTML string
        """
        ast = parse_to_ast(source)
        return render_ast(
            ast,
            highlight=self._highlight,
            highlight_style=self._highlight_style,
        )

    def parse_to_ast(self, source: str) -> Sequence[Block]:
        """Parse source to AST without rendering."""
        return parse_to_ast(source)

    def render_ast(self, ast: Sequence[Block]) -> str:
        """Render AST to HTML."""
        return render_ast(
            ast,
            highlight=self._highlight,
            highlight_style=self._highlight_style,
        )
