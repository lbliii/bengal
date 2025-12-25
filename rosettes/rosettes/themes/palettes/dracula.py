"""Dracula palette for Rosettes.

Dracula — a dark theme with purple accents.
Based on the popular Dracula theme: https://draculatheme.com/
"""

from rosettes.themes._palette import SyntaxPalette

__all__ = ["DRACULA"]


DRACULA = SyntaxPalette(
    name="dracula",
    # Background
    background="#282a36",
    background_highlight="#44475a",
    # Control & Structure
    control_flow="#ff79c6",  # Pink
    declaration="#ff79c6",  # Pink
    import_="#ff79c6",  # Pink
    # Data & Literals
    string="#f1fa8c",  # Yellow
    number="#bd93f9",  # Purple
    boolean="#bd93f9",  # Purple
    # Identifiers
    type_="#8be9fd",  # Cyan
    function="#50fa7b",  # Green
    variable="#f8f8f2",  # Foreground
    constant="#bd93f9",  # Purple
    # Documentation
    comment="#6272a4",  # Comment gray-blue
    docstring="#6272a4",  # Comment gray-blue
    # Feedback
    error="#ff5555",  # Red
    warning="#ffb86c",  # Orange
    added="#50fa7b",  # Green
    removed="#ff5555",  # Red
    # Base
    text="#f8f8f2",  # Foreground
    muted="#6272a4",  # Comment
    # Additional
    punctuation="#f8f8f2",  # Foreground
    operator="#ff79c6",  # Pink
    attribute="#50fa7b",  # Green
    namespace="#f8f8f2",  # Foreground
    tag="#ff79c6",  # Pink
    regex="#f1fa8c",  # Yellow
    escape="#ff79c6",  # Pink
    # Style
    bold_control=False,
    bold_declaration=False,
    italic_comment=True,
    italic_docstring=True,
)
