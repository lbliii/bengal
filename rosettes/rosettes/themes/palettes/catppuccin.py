"""Catppuccin palette for Rosettes.

Catppuccin — soothing pastel theme with warm colors.
Based on Catppuccin: https://catppuccin.com/

Flavors:
    - Latte: Light mode (warm, creamy)
    - Mocha: Dark mode (rich, deep)
"""

from rosettes.themes._palette import AdaptivePalette, SyntaxPalette

__all__ = ["CATPPUCCIN", "CATPPUCCIN_LATTE", "CATPPUCCIN_MOCHA"]


CATPPUCCIN_LATTE = SyntaxPalette(
    name="catppuccin-latte",
    # Background (Base)
    background="#eff1f5",
    background_highlight="#e6e9ef",
    # Control & Structure
    control_flow="#8839ef",  # Mauve
    declaration="#8839ef",  # Mauve
    import_="#8839ef",  # Mauve
    # Data & Literals
    string="#40a02b",  # Green
    number="#fe640b",  # Peach
    boolean="#fe640b",  # Peach
    # Identifiers
    type_="#df8e1d",  # Yellow
    function="#1e66f5",  # Blue
    variable="#4c4f69",  # Text
    constant="#fe640b",  # Peach
    # Documentation
    comment="#9ca0b0",  # Overlay0
    docstring="#9ca0b0",  # Overlay0
    # Feedback
    error="#d20f39",  # Red
    warning="#df8e1d",  # Yellow
    added="#40a02b",  # Green
    removed="#d20f39",  # Red
    # Base
    text="#4c4f69",  # Text
    muted="#9ca0b0",  # Overlay0
    # Additional
    punctuation="#5c5f77",  # Subtext1
    operator="#04a5e5",  # Sky
    attribute="#dc8a78",  # Rosewater
    namespace="#e64553",  # Maroon
    tag="#179299",  # Teal
    regex="#40a02b",  # Green
    escape="#04a5e5",  # Sky
    # Style
    bold_control=False,
    bold_declaration=False,
    italic_comment=True,
    italic_docstring=True,
)


CATPPUCCIN_MOCHA = SyntaxPalette(
    name="catppuccin-mocha",
    # Background (Base)
    background="#1e1e2e",
    background_highlight="#313244",
    # Control & Structure
    control_flow="#cba6f7",  # Mauve
    declaration="#cba6f7",  # Mauve
    import_="#cba6f7",  # Mauve
    # Data & Literals
    string="#a6e3a1",  # Green
    number="#fab387",  # Peach
    boolean="#fab387",  # Peach
    # Identifiers
    type_="#f9e2af",  # Yellow
    function="#89b4fa",  # Blue
    variable="#cdd6f4",  # Text
    constant="#fab387",  # Peach
    # Documentation
    comment="#6c7086",  # Overlay0
    docstring="#6c7086",  # Overlay0
    # Feedback
    error="#f38ba8",  # Red
    warning="#f9e2af",  # Yellow
    added="#a6e3a1",  # Green
    removed="#f38ba8",  # Red
    # Base
    text="#cdd6f4",  # Text
    muted="#6c7086",  # Overlay0
    # Additional
    punctuation="#a6adc8",  # Subtext1
    operator="#89dceb",  # Sky
    attribute="#f5e0dc",  # Rosewater
    namespace="#eba0ac",  # Maroon
    tag="#94e2d5",  # Teal
    regex="#a6e3a1",  # Green
    escape="#89dceb",  # Sky
    # Style
    bold_control=False,
    bold_declaration=False,
    italic_comment=True,
    italic_docstring=True,
)


CATPPUCCIN = AdaptivePalette(
    name="catppuccin",
    light=CATPPUCCIN_LATTE,
    dark=CATPPUCCIN_MOCHA,
)
