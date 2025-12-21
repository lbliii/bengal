"""
Steps directive for Mistune.

Provides visual step-by-step guides using nested directives.

Architecture:
    Uses DirectiveContract validation for enforcing valid nesting:
    - StepsDirective: requires_children=["step"]
    - StepDirective: requires_parent=["steps"]

Syntax (preferred - named closers, no colon counting):
    :::{steps}
    :start: 1

    :::{step} Step Title
    :description: Brief context before diving into the step content.
    :duration: 5 min
    Step 1 content with **markdown** and nested directives.
    :::{/step}

    :::{step} Optional Step
    :optional:
    This step can be skipped.
    :::{/step}
    :::{/steps}

Alternative syntax (fence-depth counting):
    ::::{steps}
    :::{step} Step Title
    Step 1 content
    :::
    ::::

Steps Container Options:
    :class: - Custom CSS class for the steps container
    :style: - Visual style (default, compact)
    :start: - Start numbering from this value (default: 1)

Step Options:
    :class: - Custom CSS class for the step
    :description: - Lead-in text with special typography (rendered before main content)
    :optional: - Mark step as optional/skippable (adds visual indicator)
    :duration: - Estimated time for the step (e.g., "5 min", "1 hour")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.contracts import (
    STEP_CONTRACT,
    STEPS_CONTRACT,
    DirectiveContract,
)
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

__all__ = [
    "StepsDirective",
    "StepDirective",
    "StepsOptions",
    "StepOptions",
]

logger = get_logger(__name__)


# =============================================================================
# Step Directive (must be nested in steps)
# =============================================================================


@dataclass
class StepOptions(DirectiveOptions):
    """
    Options for step directive.

    Attributes:
        css_class: Custom CSS class for the step
        description: Lead-in text with special typography (rendered before main content)
        optional: Mark step as optional/skippable (adds visual indicator)
        duration: Estimated time for the step (e.g., "5 min", "1 hour")

    Example:
        :::{step} Configure Settings
        :class: important-step
        :description: Before we begin, ensure your environment is properly set up.
        :duration: 5 min
        :optional:
        Content here
        :::{/step}
    """

    css_class: str = ""
    description: str = ""
    optional: bool = False
    duration: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class StepDirective(BengalDirective):
    """
    Individual step directive (nested in steps).

    Syntax:
        :::{step} Optional Title
        :class: custom-class
        Step content with **markdown** and nested directives.
        :::

    Contract:
        MUST be nested inside a :::{steps} directive.
        If used outside steps, a warning is logged.
    """

    NAMES: ClassVar[list[str]] = ["step"]
    TOKEN_TYPE: ClassVar[str] = "step"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = StepOptions

    # Contract: step MUST be inside steps
    CONTRACT: ClassVar[DirectiveContract] = STEP_CONTRACT

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["step"]

    def parse_directive(
        self,
        title: str,
        options: StepOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build step token from parsed components.

        Title becomes the step heading, content is parsed as markdown.
        Description (if provided) renders as lead-in text with special typography.
        Optional and duration add visual indicators.
        """
        attrs: dict[str, Any] = {}
        if title:
            attrs["title"] = title
        if options.css_class:
            attrs["css_class"] = options.css_class
        if options.description:
            attrs["description"] = options.description
        if options.optional:
            attrs["optional"] = True
        if options.duration:
            attrs["duration"] = options.duration

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs=attrs,
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render individual step to HTML.

        Step titles are rendered as headings (h2/h3/h4) based on parent level.
        Step markers are rendered as anchor links for direct navigation.
        Descriptions are rendered as lead-in text with special typography.
        Optional steps get a visual indicator.
        Duration is shown as a time estimate badge.
        """
        title = attrs.get("title", "")
        description = attrs.get("description", "")
        css_class = attrs.get("css_class", "").strip()
        heading_level = attrs.get("heading_level", 2)
        optional = attrs.get("optional", False)
        duration = attrs.get("duration", "")
        step_number = attrs.get("step_number", 1)

        # Generate step ID from title or fallback to step number
        step_id = self._slugify(title) if title else f"step-{step_number}"

        # Build class list
        classes = []
        if css_class:
            classes.append(css_class)
        if optional:
            classes.append("step-optional")

        class_attr = f' class="{" ".join(classes)}"' if classes else ""

        # Build step marker as anchor link
        marker_html = (
            f'<a class="step-marker" href="#{step_id}" '
            f'aria-label="Step {step_number}">{step_number}</a>'
        )

        # Build metadata line (optional badge + duration)
        metadata_html = ""
        metadata_parts = []
        if optional:
            metadata_parts.append('<span class="step-badge step-badge-optional">Optional</span>')
        if duration:
            duration_text = self._parse_inline_markdown(renderer, duration)
            metadata_parts.append(f'<span class="step-duration">{duration_text}</span>')
        if metadata_parts:
            metadata_html = f'<div class="step-metadata">{" ".join(metadata_parts)}</div>\n'

        # Build description HTML if provided
        description_html = ""
        if description:
            desc_text = self._parse_inline_markdown(renderer, description)
            description_html = f'<p class="step-description">{desc_text}</p>\n'

        if title:
            title_html = self._parse_inline_markdown(renderer, title)
            heading_tag = f"h{heading_level}"
            return (
                f'<li{class_attr} id="{step_id}">'
                f"{marker_html}"
                f'<{heading_tag} class="step-title">{title_html}</{heading_tag}>'
                f"{metadata_html}"
                f"{description_html}"
                f"{text}</li>\n"
            )

        return (
            f'<li{class_attr} id="{step_id}">'
            f"{marker_html}"
            f"{metadata_html}{description_html}{text}</li>\n"
        )

    @staticmethod
    def _parse_inline_markdown(renderer: Any, text: str) -> str:
        """
        Parse inline markdown in step titles.

        Tries mistune's inline parser first, falls back to regex.
        """
        # Try mistune's inline parser
        md_instance = getattr(renderer, "_md", None) or getattr(renderer, "md", None)
        if md_instance and hasattr(md_instance, "inline"):
            try:
                return str(md_instance.inline(text))
            except Exception as e:
                logger.debug(
                    "steps_inline_parse_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Fallback to simple regex
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
        text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
        return text

    @staticmethod
    def _slugify(text: str) -> str:
        """
        Convert text to URL-safe slug for anchor IDs.

        Converts to lowercase, replaces spaces with hyphens,
        removes non-alphanumeric characters except hyphens.
        """
        # Convert to lowercase and strip
        slug = text.lower().strip()
        # Replace spaces and underscores with hyphens
        slug = re.sub(r"[\s_]+", "-", slug)
        # Remove anything that isn't alphanumeric or hyphen
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        # Collapse multiple hyphens
        slug = re.sub(r"-+", "-", slug)
        # Strip leading/trailing hyphens
        slug = slug.strip("-")
        return slug or "step"


# =============================================================================
# Steps Container Directive
# =============================================================================


@dataclass
class StepsOptions(DirectiveOptions):
    """
    Options for steps container directive.

    Attributes:
        css_class: Custom CSS class for the steps container
        style: Step style (compact, default)
        start: Start numbering from this value (default: 1)

    Example:
        :::{steps}
        :class: installation-steps
        :style: compact
        :start: 5
        ...
        :::{/steps}
    """

    css_class: str = ""
    style: str = "default"
    start: int = 1

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "style": ["default", "compact"],
    }


class StepsDirective(BengalDirective):
    """
    Steps directive for visual step-by-step guides.

    Syntax (preferred - supports nested directives):
        ::::{steps}
        :class: custom-class
        :style: compact

        :::{step} Step 1 Title
        Step 1 content with nested :::{tip} directives
        :::

        :::{step} Step 2 Title
        Step 2 content
        :::
        ::::

    Note: Parent container (steps) uses 4 colons, nested steps use 3 colons.

    Contract:
        REQUIRES at least one :::{step} child directive.
        If no steps found, a warning is logged.
    """

    NAMES: ClassVar[list[str]] = ["steps"]
    TOKEN_TYPE: ClassVar[str] = "steps"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = StepsOptions

    # Contract: steps REQUIRES step children
    CONTRACT: ClassVar[DirectiveContract] = STEPS_CONTRACT

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["steps"]

    def parse_directive(
        self,
        title: str,
        options: StepsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build steps token from parsed components.

        Injects heading_level and step_number into child step tokens for
        proper semantic HTML and anchor link support.
        """
        # Detect parent heading level for semantic step titles
        heading_level = self._detect_heading_level(state)

        # Inject heading_level and step_number into step children
        children = self._inject_step_metadata(children, heading_level, options.start)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "css_class": options.css_class,
                "style": options.style,
                "start": options.start,
                "heading_level": heading_level,
            },
            children=children,
        )

    def _inject_step_metadata(
        self, children: list[Any], heading_level: int, start: int
    ) -> list[Any]:
        """
        Inject heading_level and step_number into step tokens.

        This allows step titles to render as proper headings (h2/h3/h4)
        and step markers to be anchor links with the correct number.
        """
        result: list[Any] = []
        step_num = start
        for child in children:
            if isinstance(child, dict) and child.get("type") == "step":
                child.setdefault("attrs", {})["heading_level"] = heading_level
                child["attrs"]["step_number"] = step_num
                step_num += 1
            result.append(child)
        return result

    def _detect_heading_level(self, state: Any) -> int:
        """
        Detect the current heading level from parser state.

        Steps should render step titles as headings one level deeper than
        the parent heading (h1 -> h2, h2 -> h3, etc.).

        Returns the heading level (2-6) that steps should use.
        Defaults to h2 if no heading context found.
        """
        try:
            if hasattr(state, "tokens") and state.tokens:
                for token in reversed(state.tokens):
                    if isinstance(token, dict) and token.get("type") == "heading":
                        level = int(token.get("attrs", {}).get("level", 2))
                        return min(level + 1, 6)
        except (AttributeError, TypeError):
            pass

        return 2

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render steps container to HTML.

        Wraps step list items in <ol> if present.
        Supports custom start number for continuing numbered lists.
        """
        css_class = attrs.get("css_class", "").strip()
        style = attrs.get("style", "default").strip()
        start = attrs.get("start", 1)

        # Build class string
        classes = ["steps"]
        if css_class:
            classes.append(css_class)
        if style and style != "default":
            classes.append(f"steps-{style}")

        class_str = " ".join(classes)

        # Build start attribute for <ol> if not 1
        start_attr = f' start="{start}"' if start != 1 else ""

        # Build style for counter reset if start != 1
        style_attr = ""
        if start != 1:
            # CSS counter needs to start at start-1 because counter-increment happens before display
            style_attr = f' style="counter-reset: step {start - 1}"'

        # Wrap in <ol> if contains step <li> elements
        if "<li>" in text or "<li " in text:
            return f'<div class="{class_str}"{style_attr}>\n<ol{start_attr}>\n{text}</ol>\n</div>\n'
        return f'<div class="{class_str}">\n{text}</div>\n'
