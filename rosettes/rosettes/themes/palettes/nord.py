"""Nord palette for Rosettes.

Nord — arctic, bluish color palette.
Based on Nord: https://www.nordtheme.com/

Features frost colors with excellent contrast.
"""

from rosettes.themes._palette import AdaptivePalette, SyntaxPalette

__all__ = ["NORD", "NORD_LIGHT", "NORD_DARK"]


NORD_LIGHT = SyntaxPalette(
    name="nord-light",
    # Background (Snow Storm)
    background="#eceff4",  # Nord6
    background_highlight="#e5e9f0",  # Nord5
    # Control & Structure (Frost)
    control_flow="#5e81ac",  # Nord10 (darker frost)
    declaration="#5e81ac",  # Nord10
    import_="#5e81ac",  # Nord10
    # Data & Literals (Aurora)
    string="#a3be8c",  # Nord14 (green)
    number="#b48ead",  # Nord15 (purple)
    boolean="#b48ead",  # Nord15
    # Identifiers
    type_="#81a1c1",  # Nord9 (frost)
    function="#88c0d0",  # Nord8 (frost)
    variable="#2e3440",  # Nord0 (dark)
    constant="#b48ead",  # Nord15
    # Documentation
    comment="#4c566a",  # Nord3 (dark gray)
    docstring="#4c566a",  # Nord3
    # Feedback (Aurora)
    error="#bf616a",  # Nord11 (red)
    warning="#ebcb8b",  # Nord13 (yellow)
    added="#a3be8c",  # Nord14 (green)
    removed="#bf616a",  # Nord11 (red)
    # Base
    text="#2e3440",  # Nord0
    muted="#4c566a",  # Nord3
    # Additional
    punctuation="#3b4252",  # Nord1
    operator="#81a1c1",  # Nord9
    attribute="#8fbcbb",  # Nord7
    namespace="#5e81ac",  # Nord10
    tag="#81a1c1",  # Nord9
    regex="#ebcb8b",  # Nord13
    escape="#d08770",  # Nord12 (orange)
    # Style
    bold_control=False,
    bold_declaration=False,
    italic_comment=True,
    italic_docstring=True,
)


NORD_DARK = SyntaxPalette(
    name="nord-dark",
    # Background (Polar Night)
    background="#2e3440",  # Nord0
    background_highlight="#3b4252",  # Nord1
    # Control & Structure (Frost)
    control_flow="#81a1c1",  # Nord9
    declaration="#81a1c1",  # Nord9
    import_="#81a1c1",  # Nord9
    # Data & Literals (Aurora)
    string="#a3be8c",  # Nord14 (green)
    number="#b48ead",  # Nord15 (purple)
    boolean="#b48ead",  # Nord15
    # Identifiers (Frost)
    type_="#8fbcbb",  # Nord7
    function="#88c0d0",  # Nord8
    variable="#d8dee9",  # Nord4
    constant="#b48ead",  # Nord15
    # Documentation
    comment="#616e88",  # Brightened Nord3
    docstring="#616e88",  # Brightened Nord3
    # Feedback (Aurora)
    error="#bf616a",  # Nord11 (red)
    warning="#ebcb8b",  # Nord13 (yellow)
    added="#a3be8c",  # Nord14 (green)
    removed="#bf616a",  # Nord11 (red)
    # Base (Snow Storm)
    text="#d8dee9",  # Nord4
    muted="#616e88",  # Brightened Nord3
    # Additional
    punctuation="#d8dee9",  # Nord4
    operator="#81a1c1",  # Nord9
    attribute="#8fbcbb",  # Nord7
    namespace="#5e81ac",  # Nord10
    tag="#81a1c1",  # Nord9
    regex="#ebcb8b",  # Nord13
    escape="#d08770",  # Nord12 (orange)
    # Style
    bold_control=False,
    bold_declaration=False,
    italic_comment=True,
    italic_docstring=True,
)


NORD = AdaptivePalette(
    name="nord",
    light=NORD_LIGHT,
    dark=NORD_DARK,
)
