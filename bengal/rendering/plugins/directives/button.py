"""
Button directive for Mistune.

Provides clean button syntax for CTAs and navigation:

    :::{button} /get-started/
    :color: primary
    :style: pill
    :size: large

    Get Started
    :::

Replaces Sphinx-Design's complex button-ref syntax with a simpler approach.
"""

from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

__all__ = ["ButtonDirective"]


class ButtonDirective(DirectivePlugin):
    """
    Button directive for creating styled link buttons.

    Syntax:
        :::{button} /path/to/page/
        :color: primary
        :style: pill
        :size: large
        :icon: rocket
        :target: _blank

        Button Text
        :::

    Options:
        color: primary, secondary, success, danger, warning, info, light, dark
        style: default (rounded), pill (fully rounded), outline
        size: small, medium (default), large
        icon: Icon name (same as cards)
        target: _blank for external links (optional)

    Examples:
        # Basic button
        :::{button} /docs/
        Get Started
        :::

        # Primary CTA
        :::{button} /signup/
        :color: primary
        :style: pill
        :size: large

        Sign Up Free
        :::

        # External link
        :::{button} https://github.com/yourproject
        :color: secondary
        :target: _blank

        View on GitHub
        :::
    """

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """
        Parse button directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'button'
        """
        # Get URL/path from title
        url = self.parse_title(m).strip()

        # Parse options
        options = dict(self.parse_options(m))

        # Parse button text content
        content = self.parse_content(m).strip()

        # Extract options with defaults
        color = options.get("color", "primary").strip()
        style = options.get("style", "default").strip()
        size = options.get("size", "medium").strip()
        icon = options.get("icon", "").strip()
        target = options.get("target", "").strip()

        return {
            "type": "button",
            "attrs": {
                "url": url,
                "text": content,
                "color": color,
                "style": style,
                "size": size,
                "icon": icon,
                "target": target,
            },
        }

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("button", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("button", render_button)


def render_button(renderer, text: str, **attrs) -> str:
    """
    Render button as HTML link.

    Args:
        renderer: Mistune renderer
        text: Button text (content between :::{button} and :::)
        **attrs: Button attributes (url, color, style, size, icon, target)

    Returns:
        HTML string for button
    """
    url = attrs.get("url", "#")
    button_text = attrs.get("text", text or "Button")
    color = attrs.get("color", "primary")
    style = attrs.get("style", "default")
    size = attrs.get("size", "medium")
    icon = attrs.get("icon", "")
    target = attrs.get("target", "")

    # Build CSS classes
    classes = ["button"]

    # Color class
    valid_colors = ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]
    if color in valid_colors:
        classes.append(f"button-{color}")
    else:
        classes.append("button-primary")  # Fallback

    # Style class
    if style == "pill":
        classes.append("button-pill")
    elif style == "outline":
        classes.append("button-outline")
    # 'default' style has no extra class

    # Size class
    if size == "small":
        classes.append("button-sm")
    elif size == "large":
        classes.append("button-lg")
    # 'medium' is default, no extra class

    class_str = " ".join(classes)

    # Build HTML attributes
    attrs_parts = [f'class="{class_str}"', f'href="{_escape_html(url)}"']

    if target:
        attrs_parts.append(f'target="{_escape_html(target)}"')
        if target == "_blank":
            attrs_parts.append('rel="noopener noreferrer"')

    attrs_str = " ".join(attrs_parts)

    # Build button content (optional icon + text)
    content_parts = []

    if icon:
        rendered_icon = _render_icon(icon)
        if rendered_icon:
            content_parts.append(f'<span class="button-icon">{rendered_icon}</span>')

    content_parts.append(f'<span class="button-text">{_escape_html(button_text)}</span>')

    content_html = "".join(content_parts)

    return f"<a {attrs_str}>{content_html}</a>\n"


def _render_icon(icon_name: str) -> str:
    """
    Render icon for button (same as cards).

    Args:
        icon_name: Name of the icon

    Returns:
        HTML for icon, or empty string if not found
    """
    icon_map = {
        "book": "📖",
        "code": "💻",
        "rocket": "🚀",
        "users": "👥",
        "star": "⭐",
        "download": "⬇️",
        "upload": "⬆️",
        "external": "🔗",
        "github": "🐙",
        "arrow-right": "→",
        "check": "✓",
        "info": "ℹ️",
        "warning": "⚠️",
    }

    return icon_map.get(icon_name, "")


def _escape_html(text: str) -> str:
    """
    Escape HTML special characters.

    Args:
        text: Text to escape

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
