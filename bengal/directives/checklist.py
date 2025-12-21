"""
Checklist directive for Mistune.

Provides styled checklist containers for bullet lists and task lists
with optional titles and custom styling.


Syntax (preferred - named closers):
    :::{checklist} Prerequisites
    :style: numbered
    :show-progress:
    - [x] Python 3.14+
    - [x] Bengal installed
    - [ ] Git configured
    :::{/checklist}

Options:
    :style: - Visual style (default, numbered)
    :show-progress: - Display completion percentage for task lists
    :compact: - Tighter spacing for dense lists
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = ["ChecklistDirective", "ChecklistOptions"]

# Valid style options
VALID_STYLES = frozenset(["default", "numbered", "minimal"])


@dataclass
class ChecklistOptions(DirectiveOptions):
    """
    Options for checklist directive.

    Attributes:
        style: Visual style (default, numbered)
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

        # Check if content has task list checkboxes
        has_checkboxes = 'type="checkbox"' in text

        # Add class for task list styling (hides bullet arrows)
        if has_checkboxes:
            classes.append("checklist-has-tasks")

        class_str = " ".join(classes)

        # Remove 'disabled' attribute from checkboxes to make them interactive
        # Mistune's task_lists plugin adds disabled by default
        if has_checkboxes:
            text = self._make_checkboxes_interactive(text)

        parts = [f'<div class="{class_str}">\n']

        # Header row: title + progress (inline)
        has_header = title or (show_progress and has_checkboxes)
        if has_header:
            parts.append('  <div class="checklist-header">\n')
            if title:
                parts.append(f'    <p class="checklist-title">{self.escape_html(title)}</p>\n')
            if show_progress and has_checkboxes:
                progress_html = self._render_progress_bar(text)
                if progress_html:
                    parts.append(progress_html)
            parts.append("  </div>\n")

        parts.append('  <div class="checklist-content">\n')
        parts.append(f"{text}")
        parts.append("  </div>\n")

        # Add JavaScript for interactive progress updates if we have progress bar
        if show_progress and has_checkboxes:
            parts.append(self._render_progress_script())

        parts.append("</div>\n")

        return "".join(parts)

    def _make_checkboxes_interactive(self, html_content: str) -> str:
        """
        Remove 'disabled' attribute from checkboxes to allow interaction.

        Mistune's task_lists plugin adds 'disabled' by default. We remove it
        for checklist directives to enable interactive checklists.
        """
        # Remove disabled attribute from checkbox inputs
        # Pattern handles both 'disabled' and 'disabled=""' formats
        return re.sub(
            r'(<input[^>]*type="checkbox"[^>]*)\s+disabled(?:="")?([^>]*>)',
            r"\1\2",
            html_content,
        )

    def _render_progress_script(self) -> str:
        """
        Render JavaScript for interactive progress bar updates.

        When a checkbox is toggled, updates the progress bar and text.
        """
        return """  <script>
    (function() {
      const checklist = document.currentScript.closest('.checklist');
      if (!checklist) return;

      const progressBar = checklist.querySelector('.checklist-progress-bar');
      const progressText = checklist.querySelector('.checklist-progress-text');
      const checkboxes = checklist.querySelectorAll('input[type="checkbox"]');

      if (!progressBar || !progressText || !checkboxes.length) return;

      function updateProgress() {
        const total = checkboxes.length;
        const checked = Array.from(checkboxes).filter(cb => cb.checked).length;
        const percentage = Math.round((checked / total) * 100);

        progressBar.style.width = percentage + '%';
        progressText.textContent = checked + '/' + total;
      }

      checkboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', updateProgress);
      });
    })();
  </script>
"""

    def _render_progress_bar(self, html_content: str) -> str:
        """
        Calculate and render progress bar from checkbox states.

        Counts checked vs unchecked checkboxes in the rendered HTML.
        Returns empty string if no checkboxes found.
        """
        # Count checked and total checkboxes
        checked = len(re.findall(r"checked", html_content))
        total_checkboxes = len(re.findall(r'type="checkbox"', html_content))

        if total_checkboxes == 0:
            return ""

        percentage = int((checked / total_checkboxes) * 100)

        return (
            f'    <div class="checklist-progress">\n'
            f'      <span class="checklist-progress-text">{checked}/{total_checkboxes} complete</span>\n'
            f'      <div class="checklist-progress-track">\n'
            f'        <div class="checklist-progress-bar" style="width: {percentage}%"></div>\n'
            f"      </div>\n"
            f"    </div>\n"
        )


# Backward compatibility
