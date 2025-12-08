"""
Container directive for Mistune.

Provides a generic wrapper div with custom CSS classes.
Similar to Sphinx/MyST container directive.

Use cases:
- Wrapping content with semantic styling (api-attributes, api-signatures)
- Creating styled blocks without affecting heading hierarchy
- Grouping related content with a common class
"""

from __future__ import annotations

from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

__all__ = ["ContainerDirective", "render_container"]


class ContainerDirective(DirectivePlugin):
    """
    Container directive for wrapping content in a styled div.

    Syntax:
        :::{container} class-name
        Content goes here...
        :::

        :::{container} api-attributes
        `attr1`
        : Description of attr1

        `attr2`
        : Description of attr2
        :::

    Multiple classes:
        :::{container} api-section highlighted
        Content with multiple classes...
        :::

    The first line after the directive is the class(es) to apply.
    Content is parsed as markdown.
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["container", "div"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """Parse container directive."""
        # Get the class name(s) from the title position
        title = self.parse_title(m) or ""
        classes = title.strip()

        # Parse options (e.g., :class: additional-class)
        options = dict(self.parse_options(m))

        # Merge title classes with :class: option
        if options.get("class"):
            if classes:
                classes = f"{classes} {options['class']}"
            else:
                classes = options["class"]

        # Parse the body content as markdown
        children = self.parse_tokens(block, m, state)

        return {
            "type": "container",
            "attrs": {
                "class": classes,
            },
            "children": children,
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive and renderer."""
        directive.register("container", self.parse)
        directive.register("div", self.parse)  # Alias for convenience

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("container", render_container)


def render_container(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render container to HTML.

    Renders as a div with the specified classes, containing
    the parsed markdown content.

    Args:
        renderer: Mistune renderer
        text: Rendered children content
        **attrs: Directive attributes (class, etc.)
    """
    css_class = attrs.get("class", "").strip()

    if css_class:
        return f'<div class="{css_class}">\n{text}</div>\n'
    else:
        return f"<div>\n{text}</div>\n"

