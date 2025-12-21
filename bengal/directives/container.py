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

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = ["ContainerDirective", "ContainerOptions"]


@dataclass
class ContainerOptions(DirectiveOptions):
    """
    Options for container directive.

    Attributes:
        css_class: Additional CSS classes (merged with title classes)

    Example:
        :::{container} api-section
        :class: highlighted
        Content
        :::
    """

    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class ContainerDirective(BengalDirective):
    """
    Container directive for wrapping content in a styled div.

    Syntax:
        :::{container} class-name
        Content goes here...
        :::

        :::{container} api-attributes
        `attr1`
        : Description of attr1
        :::

    Multiple classes:
        :::{container} api-section highlighted
        Content with multiple classes...
        :::

    The first line after the directive (title) is the class(es) to apply.
    Additional classes can be added via :class: option.
    Content is parsed as markdown.

    Aliases:
        - container: Primary name
        - div: HTML semantic alias
    """

    NAMES: ClassVar[list[str]] = ["container", "div"]
    TOKEN_TYPE: ClassVar[str] = "container"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = ContainerOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["container", "div"]

    def parse_directive(
        self,
        title: str,
        options: ContainerOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build container token from parsed components.

        The title is treated as class names. Additional classes from
        :class: option are merged.
        """
        # Title contains class name(s)
        classes = title.strip() if title else ""

        # Merge with :class: option
        if options.css_class:
            classes = f"{classes} {options.css_class}" if classes else options.css_class

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={"class": classes},
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render container to HTML.

        Renders as a div with the specified classes.
        """
        css_class = attrs.get("class", "").strip()

        if css_class:
            return f'<div class="{self.escape_html(css_class)}">\n{text}</div>\n'
        else:
            return f"<div>\n{text}</div>\n"


# Backward compatibility
