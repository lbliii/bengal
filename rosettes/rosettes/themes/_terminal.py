"""Terminal (ANSI) palette support for Rosettes.

Provides palettes for terminal output using ANSI escape codes.
Supports 16-color, 256-color, and truecolor modes.

Thread-safe: All dataclasses are frozen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal

    ColorMode = Literal["16", "256", "truecolor"]

__all__ = ["TerminalPalette"]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB to (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _rgb_to_ansi256(r: int, g: int, b: int) -> int:
    """Convert RGB to nearest 256-color ANSI code.

    Uses the 6x6x6 color cube (codes 16-231) or grayscale (232-255).
    """
    # Check for grayscale (r ~= g ~= b)
    if abs(r - g) < 8 and abs(g - b) < 8:
        gray = (r + g + b) // 3
        if gray < 8:
            return 16
        if gray > 248:
            return 231
        return round((gray - 8) / 247 * 24) + 232

    # Map to 6x6x6 color cube
    def to_6(c: int) -> int:
        return round(c / 255 * 5)

    return 16 + 36 * to_6(r) + 6 * to_6(g) + to_6(b)


@dataclass(frozen=True, slots=True)
class TerminalPalette:
    """ANSI color palette for terminal output.

    Maps semantic roles to ANSI escape codes.
    Supports three color modes:
        - 16: Standard 16 ANSI colors (most compatible)
        - 256: Extended 256-color palette
        - truecolor: 24-bit RGB colors

    ANSI code format:
        - Standard: 30-37 (fg), 40-47 (bg), 90-97 (bright fg)
        - 256-color: 38;5;N (fg) or 48;5;N (bg)
        - Truecolor: 38;2;R;G;B (fg) or 48;2;R;G;B (bg)
        - Modifiers: 1 (bold), 2 (dim), 3 (italic), 4 (underline)

    Attributes:
        name: Unique identifier for the palette.
        control_flow: ANSI code for control keywords.
        declaration: ANSI code for declarations.
        import_: ANSI code for imports.
        string: ANSI code for strings.
        number: ANSI code for numbers.
        boolean: ANSI code for booleans.
        type_: ANSI code for types.
        function: ANSI code for functions.
        variable: ANSI code for variables.
        constant: ANSI code for constants.
        comment: ANSI code for comments.
        docstring: ANSI code for docstrings.
        error: ANSI code for errors.
        warning: ANSI code for warnings.
        added: ANSI code for diff additions.
        removed: ANSI code for diff removals.
        text: ANSI code for default text.
        muted: ANSI code for muted text.
        punctuation: ANSI code for punctuation.
        operator: ANSI code for operators.
        attribute: ANSI code for attributes.
        tag: ANSI code for tags.
        escape: ANSI code for escape sequences.
    """

    name: str

    # Control & Structure
    control_flow: str = "1;35"  # Bold magenta
    declaration: str = "1;34"  # Bold blue
    import_: str = "35"  # Magenta

    # Data & Literals
    string: str = "32"  # Green
    number: str = "33"  # Yellow
    boolean: str = "33"  # Yellow

    # Identifiers
    type_: str = "36"  # Cyan
    function: str = "34"  # Blue
    variable: str = "0"  # Default
    constant: str = "1;33"  # Bold yellow

    # Documentation
    comment: str = "2;37"  # Dim white (gray)
    docstring: str = "2;32"  # Dim green

    # Feedback
    error: str = "1;31"  # Bold red
    warning: str = "33"  # Yellow
    added: str = "32"  # Green
    removed: str = "31"  # Red

    # Base
    text: str = "0"  # Default
    muted: str = "2;37"  # Dim white

    # Additional
    punctuation: str = "0"  # Default
    operator: str = "35"  # Magenta
    attribute: str = "36"  # Cyan
    tag: str = "34"  # Blue
    escape: str = "33"  # Yellow

    @classmethod
    def from_syntax_palette(
        cls,
        palette: SyntaxPalette,  # Forward reference to avoid circular import
        color_mode: ColorMode = "256",
    ) -> TerminalPalette:
        """Convert a SyntaxPalette to ANSI codes.

        Args:
            palette: The syntax palette to convert.
            color_mode: Target color mode ("16", "256", or "truecolor").

        Returns:
            A new TerminalPalette with appropriate ANSI codes.
        """
        if color_mode == "16":
            # Use reasonable defaults for 16-color mode
            return cls(name=f"{palette.name}-terminal-16")

        filled = palette.with_defaults()

        if color_mode == "truecolor":
            return cls(
                name=f"{palette.name}-terminal-truecolor",
                control_flow=_hex_to_truecolor(filled.control_flow, bold=filled.bold_control),
                declaration=_hex_to_truecolor(filled.declaration, bold=filled.bold_declaration),
                import_=_hex_to_truecolor(filled.import_),
                string=_hex_to_truecolor(filled.string),
                number=_hex_to_truecolor(filled.number),
                boolean=_hex_to_truecolor(filled.boolean),
                type_=_hex_to_truecolor(filled.type_),
                function=_hex_to_truecolor(filled.function),
                variable=_hex_to_truecolor(filled.variable),
                constant=_hex_to_truecolor(filled.constant),
                comment=_hex_to_truecolor(filled.comment, italic=filled.italic_comment),
                docstring=_hex_to_truecolor(filled.docstring, italic=filled.italic_docstring),
                error=_hex_to_truecolor(filled.error, bold=True),
                warning=_hex_to_truecolor(filled.warning),
                added=_hex_to_truecolor(filled.added),
                removed=_hex_to_truecolor(filled.removed),
                text=_hex_to_truecolor(filled.text),
                muted=_hex_to_truecolor(filled.muted),
                punctuation=_hex_to_truecolor(filled.punctuation),
                operator=_hex_to_truecolor(filled.operator),
                attribute=_hex_to_truecolor(filled.attribute),
                tag=_hex_to_truecolor(filled.tag),
                escape=_hex_to_truecolor(filled.escape),
            )

        # 256-color mode
        return cls(
            name=f"{palette.name}-terminal-256",
            control_flow=_hex_to_256(filled.control_flow, bold=filled.bold_control),
            declaration=_hex_to_256(filled.declaration, bold=filled.bold_declaration),
            import_=_hex_to_256(filled.import_),
            string=_hex_to_256(filled.string),
            number=_hex_to_256(filled.number),
            boolean=_hex_to_256(filled.boolean),
            type_=_hex_to_256(filled.type_),
            function=_hex_to_256(filled.function),
            variable=_hex_to_256(filled.variable),
            constant=_hex_to_256(filled.constant),
            comment=_hex_to_256(filled.comment, italic=filled.italic_comment),
            docstring=_hex_to_256(filled.docstring, italic=filled.italic_docstring),
            error=_hex_to_256(filled.error, bold=True),
            warning=_hex_to_256(filled.warning),
            added=_hex_to_256(filled.added),
            removed=_hex_to_256(filled.removed),
            text=_hex_to_256(filled.text),
            muted=_hex_to_256(filled.muted),
            punctuation=_hex_to_256(filled.punctuation),
            operator=_hex_to_256(filled.operator),
            attribute=_hex_to_256(filled.attribute),
            tag=_hex_to_256(filled.tag),
            escape=_hex_to_256(filled.escape),
        )

    def get_code(self, role: str) -> str:
        """Get the ANSI code for a role name.

        Args:
            role: The role name (e.g., "control_flow", "string").

        Returns:
            The ANSI code string.
        """
        # Handle trailing underscore for Python reserved words
        attr = role if not role.endswith("_") else role
        return getattr(self, attr, self.text)


def _hex_to_truecolor(
    hex_color: str,
    *,
    bold: bool = False,
    italic: bool = False,
) -> str:
    """Convert hex color to truecolor ANSI code."""
    r, g, b = _hex_to_rgb(hex_color)
    code = f"38;2;{r};{g};{b}"

    modifiers = []
    if bold:
        modifiers.append("1")
    if italic:
        modifiers.append("3")

    if modifiers:
        return ";".join(modifiers) + ";" + code
    return code


def _hex_to_256(
    hex_color: str,
    *,
    bold: bool = False,
    italic: bool = False,
) -> str:
    """Convert hex color to 256-color ANSI code."""
    r, g, b = _hex_to_rgb(hex_color)
    color_code = _rgb_to_ansi256(r, g, b)
    code = f"38;5;{color_code}"

    modifiers = []
    if bold:
        modifiers.append("1")
    if italic:
        modifiers.append("3")

    if modifiers:
        return ";".join(modifiers) + ";" + code
    return code


# Import SyntaxPalette at module level for type checking
# The actual import happens in from_syntax_palette to avoid circular imports
if TYPE_CHECKING:
    from rosettes.themes._palette import SyntaxPalette
