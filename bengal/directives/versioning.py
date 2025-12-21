"""
Version-aware directives for documentation.

Provides MyST-style directives for marking version-specific content:
    :::{since} v2.0
    This feature was added in version 2.0.
    :::

    :::{deprecated} v3.0
    Use new_function() instead.
    :::

Architecture:
    Enhanced to align with Bengal's default theme aesthetic:
    - Luminescent left-edge glow animation
    - Palette-aware colors via CSS custom properties
    - Neumorphic badge styling
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.errors import format_suggestion
from bengal.utils.logger import get_logger

__all__ = ["SinceDirective", "DeprecatedDirective", "ChangedDirective"]

logger = get_logger(__name__)


# SVG Icons for version badges (inline for performance, themed via currentColor)
# Using Lucide-style icons at 14x14px
ICON_SPARKLES = (
    '<svg class="version-badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21'
    'l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>'
    '<path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>'
    "</svg>"
)

ICON_ALERT_TRIANGLE = (
    '<svg class="version-badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
    '<path d="M12 9v4"/><path d="M12 17h.01"/>'
    "</svg>"
)

ICON_REFRESH_CW = (
    '<svg class="version-badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
    '<path d="M21 3v5h-5"/>'
    '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
    '<path d="M8 16H3v5"/>'
    "</svg>"
)


@dataclass
class SinceOptions(DirectiveOptions):
    """
    Options for since directive.

    Attributes:
        css_class: CSS classes for styling

    Example:
        :::{since} v2.0
        :class: version-badge
        This feature was added in version 2.0.
        :::
    """

    css_class: str = "version-since"

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class SinceDirective(BengalDirective):
    """
    Directive for marking when a feature was introduced.

    Renders as a badge with optional explanatory content.

    Syntax:
        :::{since} v2.0
        :::

        :::{since} v2.0
        This feature was added in version 2.0.
        :::

    The version is provided as the title (after directive name).
    Optional content provides additional context.
    """

    NAMES: ClassVar[list[str]] = ["since", "versionadded"]
    TOKEN_TYPE: ClassVar[str] = "since"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = SinceOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["since", "versionadded"]

    def parse_directive(
        self,
        title: str,
        options: SinceOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build since token from parsed components.

        Title is the version number.
        """
        if not title:
            suggestion = format_suggestion("directive", "since_empty")
            logger.warning(
                "since_directive_empty",
                info="Since directive has no version",
                suggestion=suggestion,
            )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "version": title.strip() if title else "",
                "class": options.css_class,
                "has_content": bool(content.strip()),
            },
            children=children if children else [],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render since directive as HTML.

        If there's content, renders as a full directive container with
        left-edge glow animation matching Bengal's admonition aesthetic.
        If no content, renders as inline badge.
        """
        version = attrs.get("version", "")
        css_class = attrs.get("class", "version-since")
        has_content = attrs.get("has_content", False)

        if not version:
            return ""

        # Badge with icon
        badge_html = (
            f'<span class="version-badge version-badge-since">'
            f"{ICON_SPARKLES}"
            f"<span>New in {self.escape_html(version)}</span>"
            f"</span>"
        )

        if has_content and text.strip():
            # Full directive container with Bengal theme aesthetic
            return (
                f'<div class="version-directive {css_class}">'
                f'<div class="version-directive-header">{badge_html}</div>'
                f'<div class="version-directive-content">{text}</div>'
                f"</div>"
            )
        else:
            return badge_html


@dataclass
class DeprecatedOptions(DirectiveOptions):
    """
    Options for deprecated directive.

    Attributes:
        css_class: CSS classes for styling

    Example:
        :::{deprecated} v3.0
        :class: version-warning
        Use new_function() instead.
        :::
    """

    css_class: str = "version-deprecated"

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class DeprecatedDirective(BengalDirective):
    """
    Directive for marking deprecated features.

    Renders as a warning box with deprecation notice.

    Syntax:
        :::{deprecated} v3.0
        :::

        :::{deprecated} v3.0
        Use new_function() instead.
        :::

    The version is the version where deprecation occurred.
    Optional content explains the migration path.
    """

    NAMES: ClassVar[list[str]] = ["deprecated", "versionremoved"]
    TOKEN_TYPE: ClassVar[str] = "deprecated"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DeprecatedOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["deprecated", "versionremoved"]

    def parse_directive(
        self,
        title: str,
        options: DeprecatedOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build deprecated token from parsed components.

        Title is the version number.
        """
        if not title:
            suggestion = format_suggestion("directive", "deprecated_empty")
            logger.warning(
                "deprecated_directive_empty",
                info="Deprecated directive has no version",
                suggestion=suggestion,
            )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "version": title.strip() if title else "",
                "class": options.css_class,
                "has_content": bool(content.strip()),
            },
            children=children if children else [],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render deprecated directive as HTML warning box.

        Uses Bengal's version-directive container with warning theme
        for the left-edge glow animation and palette-aware colors.
        """
        version = attrs.get("version", "")
        css_class = attrs.get("class", "version-deprecated")
        has_content = attrs.get("has_content", False)

        if not version:
            version_text = "Deprecated"
        else:
            version_text = f"Deprecated since {self.escape_html(version)}"

        # Badge with icon
        badge_html = (
            f'<span class="version-badge version-badge-deprecated">'
            f"{ICON_ALERT_TRIANGLE}"
            f"<span>{version_text}</span>"
            f"</span>"
        )

        if has_content and text.strip():
            # Full directive container with warning theme
            return (
                f'<div class="version-directive {css_class}">'
                f'<div class="version-directive-header">{badge_html}</div>'
                f'<div class="version-directive-content">{text}</div>'
                f"</div>"
            )
        else:
            # Inline badge for simple deprecation notice
            return badge_html


@dataclass
class ChangedOptions(DirectiveOptions):
    """
    Options for changed directive.

    Attributes:
        css_class: CSS classes for styling

    Example:
        :::{changed} v2.5
        :class: version-info
        The default value changed from 10 to 20.
        :::
    """

    css_class: str = "version-changed"

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class ChangedDirective(BengalDirective):
    """
    Directive for marking behavior changes.

    Renders as an info box with change notice.

    Syntax:
        :::{changed} v2.5
        :::

        :::{changed} v2.5
        The default value changed from 10 to 20.
        :::

    The version is when the change occurred.
    Optional content explains what changed.
    """

    NAMES: ClassVar[list[str]] = ["changed", "versionchanged"]
    TOKEN_TYPE: ClassVar[str] = "changed"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = ChangedOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["changed", "versionchanged"]

    def parse_directive(
        self,
        title: str,
        options: ChangedOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build changed token from parsed components.

        Title is the version number.
        """
        if not title:
            suggestion = format_suggestion("directive", "changed_empty")
            logger.warning(
                "changed_directive_empty",
                info="Changed directive has no version",
                suggestion=suggestion,
            )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "version": title.strip() if title else "",
                "class": options.css_class,
                "has_content": bool(content.strip()),
            },
            children=children if children else [],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render changed directive as HTML info box.

        Uses Bengal's version-directive container with info theme
        for the left-edge glow animation and palette-aware colors.
        """
        version = attrs.get("version", "")
        css_class = attrs.get("class", "version-changed")
        has_content = attrs.get("has_content", False)

        version_text = "Changed" if not version else f"Changed in {self.escape_html(version)}"

        # Badge with icon
        badge_html = (
            f'<span class="version-badge version-badge-changed">'
            f"{ICON_REFRESH_CW}"
            f"<span>{version_text}</span>"
            f"</span>"
        )

        if has_content and text.strip():
            # Full directive container with info theme
            return (
                f'<div class="version-directive {css_class}">'
                f'<div class="version-directive-header">{badge_html}</div>'
                f'<div class="version-directive-content">{text}</div>'
                f"</div>"
            )
        else:
            # Inline badge for simple change notice
            return badge_html
