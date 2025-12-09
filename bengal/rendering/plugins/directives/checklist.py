"""
Checklist directive for Mistune.

Provides styled checklist containers for bullet lists and task lists
with optional titles and custom styling.

Architecture:
    Migrated to BengalDirective base class as part of directive system v2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken

__all__ = ["ChecklistDirective", "ChecklistOptions"]


@dataclass
class ChecklistOptions(DirectiveOptions):
    """Options for checklist directive (currently none)."""

    pass


class ChecklistDirective(BengalDirective):
    """
    Checklist directive using Mistune's fenced syntax.

    Syntax:
        :::{checklist} Optional Title
        - Item one
        - Item two
        - [x] Completed item
        - [ ] Unchecked item
        :::

    Supports both regular bullet lists and task lists (checkboxes).
    The directive wraps the list in a styled container.
    """

    NAMES: ClassVar[list[str]] = ["checklist"]
    TOKEN_TYPE: ClassVar[str] = "checklist"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = ChecklistOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["checklist"]

    def parse_directive(
        self,
        title: str,
        options: ChecklistOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build checklist token."""
        attrs = {}
        if title:
            attrs["title"] = title

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs=attrs,
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render checklist to HTML."""
        title = attrs.get("title", "")

        parts = ['<div class="checklist">\n']

        if title:
            parts.append(f'  <p class="checklist-title">{self.escape_html(title)}</p>\n')

        parts.append('  <div class="checklist-content">\n')
        parts.append(f"{text}")
        parts.append("  </div>\n")
        parts.append("</div>\n")

        return "".join(parts)


# Backward compatibility
def render_checklist(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return ChecklistDirective().render(renderer, text, **attrs)
