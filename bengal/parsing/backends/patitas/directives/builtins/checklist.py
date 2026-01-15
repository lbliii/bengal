"""Checklist directive for styled lists with progress tracking.

Provides:
- checklist: Styled container for bullet/task lists

Use cases:
- Prerequisites checklists
- Progress tracking with checkboxes
- Numbered step lists

Example:
:::{checklist} Prerequisites
:style: numbered
:show-progress:
- [x] Python 3.14+
- [x] Bengal installed
- [ ] Git configured
:::

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's checklist directive exactly for parity.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract
from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder


__all__ = ["ChecklistDirective"]


# =============================================================================
# Typed Options
# =============================================================================


@dataclass(frozen=True, slots=True)
class ChecklistOptions(DirectiveOptions):
    """
    Typed options for checklist directive.
    
    Attributes:
        style: Visual style (default, numbered, minimal)
        show_progress: Display completion percentage for task lists
        compact: Tighter spacing between items
        css_class: Additional CSS classes
        
    """

    style: str = "default"
    show_progress: bool = False
    compact: bool = False
    css_class: str = ""


# =============================================================================
# Checklist Directive Handler
# =============================================================================


class ChecklistDirective:
    """
    Checklist directive for styled lists with progress tracking.
    
    Syntax:
        :::{checklist} Optional Title
        :style: numbered
        :show-progress:
        :compact:
        - Item one
        - Item two
        - [x] Completed item
        - [ ] Unchecked item
        :::
    
    Options:
        :style: Visual style
            - default: Standard bullet list styling
            - numbered: Ordered list with numbers
            - minimal: Minimal styling
        :show-progress: Show completion bar for task lists
        :compact: Tighter spacing between items
        :class: Additional CSS classes
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("checklist",)
    token_type: ClassVar[str] = "checklist"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ChecklistOptions]] = ChecklistOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: ChecklistOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build checklist AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[ChecklistOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render checklist to HTML."""
        opts = node.options  # Direct typed access!

        title = node.title or ""
        style = opts.style
        show_progress = opts.show_progress
        compact = opts.compact
        css_class = opts.css_class

        # Build class list
        classes = ["checklist"]
        if style and style != "default":
            classes.append(f"checklist-{style}")
        if compact:
            classes.append("checklist-compact")
        if css_class:
            classes.append(css_class)

        # Check if content has task list checkboxes
        has_checkboxes = 'type="checkbox"' in rendered_children

        # Add class for task list styling
        if has_checkboxes:
            classes.append("checklist-has-tasks")

        class_str = " ".join(classes)

        # Make checkboxes interactive by removing disabled attribute
        content = rendered_children
        if has_checkboxes:
            content = self._make_checkboxes_interactive(content)

        sb.append(f'<div class="{class_str}">\n')

        # Header row: title + progress (inline)
        has_header = title or (show_progress and has_checkboxes)
        if has_header:
            sb.append('  <div class="checklist-header">\n')
            if title:
                sb.append(f'    <p class="checklist-title">{html_escape(title)}</p>\n')
            if show_progress and has_checkboxes:
                progress_html = self._render_progress_bar(content)
                if progress_html:
                    sb.append(progress_html)
            sb.append("  </div>\n")

        sb.append('  <div class="checklist-content">\n')
        sb.append(content)
        sb.append("  </div>\n")

        # Add JavaScript for interactive progress updates
        if show_progress and has_checkboxes:
            sb.append(self._render_progress_script())

        sb.append("</div>\n")

    def _make_checkboxes_interactive(self, html_content: str) -> str:
        """Remove 'disabled' attribute from checkboxes to allow interaction."""
        return re.sub(
            r'(<input[^>]*type="checkbox"[^>]*)\s+disabled(?:="")?([^>]*>)',
            r"\1\2",
            html_content,
        )

    def _render_progress_script(self) -> str:
        """Render JavaScript for interactive progress bar updates."""
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
        """Calculate and render progress bar from checkbox states."""
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
