"""
Badge directive for Mistune.

Provides MyST-style badge directive: ```{badge} Text :class: badge-class```

Supports badge syntax with custom CSS classes.
"""

from __future__ import annotations

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["BadgeDirective", "render_badge"]


class BadgeDirective(DirectivePlugin):
    """
    Badge directive for MyST-style badges.

    Syntax:
        ```{badge} Command
        :class: badge-cli-command
        ```

        ```{badge} Deprecated
        :class: badge-danger
        ```

    The badge text is on the first line after the directive name.
    Optional `:class:` attribute can be used to specify CSS classes.
    If no class is specified, defaults to `badge badge-secondary`.

    MyST Compatibility:
        Full support for MyST badge directive syntax.
        Maps to Bengal's badge CSS classes.
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["badge", "bdg"]

    def parse(self, block, m, state):
        """
        Parse badge directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Dict with badge data for rendering
        """
        # Extract badge text (title)
        title = self.parse_title(m)
        if not title:
            logger.warning("badge_directive_empty", info="Badge directive has no text")
            title = ""

        # Parse options (e.g., :class: badge-cli-command)
        options = dict(self.parse_options(m))
        badge_class = options.get("class", "badge badge-secondary")

        # Ensure base "badge" class is always present
        # Handle cases like "badge-secondary", "badge-danger", "api-badge", etc.
        if badge_class:
            # Split into individual classes
            classes = badge_class.split()

            # Check if base "badge" or "api-badge" is already present
            has_base_badge = any(cls in ("badge", "api-badge") for cls in classes)

            if not has_base_badge:
                # Determine which base class to use based on existing classes
                if any(cls.startswith("api-badge") for cls in classes):
                    # API badges use api-badge as base
                    classes.insert(0, "api-badge")
                elif any(cls.startswith("badge-") for cls in classes):
                    # Standard badges use badge as base
                    classes.insert(0, "badge")
                else:
                    # Default to badge if unclear
                    classes.insert(0, "badge")

                badge_class = " ".join(classes)
        else:
            badge_class = "badge badge-secondary"

        return {
            "type": "badge",
            "attrs": {
                "label": title,  # Use 'label' instead of 'text' to avoid conflict with Mistune's text parameter
                "class": badge_class,
            },
            "children": [],  # Badges don't have children content
        }

    def __call__(self, directive, md):
        """
        Register badge directive with Mistune.

        Args:
            directive: FencedDirective instance
            md: Markdown instance
        """
        directive.register("badge", self.parse)
        directive.register("bdg", self.parse)  # Alias for compatibility

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("badge", render_badge)


def render_badge(renderer, text, **attrs) -> str:
    """
    Render badge directive to HTML.

    Args:
        renderer: Mistune renderer
        text: Rendered children content (unused for badges)
        **attrs: Directive attributes (label, class)

    Returns:
        HTML span element with badge classes
    """
    badge_text = attrs.get("label", "")
    badge_class = attrs.get("class", "badge badge-secondary")

    if not badge_text:
        return ""

    # Escape HTML in badge text
    escaped_text = (
        badge_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

    return f'<span class="{badge_class}">{escaped_text}</span>'
