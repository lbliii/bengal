"""
Quick Action Widget.

Grid action item for the landing screen.
Displays an emoji, title, and description with hover/focus styling.

Usage:
    from bengal.cli.dashboard.widgets import QuickAction

    action = QuickAction("🔨", "Build Site", "Run a full site build")
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Static


class QuickAction(Static, can_focus=True):
    """
    Quick action grid item for landing screen.

    Displays an emoji icon, title, and description.
    Emits Selected message when clicked or activated.

    Attributes:
        emoji: Icon emoji to display
        title: Action title (e.g., "Build Site")
        description: Short description of the action

    Example:
        action = QuickAction(
            "🔨",
            "Build Site",
            "Run a full site build",
            id="action-build"
        )
    """

    DEFAULT_CSS = """
    QuickAction {
        width: 1fr;
        height: auto;
        min-height: 4;
        padding: 1 2;
        background: $surface;
        border: solid $secondary;
    }
    QuickAction:hover {
        background: $surface-lighten-2;
        border: solid $primary;
    }
    QuickAction:focus {
        background: $surface-lighten-2;
        border: solid $primary;
    }
    QuickAction .quick-action-emoji {
        text-style: bold;
        width: 4;
        height: 100%;
        content-align: center middle;
    }
    QuickAction .quick-action-content {
        width: 1fr;
    }
    QuickAction .quick-action-title {
        text-style: bold;
        color: $primary;
    }
    QuickAction .quick-action-description {
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("enter", "select", "Select"),
        ("space", "select", "Select"),
    ]

    class Selected(Message):
        """Message emitted when action is selected."""

        def __init__(self, action: QuickAction) -> None:
            """Initialize with the selected action."""
            self.action = action
            super().__init__()

        @property
        def action_id(self) -> str | None:
            """Get the action's widget ID."""
            return self.action.id

    def __init__(
        self,
        emoji: str,
        title: str,
        description: str,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initialize quick action.

        Args:
            emoji: Icon emoji to display
            title: Action title
            description: Short description
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.emoji = emoji
        self.action_title = title
        self.description = description

    def compose(self) -> ComposeResult:
        """Compose the action layout."""
        with Horizontal():
            yield Static(self.emoji, classes="quick-action-emoji")
            with Vertical(classes="quick-action-content"):
                yield Static(self.action_title, classes="quick-action-title")
                yield Static(self.description, classes="quick-action-description")

    def action_select(self) -> None:
        """Handle selection action."""
        self.post_message(self.Selected(self))

    def on_click(self) -> None:
        """Handle click event."""
        self.post_message(self.Selected(self))
