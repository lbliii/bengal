"""Immutable palette definitions for Rosettes theming.

Provides frozen dataclasses for syntax highlighting palettes.
All palettes are thread-safe by design.

Examples:
    >>> from rosettes.themes import SyntaxPalette
    >>> my_theme = SyntaxPalette(
    ...     name="my-theme",
    ...     background="#1e1e1e",
    ...     text="#d4d4d4",
    ...     # ... other colors
    ... )
    >>> my_theme.name
    'my-theme'
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

    Attributes:
        name: Unique identifier for the palette.
        background: Code block background color.
        background_highlight: Highlighted line background.
        control_flow: Color for control keywords (if, for, while).
        declaration: Color for declarations (def, class, const).
        import_: Color for import statements.
        string: Color for string literals.
        number: Color for numeric literals.
        boolean: Color for boolean literals.
        type_: Color for type names and annotations.
        function: Color for function names.
        variable: Color for variable names.
        constant: Color for constants (ALL_CAPS).
        comment: Color for comments.
        docstring: Color for documentation strings.
        error: Color for errors.
        warning: Color for warnings.
        added: Color for diff additions.
        removed: Color for diff removals.
        text: Default text color.
        muted: De-emphasized text color.
        punctuation: Color for punctuation.
        operator: Color for operators.
        attribute: Color for decorators/attributes.
        namespace: Color for namespace/module names.
        tag: Color for markup tags.
        regex: Color for regex literals.
        escape: Color for escape sequences.
        bold_control: Whether control keywords are bold.
        bold_declaration: Whether declarations are bold.
        italic_comment: Whether comments are italic.
        italic_docstring: Whether docstrings are italic.
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
        """Validate palette after initialization.

        Performs basic validation. For full WCAG validation,
        use the validate_palette() function.
        """
        # Ensure required fields are set
        if not self.name:
            raise ValueError("Palette name is required")
        if not self.background:
            raise ValueError("Background color is required")
        if not self.text:
            raise ValueError("Text color is required")

    def with_defaults(self) -> SyntaxPalette:
        """Return a new palette with empty fields filled from defaults.

        Uses text color as default for most fields, muted for less
        important elements.
        """
        # Can't modify frozen dataclass, so we return a new one
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
        """Generate CSS custom property declarations.

        Args:
            indent: Number of spaces to indent each line.

        Returns:
            CSS variable declarations as a string.
        """
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
    """Theme that adapts to light/dark mode preference.

    Combines a light and dark palette into a single adaptive theme
    that responds to user preferences via CSS media queries or
    data attributes.

    Attributes:
        name: Unique identifier for the adaptive palette.
        light: Palette for light mode.
        dark: Palette for dark mode.
    """

    name: str
    light: SyntaxPalette
    dark: SyntaxPalette

    def __post_init__(self) -> None:
        """Validate adaptive palette."""
        if not self.name:
            raise ValueError("Palette name is required")

    def to_css(
        self,
        css_class_style: CssClassStyle = "semantic",
        use_light_dark: bool = True,
    ) -> str:
        """Generate CSS for adaptive theme.

        Uses modern CSS light-dark() function with fallback for
        older browsers.

        Args:
            css_class_style: "semantic" for .syntax-* or "pygments" for .k, .nf
            use_light_dark: If True, use light-dark() CSS function.

        Returns:
            Complete CSS stylesheet as a string.
        """
        # Import here to avoid circular dependency
        from rosettes.themes._css import generate_css

        light_filled = self.light.with_defaults()
        dark_filled = self.dark.with_defaults()

        lines = [
            f"/* {self.name} - Adaptive Theme */",
            "/* Generated by Rosettes */",
            "",
        ]

        if use_light_dark:
            # Modern: light-dark() function (Chrome 123+, Firefox 120+, Safari 17.5+)
            lines.extend(
                [
                    ":root {",
                    "  color-scheme: light dark;",
                    "",
                    "  /* Modern: light-dark() function */",
                    f"  --syntax-bg: light-dark({light_filled.background}, {dark_filled.background});",
                    f"  --syntax-bg-highlight: light-dark({light_filled.background_highlight}, {dark_filled.background_highlight});",
                    f"  --syntax-control: light-dark({light_filled.control_flow}, {dark_filled.control_flow});",
                    f"  --syntax-declaration: light-dark({light_filled.declaration}, {dark_filled.declaration});",
                    f"  --syntax-import: light-dark({light_filled.import_}, {dark_filled.import_});",
                    f"  --syntax-string: light-dark({light_filled.string}, {dark_filled.string});",
                    f"  --syntax-number: light-dark({light_filled.number}, {dark_filled.number});",
                    f"  --syntax-boolean: light-dark({light_filled.boolean}, {dark_filled.boolean});",
                    f"  --syntax-type: light-dark({light_filled.type_}, {dark_filled.type_});",
                    f"  --syntax-function: light-dark({light_filled.function}, {dark_filled.function});",
                    f"  --syntax-variable: light-dark({light_filled.variable}, {dark_filled.variable});",
                    f"  --syntax-constant: light-dark({light_filled.constant}, {dark_filled.constant});",
                    f"  --syntax-comment: light-dark({light_filled.comment}, {dark_filled.comment});",
                    f"  --syntax-docstring: light-dark({light_filled.docstring}, {dark_filled.docstring});",
                    f"  --syntax-error: light-dark({light_filled.error}, {dark_filled.error});",
                    f"  --syntax-warning: light-dark({light_filled.warning}, {dark_filled.warning});",
                    f"  --syntax-added: light-dark({light_filled.added}, {dark_filled.added});",
                    f"  --syntax-removed: light-dark({light_filled.removed}, {dark_filled.removed});",
                    f"  --syntax-text: light-dark({light_filled.text}, {dark_filled.text});",
                    f"  --syntax-muted: light-dark({light_filled.muted}, {dark_filled.muted});",
                    f"  --syntax-punctuation: light-dark({light_filled.punctuation}, {dark_filled.punctuation});",
                    f"  --syntax-operator: light-dark({light_filled.operator}, {dark_filled.operator});",
                    f"  --syntax-attribute: light-dark({light_filled.attribute}, {dark_filled.attribute});",
                    f"  --syntax-namespace: light-dark({light_filled.namespace}, {dark_filled.namespace});",
                    f"  --syntax-tag: light-dark({light_filled.tag}, {dark_filled.tag});",
                    f"  --syntax-regex: light-dark({light_filled.regex}, {dark_filled.regex});",
                    f"  --syntax-escape: light-dark({light_filled.escape}, {dark_filled.escape});",
                    "}",
                    "",
                ]
            )

        # Fallback for older browsers
        lines.extend(
            [
                "/* Fallback for older browsers */",
                "@supports not (color: light-dark(white, black)) {",
                "  :root {",
                light_filled.to_css_vars(indent=4),
                "  }",
                "",
                "  @media (prefers-color-scheme: dark) {",
                "    :root {",
                dark_filled.to_css_vars(indent=6),
                "    }",
                "  }",
                "}",
                "",
            ]
        )

        # Explicit overrides via data attribute
        lines.extend(
            [
                "/* Explicit overrides via data attribute */",
                '[data-theme="dark"] {',
                dark_filled.to_css_vars(indent=2),
                "}",
                "",
                '[data-theme="light"] {',
                light_filled.to_css_vars(indent=2),
                "}",
                "",
            ]
        )

        # Add token classes
        lines.append(generate_css(css_class_style=css_class_style, include_vars=False))

        return "\n".join(lines)
