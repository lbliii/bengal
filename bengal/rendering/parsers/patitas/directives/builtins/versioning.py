"""Versioning directives for documentation.

Provides:
- since: Mark when a feature was introduced
- deprecated: Mark deprecated features with migration guidance
- changed: Mark behavior changes between versions

Use cases:
- API documentation version badges
- Deprecation warnings with migration paths
- Change notices for breaking changes

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's versioning directives exactly for parity.

"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import DirectiveOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder

__all__ = ["SinceDirective", "DeprecatedDirective", "ChangedDirective"]


# =============================================================================
# SVG Icons (inline for performance, themed via currentColor)
# =============================================================================

# Lucide-style icons at 14x14px
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


# =============================================================================
# Since Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class SinceOptions(DirectiveOptions):
    """Options for since directive."""

    css_class: str = "version-since"

    # Computed attributes (populated during parse)
    version: str = ""
    has_content: bool = False


class SinceDirective:
    """
    Directive for marking when a feature was introduced.
    
    Syntax:
        :::{since} v2.0
        :::
    
        :::{since} v2.0
        This feature was added in version 2.0.
        :::
    
    Output (inline badge):
        <span class="version-badge version-badge-since">
          <svg ...>...</svg>
          <span>New in v2.0</span>
        </span>
    
    Output (with content):
        <div class="version-directive version-since">
          <div class="version-directive-header">
            <span class="version-badge version-badge-since">...</span>
          </div>
          <div class="version-directive-content">...</div>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("since", "versionadded")
    token_type: ClassVar[str] = "since"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[SinceOptions]] = SinceOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: SinceOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build since AST node."""
        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            version=title.strip() if title else "",
            has_content=bool(content.strip()),
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[SinceOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render since directive to HTML."""
        opts = node.options  # Direct typed access!

        version = getattr(opts, "version", "")
        css_class = opts.css_class
        has_content = getattr(opts, "has_content", False)

        if not version:
            return

        # Badge with icon
        badge_html = (
            f'<span class="version-badge version-badge-since">'
            f"{ICON_SPARKLES}"
            f"<span>New in {html_escape(version)}</span>"
            f"</span>"
        )

        if has_content and rendered_children.strip():
            # Full directive container with Bengal theme aesthetic
            sb.append(f'<div class="version-directive {css_class}">')
            sb.append(f'<div class="version-directive-header">{badge_html}</div>')
            sb.append(f'<div class="version-directive-content">{rendered_children}</div>')
            sb.append("</div>")
        else:
            sb.append(badge_html)


# =============================================================================
# Deprecated Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class DeprecatedOptions(DirectiveOptions):
    """Options for deprecated directive."""

    css_class: str = "version-deprecated"

    # Computed attributes (populated during parse)
    version: str = ""
    has_content: bool = False


class DeprecatedDirective:
    """
    Directive for marking deprecated features.
    
    Syntax:
        :::{deprecated} v3.0
        :::
    
        :::{deprecated} v3.0
        Use new_function() instead.
        :::
    
    Output (inline badge):
        <span class="version-badge version-badge-deprecated">
          <svg ...>...</svg>
          <span>Deprecated since v3.0</span>
        </span>
    
    Output (with content):
        <div class="version-directive version-deprecated">
          <div class="version-directive-header">
            <span class="version-badge version-badge-deprecated">...</span>
          </div>
          <div class="version-directive-content">...</div>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("deprecated", "versionremoved")
    token_type: ClassVar[str] = "deprecated"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[DeprecatedOptions]] = DeprecatedOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: DeprecatedOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build deprecated AST node."""
        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            version=title.strip() if title else "",
            has_content=bool(content.strip()),
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[DeprecatedOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render deprecated directive to HTML."""
        opts = node.options  # Direct typed access!

        version = getattr(opts, "version", "")
        css_class = opts.css_class
        has_content = getattr(opts, "has_content", False)

        version_text = "Deprecated" if not version else f"Deprecated since {html_escape(version)}"

        # Badge with icon
        badge_html = (
            f'<span class="version-badge version-badge-deprecated">'
            f"{ICON_ALERT_TRIANGLE}"
            f"<span>{version_text}</span>"
            f"</span>"
        )

        if has_content and rendered_children.strip():
            # Full directive container with warning theme
            sb.append(f'<div class="version-directive {css_class}">')
            sb.append(f'<div class="version-directive-header">{badge_html}</div>')
            sb.append(f'<div class="version-directive-content">{rendered_children}</div>')
            sb.append("</div>")
        else:
            # Inline badge for simple deprecation notice
            sb.append(badge_html)


# =============================================================================
# Changed Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class ChangedOptions(DirectiveOptions):
    """Options for changed directive."""

    css_class: str = "version-changed"

    # Computed attributes (populated during parse)
    version: str = ""
    has_content: bool = False


class ChangedDirective:
    """
    Directive for marking behavior changes.
    
    Syntax:
        :::{changed} v2.5
        :::
    
        :::{changed} v2.5
        The default value changed from 10 to 20.
        :::
    
    Output (inline badge):
        <span class="version-badge version-badge-changed">
          <svg ...>...</svg>
          <span>Changed in v2.5</span>
        </span>
    
    Output (with content):
        <div class="version-directive version-changed">
          <div class="version-directive-header">
            <span class="version-badge version-badge-changed">...</span>
          </div>
          <div class="version-directive-content">...</div>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("changed", "versionchanged")
    token_type: ClassVar[str] = "changed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ChangedOptions]] = ChangedOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: ChangedOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build changed AST node."""
        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            version=title.strip() if title else "",
            has_content=bool(content.strip()),
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[ChangedOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render changed directive to HTML."""
        opts = node.options  # Direct typed access!

        version = getattr(opts, "version", "")
        css_class = opts.css_class
        has_content = getattr(opts, "has_content", False)

        version_text = "Changed" if not version else f"Changed in {html_escape(version)}"

        # Badge with icon
        badge_html = (
            f'<span class="version-badge version-badge-changed">'
            f"{ICON_REFRESH_CW}"
            f"<span>{version_text}</span>"
            f"</span>"
        )

        if has_content and rendered_children.strip():
            # Full directive container with info theme
            sb.append(f'<div class="version-directive {css_class}">')
            sb.append(f'<div class="version-directive-header">{badge_html}</div>')
            sb.append(f'<div class="version-directive-content">{rendered_children}</div>')
            sb.append("</div>")
        else:
            # Inline badge for simple change notice
            sb.append(badge_html)
