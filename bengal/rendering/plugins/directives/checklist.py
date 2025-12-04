"""
Checklist directive for Mistune.

Provides styled checklist containers for bullet lists and task lists
with optional titles and custom styling.
"""

from __future__ import annotations

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = ["ChecklistDirective", "render_checklist"]

logger = get_logger(__name__)


class ChecklistDirective(DirectivePlugin):
    """
    Checklist directive using Mistune's fenced syntax.

    Syntax:
        ```{checklist} Optional Title
        - Item one
        - Item two
        - [x] Completed item
        - [ ] Unchecked item
        ```

    Supports both regular bullet lists and task lists (checkboxes).
    The directive wraps the list in a styled container for visual emphasis.
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["checklist"]

    def parse(self, block, m, state):
        """Parse checklist directive."""
        title = self.parse_title(m)
        content = self.parse_content(m)

        # Parse nested markdown content (will handle task lists automatically)
        children = self.parse_tokens(block, content, state)

        return {
            "type": "checklist",
            "attrs": {"title": title} if title else {},
            "children": children,
        }

    def __call__(self, directive, md):
        """Register the directive and renderer."""
        directive.register("checklist", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("checklist", render_checklist)


def render_checklist(renderer, text: str, **attrs) -> str:
    """Render checklist to HTML."""
    title = attrs.get("title", "")

    # Build HTML structure
    html_parts = ['<div class="checklist">\n']

    if title:
        html_parts.append(f'  <p class="checklist-title">{title}</p>\n')

    html_parts.append('  <div class="checklist-content">\n')
    html_parts.append(f"{text}")
    html_parts.append("  </div>\n")
    html_parts.append("</div>\n")

    return "".join(html_parts)
