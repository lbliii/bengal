"""Monokai palette for Rosettes.

Classic Monokai — warm, vibrant dark theme.
Inspired by Sublime Text's iconic color scheme.
"""

from rosettes.themes._palette import SyntaxPalette
from rosettes.themes._terminal import TerminalPalette

__all__ = ["MONOKAI", "TERMINAL_MONOKAI"]


MONOKAI = SyntaxPalette(
    name="monokai",
    # Background
    background="#272822",
    background_highlight="#49483e",
    # Control & Structure
    control_flow="#f92672",  # Pink/magenta
    declaration="#66d9ef",  # Cyan
    import_="#f92672",  # Pink
    # Data & Literals
    string="#e6db74",  # Yellow
    number="#ae81ff",  # Purple
    boolean="#ae81ff",  # Purple
    # Identifiers
    type_="#a6e22e",  # Green
    function="#a6e22e",  # Green
    variable="#f8f8f2",  # White
    constant="#ae81ff",  # Purple
    # Documentation
    comment="#75715e",  # Gray/brown
    docstring="#75715e",  # Gray/brown
    # Feedback
    error="#f92672",  # Pink
    warning="#e6db74",  # Yellow
    added="#a6e22e",  # Green
    removed="#f92672",  # Pink
    # Base
    text="#f8f8f2",  # White
    muted="#75715e",  # Gray
    # Additional
    punctuation="#f8f8f2",  # White
    operator="#f92672",  # Pink
    attribute="#a6e22e",  # Green (decorators)
    namespace="#f8f8f2",  # White
    tag="#f92672",  # Pink
    regex="#e6db74",  # Yellow
    escape="#ae81ff",  # Purple
    # Style
    bold_control=True,
    bold_declaration=False,
    italic_comment=True,
    italic_docstring=True,
)


TERMINAL_MONOKAI = TerminalPalette(
    name="monokai-terminal",
    # Control & Structure
    control_flow="38;5;197",  # Pink
    declaration="38;5;81",  # Cyan
    import_="38;5;197",  # Pink
    # Data & Literals
    string="38;5;186",  # Yellow
    number="38;5;141",  # Purple
    boolean="38;5;141",  # Purple
    # Identifiers
    type_="38;5;148",  # Green
    function="38;5;148",  # Green
    variable="38;5;231",  # White
    constant="38;5;141",  # Purple
    # Documentation
    comment="38;5;102",  # Gray
    docstring="3;38;5;102",  # Italic gray
    # Feedback
    error="1;38;5;197",  # Bold pink
    warning="38;5;186",  # Yellow
    added="38;5;148",  # Green
    removed="38;5;197",  # Pink
    # Base
    text="38;5;231",  # White
    muted="38;5;102",  # Gray
    # Additional
    punctuation="38;5;231",
    operator="38;5;197",
    attribute="38;5;148",
    tag="38;5;197",
    escape="38;5;141",
)
