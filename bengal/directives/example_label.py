"""
Example label directive for Mistune.

Provides a lightweight semantic label for example sections - a "soft header"
that doesn't appear in TOC and is lighter weight than a full admonition callout.

Use cases:
    - Example sections in documentation
    - Code example labels
    - Demo/sample section headers

Syntax:
    :::{example-label} Basic Usage
    :::

    Content follows...

Renders as:
    <p class="example-label" role="heading" aria-level="6">
      <span class="example-label-prefix">Example:</span> Basic Usage
    </p>

Architecture:
    Similar to rubric but purpose-built for examples with semantic styling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = ["ExampleLabelDirective", "ExampleLabelOptions"]


@dataclass
class ExampleLabelOptions(DirectiveOptions):
    """
    Options for example-label directive.

    Attributes:
        css_class: Additional CSS classes
        prefix: Custom prefix text (default: "Example")
        no_prefix: If true, don't show the prefix

    Example:
        :::{example-label} Basic Usage
        :class: featured
        :::

        :::{example-label} API Call
        :prefix: Demo
        :::

        :::{example-label} Simple
        :no-prefix:
        :::
    """

    css_class: str = ""
    prefix: str = "Example"
    no_prefix: bool = False

    _field_aliases: ClassVar[dict[str, str]] = {
        "class": "css_class",
        "no-prefix": "no_prefix",
    }


class ExampleLabelDirective(BengalDirective):
    """
    Example label directive for lightweight example section headers.

    Syntax:
        :::{example-label} Title Text
        :::

    With options:
        :::{example-label} API Usage
        :prefix: Demo
        :class: featured
        :::

    Creates a semantic label that looks like a soft header but doesn't appear
    in TOC. Lighter weight than admonition callouts, perfect for example sections.

    Renders immediately with no content inside - any content is ignored.
    """

    NAMES: ClassVar[list[str]] = ["example-label"]
    TOKEN_TYPE: ClassVar[str] = "example_label"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = ExampleLabelOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["example-label"]

    def parse_directive(
        self,
        title: str,
        options: ExampleLabelOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build example label token from parsed components.

        Example labels are label-only - children are always empty.
        """
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title or "",
                "css_class": options.css_class,
                "prefix": options.prefix,
                "no_prefix": options.no_prefix,
            },
            children=[],  # Example labels never have children
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render example label to HTML.

        Renders as a styled paragraph with role="heading" for accessibility.
        Uses aria-level="6" to not interfere with document outline (lower than rubric's 5).
        """
        title = attrs.get("title", "")
        css_class = attrs.get("css_class", "")
        prefix = attrs.get("prefix", "Example")
        no_prefix = attrs.get("no_prefix", False)

        # Build class list
        class_str = self.build_class_string("example-label", css_class)

        # Build title with optional prefix
        if no_prefix or not title:
            # No prefix: just show the title (or prefix as title if no title)
            display_text = title if title else prefix
            title_html = self.escape_html(display_text)
        else:
            # With prefix: "Example: Title"
            title_html = (
                f'<span class="example-label-prefix">{self.escape_html(prefix)}:</span> '
                f"{self.escape_html(title)}"
            )

        return f'<p class="{class_str}" role="heading" aria-level="6">{title_html}</p>\n'
