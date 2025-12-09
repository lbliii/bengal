"""
Dropdown directive for Mistune.

Provides collapsible sections with markdown support including
nested directives and code blocks.

Architecture:
    Migrated to BengalDirective base class as part of directive system v2.
    Uses typed DropdownOptions and encapsulated render method.

Related:
    - bengal/rendering/plugins/directives/base.py: BengalDirective
    - RFC: plan/active/rfc-directive-system-v2.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken

__all__ = ["DropdownDirective", "DropdownOptions"]


@dataclass
class DropdownOptions(DirectiveOptions):
    """
    Options for dropdown directive.

    Attributes:
        open: Whether dropdown is initially open (expanded)
        css_class: Additional CSS classes for the container

    Example:
        :::{dropdown} My Title
        :open: true
        :class: my-custom-class

        Content here
        :::
    """

    open: bool = False
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class DropdownDirective(BengalDirective):
    """
    Collapsible dropdown directive with markdown support.

    Syntax:
        :::{dropdown} Title
        :open: true
        :class: custom-class

        Content with **markdown**, code blocks, etc.

        :::{note}
        Even nested admonitions work!
        :::
        :::

    Or using the HTML5 semantic alias:
        :::{details} Summary Text
        Content
        :::

    Aliases:
        - dropdown: Primary name
        - details: HTML5 semantic alias (renders as <details>)

    Options:
        :open: true/false - Whether initially expanded (default: false)
        :class: string - Additional CSS classes
    """

    # Directive names to register
    NAMES: ClassVar[list[str]] = ["dropdown", "details"]

    # Token type for AST
    TOKEN_TYPE: ClassVar[str] = "dropdown"

    # Typed options class
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DropdownOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["dropdown", "details"]

    def parse_directive(
        self,
        title: str,
        options: DropdownOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build dropdown token from parsed components.

        Args:
            title: Dropdown title (text after directive name)
            options: Typed dropdown options
            content: Raw content string (unused, children are already parsed)
            children: Parsed nested content tokens
            state: Parser state

        Returns:
            DirectiveToken for the dropdown
        """
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title or "Details",
                "open": options.open,
                "css_class": options.css_class,
            },
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render dropdown to HTML.

        Renders as HTML5 <details>/<summary> elements for native
        collapsible behavior without JavaScript.

        Args:
            renderer: Mistune renderer instance
            text: Pre-rendered children HTML
            **attrs: Token attributes (title, open, css_class)

        Returns:
            HTML string
        """
        title = attrs.get("title", "Details")
        is_open = attrs.get("open", False)
        css_class = attrs.get("css_class", "")

        # Build class string
        class_str = self.build_class_string("dropdown", css_class)

        # Escape title for safe HTML
        safe_title = self.escape_html(title)

        return (
            f'<details class="{class_str}"{self.bool_attr("open", is_open)}>\n'
            f"  <summary>{safe_title}</summary>\n"
            f'  <div class="dropdown-content">\n'
            f"{text}"
            f"  </div>\n"
            f"</details>\n"
        )


# =============================================================================
# Backward Compatibility
# =============================================================================
# Legacy render_dropdown function for any code that imported it directly.
# New code should use DropdownDirective.render() method.


def render_dropdown(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Legacy render function for backward compatibility.

    Deprecated: Use DropdownDirective class which encapsulates rendering.

    Args:
        renderer: Mistune renderer instance
        text: Pre-rendered children HTML
        **attrs: Token attributes

    Returns:
        HTML string
    """
    # Delegate to a static instance
    return DropdownDirective().render(renderer, text, **attrs)
