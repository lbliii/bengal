"""
Button directive for Mistune.

Provides clean button syntax for CTAs and navigation.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = ["ButtonDirective", "ButtonOptions"]


# Valid option values
VALID_COLORS = frozenset(
    ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]
)
VALID_STYLES = frozenset(["default", "pill", "outline"])
VALID_SIZES = frozenset(["small", "medium", "large"])


@dataclass
class ButtonOptions(DirectiveOptions):
    """
    Options for button directive.

    Attributes:
        color: Button color theme (primary, secondary, success, danger, etc.)
        style: Button style (default, pill, outline)
        size: Button size (small, medium, large)
        icon: Optional icon name
        target: Link target (_blank for external links)

    Example:
        :::{button} /get-started/
        :color: primary
        :style: pill
        :size: large
        :icon: rocket

        Get Started
        :::
    """

    color: str = "primary"
    style: str = "default"
    size: str = "medium"
    icon: str = ""
    target: str = ""

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "color": list(VALID_COLORS),
        "style": list(VALID_STYLES),
        "size": list(VALID_SIZES),
    }


class ButtonDirective(BengalDirective):
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
    """

    NAMES: ClassVar[list[str]] = ["button"]
    TOKEN_TYPE: ClassVar[str] = "button"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = ButtonOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["button"]

    def parse_directive(
        self,
        title: str,
        options: ButtonOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build button token from parsed components.

        Title is the URL, content is the button text.
        Note: Uses 'label' instead of 'text' to avoid conflict with mistune's
        render signature which passes text as positional argument.
        """
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "url": title.strip() if title else "#",
                "label": content.strip() if content else "Button",  # 'label' avoids conflict
                "color": options.color,
                "style": options.style,
                "size": options.size,
                "icon": options.icon,
                "target": options.target,
            },
            children=[],  # Buttons don't have parsed children
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render button as HTML link.

        Renders as an <a> tag with button styling classes.

        Note: Button text is in attrs['label'] (not 'text') to avoid
        conflict with mistune's render signature.
        """
        url = attrs.get("url", "#")
        button_text = attrs.get("label", "Button")  # Use 'label', not 'text'
        color = attrs.get("color", "primary")
        style = attrs.get("style", "default")
        size = attrs.get("size", "medium")
        icon = attrs.get("icon", "")
        target = attrs.get("target", "")

        # Build CSS classes
        classes = ["button"]

        # Color class
        if color in VALID_COLORS:
            classes.append(f"button-{color}")
        else:
            classes.append("button-primary")

        # Style class
        if style == "pill":
            classes.append("button-pill")
        elif style == "outline":
            classes.append("button-outline")

        # Size class
        if size == "small":
            classes.append("button-sm")
        elif size == "large":
            classes.append("button-lg")

        class_str = " ".join(classes)

        # Build HTML attributes
        attrs_parts = [f'class="{class_str}"', f'href="{self.escape_html(url)}"']

        if target:
            attrs_parts.append(f'target="{self.escape_html(target)}"')
            if target == "_blank":
                attrs_parts.append('rel="noopener noreferrer"')

        attrs_str = " ".join(attrs_parts)

        # Build button content (optional icon + text)
        content_parts = []

        if icon:
            rendered_icon = self._render_icon(icon, button_text=button_text)
            if rendered_icon:
                content_parts.append(f'<span class="button-icon">{rendered_icon}</span>')

        content_parts.append(f'<span class="button-text">{self.escape_html(button_text)}</span>')

        content_html = "".join(content_parts)

        return f"<a {attrs_str}>{content_html}</a>\n"

    @staticmethod
    def _render_icon(icon_name: str, button_text: str = "") -> str:
        """
        Render icon for button using Bengal SVG icons.

        Args:
            icon_name: Name of the icon to render
            button_text: Button text (for warning context)

        Returns:
            SVG HTML string, or empty string if not found
        """
        from bengal.directives._icons import render_icon, warn_missing_icon

        icon_html = render_icon(icon_name, size=18)

        if not icon_html and icon_name:
            warn_missing_icon(icon_name, directive="button", context=button_text)

        return icon_html


# Backward compatibility
