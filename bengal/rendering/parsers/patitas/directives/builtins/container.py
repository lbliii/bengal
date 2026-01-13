"""Container directive for generic wrapper divs.

Provides a generic wrapper div with custom CSS classes.
Similar to Sphinx/MyST container directive.

Use cases:
- Wrapping content with semantic styling (api-attributes, api-signatures)
- Creating styled blocks without affecting heading hierarchy
- Grouping related content with a common class

Example:
:::{container} api-section
:class: highlighted

Content here
:::

Thread Safety:
Stateless handler. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's container directive exactly:
<div class="class-names">
{content}
</div>

"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import StyledOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder


@dataclass(frozen=True, slots=True)
class ContainerOptions(StyledOptions):
    """Options for container directive.
    
    The :class: option adds additional CSS classes beyond
    those specified in the title.
        
    """

    pass  # Uses class_ from StyledOptions


class ContainerDirective:
    """Handler for container directive.
    
    Renders a generic wrapper div with custom CSS classes.
    The title line is treated as class names.
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("container", "div")
    token_type: ClassVar[str] = "container"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ContainerOptions]] = ContainerOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: ContainerOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build container AST node.

        The title is treated as class name(s). Additional classes
        from :class: option are merged.
        """
        # Title contains class name(s)
        classes = title.strip() if title else ""

        # Merge with :class: option
        extra_class = options.class_ or ""
        if extra_class:
            classes = f"{classes} {extra_class}" if classes else extra_class

        # Create options with merged classes
        from dataclasses import replace

        merged_opts = replace(options, class_=classes)

        return Directive(
            location=location,
            name=name,
            title=None,  # Title is used as classes, not displayed
            options=merged_opts,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[ContainerOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render container to HTML.

        Produces a div with the specified classes.
        The title is used as class name(s), merged with :class: option.
        """
        opts = node.options  # Direct typed access!

        # Title contains class name(s) - but we merged them in parse()
        classes = opts.class_ or ""

        if classes:
            sb.append(f'<div class="{html_escape(classes)}">\n')
        else:
            sb.append("<div>\n")

        sb.append(rendered_children)
        sb.append("</div>\n")
