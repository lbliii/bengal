"""GitHub palette for Rosettes.

GitHub — adaptive light/dark theme matching GitHub's syntax highlighting.
Automatically adapts to user's color scheme preference.
"""

from rosettes.themes._palette import AdaptivePalette, SyntaxPalette

__all__ = ["GITHUB", "GITHUB_LIGHT", "GITHUB_DARK"]


GITHUB_LIGHT = SyntaxPalette(
    name="github-light",
    # Background
    background="#ffffff",
    background_highlight="#fffbdd",
    # Control & Structure
    control_flow="#d73a49",  # Red (keywords)
    declaration="#d73a49",  # Red
    import_="#d73a49",  # Red
    # Data & Literals
    string="#032f62",  # Dark blue
    number="#005cc5",  # Blue
    boolean="#005cc5",  # Blue
    # Identifiers
    type_="#6f42c1",  # Purple
    function="#6f42c1",  # Purple
    variable="#24292e",  # Dark
    constant="#005cc5",  # Blue
    # Documentation
    comment="#6a737d",  # Gray
    docstring="#6a737d",  # Gray
    # Feedback
    error="#cb2431",  # Error red
    warning="#b08800",  # Warning yellow
    added="#22863a",  # Green
    removed="#cb2431",  # Red
    # Base
    text="#24292e",  # Dark
    muted="#6a737d",  # Gray
    # Additional
    punctuation="#24292e",  # Dark
    operator="#d73a49",  # Red
    attribute="#6f42c1",  # Purple
    namespace="#005cc5",  # Blue
    tag="#22863a",  # Green
    regex="#032f62",  # Dark blue
    escape="#005cc5",  # Blue
    # Style
    bold_control=True,
    bold_declaration=True,
    italic_comment=True,
    italic_docstring=True,
)


GITHUB_DARK = SyntaxPalette(
    name="github-dark",
    # Background
    background="#0d1117",
    background_highlight="#161b22",
    # Control & Structure
    control_flow="#ff7b72",  # Coral
    declaration="#ff7b72",  # Coral
    import_="#ff7b72",  # Coral
    # Data & Literals
    string="#a5d6ff",  # Light blue
    number="#79c0ff",  # Blue
    boolean="#79c0ff",  # Blue
    # Identifiers
    type_="#d2a8ff",  # Light purple
    function="#d2a8ff",  # Light purple
    variable="#c9d1d9",  # Light gray
    constant="#79c0ff",  # Blue
    # Documentation
    comment="#8b949e",  # Gray
    docstring="#8b949e",  # Gray
    # Feedback
    error="#f85149",  # Error red
    warning="#d29922",  # Warning yellow
    added="#3fb950",  # Green
    removed="#f85149",  # Red
    # Base
    text="#c9d1d9",  # Light gray
    muted="#8b949e",  # Gray
    # Additional
    punctuation="#c9d1d9",  # Light gray
    operator="#ff7b72",  # Coral
    attribute="#d2a8ff",  # Light purple
    namespace="#79c0ff",  # Blue
    tag="#7ee787",  # Green
    regex="#a5d6ff",  # Light blue
    escape="#79c0ff",  # Blue
    # Style
    bold_control=True,
    bold_declaration=True,
    italic_comment=True,
    italic_docstring=True,
)


GITHUB = AdaptivePalette(
    name="github",
    light=GITHUB_LIGHT,
    dark=GITHUB_DARK,
)
