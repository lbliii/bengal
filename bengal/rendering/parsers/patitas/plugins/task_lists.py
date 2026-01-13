"""Task list plugin for Patitas.

Adds support for checkbox task lists.

Usage:
    >>> md = create_markdown(plugins=["task_lists"])
    >>> md("- [ ] Unchecked\n- [x] Checked")
    '<ul><li class="task-list-item"><input type="checkbox" disabled> Unchecked</li>...'

Syntax:
- [ ] Unchecked task
- [x] Checked task
- [X] Also checked (uppercase)

Works with ordered lists too:
1. [ ] First task
2. [x] Second task

Notes:
- Checkboxes are rendered disabled by default
- The ListItem node has a `checked` field (True/False/None)
- Task list support is enabled by default in core parser

Thread Safety:
This plugin is stateless and thread-safe.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.plugins import register_plugin

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.lexer import Lexer
    from bengal.rendering.parsers.patitas.parser import Parser
    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer


@register_plugin("task_lists")
class TaskListPlugin:
    """Plugin for task list checkbox support.
    
    Task lists are partially built into the core parser via the
    ListItem.checked field. This plugin enables checkbox detection.
        
    """

    @property
    def name(self) -> str:
        return "task_lists"

    def extend_lexer(self, lexer_class: type[Lexer]) -> None:
        """Enable task list detection in lexer."""
        lexer_class._task_lists_enabled = True

    def extend_parser(self, parser_class: type[Parser]) -> None:
        """Enable task list parsing."""
        parser_class._task_lists_enabled = True

    def extend_renderer(self, renderer_class: type[HtmlRenderer]) -> None:
        """Task list rendering is handled in base renderer."""
        pass


# Task list parsing is integrated into list handling.
# See:
# - parser.py: _parse_list_item() checks for [ ] / [x] / [X]
# - nodes.py: ListItem has checked: bool | None field
# - html.py: _render_list_item() renders checkbox
