"""Immutable palette definitions for Rosettes theming.

Provides frozen dataclasses for syntax highlighting palettes.
All palettes are thread-safe by design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal

    CssClassStyle = Literal["semantic", "pygments"]

__all__ = ["SyntaxPalette", "AdaptivePalette"]


@dataclass(frozen=True, slots=True)
class SyntaxPalette:
    """Immutable syntax highlighting palette.

    Thread-safe by design. Defines ~20 semantic color slots
    instead of 100+ individual token colors.
    """

    # Required fields
    name: str
    background: str
    text: str

    # Background variants
    background_highlight: str = ""

    # Control & Structure
    control_flow: str = ""
    declaration: str = ""
    import_: str = ""

    # Data & Literals
    string: str = ""
    number: str = ""
    boolean: str = ""

    # Identifiers
    type_: str = ""
    function: str = ""
    variable: str = ""
    constant: str = ""

    # Documentation
    comment: str = ""
    docstring: str = ""

    # Feedback
    error: str = ""
    warning: str = ""
    added: str = ""
    removed: str = ""

    # Base
    muted: str = ""

    # Additional roles
    punctuation: str = ""
    operator: str = ""
    attribute: str = ""
    namespace: str = ""
    tag: str = ""
    regex: str = ""
    escape: str = ""

    # Style modifiers
    bold_control: bool = True
    bold_declaration: bool = True
    italic_comment: bool = True
    italic_docstring: bool = True

    def __post_init__(self) -> None:
        """Validate palette after initialization."""
        if not self.name:
            raise ValueError("Palette name is required")
        if not self.background:
            raise ValueError("Background color is required")
        if not self.text:
            raise ValueError("Text color is required")

    def with_defaults(self) -> SyntaxPalette:
        """Return a new palette with empty fields filled from defaults."""
        return SyntaxPalette(
            name=self.name,
            background=self.background,
            text=self.text,
            background_highlight=self.background_highlight or self.background,
            control_flow=self.control_flow or self.text,
            declaration=self.declaration or self.text,
            import_=self.import_ or self.control_flow or self.text,
            string=self.string or self.text,
            number=self.number or self.text,
            boolean=self.boolean or self.number or self.text,
            type_=self.type_ or self.text,
            function=self.function or self.text,
            variable=self.variable or self.text,
            constant=self.constant or self.text,
            comment=self.comment or self.muted or self.text,
            docstring=self.docstring or self.comment or self.muted or self.text,
            error=self.error or "#ff0000",
            warning=self.warning or "#ffcc00",
            added=self.added or "#00ff00",
            removed=self.removed or "#ff0000",
            muted=self.muted or self.text,
            punctuation=self.punctuation or self.muted or self.text,
            operator=self.operator or self.control_flow or self.text,
            attribute=self.attribute or self.declaration or self.text,
            namespace=self.namespace or self.type_ or self.text,
            tag=self.tag or self.type_ or self.text,
            regex=self.regex or self.string or self.text,
            escape=self.escape or self.string or self.text,
            bold_control=self.bold_control,
            bold_declaration=self.bold_declaration,
            italic_comment=self.italic_comment,
            italic_docstring=self.italic_docstring,
        )

    def to_css_vars(self, indent: int = 0) -> str:
        """Generate CSS custom property declarations."""
        prefix = " " * indent
        filled = self.with_defaults()

        lines = [
            f"{prefix}--syntax-bg: {filled.background};",
            f"{prefix}--syntax-bg-highlight: {filled.background_highlight};",
            f"{prefix}--syntax-control: {filled.control_flow};",
            f"{prefix}--syntax-declaration: {filled.declaration};",
            f"{prefix}--syntax-import: {filled.import_};",
            f"{prefix}--syntax-string: {filled.string};",
            f"{prefix}--syntax-number: {filled.number};",
            f"{prefix}--syntax-boolean: {filled.boolean};",
            f"{prefix}--syntax-type: {filled.type_};",
            f"{prefix}--syntax-function: {filled.function};",
            f"{prefix}--syntax-variable: {filled.variable};",
            f"{prefix}--syntax-constant: {filled.constant};",
            f"{prefix}--syntax-comment: {filled.comment};",
            f"{prefix}--syntax-docstring: {filled.docstring};",
            f"{prefix}--syntax-error: {filled.error};",
            f"{prefix}--syntax-warning: {filled.warning};",
            f"{prefix}--syntax-added: {filled.added};",
            f"{prefix}--syntax-removed: {filled.removed};",
            f"{prefix}--syntax-text: {filled.text};",
            f"{prefix}--syntax-muted: {filled.muted};",
            f"{prefix}--syntax-punctuation: {filled.punctuation};",
            f"{prefix}--syntax-operator: {filled.operator};",
            f"{prefix}--syntax-attribute: {filled.attribute};",
            f"{prefix}--syntax-namespace: {filled.namespace};",
            f"{prefix}--syntax-tag: {filled.tag};",
            f"{prefix}--syntax-regex: {filled.regex};",
            f"{prefix}--syntax-escape: {filled.escape};",
        ]
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class AdaptivePalette:
    """Theme that adapts to light/dark mode preference."""

    name: str
    light: SyntaxPalette
    dark: SyntaxPalette

    def __post_init__(self) -> None:
        """Validate adaptive palette."""
        if not self.name:
            raise ValueError("Palette name is required")
