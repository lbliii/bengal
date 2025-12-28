"""Tab directives for tabbed content.

Example:
    :::{tab-set}

    :::{tab-item} Tab 1
    Content for tab 1.
    :::

    :::{tab-item} Tab 2
    :selected:

    Content for tab 2.
    :::

    :::
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import (
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    DirectiveContract,
)
from bengal.rendering.parsers.patitas.directives.options import TabItemOptions, TabSetOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


class TabSetDirective:
    """Handler for tab-set container directive.

    Contains tab-item children that form a tabbed interface.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("tab-set", "tabs")
    token_type: ClassVar[str] = "tab-set"
    contract: ClassVar[DirectiveContract | None] = TAB_SET_CONTRACT
    options_class: ClassVar[type[TabSetOptions]] = TabSetOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: TabSetOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build tab-set AST node."""
        opts_dict = asdict(options)
        opts_items = [(k, str(v)) for k, v in opts_dict.items() if v is not None]

        return Directive(
            location=location,
            name=name,
            title=title,
            options=frozenset(opts_items),
            children=tuple(children),
        )

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render tab-set to HTML.

        Creates a tabbed interface with radio button controls.
        """
        opts = dict(node.options)

        # Build CSS classes
        classes = ["tab-set"]
        if opts.get("class_"):
            classes.append(opts["class_"])

        class_str = " ".join(classes)

        # Get sync group for synchronized tabs
        sync_group = opts.get("sync_group", "")

        sb.append(f'<div class="{html_escape(class_str)}"')
        if sync_group:
            sb.append(f' data-sync-group="{html_escape(sync_group)}"')
        sb.append(">\n")

        # Render tab buttons
        sb.append('<div class="tab-set-labels" role="tablist">\n')

        # Extract tab items from children for labels
        tab_id = 0
        for child in node.children:
            if isinstance(child, Directive) and child.name in ("tab-item", "tab"):
                tab_label = child.title or f"Tab {tab_id + 1}"
                child_opts = dict(child.options)
                selected = child_opts.get("selected", "").lower() in ("true", "1", "yes", "")
                selected_attr = ' aria-selected="true"' if selected or tab_id == 0 else ""
                sb.append(
                    f'<button class="tab-label" role="tab"{selected_attr}>'
                    f"{html_escape(tab_label)}</button>\n"
                )
                tab_id += 1

        sb.append("</div>\n")

        # Render tab content
        sb.append('<div class="tab-set-content">\n')
        sb.append(rendered_children)
        sb.append("</div>\n")

        sb.append("</div>\n")


class TabItemDirective:
    """Handler for tab-item directive.

    Must be inside a tab-set container.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("tab-item", "tab")
    token_type: ClassVar[str] = "tab-item"
    contract: ClassVar[DirectiveContract | None] = TAB_ITEM_CONTRACT
    options_class: ClassVar[type[TabItemOptions]] = TabItemOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: TabItemOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build tab-item AST node."""
        opts_dict = asdict(options)
        opts_items = [(k, str(v)) for k, v in opts_dict.items() if v is not None]

        return Directive(
            location=location,
            name=name,
            title=title or "Tab",
            options=frozenset(opts_items),
            children=tuple(children),
        )

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render tab-item to HTML."""
        opts = dict(node.options)

        # Build CSS classes
        classes = ["tab-item"]
        if opts.get("class_"):
            classes.append(opts["class_"])

        selected = opts.get("selected", "").lower() in ("true", "1", "yes", "")
        if selected:
            classes.append("selected")

        class_str = " ".join(classes)

        sb.append(f'<div class="{html_escape(class_str)}" role="tabpanel">\n')
        sb.append(rendered_children)
        sb.append("</div>\n")
