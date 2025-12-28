"""Steps directive for visual step-by-step guides.

Provides visual step-by-step guides using nested directives
with contract-based validation.

Steps Container Options:
    :class: - Custom CSS class for the steps container
    :style: - Visual style (default, compact)
    :start: - Start numbering from this value (default: 1)

Step Options:
    :class: - Custom CSS class for the step
    :description: - Lead-in text with special typography
    :optional: - Mark step as optional/skippable
    :duration: - Estimated time for the step

Example:
    :::{steps}
    :start: 1

    :::{step} Configure Settings
    :description: Before we begin, ensure your environment is set up.
    :duration: 5 min

    Step content with **markdown** support.
    :::

    :::{step} Optional Step
    :optional:

    This step can be skipped.
    :::

    :::

Thread Safety:
    Stateless handlers. Safe for concurrent use across threads.

HTML Output:
    Matches Bengal's steps directive exactly.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import (
    STEP_CONTRACT,
    STEPS_CONTRACT,
    DirectiveContract,
)
from bengal.rendering.parsers.patitas.directives.options import StyledOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


@dataclass(frozen=True, slots=True)
class StepOptions(StyledOptions):
    """Options for step directive.

    Attributes:
        description: Lead-in text with special typography
        optional: Mark step as optional/skippable
        duration: Estimated time for the step
    """

    description: str | None = None
    optional: bool = False
    duration: str | None = None


@dataclass(frozen=True, slots=True)
class StepsOptions(StyledOptions):
    """Options for steps container directive.

    Attributes:
        style: Step style (compact, default)
        start: Start numbering from this value
    """

    style: str | None = None
    start: int = 1


class StepDirective:
    """Handler for step directive.

    Individual step that must be inside a steps container.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("step",)
    token_type: ClassVar[str] = "step"
    contract: ClassVar[DirectiveContract | None] = STEP_CONTRACT
    options_class: ClassVar[type[StepOptions]] = StepOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: StepOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build step AST node."""
        opts_dict = asdict(options)
        opts_items = [(k, str(v)) for k, v in opts_dict.items() if v is not None]

        return Directive(
            location=location,
            name=name,
            title=title,
            options=frozenset(opts_items),
            children=tuple(children),
        )

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render step to HTML.

        Creates an <li> element with step marker, title, metadata,
        and content. The parent steps container wraps these in <ol>.
        """
        opts = dict(node.options)
        title = node.title or ""
        description = opts.get("description", "") or ""
        optional = opts.get("optional", "").lower() in ("true", "1", "yes")
        duration = opts.get("duration", "") or ""
        css_class = opts.get("class_", "") or ""

        # Clean up None strings
        if description == "None":
            description = ""
        if duration == "None":
            duration = ""
        if css_class == "None":
            css_class = ""

        # Get step number from options (injected by parent steps)
        step_number = 1
        if "step_number" in opts:
            with contextlib.suppress(ValueError, TypeError):
                step_number = int(opts["step_number"])

        # Get heading level from options (injected by parent steps)
        heading_level = 2
        if "heading_level" in opts:
            with contextlib.suppress(ValueError, TypeError):
                heading_level = int(opts["heading_level"])

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
            f'<a class="step-marker" href="#{html_escape(step_id)}" '
            f'aria-label="Step {step_number}">{step_number}</a>'
        )

        # Build metadata line (optional badge + duration)
        metadata_parts = []
        if optional:
            metadata_parts.append('<span class="step-badge step-badge-optional">Optional</span>')
        if duration:
            metadata_parts.append(f'<span class="step-duration">{html_escape(duration)}</span>')
        metadata_html = ""
        if metadata_parts:
            metadata_html = f'<div class="step-metadata">{" ".join(metadata_parts)}</div>\n'

        # Build description HTML if provided
        description_html = ""
        if description:
            description_html = f'<p class="step-description">{html_escape(description)}</p>\n'

        if title:
            heading_tag = f"h{heading_level}"
            sb.append(f'<li{class_attr} id="{html_escape(step_id)}">')
            sb.append(marker_html)
            sb.append(f'<{heading_tag} class="step-title">{html_escape(title)}</{heading_tag}>')
            sb.append(metadata_html)
            sb.append(description_html)
            sb.append(rendered_children)
            sb.append("</li>\n")
        else:
            sb.append(f'<li{class_attr} id="{html_escape(step_id)}">')
            sb.append(marker_html)
            sb.append(metadata_html)
            sb.append(description_html)
            sb.append(rendered_children)
            sb.append("</li>\n")

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-safe slug for anchor IDs."""
        slug = text.lower().strip()
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")
        return slug or "step"


class StepsDirective:
    """Handler for steps container directive.

    Contains step children that form a numbered list.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("steps",)
    token_type: ClassVar[str] = "steps"
    contract: ClassVar[DirectiveContract | None] = STEPS_CONTRACT
    options_class: ClassVar[type[StepsOptions]] = StepsOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: StepsOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build steps AST node.

        Injects step_number and heading_level into child step directives.
        """
        opts_dict = asdict(options)
        opts_items = [(k, str(v)) for k, v in opts_dict.items() if v is not None]

        # Inject step numbers into children
        start = options.start
        heading_level = 2  # Default heading level

        processed_children = []
        step_num = start

        for child in children:
            if isinstance(child, Directive) and child.name == "step":
                # Add step_number and heading_level to child's options
                new_opts = dict(child.options)
                new_opts["step_number"] = str(step_num)
                new_opts["heading_level"] = str(heading_level)
                step_num += 1

                # Create new Directive with updated options
                processed_children.append(
                    Directive(
                        location=child.location,
                        name=child.name,
                        title=child.title,
                        options=frozenset(new_opts.items()),
                        children=child.children,
                    )
                )
            else:
                processed_children.append(child)

        return Directive(
            location=location,
            name=name,
            title=title,
            options=frozenset(opts_items),
            children=tuple(processed_children),
        )

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render steps container to HTML.

        Wraps step list items in <ol>.
        """
        opts = dict(node.options)
        css_class = opts.get("class_", "") or ""
        style = opts.get("style", "default") or "default"

        # Clean up None strings
        if css_class == "None":
            css_class = ""
        if style == "None":
            style = "default"

        # Get start number
        start = 1
        if "start" in opts:
            with contextlib.suppress(ValueError, TypeError):
                start = int(opts["start"])

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
            style_attr = f' style="counter-reset: step {start - 1}"'

        # Wrap in <ol> if contains step <li> elements
        if "<li>" in rendered_children or "<li " in rendered_children:
            sb.append(f'<div class="{html_escape(class_str)}"{style_attr}>\n')
            sb.append(f"<ol{start_attr}>\n")
            sb.append(rendered_children)
            sb.append("</ol>\n")
            sb.append("</div>\n")
        else:
            sb.append(f'<div class="{html_escape(class_str)}">\n')
            sb.append(rendered_children)
            sb.append("</div>\n")
