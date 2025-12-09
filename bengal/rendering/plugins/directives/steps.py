"""
Steps directive for Mistune.

Provides visual step-by-step guides using nested directives.

Architecture:
    Migrated to BengalDirective base class with DirectiveContract validation.
    This demonstrates the contract system for enforcing valid nesting:
    - StepsDirective: requires_children=["step"]
    - StepDirective: requires_parent=["steps"]

Syntax (preferred - named closers, no colon counting):
    :::{steps}
    :::{step} Step Title
    :description: Brief context before diving into the step content.
    Step 1 content with **markdown** and nested directives.
    :::{/step}

    :::{step} Another Step
    Step 2 content
    :::{/step}
    :::{/steps}

Legacy syntax (fence-depth counting - still works):
    ::::{steps}
    :::{step} Step Title
    Step 1 content
    :::
    ::::

Step Options:
    :class: - Custom CSS class for the step
    :description: - Lead-in text with special typography (rendered before main content)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.contracts import (
    STEP_CONTRACT,
    STEPS_CONTRACT,
    DirectiveContract,
)
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken
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

    Example:
        :::{step} Configure Settings
        :class: important-step
        :description: Before we begin, ensure your environment is properly set up.
        Content here
        :::{/step}
    """

    css_class: str = ""
    description: str = ""

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
        """
        attrs: dict[str, Any] = {}
        if title:
            attrs["title"] = title
        if options.css_class:
            attrs["css_class"] = options.css_class
        if options.description:
            attrs["description"] = options.description

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs=attrs,
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render individual step to HTML.

        Step titles are rendered as headings (h2/h3/h4) based on parent level.
        Descriptions are rendered as lead-in text with special typography.
        """
        title = attrs.get("title", "")
        description = attrs.get("description", "")
        css_class = attrs.get("css_class", "").strip()
        heading_level = attrs.get("heading_level", 2)

        class_attr = f' class="{css_class}"' if css_class else ""

        # Build description HTML if provided
        description_html = ""
        if description:
            desc_text = self._parse_inline_markdown(renderer, description)
            description_html = f'<p class="step-description">{desc_text}</p>\n'

        if title:
            title_html = self._parse_inline_markdown(renderer, title)
            heading_tag = f"h{heading_level}"
            return (
                f"<li{class_attr}>"
                f'<{heading_tag} class="step-title">{title_html}</{heading_tag}>'
                f"{description_html}"
                f"{text}</li>\n"
            )

        return f"<li{class_attr}>{description_html}{text}</li>\n"

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

    Example:
        ::::{steps}
        :class: installation-steps
        :style: compact
        ...
        ::::
    """

    css_class: str = ""
    style: str = "default"

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

        Injects heading_level into child step tokens for proper semantic HTML.
        """
        # Detect parent heading level for semantic step titles
        heading_level = self._detect_heading_level(state)

        # Inject heading_level into step children
        children = self._inject_heading_level(children, heading_level)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "css_class": options.css_class,
                "style": options.style,
                "heading_level": heading_level,
            },
            children=children,
        )

    def _inject_heading_level(self, children: list[Any], heading_level: int) -> list[Any]:
        """
        Inject heading_level into step tokens.

        This allows step titles to render as proper headings (h2/h3/h4)
        based on the document structure.
        """
        result: list[Any] = []
        for child in children:
            if isinstance(child, dict) and child.get("type") == "step":
                child.setdefault("attrs", {})["heading_level"] = heading_level
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
        """
        css_class = attrs.get("css_class", "").strip()
        style = attrs.get("style", "default").strip()

        # Build class string
        classes = ["steps"]
        if css_class:
            classes.append(css_class)
        if style and style != "default":
            classes.append(f"steps-{style}")

        class_str = " ".join(classes)

        # Wrap in <ol> if contains step <li> elements
        if "<li>" in text or "<li " in text:
            return f'<div class="{class_str}">\n<ol>\n{text}</ol>\n</div>\n'
        return f'<div class="{class_str}">\n{text}</div>\n'


# =============================================================================
# Backward Compatibility
# =============================================================================


def render_step(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return StepDirective().render(renderer, text, **attrs)


def render_steps(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return StepsDirective().render(renderer, text, **attrs)
