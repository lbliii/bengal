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
    Migrated to BengalDirective base class as part of directive system v2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

__all__ = ["SinceDirective", "DeprecatedDirective", "ChangedDirective"]

logger = get_logger(__name__)


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
            logger.warning("since_directive_empty", info="Since directive has no version")

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

        If there's content, renders as a box with badge.
        If no content, renders as inline badge.
        """
        version = attrs.get("version", "")
        css_class = attrs.get("class", "version-since")
        has_content = attrs.get("has_content", False)

        if not version:
            return ""

        badge_html = (
            f'<span class="version-badge version-badge-since">'
            f"New in {self.escape_html(version)}</span>"
        )

        if has_content and text.strip():
            return (
                f'<div class="{css_class}">'
                f"{badge_html}"
                f'<div class="version-content">{text}</div>'
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
            logger.warning("deprecated_directive_empty", info="Deprecated directive has no version")

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
        """
        version = attrs.get("version", "")
        css_class = attrs.get("class", "version-deprecated")
        has_content = attrs.get("has_content", False)

        if not version:
            version_text = "Deprecated"
        else:
            version_text = f"Deprecated since {self.escape_html(version)}"

        badge_html = f'<span class="version-badge version-badge-deprecated">{version_text}</span>'

        if has_content and text.strip():
            return (
                f'<div class="admonition warning {css_class}">'
                f'<p class="admonition-title">{badge_html}</p>'
                f'<div class="version-content">{text}</div>'
                f"</div>"
            )
        else:
            return (
                f'<div class="admonition warning {css_class}">'
                f'<p class="admonition-title">{badge_html}</p>'
                f"</div>"
            )


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
            logger.warning("changed_directive_empty", info="Changed directive has no version")

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
        """
        version = attrs.get("version", "")
        css_class = attrs.get("class", "version-changed")
        has_content = attrs.get("has_content", False)

        version_text = "Changed" if not version else f"Changed in {self.escape_html(version)}"

        badge_html = f'<span class="version-badge version-badge-changed">{version_text}</span>'

        if has_content and text.strip():
            return (
                f'<div class="admonition note {css_class}">'
                f'<p class="admonition-title">{badge_html}</p>'
                f'<div class="version-content">{text}</div>'
                f"</div>"
            )
        else:
            return (
                f'<div class="admonition note {css_class}">'
                f'<p class="admonition-title">{badge_html}</p>'
                f"</div>"
            )
