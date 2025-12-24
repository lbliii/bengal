"""
Child cards directive for auto-generating cards from section children.

Automatically generates cards from the current page's child sections and pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.cards.utils import (
    VALID_GAPS,
    VALID_LAYOUTS,
    VALID_STYLES,
    collect_children,
    render_child_card,
)
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["ChildCardsDirective", "ChildCardsOptions"]


@dataclass
class ChildCardsOptions(DirectiveOptions):
    """
    Options for child-cards directive.

    Attributes:
        columns: Column layout
        gap: Grid gap
        include: What to include (sections, pages, all)
        fields: Fields to pull (comma-separated)
        layout: Card layout
        style: Visual style
    """

    columns: str = "auto"
    gap: str = "medium"
    include: str = "all"
    fields: str = "title, description"
    layout: str = "default"
    style: str = "default"

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "gap": list(VALID_GAPS),
        "include": ["sections", "pages", "all"],
        "layout": list(VALID_LAYOUTS),
        "style": list(VALID_STYLES),
    }


class ChildCardsDirective(BengalDirective):
    """
    Auto-generate cards from current page's child sections/pages.

    Syntax:
        :::{child-cards}
        :columns: 3
        :include: sections
        :fields: title, description, icon
        :::
    """

    NAMES: ClassVar[list[str]] = ["child-cards"]
    TOKEN_TYPE: ClassVar[str] = "child_cards"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = ChildCardsOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["child-cards"]

    def parse_directive(
        self,
        title: str,
        options: ChildCardsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build child-cards token."""
        fields = [f.strip() for f in options.fields.split(",") if f.strip()]

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "columns": options.columns,
                "gap": options.gap,
                "include": options.include,
                "fields": fields,
                "layout": options.layout,
                "style": options.style,
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render child cards by walking the page object tree."""
        columns = attrs.get("columns", "auto")
        gap = attrs.get("gap", "medium")
        include = attrs.get("include", "all")
        fields = attrs.get("fields", ["title", "description"])
        layout = attrs.get("layout", "default")
        style = attrs.get("style", "default")

        no_content = '<div class="card-grid" data-columns="auto"><p><em>{}</em></p></div>'

        current_page = getattr(renderer, "_current_page", None)
        if not current_page:
            logger.debug("child_cards_no_current_page")
            return no_content.format("No page context available")

        section = getattr(current_page, "_section", None)
        if not section:
            logger.debug("child_cards_no_section", page=str(current_page.source_path))
            return no_content.format("Page has no section")

        children_items = collect_children(section, current_page, include)

        if not children_items:
            logger.debug("child_cards_no_children", page=str(current_page.source_path))
            return no_content.format("No child content found")

        # Generate card HTML
        cards_html = []
        for child in children_items:
            card_html = render_child_card(child, fields, layout, self.escape_html)
            cards_html.append(card_html)

        return (
            f'<div class="card-grid" '
            f'data-columns="{columns}" '
            f'data-gap="{gap}" '
            f'data-style="{style}" '
            f'data-variant="navigation" '
            f'data-layout="{layout}">\n'
            f"{''.join(cards_html)}"
            f"</div>\n"
        )
