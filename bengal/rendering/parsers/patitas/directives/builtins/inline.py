"""Inline directives for documentation.

Provides:
- badge: Inline badge/pill elements
- icon: Inline SVG icons from Bengal's icon library
- target: Explicit anchor targets for cross-references
- rubric: Pseudo-headings that don't appear in TOC

Use cases:
- API status badges (deprecated, beta, new)
- Inline icons for visual cues
- Stable anchor points for linking
- Section labels without heading semantics

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's inline directives exactly for parity.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = ["BadgeDirective", "IconDirective", "TargetDirective", "RubricDirective"]


# =============================================================================
# Badge Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class BadgeOptions(DirectiveOptions):
    """Options for badge directive."""

    css_class: str = "badge badge-secondary"
    label: str = ""  # Computed from title


class BadgeDirective:
    """
    Badge directive for inline pill/badge elements.
    
    Syntax:
        :::{badge} Command
        :class: badge-cli-command
        :::
    
        :::{badge} Deprecated
        :class: badge-danger
        :::
    
    Output:
        <span class="badge badge-danger">Deprecated</span>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("badge", "bdg")
    token_type: ClassVar[str] = "badge"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[BadgeOptions]] = BadgeOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: BadgeOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build badge AST node."""
        label = title.strip() if title else ""

        # Ensure base badge class is present
        badge_class = self._ensure_base_class(options.css_class)

        # Store computed values as attributes (use replace for frozen dataclass)
        from dataclasses import replace

        computed_opts = replace(options, css_class=badge_class, label=label)

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=(),  # Badges don't have children
        )

    @staticmethod
    def _ensure_base_class(css_class: str) -> str:
        """Ensure the badge has a base class."""
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

    def render(
        self,
        node: Directive[BadgeOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render badge to HTML."""
        opts = node.options  # Direct typed access!

        label = opts.label
        badge_class = opts.css_class

        if not label:
            return

        sb.append(f'<span class="{badge_class}">{html_escape(label)}</span>')


# =============================================================================
# Icon Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class IconOptions(DirectiveOptions):
    """Options for icon directive."""

    size: int = 24
    css_class: str = ""
    aria_label: str = ""
    icon_name: str = ""  # Computed from title
    error: str = ""  # Validation error if any


class IconDirective:
    """
    Icon directive for inline SVG icons.
    
    Syntax:
        :::{icon} terminal
        :::
    
        :::{icon} docs
        :size: 16
        :class: text-muted
        :::
    
    Output:
        <svg width="24" height="24" class="bengal-icon icon-terminal" ...>...</svg>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("icon", "svg-icon")
    token_type: ClassVar[str] = "icon"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[IconOptions]] = IconOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: IconOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build icon AST node."""
        icon_name = title.strip().lower().replace(" ", "-") if title else ""

        # Ensure size is valid
        size = options.size if options.size > 0 else 24
        error = "" if icon_name else "Icon directive requires a name"

        # Store computed values (use replace for frozen dataclass)
        from dataclasses import replace

        computed_opts = replace(options, size=size, icon_name=icon_name, error=error)

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=(),  # Icons don't have children
        )

    def render(
        self,
        node: Directive[IconOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render icon to HTML."""
        opts = node.options  # Direct typed access!

        icon_name = opts.icon_name
        error = opts.error

        if error or not icon_name:
            sb.append('<span class="bengal-icon bengal-icon--error" aria-hidden="true">⚠️</span>')
            return

        size = opts.size
        css_class = opts.css_class
        aria_label = opts.aria_label

        # Try to load SVG via Bengal's icon resolver
        try:
            from bengal.icons import resolver as icon_resolver

            svg_content = icon_resolver.load_icon(icon_name)
        except ImportError:
            svg_content = None

        if svg_content is None:
            sb.append(
                f'<span class="bengal-icon bengal-icon--missing" aria-hidden="true" '
                f'title="Icon not found: {icon_name}">❓</span>'
            )
            return

        # Build class list
        classes = ["bengal-icon", f"icon-{icon_name}"]
        if css_class:
            classes.extend(css_class.split())
        class_attr = " ".join(classes)

        # Accessibility attributes
        if aria_label:
            aria_attrs = f'aria-label="{html_escape(aria_label)}" role="img"'
        else:
            aria_attrs = 'aria-hidden="true"'

        # Modify SVG to set size and add attributes
        svg_modified = re.sub(r'\s+(width|height)="[^"]*"', "", svg_content)
        svg_modified = re.sub(r'\s+class="[^"]*"', "", svg_modified)

        svg_modified = re.sub(
            r"<svg\s",
            f'<svg width="{size}" height="{size}" class="{class_attr}" {aria_attrs} ',
            svg_modified,
            count=1,
        )

        sb.append(svg_modified)


# =============================================================================
# Target Directive
# =============================================================================

# Validation pattern for anchor IDs
TARGET_ID_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


@dataclass(frozen=True, slots=True)
class TargetOptions(DirectiveOptions):
    """Options for target directive.
    
    Attributes:
        id: Anchor ID (computed from title)
        error: Validation error message (if any)
        
    """

    id: str | None = None  # Computed from title
    error: str | None = None  # Validation error if any


class TargetDirective:
    """
    Create an explicit anchor target at any location.
    
    Syntax:
        :::{target} my-anchor-id
        :::
    
    Output:
        <span id="my-anchor-id" class="target-anchor"></span>
    
    Use Cases:
        - Anchor before a note/warning that users should link to
        - Stable anchor that survives content restructuring
        - Migration from Sphinx's ``.. _label:`` syntax
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("target", "anchor")
    token_type: ClassVar[str] = "target"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[TargetOptions]] = TargetOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: TargetOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build target AST node."""
        anchor_id = title.strip() if title else ""

        # Validate anchor ID
        error = ""
        if not anchor_id:
            error = "Target directive requires an ID"
        elif not TARGET_ID_PATTERN.match(anchor_id):
            error = (
                f"Invalid anchor ID: {anchor_id!r}. "
                f"Must start with letter, contain only letters, numbers, hyphens, underscores."
            )

        # Store computed values in options
        from dataclasses import replace

        computed_opts = replace(
            options,
            id=anchor_id,
            error=error,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=(),  # Targets never have children
        )

    def render(
        self,
        node: Directive[TargetOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render target as invisible anchor element."""
        opts = node.options  # Direct typed access!

        error = opts.error or ""
        if error:
            sb.append(
                f'<span class="directive-error" '
                f'title="{html_escape(error)}">[target error]</span>\n'
            )
            return

        anchor_id = opts.id or ""
        sb.append(f'<span id="{html_escape(anchor_id)}" class="target-anchor"></span>\n')


# =============================================================================
# Rubric Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class RubricOptions(DirectiveOptions):
    """Options for rubric directive."""

    css_class: str = ""


class RubricDirective:
    """
    Rubric directive for pseudo-headings.
    
    Syntax:
        :::{rubric} Parameters
        :class: rubric-parameters
        :::
    
    Output:
        <div class="rubric rubric-parameters" role="heading" aria-level="5">Parameters</div>
    
    Creates styled text that looks like a heading but doesn't appear in TOC.
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("rubric",)
    token_type: ClassVar[str] = "rubric"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[RubricOptions]] = RubricOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: RubricOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build rubric AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=(),  # Rubrics never have children
        )

    def render(
        self,
        node: Directive[RubricOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render rubric to HTML."""
        opts = node.options  # Direct typed access!

        title = node.title or ""
        css_class = opts.css_class

        # Build class list
        classes = ["rubric"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        sb.append(
            f'<div class="{class_str}" role="heading" aria-level="5">{html_escape(title)}</div>\n'
        )
