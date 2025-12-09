"""
Checklist directive for Mistune.

Provides styled checklist containers for bullet lists and task lists
with optional titles and custom styling.

Architecture:
    Migrated to BengalDirective base class as part of directive system v2.

Syntax (preferred - named closers):
    :::{checklist} Prerequisites
    :style: numbered
    :show-progress:
    - [x] Python 3.14+
    - [x] Bengal installed
    - [ ] Git configured
    :::{/checklist}

Options:
    :style: - Visual style (default, numbered, minimal)
    :show-progress: - Display completion percentage for task lists
    :compact: - Tighter spacing for dense lists
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken

__all__ = ["ChecklistDirective", "ChecklistOptions"]

# Valid style options
VALID_STYLES = frozenset(["default", "numbered", "minimal"])


@dataclass
class ChecklistOptions(DirectiveOptions):
    """
    Options for checklist directive.

    Attributes:
        style: Visual style (default, numbered, minimal)
        show_progress: Display completion percentage for task lists
        compact: Tighter spacing for dense lists
        css_class: Additional CSS classes

    Example:
        :::{checklist} Prerequisites
        :style: numbered
        :show-progress:
        :compact:
        - [x] Python 3.14+
        - [x] Bengal installed
        - [ ] Git configured
        :::{/checklist}
    """

    style: str = "default"
    show_progress: bool = False
    compact: bool = False
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "style": list(VALID_STYLES),
    }


class ChecklistDirective(BengalDirective):
    """
    Checklist directive using Mistune's fenced syntax.

    Syntax:
        :::{checklist} Optional Title
        :style: numbered
        :show-progress:
        :compact:
        - Item one
        - Item two
        - [x] Completed item
        - [ ] Unchecked item
        :::{/checklist}

    Options:
        :style: - Visual style
            - default: Standard bullet list styling
            - numbered: Ordered list with numbers
            - minimal: Reduced visual chrome
        :show-progress: - Show completion bar for task lists
        :compact: - Tighter spacing between items

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
        attrs: dict[str, Any] = {
            "style": options.style,
            "show_progress": options.show_progress,
            "compact": options.compact,
            "css_class": options.css_class,
        }
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
        style = attrs.get("style", "default")
        show_progress = attrs.get("show_progress", False)
        compact = attrs.get("compact", False)
        css_class = attrs.get("css_class", "")

        # Build class list
        classes = ["checklist"]
        if style and style != "default":
            classes.append(f"checklist-{style}")
        if compact:
            classes.append("checklist-compact")
        if css_class:
            classes.append(css_class)

        class_str = " ".join(classes)

        parts = [f'<div class="{class_str}">\n']

        # Title
        if title:
            parts.append(f'  <p class="checklist-title">{self.escape_html(title)}</p>\n')

        # Progress bar (if enabled and has checkboxes)
        if show_progress:
            progress_html = self._render_progress_bar(text)
            if progress_html:
                parts.append(progress_html)

        parts.append('  <div class="checklist-content">\n')
        parts.append(f"{text}")
        parts.append("  </div>\n")
        parts.append("</div>\n")

        return "".join(parts)

    def _render_progress_bar(self, html_content: str) -> str:
        """
        Calculate and render progress bar from checkbox states.

        Counts checked vs unchecked checkboxes in the rendered HTML.
        Returns empty string if no checkboxes found.
        """
        # Count checked and unchecked checkboxes
        checked_pattern = r'<input[^>]*type="checkbox"[^>]*checked[^>]*>'
        unchecked_pattern = r'<input[^>]*type="checkbox"[^>]*(?!checked)[^>]*>'

        # Simpler patterns that work better
        checked = len(re.findall(r'checked', html_content))
        total_checkboxes = len(re.findall(r'type="checkbox"', html_content))

        if total_checkboxes == 0:
            return ""

        percentage = int((checked / total_checkboxes) * 100)

        return (
            f'  <div class="checklist-progress">\n'
            f'    <div class="checklist-progress-bar" style="width: {percentage}%"></div>\n'
            f'    <span class="checklist-progress-text">{checked}/{total_checkboxes} complete</span>\n'
            f'  </div>\n'
        )


# Backward compatibility
def render_checklist(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return ChecklistDirective().render(renderer, text, **attrs)
