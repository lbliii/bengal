"""
Badge directive for Mistune.

Provides MyST-style badge directive: ```{badge} Text :class: badge-class```

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

__all__ = ["BadgeDirective", "BadgeOptions"]

logger = get_logger(__name__)


@dataclass
class BadgeOptions(DirectiveOptions):
    """
    Options for badge directive.

    Attributes:
        css_class: CSS classes for the badge

    Example:
        :::{badge} Command
        :class: badge-cli-command
        :::
    """

    css_class: str = "badge badge-secondary"

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class BadgeDirective(BengalDirective):
    """
    Badge directive for MyST-style badges.

    Syntax:
        :::{badge} Command
        :class: badge-cli-command
        :::

        :::{badge} Deprecated
        :class: badge-danger
        :::

    The badge text is provided as the title (after directive name).
    Optional :class: attribute specifies CSS classes.
    Default class is "badge badge-secondary".

    Aliases:
        - badge: Primary name
        - bdg: Short alias for compatibility
    """

    NAMES: ClassVar[list[str]] = ["badge", "bdg"]
    TOKEN_TYPE: ClassVar[str] = "badge"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = BadgeOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["badge", "bdg"]

    def parse_directive(
        self,
        title: str,
        options: BadgeOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build badge token from parsed components.

        Title is the badge text. Ensures base "badge" class is present.
        """
        if not title:
            logger.warning("badge_directive_empty", info="Badge directive has no text")

        # Ensure base badge class is present
        badge_class = self._ensure_base_class(options.css_class)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "label": title or "",  # 'label' avoids conflict with Mistune's text
                "class": badge_class,
            },
            children=[],  # Badges don't have children
        )

    @staticmethod
    def _ensure_base_class(css_class: str) -> str:
        """
        Ensure the badge has a base class (badge or api-badge).

        Handles cases like "badge-secondary", "badge-danger", "api-badge", etc.
        """
        if not css_class:
            return "badge badge-secondary"

        classes = css_class.split()

        # Check if base class is already present
        has_base_badge = any(cls in ("badge", "api-badge") for cls in classes)

        if not has_base_badge:
            # Determine which base class to use
            if any(cls.startswith("api-badge") for cls in classes):
                classes.insert(0, "api-badge")
            elif any(cls.startswith("badge-") for cls in classes):
                classes.insert(0, "badge")
            else:
                classes.insert(0, "badge")

            return " ".join(classes)

        return css_class

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render badge as HTML span.

        Returns empty string if no label text.
        """
        badge_text = attrs.get("label", "")
        badge_class = attrs.get("class", "badge badge-secondary")

        if not badge_text:
            return ""

        return f'<span class="{badge_class}">{self.escape_html(badge_text)}</span>'


# Backward compatibility
