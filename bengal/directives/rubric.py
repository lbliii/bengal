"""
Rubric directive for Mistune.

Provides styled text that looks like a heading but isn't part of the
document hierarchy or table of contents. Perfect for API documentation
section labels like "Parameters:", "Returns:", "Raises:", etc.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = ["RubricDirective", "RubricOptions"]


@dataclass
class RubricOptions(DirectiveOptions):
    """
    Options for rubric directive.

    Attributes:
        css_class: Additional CSS classes

    Example:
        :::{rubric} Parameters
        :class: rubric-parameters
        :::
    """

    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class RubricDirective(BengalDirective):
    """
    Rubric directive for pseudo-headings.

    Syntax:
        :::{rubric} Parameters
        :class: rubric-parameters
        :::

    Creates styled text that looks like a heading but doesn't appear in TOC.
    The rubric renders immediately with no content inside - any content is ignored.

    Use cases:
        - API documentation section labels (Parameters, Returns, Raises)
        - Section dividers that shouldn't be in navigation
        - Styled labels without heading semantics
    """

    NAMES: ClassVar[list[str]] = ["rubric"]
    TOKEN_TYPE: ClassVar[str] = "rubric"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = RubricOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["rubric"]

    def parse_directive(
        self,
        title: str,
        options: RubricOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build rubric token from parsed components.

        Rubrics are label-only - children are always empty.
        """
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title or "",
                "css_class": options.css_class,
            },
            children=[],  # Rubrics never have children
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render rubric to HTML.

        Renders as a styled div with role="heading" for accessibility.
        Uses aria-level="5" to not interfere with document outline.
        """
        title = attrs.get("title", "")
        css_class = attrs.get("css_class", "")

        # Build class list
        class_str = self.build_class_string("rubric", css_class)

        return (
            f'<div class="{class_str}" role="heading" aria-level="5">'
            f"{self.escape_html(title)}</div>\n"
        )


# Backward compatibility
