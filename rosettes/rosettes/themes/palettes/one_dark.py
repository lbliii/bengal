"""One Dark palette for Rosettes.

One Dark — balanced dark theme from Atom.
Based on Atom's One Dark syntax theme.
"""

from rosettes.themes._palette import SyntaxPalette

__all__ = ["ONE_DARK"]


ONE_DARK = SyntaxPalette(
    name="one-dark",
    # Background
    background="#282c34",
    background_highlight="#2c313c",
    # Control & Structure
    control_flow="#c678dd",  # Purple (keywords)
    declaration="#c678dd",  # Purple
    import_="#c678dd",  # Purple
    # Data & Literals
    string="#98c379",  # Green
    number="#d19a66",  # Orange
    boolean="#d19a66",  # Orange
    # Identifiers
    type_="#e5c07b",  # Yellow
    function="#61afef",  # Blue
    variable="#e06c75",  # Red (variables in One Dark)
    constant="#d19a66",  # Orange
    # Documentation
    comment="#5c6370",  # Gray (dark)
    docstring="#5c6370",  # Gray
    # Feedback
    error="#e06c75",  # Red
    warning="#e5c07b",  # Yellow
    added="#98c379",  # Green
    removed="#e06c75",  # Red
    # Base
    text="#abb2bf",  # Foreground
    muted="#5c6370",  # Gray
    # Additional
    punctuation="#abb2bf",  # Foreground
    operator="#56b6c2",  # Cyan
    attribute="#e5c07b",  # Yellow (decorators)
    namespace="#e06c75",  # Red
    tag="#e06c75",  # Red
    regex="#98c379",  # Green
    escape="#56b6c2",  # Cyan
    # Style
    bold_control=False,
    bold_declaration=False,
    italic_comment=True,
    italic_docstring=True,
)
