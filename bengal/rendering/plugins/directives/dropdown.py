"""
Dropdown directive for Mistune.

Provides collapsible sections with markdown support including
nested directives and code blocks.
"""

from __future__ import annotations

from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = ["DropdownDirective", "render_dropdown"]

logger = get_logger(__name__)


class DropdownDirective(DirectivePlugin):
    """
    Collapsible dropdown directive with markdown support.

    Syntax:
        ````{dropdown} Title
        :open: true

        Content with **markdown**, code blocks, etc.

        !!! note
            Even nested admonitions work!
        ````
    """

    # Directive names this class registers (for health check introspection)
    # "details" is an alias for compatibility
    DIRECTIVE_NAMES = ["dropdown", "details"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """Parse dropdown directive with nested content support."""
        title = self.parse_title(m)
        if not title:
            title = "Details"

        options = dict(self.parse_options(m))
        content = self.parse_content(m)

        # Parse nested markdown content
        children = self.parse_tokens(block, content, state)

        return {"type": "dropdown", "attrs": {"title": title, **options}, "children": children}

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive and renderer."""
        directive.register("dropdown", self.parse)
        directive.register("details", self.parse)  # Alias

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("dropdown", render_dropdown)


def render_dropdown(renderer: Any, text: str, **attrs: Any) -> str:
    """Render dropdown to HTML."""
    title = attrs.get("title", "Details")
    is_open = attrs.get("open", "").lower() in ("true", "1", "yes")
    open_attr = " open" if is_open else ""

    html = (
        f'<details class="dropdown"{open_attr}>\n'
        f"  <summary>{title}</summary>\n"
        f'  <div class="dropdown-content">\n'
        f"{text}"
        f"  </div>\n"
        f"</details>\n"
    )
    return html
