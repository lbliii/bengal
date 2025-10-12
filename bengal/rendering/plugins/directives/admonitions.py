"""
Admonition directive for Mistune.

Provides note, warning, tip, danger, and other callout boxes with
full markdown support.
"""

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = ["AdmonitionDirective", "render_admonition"]

logger = get_logger(__name__)


class AdmonitionDirective(DirectivePlugin):
    """
    Admonition directive using Mistune's fenced syntax.

    Syntax:
        ```{note} Optional Title
        Content with **markdown** support.
        ```

    Supported types: note, tip, warning, danger, error, info, example, success, caution
    """

    ADMONITION_TYPES = [
        "note",
        "tip",
        "warning",
        "danger",
        "error",
        "info",
        "example",
        "success",
        "caution",
    ]

    def parse(self, block, m, state):
        """Parse admonition directive."""
        admon_type = self.parse_type(m)
        title = self.parse_title(m)

        # Use type as title if no title provided
        if not title:
            title = admon_type.capitalize()

        content = self.parse_content(m)

        # Parse nested markdown content
        children = self.parse_tokens(block, content, state)

        return {
            "type": "admonition",
            "attrs": {"admon_type": admon_type, "title": title},
            "children": children,
        }

    def __call__(self, directive, md):
        """Register all admonition types as directives."""
        for admon_type in self.ADMONITION_TYPES:
            directive.register(admon_type, self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("admonition", render_admonition)


def render_admonition(renderer, text: str, admon_type: str, title: str) -> str:
    """Render admonition to HTML."""
    # Map types to CSS classes
    type_map = {
        "note": "note",
        "tip": "tip",
        "warning": "warning",
        "caution": "warning",
        "danger": "danger",
        "error": "error",
        "info": "info",
        "example": "example",
        "success": "success",
    }

    css_class = type_map.get(admon_type, "note")

    # text contains the rendered children
    html = (
        f'<div class="admonition {css_class}">\n'
        f'  <p class="admonition-title">{title}</p>\n'
        f"{text}"
        f"</div>\n"
    )
    return html
