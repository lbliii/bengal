"""Bengal brand palettes for Rosettes.

Bengal-native palettes designed to integrate with Bengal's design token system.
Features the signature Bengal orange accent color.

Variants:
    - BENGAL_TIGER: Primary dark theme (orange accent)
    - BENGAL_SNOW_LYNX: Light theme (teal accent)
    - BENGAL_CHARCOAL: Minimal dark variant
"""

from rosettes.themes._palette import SyntaxPalette

__all__ = ["BENGAL_TIGER", "BENGAL_SNOW_LYNX", "BENGAL_CHARCOAL"]


BENGAL_TIGER = SyntaxPalette(
    name="bengal-tiger",
    # Background
    background="#1a1a1a",
    background_highlight="#2d2d2d",
    # Control & Structure
    control_flow="#FF9D00",  # Bengal orange (primary)
    declaration="#3498DB",  # Blue (secondary)
    import_="#FF9D00",  # Bengal orange
    # Data & Literals
    string="#2ECC71",  # Emerald green
    number="#E67E22",  # Carrot orange
    boolean="#E67E22",  # Carrot orange
    # Identifiers
    type_="#9b59b6",  # Purple
    function="#3498DB",  # Blue
    variable="#e0e0e0",  # Light gray
    constant="#F1C40F",  # Yellow (accent)
    # Documentation
    comment="#757575",  # Muted gray
    docstring="#9e9e9e",  # Secondary gray
    # Feedback
    error="#E74C3C",  # Alizarin red
    warning="#F1C40F",  # Yellow
    added="#2ECC71",  # Green
    removed="#E74C3C",  # Red
    # Base
    text="#e0e0e0",  # Light gray
    muted="#757575",  # Muted
    # Additional
    punctuation="#bdbdbd",  # Gray
    operator="#FF9D00",  # Bengal orange
    attribute="#9b59b6",  # Purple (decorators)
    namespace="#3498DB",  # Blue
    tag="#E74C3C",  # Red
    regex="#2ECC71",  # Green
    escape="#F1C40F",  # Yellow
    # Style
    bold_control=True,
    bold_declaration=True,
    italic_comment=True,
    italic_docstring=True,
)


BENGAL_SNOW_LYNX = SyntaxPalette(
    name="bengal-snow-lynx",
    # Background
    background="#fafafa",
    background_highlight="#f0f0f0",
    # Control & Structure
    control_flow="#00796B",  # Teal (primary for light)
    declaration="#1976D2",  # Blue
    import_="#00796B",  # Teal
    # Data & Literals
    string="#2E7D32",  # Green
    number="#E65100",  # Deep orange
    boolean="#E65100",  # Deep orange
    # Identifiers
    type_="#7B1FA2",  # Purple
    function="#1976D2",  # Blue
    variable="#212121",  # Near black
    constant="#F57C00",  # Orange
    # Documentation
    comment="#757575",  # Gray
    docstring="#9e9e9e",  # Light gray
    # Feedback
    error="#C62828",  # Red
    warning="#F9A825",  # Amber
    added="#2E7D32",  # Green
    removed="#C62828",  # Red
    # Base
    text="#212121",  # Near black
    muted="#757575",  # Gray
    # Additional
    punctuation="#424242",  # Dark gray
    operator="#00796B",  # Teal
    attribute="#7B1FA2",  # Purple
    namespace="#1976D2",  # Blue
    tag="#C62828",  # Red
    regex="#2E7D32",  # Green
    escape="#F57C00",  # Orange
    # Style
    bold_control=True,
    bold_declaration=True,
    italic_comment=True,
    italic_docstring=True,
)


BENGAL_CHARCOAL = SyntaxPalette(
    name="bengal-charcoal",
    # Background (very dark, minimal)
    background="#121212",
    background_highlight="#1e1e1e",
    # Control & Structure (muted orange)
    control_flow="#FFB74D",  # Soft orange
    declaration="#64B5F6",  # Light blue
    import_="#FFB74D",  # Soft orange
    # Data & Literals
    string="#81C784",  # Soft green
    number="#FFB74D",  # Soft orange
    boolean="#FFB74D",  # Soft orange
    # Identifiers
    type_="#CE93D8",  # Soft purple
    function="#64B5F6",  # Light blue
    variable="#e0e0e0",  # Light gray
    constant="#FFF176",  # Soft yellow
    # Documentation
    comment="#616161",  # Dark gray
    docstring="#757575",  # Gray
    # Feedback
    error="#EF5350",  # Soft red
    warning="#FFF176",  # Soft yellow
    added="#81C784",  # Soft green
    removed="#EF5350",  # Soft red
    # Base
    text="#e0e0e0",  # Light gray
    muted="#616161",  # Dark gray
    # Additional
    punctuation="#9e9e9e",  # Gray
    operator="#FFB74D",  # Soft orange
    attribute="#CE93D8",  # Soft purple
    namespace="#64B5F6",  # Light blue
    tag="#EF5350",  # Soft red
    regex="#81C784",  # Soft green
    escape="#FFF176",  # Soft yellow
    # Style
    bold_control=False,
    bold_declaration=False,
    italic_comment=True,
    italic_docstring=True,
)
