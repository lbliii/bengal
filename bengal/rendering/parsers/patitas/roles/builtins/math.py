"""Math role for inline mathematical expressions.

Provides the {math} role as an alternative to $...$ syntax.

Example:
    The equation {math}`E = mc^2` is famous.
"""

from __future__ import annotations

from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.nodes import Role

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


class MathRole:
    """Handler for {math}`expression` role.

    Renders inline mathematical expressions. The output format
    depends on the math rendering library configured (MathJax, KaTeX, etc.).

    Syntax:
        {math}`E = mc^2`
        {math}`\\sum_{i=1}^n x_i`

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("math",)
    token_type: ClassVar[str] = "math"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse math role content.

        Content is preserved as-is for math rendering.
        """
        return Role(
            location=location,
            name=name,
            content=content,  # Don't strip - whitespace may be significant
        )

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render math expression.

        Uses span with math class for CSS styling and JS rendering.
        The content is escaped but wrapped in delimiters for the
        math rendering library.
        """
        # Use \( \) delimiters for inline math (MathJax/KaTeX compatible)
        sb.append('<span class="math notranslate nohighlight">\\(')
        sb.append(html_escape(node.content))
        sb.append("\\)</span>")
