"""Admonition directive for callout boxes.

Supports standard admonition types:
    - note: General information
    - warning: Potential issues
    - tip: Helpful suggestions
    - important: Critical information
    - caution: Proceed carefully
    - attention: Pay attention
    - danger: Serious risk
    - error: Error conditions
    - hint: Subtle suggestions
    - seealso: Related information

Example:
    :::{note} Optional Title
    :class: custom-class
    :collapsible:

    This is the note content.
    :::
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import AdmonitionOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


# Standard admonition types and their default titles
ADMONITION_TYPES: dict[str, str] = {
    "note": "Note",
    "warning": "Warning",
    "tip": "Tip",
    "important": "Important",
    "caution": "Caution",
    "attention": "Attention",
    "danger": "Danger",
    "error": "Error",
    "hint": "Hint",
    "seealso": "See Also",
    "admonition": "Note",  # Generic admonition
}


class AdmonitionDirective:
    """Handler for admonition directives.

    Renders callout boxes for notes, warnings, tips, etc.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = tuple(ADMONITION_TYPES.keys())
    token_type: ClassVar[str] = "admonition"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[AdmonitionOptions]] = AdmonitionOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: AdmonitionOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build admonition AST node.

        Args:
            name: Admonition type (note, warning, etc.)
            title: Custom title (uses default if None)
            options: Typed admonition options
            content: Raw content (unused, prefer children)
            children: Parsed child blocks
            location: Source location

        Returns:
            Directive node for AST
        """
        # Use custom title or default for type
        effective_title = title or ADMONITION_TYPES.get(name, "Note")

        # Convert options to frozenset
        opts_dict = asdict(options)
        # Filter out None values and convert
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
        """Render admonition to HTML.

        Produces a <div class="admonition TYPE"> with optional collapsible
        behavior using <details>/<summary>.

        Args:
            node: Directive AST node
            rendered_children: Pre-rendered child content
            sb: StringBuilder for output
        """
        opts = dict(node.options)
        admon_type = node.name
        title = node.title or ADMONITION_TYPES.get(admon_type, "Note")

        # Check collapsible option
        collapsible = opts.get("collapsible", "").lower() in ("true", "1", "yes", "")
        if "collapsible" in opts and opts["collapsible"] == "":
            collapsible = True

        is_open = opts.get("open", "true").lower() in ("true", "1", "yes", "")

        # Build CSS classes
        classes = ["admonition", admon_type]
        if opts.get("class_"):
            classes.append(opts["class_"])

        class_str = " ".join(classes)

        if collapsible:
            # Use <details>/<summary> for collapsible
            open_attr = " open" if is_open else ""
            sb.append(f'<details class="{html_escape(class_str)}"{open_attr}>\n')
            sb.append(f'<summary class="admonition-title">{html_escape(title)}</summary>\n')
            sb.append(rendered_children)
            sb.append("</details>\n")
        else:
            # Standard div structure
            sb.append(f'<div class="{html_escape(class_str)}">\n')
            sb.append(f'<p class="admonition-title">{html_escape(title)}</p>\n')
            sb.append(rendered_children)
            sb.append("</div>\n")
