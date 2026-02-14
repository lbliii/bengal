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

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import (
    STEP_CONTRACT,
    STEPS_CONTRACT,
    DirectiveContract,
)
from bengal.parsing.backends.patitas.directives.options import StyledOptions
from bengal.utils.primitives.text import slugify_id

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder


@dataclass(frozen=True, slots=True)
class StepOptions(StyledOptions):
    """Options for step directive.

    Attributes:
        description: Lead-in text with special typography
        optional: Mark step as optional/skippable
        duration: Estimated time for the step
        step_number: Step number (injected by parent steps container)
        heading_level: Heading level for step title (injected by parent)

    """

    description: str | None = None
    optional: bool = False
    duration: str | None = None
    step_number: int | None = None  # Injected by StepsDirective.parse()
    heading_level: int | None = None  # Injected by StepsDirective.parse()


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
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[StepOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render step to HTML.

        Creates an <li> element with step marker, title, metadata,
        and content. The parent steps container wraps these in <ol>.
        """
        opts = node.options  # Direct typed access!
        title = node.title or ""
        description = opts.description or ""
        optional = opts.optional
        duration = opts.duration or ""
        css_class = opts.class_ or ""

        # Clean up None strings
        if description == "None":
            description = ""
        if duration == "None":
            duration = ""
        if css_class == "None":
            css_class = ""

        # Get step number from options (injected by parent steps)
        step_number = opts.step_number if opts.step_number is not None else 1

        # Get heading level from options (injected by parent steps)
        heading_level = opts.heading_level if opts.heading_level is not None else 2

        # Generate step ID from title or fallback to step number
        step_id = self._make_step_id(title) if title else f"step-{step_number}"

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
    def _make_step_id(text: str) -> str:
        """Convert step title to URL-safe anchor ID."""
        return slugify_id(text, default="step")


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
        # Inject step numbers into children
        start = options.start
        heading_level = 2  # Default heading level

        processed_children = []
        step_num = start

        for child in children:
            if isinstance(child, Directive) and child.name == "step":
                # Create new StepOptions with injected step_number and heading_level
                # We need to extend the options with these fields
                from dataclasses import replace

                # Get the child's options
                child_opts = child.options

                # Create a new options object with injected step_number and heading_level
                # StepOptions now includes these fields, so we can use replace()
                new_opts = replace(
                    child_opts,
                    step_number=step_num,
                    heading_level=heading_level,
                )
                step_num += 1

                # Create new Directive with updated options
                processed_children.append(
                    Directive(
                        location=child.location,
                        name=child.name,
                        title=child.title,
                        options=new_opts,  # Use typed options
                        children=child.children,
                    )
                )
            else:
                processed_children.append(child)

        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=tuple(processed_children),
        )

    def render(
        self,
        node: Directive[StepsOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        render_child_directive=None,
    ) -> None:
        """Render steps container to HTML.

        Wraps step list items in <ol>.

        Note: This handler renders its own children to inject step numbers,
        so it ignores the pre-rendered `rendered_children` parameter.

        Args:
            node: The steps directive AST node
            rendered_children: Pre-rendered children (ignored - we render ourselves)
            sb: StringBuilder for output
            render_child_directive: Optional callback to render child directives
        """
        opts = node.options  # Direct typed access!
        css_class = opts.class_ or ""
        style = opts.style or "default"

        # Clean up None strings
        if css_class == "None":
            css_class = ""
        if style == "None":
            style = "default"

        # Get start number
        start = opts.start

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

        # Render children with step numbers
        children_html = self._render_step_children(node.children, start, render_child_directive)

        # Wrap in <ol> if contains step <li> elements
        if "<li>" in children_html or "<li " in children_html:
            sb.append(f'<div class="{html_escape(class_str)}"{style_attr}>\n')
            sb.append(f"<ol{start_attr}>\n")
            sb.append(children_html)
            sb.append("</ol>\n")
            sb.append("</div>\n")
        else:
            sb.append(f'<div class="{html_escape(class_str)}">\n')
            sb.append(children_html)
            sb.append("</div>\n")

    def _render_step_children(
        self,
        children: tuple,
        start: int,
        render_child_directive=None,
    ) -> str:
        """Render step children with proper step numbers.

        Args:
            children: Child AST nodes
            start: Starting step number
            render_child_directive: Callback to render child directives

        Returns:
            Rendered HTML string
        """
        from patitas.stringbuilder import StringBuilder

        sb = StringBuilder()
        step_num = start

        for child in children:
            if isinstance(child, Directive) and child.name == "step":
                # Get child's typed options and inject step_number/heading_level
                child_opts = child.options
                from dataclasses import replace

                # Create a new options object with injected step_number and heading_level
                # StepOptions now includes these fields, so we can use replace()
                new_opts = replace(
                    child_opts,
                    step_number=step_num,
                    heading_level=2,
                )
                step_num += 1

                # Create new directive with updated options
                updated_child = Directive(
                    location=child.location,
                    name=child.name,
                    title=child.title,
                    options=new_opts,  # Use typed options
                    children=child.children,
                )

                # Render using callback if provided, otherwise use StepDirective
                if render_child_directive:
                    render_child_directive(updated_child, sb)
                else:
                    # Render step's children first
                    child_content = self._render_step_content(
                        updated_child.children, render_child_directive
                    )
                    StepDirective().render(updated_child, child_content, sb)
            elif render_child_directive:
                render_child_directive(child, sb)
            # Non-step, non-directive children are skipped

        return sb.build()

    def _render_step_content(
        self,
        children: tuple,
        render_child_directive=None,
    ) -> str:
        """Render step content (children of a step directive).

        Args:
            children: Child AST nodes
            render_child_directive: Callback to render child nodes

        Returns:
            Rendered HTML string
        """
        from patitas.stringbuilder import StringBuilder

        if render_child_directive:
            sb = StringBuilder()
            for child in children:
                render_child_directive(child, sb)
            return sb.build()
        else:
            # Fallback: simple rendering for common node types
            return self._simple_render_children(children)

    def _simple_render_children(self, children: tuple) -> str:
        """Simple fallback renderer for step content."""
        from patitas.nodes import Paragraph
        from patitas.stringbuilder import StringBuilder

        sb = StringBuilder()
        for child in children:
            if isinstance(child, Paragraph):
                sb.append("<p>")
                for inline in child.children:
                    if hasattr(inline, "content"):
                        sb.append(html_escape(inline.content))
                sb.append("</p>\n")
            # Other types can be added as needed
        return sb.build()
