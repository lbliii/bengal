"""Plugin system for Patitas Markdown parser.

Plugins extend Patitas with additional syntax support:
- table: GFM-style pipe tables
- strikethrough: ~~deleted~~ syntax
- task_lists: - [ ] checkboxes (built into core, enabled by default)
- footnotes: [^1] references
- math: $inline$ and $$block$$ math
- autolinks: Automatic URL and email detection

Usage:
    >>> from bengal.rendering.parsers.patitas import create_markdown
    >>>
    >>> # Enable specific plugins
    >>> md = create_markdown(plugins=["table", "strikethrough", "math"])
    >>> html = md("| A | B |\\n|---|---|\\n| 1 | 2 |")
    >>>
    >>> # Enable all plugins
    >>> md = create_markdown(plugins=["all"])

Plugin Architecture:
    Unlike mistune's regex-based plugins, Patitas uses a state-machine lexer.
    Plugins hook into specific extension points:

    1. Inline plugins (strikethrough, math inline):
       - Registered with the inline parser
       - Called when special characters are encountered

    2. Block plugins (table, math block, footnote definitions):
       - Registered with the block scanner
       - Called at line start when block patterns match

    3. Post-processing plugins (footnotes, autolinks):
       - Transform AST or rendered output
       - Called after main parsing/rendering

Thread Safety:
    All plugins are stateless. State is stored in AST nodes or passed as arguments.
    Multiple threads can use the same plugin instances concurrently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.lexer import Lexer
    from bengal.rendering.parsers.patitas.parser import Parser
    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

__all__ = [
    "PatitasPlugin",
    "BUILTIN_PLUGINS",
    "get_plugin",
    "apply_plugins",
]


@runtime_checkable
class PatitasPlugin(Protocol):
    """Protocol for Patitas plugins.

    Plugins can hook into multiple extension points:
    - extend_lexer: Add token types and scanning logic
    - extend_parser: Add parsing rules for new tokens
    - extend_renderer: Add rendering methods for new nodes

    Thread Safety:
        Plugins must be stateless. All state should be in AST nodes.
    """

    @property
    def name(self) -> str:
        """Plugin identifier."""
        ...

    def extend_lexer(self, lexer_class: type[Lexer]) -> None:
        """Extend lexer with additional token scanning.

        Called once at parser configuration time.
        Should add methods or modify class behavior.
        """
        ...

    def extend_parser(self, parser_class: type[Parser]) -> None:
        """Extend parser with additional parsing rules.

        Called once at parser configuration time.
        Should add methods or modify class behavior.
        """
        ...

    def extend_renderer(self, renderer_class: type[HtmlRenderer]) -> None:
        """Extend renderer with additional render methods.

        Called once at parser configuration time.
        Should add methods for new node types.
        """
        ...


# Registry of built-in plugins
BUILTIN_PLUGINS: dict[str, type[PatitasPlugin]] = {}


def register_plugin(name: str) -> type[PatitasPlugin]:
    """Decorator to register a plugin.

    Args:
        name: Plugin name for lookup

    Returns:
        The decorated class

    Usage:
        @register_plugin("table")
        class TablePlugin:
            ...
    """

    def decorator(cls: type[PatitasPlugin]) -> type[PatitasPlugin]:
        BUILTIN_PLUGINS[name] = cls
        return cls

    return decorator


def get_plugin(name: str) -> PatitasPlugin:
    """Get a plugin instance by name.

    Args:
        name: Plugin name (e.g., "table", "strikethrough")

    Returns:
        Plugin instance

    Raises:
        KeyError: If plugin name is not recognized
    """
    if name not in BUILTIN_PLUGINS:
        available = ", ".join(sorted(BUILTIN_PLUGINS.keys()))
        raise KeyError(f"Unknown plugin: {name!r}. Available: {available}")
    return BUILTIN_PLUGINS[name]()


def apply_plugins(
    plugins: list[str],
    lexer_class: type[Lexer],
    parser_class: type[Parser],
    renderer_class: type[HtmlRenderer],
) -> None:
    """Apply plugins to parser components.

    Args:
        plugins: List of plugin names to apply
        lexer_class: Lexer class to extend
        parser_class: Parser class to extend
        renderer_class: Renderer class to extend
    """
    for plugin_name in plugins:
        if plugin_name == "all":
            # Apply all plugins
            for name in BUILTIN_PLUGINS:
                plugin = get_plugin(name)
                plugin.extend_lexer(lexer_class)
                plugin.extend_parser(parser_class)
                plugin.extend_renderer(renderer_class)
            break
        else:
            plugin = get_plugin(plugin_name)
            plugin.extend_lexer(lexer_class)
            plugin.extend_parser(parser_class)
            plugin.extend_renderer(renderer_class)


# Import built-in plugins to register them
# These imports trigger the @register_plugin decorators
from bengal.rendering.parsers.patitas.plugins.autolinks import AutolinksPlugin
from bengal.rendering.parsers.patitas.plugins.footnotes import FootnotesPlugin
from bengal.rendering.parsers.patitas.plugins.math import MathPlugin
from bengal.rendering.parsers.patitas.plugins.strikethrough import StrikethroughPlugin
from bengal.rendering.parsers.patitas.plugins.table import TablePlugin
from bengal.rendering.parsers.patitas.plugins.task_lists import TaskListPlugin

__all__ += [
    "StrikethroughPlugin",
    "TablePlugin",
    "MathPlugin",
    "TaskListPlugin",
    "FootnotesPlugin",
    "AutolinksPlugin",
]
