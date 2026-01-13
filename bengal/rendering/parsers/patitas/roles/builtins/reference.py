"""Reference roles for cross-linking.

Provides roles for linking to other parts of the documentation:
- ref: Reference to a labeled target
- doc: Reference to another document

Example:
See {ref}`installation-guide` for setup.
Read the {doc}`/getting-started` guide.

"""

from __future__ import annotations

from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.nodes import Role

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


class RefRole:
    """Handler for {ref}`target` role.
    
    Creates a cross-reference to a labeled target. The target
    is resolved during rendering based on the document structure.
    
    Syntax:
        {ref}`target` - Uses target as both ID and display text
        {ref}`display text <target>` - Custom display text
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("ref",)
    token_type: ClassVar[str] = "reference"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse ref role content.

        Handles both `target` and `text <target>` syntaxes.
        """
        target = content.strip()
        display = None

        # Check for explicit text: "display text <target>"
        if "<" in content and content.rstrip().endswith(">"):
            parts = content.rsplit("<", 1)
            if len(parts) == 2:
                display = parts[0].strip()
                target = parts[1].rstrip(">").strip()

        return Role(
            location=location,
            name=name,
            content=display or target,
            target=target,
        )

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render ref as a link placeholder.

        Actual link resolution happens at a higher level (Bengal).
        Here we output a marker that can be resolved later.
        """
        target = node.target or node.content
        display = node.content

        sb.append(f'<a class="reference internal" href="#{html_escape(target)}">')
        sb.append(html_escape(display))
        sb.append("</a>")


class DocRole:
    """Handler for {doc}`path` role.
    
    Creates a link to another document. The path is resolved
    relative to the current document.
    
    Syntax:
        {doc}`/path/to/doc` - Link to document
        {doc}`display text </path/to/doc>` - Custom display text
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("doc",)
    token_type: ClassVar[str] = "doc_reference"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse doc role content."""
        target = content.strip()
        display = None

        # Check for explicit text: "display text <target>"
        if "<" in content and content.rstrip().endswith(">"):
            parts = content.rsplit("<", 1)
            if len(parts) == 2:
                display = parts[0].strip()
                target = parts[1].rstrip(">").strip()

        return Role(
            location=location,
            name=name,
            content=display or target,
            target=target,
        )

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render doc reference as a link placeholder."""
        target = node.target or node.content
        display = node.content

        # Convert to .html extension for static site
        if not target.endswith(".html") and not target.endswith("/"):
            target = target.rstrip(".md") + ".html"

        sb.append(f'<a class="reference internal" href="{html_escape(target)}">')
        sb.append(html_escape(display))
        sb.append("</a>")
