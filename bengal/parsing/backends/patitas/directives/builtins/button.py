"""Button directive for documentation.

Provides styled link buttons for CTAs and navigation.

Use cases:
- Call-to-action buttons (Get Started, Sign Up)
- Download buttons
- Navigation links with visual emphasis

Thread Safety:
Stateless handler. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's button directive exactly for parity.

"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = ["ButtonDirective"]


# Valid option values
VALID_COLORS = frozenset(
    ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]
)
VALID_STYLES = frozenset(["default", "pill", "outline"])
VALID_SIZES = frozenset(["small", "medium", "large"])


@dataclass(frozen=True, slots=True)
class ButtonOptions(DirectiveOptions):
    """Options for button directive."""

    color: str = "primary"
    style: str = "default"
    size: str = "medium"
    icon: str = ""
    target: str = ""

    # Computed attributes (populated during parse)
    url: str = "#"
    label: str = "Button"


class ButtonDirective:
    """
    Button directive for styled link buttons.

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

    Output:
        <a class="button button-primary button-lg" href="/path/">
          <span class="button-icon">...</span>
          <span class="button-text">Button Text</span>
        </a>

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("button",)
    token_type: ClassVar[str] = "button"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ButtonOptions]] = ButtonOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: ButtonOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build button AST node."""
        url = title.strip() if title else "#"
        label = content.strip() if content else "Button"

        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            url=url,
            label=label,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=(),  # Buttons don't have parsed children
        )

    def render(
        self,
        node: Directive[ButtonOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render button as HTML link."""
        opts = node.options  # Direct typed access!

        url = getattr(opts, "url", "#")
        button_text = getattr(opts, "label", "Button")
        color = opts.color
        style = opts.style
        size = opts.size
        icon = opts.icon
        target = opts.target

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
        attrs_parts = [f'class="{class_str}"', f'href="{html_escape(url)}"']

        if target:
            attrs_parts.append(f'target="{html_escape(target)}"')
            if target == "_blank":
                attrs_parts.append('rel="noopener noreferrer"')

        attrs_str = " ".join(attrs_parts)

        # Build button content (optional icon + text)
        content_parts = []

        if icon:
            rendered_icon = self._render_icon(icon, button_text)
            if rendered_icon:
                content_parts.append(f'<span class="button-icon">{rendered_icon}</span>')

        content_parts.append(f'<span class="button-text">{html_escape(button_text)}</span>')

        content_html = "".join(content_parts)

        sb.append(f"<a {attrs_str}>{content_html}</a>\n")

    @staticmethod
    def _render_icon(icon_name: str, button_text: str = "") -> str:
        """Render icon for button using Bengal SVG icons."""
        try:
            from bengal.directives._icons import render_icon, warn_missing_icon

            icon_html = render_icon(icon_name, size=18)

            if not icon_html and icon_name:
                warn_missing_icon(icon_name, directive="button", context=button_text)

            return icon_html
        except ImportError:
            return ""
