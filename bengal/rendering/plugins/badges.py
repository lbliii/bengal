"""
Badge plugin for Mistune.

Provides badge syntax: {bdg-color}`text`

Supports badge colors that map to Bengal's design system.
"""

from __future__ import annotations

import re
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["BadgePlugin"]


class BadgePlugin:
    """
    Mistune plugin for inline badge syntax.

    Syntax:
        {bdg-primary}`text`      -> Primary color badge
        {bdg-secondary}`text`    -> Secondary/muted badge
        {bdg-success}`text`      -> Success/green badge
        {bdg-danger}`text`       -> Danger/red badge
        {bdg-warning}`text`      -> Warning/yellow badge
        {bdg-info}`text`         -> Info/blue badge
        {bdg-light}`text`        -> Light badge
        {bdg-dark}`text`         -> Dark badge

    Maps to Bengal's CSS color system:
        bdg-primary   -> badge-primary (blue)
        bdg-secondary -> badge-secondary (gray)
        bdg-success   -> badge-success (green)
        bdg-danger    -> badge-danger (red)
        bdg-warning   -> badge-warning (yellow)
        bdg-info      -> badge-info (blue)
        bdg-light     -> badge-light (light gray)
        bdg-dark      -> badge-dark (dark gray)

    Compatibility: Full support for bdg-* roles.
    """

    # Badge color mapping (legacy -> Bengal CSS classes)
    COLOR_MAP = {
        "primary": "primary",
        "secondary": "secondary",
        "success": "success",
        "danger": "danger",
        "warning": "warning",
        "info": "info",
        "light": "light",
        "dark": "dark",
    }

    def __init__(self) -> None:
        """Initialize badge plugin."""
        # Compile regex patterns once (reused for all pages)

        # Pattern 1: Match after Mistune has converted to HTML
        # Mistune converts `text` to <code>text</code> BEFORE our plugin runs
        # So we need to match: {bdg-color}<code>text</code>
        self.html_pattern = re.compile(r"\{bdg-([a-z]+)\}<code>([^<]+)</code>")

        # Pattern 2: Fallback for any remaining raw patterns (shouldn't happen in practice)
        self.raw_pattern = re.compile(r"\{bdg-([a-z]+)\}`([^`]+)`")

    def __call__(self, md: Any) -> Any:
        """
        Register the plugin with Mistune.

        Badge substitution happens in parser.py after HTML is generated.
        This method is required for Mistune plugin interface but does nothing.
        """
        # Badge plugin doesn't modify mistune internals
        # It's called manually by MistuneParser after HTML generation
        return md

    def _substitute_badges(self, html: str) -> str:
        """
        Substitute {bdg-color}<code>text</code> patterns with badge HTML.

        Mistune converts `text` to <code>text</code> before our plugin runs,
        so we match the HTML pattern: {bdg-color}<code>text</code>

        Args:
            html: HTML content that may contain badge patterns

        Returns:
            HTML with badge patterns replaced by badge spans
        """
        # Quick rejection: most HTML doesn't have badge patterns
        if "{bdg-" not in html:
            return html

        def replace_html_badge(match: re.Match[str]) -> str:
            """Replace HTML badge pattern with badge span."""
            color = match.group(1)
            badge_text = match.group(2)

            # Map color to CSS class
            css_class = self.COLOR_MAP.get(color, "secondary")

            # Validate color
            if color not in self.COLOR_MAP:
                logger.debug(
                    "badge_unknown_color", color=color, text=badge_text, using_fallback="secondary"
                )

            # Note: badge_text is already HTML-escaped by Mistune's <code> renderer
            # So we don't need to escape it again
            return f'<span class="badge badge-{css_class}">{badge_text}</span>'

        def replace_raw_badge(match: re.Match[str]) -> str:
            """Replace raw badge pattern (fallback, shouldn't happen in practice)."""
            color = match.group(1)
            badge_text = match.group(2)

            css_class = self.COLOR_MAP.get(color, "secondary")

            # This text needs escaping since it's not from <code>
            return f'<span class="badge badge-{css_class}">{self._escape_html(badge_text)}</span>'

        # Replace HTML pattern first (most common)
        html = self.html_pattern.sub(replace_html_badge, html)

        # Replace any remaining raw patterns (fallback)
        html = self.raw_pattern.sub(replace_raw_badge, html)

        return html

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters in badge text.

        Args:
            text: Badge text to escape

        Returns:
            Escaped text
        """
        if not text:
            return ""

        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
