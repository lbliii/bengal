"""
Build Flash Widget.

Inline notification widget for build status with auto-dismiss.
Inspired by Toad's Flash widget pattern.

Usage:
    from bengal.cli.dashboard.widgets import BuildFlash

    flash = BuildFlash()
    flash.show_building("Rendering pages")
    flash.show_success(1234)  # 1234ms
    flash.show_error("Template not found")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.reactive import var
from textual.timer import Timer
from textual.widgets import Static

if TYPE_CHECKING:
    pass


class BuildFlash(Static):
    """
    Inline build status notifications with auto-dismiss.

    Shows build phase, success, or error messages with appropriate styling.
    Success messages auto-dismiss after 5 seconds.

    CSS classes:
        -building: Active build phase (orange)
        -success: Build completed successfully (green)
        -error: Build failed (red)

    Example:
        flash = BuildFlash(id="build-flash")
        flash.show_building("Rendering")
        flash.show_success(1234)  # Shows "✓ Build complete in 1234ms"
        flash.show_error("Template error")
    """

    DEFAULT_CSS = """
    BuildFlash {
        height: 1;
        visibility: hidden;
        text-align: center;
    }
    BuildFlash.-building {
        visibility: visible;
        background: $primary 20%;
        color: $text-primary;
    }
    BuildFlash.-success {
        visibility: visible;
        background: $success 20%;
        color: $text-success;
    }
    BuildFlash.-error {
        visibility: visible;
        background: $error 20%;
        color: $text-error;
    }
    """

    flash_timer: var[Timer | None] = var(None)

    def show_building(self, phase: str) -> None:
        """
        Show build-in-progress message.

        Args:
            phase: Current build phase name (e.g., "Rendering", "Discovery")
        """
        self._cancel_timer()
        self.update(f"⏳ Building: {phase}...")
        self._apply_style("building")

    def show_success(self, duration_ms: int) -> None:
        """
        Show build success message with auto-dismiss.

        Args:
            duration_ms: Build duration in milliseconds
        """
        self._cancel_timer()
        self.update(f"✓ Build complete in {duration_ms}ms")
        self._apply_style("success")
        # Auto-dismiss after 5 seconds
        self.flash_timer = self.set_timer(5.0, self._hide)

    def show_error(self, message: str) -> None:
        """
        Show build error message.

        Args:
            message: Error message to display
        """
        self._cancel_timer()
        self.update(f"✗ {message}")
        self._apply_style("error")
        # Don't auto-dismiss errors - user needs to see them

    def hide(self) -> None:
        """Hide the flash message."""
        self._cancel_timer()
        self._hide()

    def _hide(self) -> None:
        """Internal hide implementation."""
        self.remove_class("-building", "-success", "-error")
        self.visible = False

    def _apply_style(self, style: str) -> None:
        """Apply style class and show widget."""
        self.remove_class("-building", "-success", "-error")
        self.add_class(f"-{style}")
        self.visible = True

    def _cancel_timer(self) -> None:
        """Cancel any pending auto-dismiss timer."""
        if self.flash_timer is not None:
            self.flash_timer.stop()
            self.flash_timer = None
