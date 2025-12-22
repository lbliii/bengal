"""
Bengal Throbber Widget.

Animated loading indicator with Bengal color gradient, inspired by Toad's throbber.
Uses a gradient animation cycling through Bengal orange shades.

Usage:
    from bengal.cli.dashboard.widgets import BengalThrobber

    throbber = BengalThrobber()
    throbber.active = True  # Start animation
    throbber.active = False  # Hide and stop
"""

from __future__ import annotations

from time import monotonic

from rich.color import Color
from rich.segment import Segment
from rich.style import Style as RichStyle
from textual.reactive import reactive
from textual.strip import Strip
from textual.visual import Visual
from textual.widget import Widget

# Bengal color gradient (orange shades)
BENGAL_COLORS = [
    "#F28C28",  # Bengal orange (bright)
    "#E07020",
    "#C85A18",
    "#B04410",
    "#982E08",  # Bengal orange (dark)
    "#B04410",
    "#C85A18",
    "#E07020",
]


class Gradient:
    """Simple gradient helper for color interpolation."""

    def __init__(self, colors: list[Color]) -> None:
        """Initialize gradient with list of colors."""
        self.colors = colors

    @classmethod
    def from_colors(cls, *colors: Color) -> Gradient:
        """Create gradient from color objects."""
        return cls(list(colors))

    def get_rich_color(self, position: float) -> Color:
        """Get color at position (0.0-1.0) in gradient."""
        position = position % 1.0
        num_colors = len(self.colors)
        if num_colors == 0:
            return Color.parse("#FF9D00")
        if num_colors == 1:
            return self.colors[0]

        # Find which two colors to interpolate between
        scaled_pos = position * (num_colors - 1)
        idx1 = int(scaled_pos)
        idx2 = min(idx1 + 1, num_colors - 1)
        blend = scaled_pos - idx1

        c1 = self.colors[idx1]
        c2 = self.colors[idx2]

        # Get RGB triplets
        r1, g1, b1 = c1.triplet
        r2, g2, b2 = c2.triplet

        # Interpolate
        r = int(r1 + (r2 - r1) * blend)
        g = int(g1 + (g2 - g1) * blend)
        b = int(b1 + (b2 - b1) * blend)

        return Color.from_rgb(r, g, b)


class BengalThrobberVisual(Visual):
    """
    Visual renderer for the throbber animation.

    Renders a horizontal line with a cycling color gradient.
    """

    gradient = Gradient.from_colors(*[Color.parse(c) for c in BENGAL_COLORS])

    def render_strips(
        self,
        width: int,
        height: int,
        base_style: RichStyle,
        /,
    ) -> list[Strip]:
        """
        Render the throbber gradient animation.

        Args:
            width: Width in characters
            height: Height in characters
            base_style: Base style to apply

        Returns:
            List of Strip objects representing the visual
        """
        time = monotonic()
        bgcolor = base_style.bgcolor if base_style.bgcolor else None

        segments = [
            Segment(
                "━",
                RichStyle.from_color(
                    self.gradient.get_rich_color((offset / max(width, 1) - time) % 1.0),
                    bgcolor,
                ),
            )
            for offset in range(width)
        ]

        strips = [Strip(segments, width)]
        return strips


class BengalThrobber(Widget):
    """
    Animated build progress indicator with Bengal colors.

    Shows a cycling gradient animation when active, hidden otherwise.
    Uses 15 FPS animation for smooth visuals without excessive CPU usage.

    Attributes:
        active: When True, shows and animates. When False, hidden.

    Example:
        throbber = BengalThrobber(id="build-throbber")
        # Start animation
        throbber.active = True
        # Stop animation
        throbber.active = False
    """

    DEFAULT_CSS = """
    BengalThrobber {
        height: 1;
        width: 100%;
        visibility: hidden;
    }
    BengalThrobber.-active {
        visibility: visible;
    }
    """

    active: reactive[bool] = reactive(False)

    def on_mount(self) -> None:
        """Set up animation refresh rate when mounted."""
        self.auto_refresh = 1 / 15  # 15 FPS animation

    def watch_active(self, active: bool) -> None:
        """Update CSS class when active state changes."""
        self.set_class(active, "-active")

    def render(self) -> BengalThrobberVisual:
        """Render the throbber visual."""
        return BengalThrobberVisual()
