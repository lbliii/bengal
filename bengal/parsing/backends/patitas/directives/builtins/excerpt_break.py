"""Excerpt break directive for author-controlled excerpt boundaries.

Provides a leaf directive that marks where the excerpt should end.
When present, the excerpt extractor uses content above the break
instead of the default position-based truncation.

Syntax:
    :::{excerpt-break}
    :::

The directive renders to nothing in HTML output — it is purely
a signal to the excerpt extraction pipeline.

Thread Safety:
    Stateless handler. Safe for concurrent use across threads.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from collections.abc import Sequence

    from patitas.nodes import Block, SourceLocation
    from patitas.rendering import StringBuilder


class ExcerptBreakDirective:
    """Mark the excerpt boundary in a document.

    Everything above this directive becomes the excerpt. When absent,
    the default position-based extraction (max_chars) applies.

    Syntax:
        :::{excerpt-break}
        :::

    Output:
        (nothing — invisible to rendered HTML)

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("excerpt-break",)
    token_type: ClassVar[str] = "excerpt_break"
    contract: ClassVar[None] = None
    options_class: ClassVar[type[DirectiveOptions]] = DirectiveOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: DirectiveOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build excerpt-break AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,
            children=(),
        )

    def render(
        self,
        node: Directive[DirectiveOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render nothing — excerpt-break is invisible in output."""
