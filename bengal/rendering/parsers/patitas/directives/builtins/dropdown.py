"""Dropdown directive for collapsible content.

Example:
    :::{dropdown} Click to expand
    :open:

    Hidden content here.
    :::
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import (
    DROPDOWN_CONTRACT,
    DirectiveContract,
)
from bengal.rendering.parsers.patitas.directives.options import StyledOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DropdownOptions(StyledOptions):
    """Options for dropdown directive."""

    open: bool = False
    """Start expanded."""

    icon: str | None = None
    """Custom icon for toggle."""


class DropdownDirective:
    """Handler for dropdown (collapsible) directive.

    Renders collapsible content using <details>/<summary>.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("dropdown", "details")
    token_type: ClassVar[str] = "dropdown"
    contract: ClassVar[DirectiveContract | None] = DROPDOWN_CONTRACT
    options_class: ClassVar[type[DropdownOptions]] = DropdownOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: DropdownOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build dropdown AST node."""
        effective_title = title or "Details"

        opts_dict = asdict(options)
        opts_items = [(k, str(v)) for k, v in opts_dict.items() if v is not None]

        return Directive(
            location=location,
            name=name,
            title=effective_title,
            options=frozenset(opts_items),
            children=tuple(children),
        )

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render dropdown to HTML using details/summary."""
        opts = dict(node.options)
        title = node.title or "Details"

        is_open = opts.get("open", "").lower() in ("true", "1", "yes", "")

        # Build CSS classes
        classes = ["dropdown"]
        if opts.get("class_"):
            classes.append(opts["class_"])

        class_str = " ".join(classes)
        open_attr = " open" if is_open else ""

        sb.append(f'<details class="{html_escape(class_str)}"{open_attr}>\n')
        sb.append(f"<summary>{html_escape(title)}</summary>\n")
        sb.append('<div class="dropdown-content">\n')
        sb.append(rendered_children)
        sb.append("</div>\n")
        sb.append("</details>\n")
