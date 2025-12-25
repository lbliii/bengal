"""Built-in syntax highlighting palettes for Bengal.

These palettes are designed to work with Bengal's design token system
and support both light and dark modes.

Bengal-specific palettes:
    - BENGAL_TIGER: Dark theme with orange accent (default)
    - BENGAL_SNOW_LYNX: Light theme with teal accent
    - BENGAL_CHARCOAL: Minimal dark theme

Third-party palettes:
    - MONOKAI: Classic dark theme
    - DRACULA: Purple-accented dark theme
    - GITHUB: GitHub adaptive (light/dark)
"""

from bengal.rendering.rosettes.themes._palette import AdaptivePalette, SyntaxPalette

__all__ = [
    # Bengal palettes
    "BENGAL_TIGER",
    "BENGAL_SNOW_LYNX",
    "BENGAL_CHARCOAL",
    "BENGAL_BLUE",
    # Third-party palettes
    "MONOKAI",
    "DRACULA",
    "GITHUB_LIGHT",
    "GITHUB_DARK",
    "GITHUB",
]

# =============================================================================
# Bengal Native Palettes
# =============================================================================

BENGAL_TIGER = SyntaxPalette(
    name="bengal-tiger",
    background="#1a1a1a",
    background_highlight="#2d2d2d",
    text="#e0e0e0",
    control_flow="#FF9D00",  # Bengal orange (primary)
    declaration="#3498DB",  # Blue (secondary)
    import_="#FF9D00",
    string="#2ECC71",  # Emerald green
    number="#E67E22",  # Carrot orange
    boolean="#E67E22",
    type_="#9b59b6",  # Purple
    function="#3498DB",
    variable="#e0e0e0",
    constant="#F1C40F",  # Yellow (accent)
    comment="#757575",  # Muted gray
    docstring="#9e9e9e",
    error="#E74C3C",  # Alizarin red
    warning="#F1C40F",
    added="#2ECC71",
    removed="#E74C3C",
    muted="#757575",
    punctuation="#9e9e9e",
    operator="#FF9D00",
    attribute="#9b59b6",
    namespace="#3498DB",
    tag="#E74C3C",
    regex="#2ECC71",
    escape="#F1C40F",
)

BENGAL_SNOW_LYNX = SyntaxPalette(
    name="bengal-snow-lynx",
    background="#FAF8F5",  # Warm cream
    background_highlight="#F4F0EA",
    text="#252525",  # Soft charcoal
    control_flow="#3D9287",  # Teal (primary)
    declaration="#4FA8A0",  # Ice blue
    import_="#3D9287",
    string="#4A8570",  # Muted green
    number="#B8845A",  # Warm brown
    boolean="#B8845A",
    type_="#7C6F9B",  # Muted purple
    function="#4FA8A0",
    variable="#5F5B56",
    constant="#D97706",  # Amber
    comment="#847F78",
    docstring="#847F78",
    error="#C62828",
    warning="#D97706",
    added="#2E7D5A",
    removed="#C62828",
    muted="#AFA9A1",
    punctuation="#847F78",
    operator="#3D9287",
    attribute="#7C6F9B",
    namespace="#4FA8A0",
    tag="#C62828",
    regex="#4A8570",
    escape="#D97706",
)

BENGAL_CHARCOAL = SyntaxPalette(
    name="bengal-charcoal",
    background="#1e1e1e",
    background_highlight="#2d2d2d",
    text="#c9d1d9",
    control_flow="#79c0ff",  # Light blue
    declaration="#d2a8ff",  # Light purple
    import_="#79c0ff",
    string="#a5d6ff",  # Pale blue
    number="#79c0ff",
    boolean="#79c0ff",
    type_="#d2a8ff",
    function="#d2a8ff",
    variable="#c9d1d9",
    constant="#79c0ff",
    comment="#8b949e",
    docstring="#8b949e",
    error="#f85149",
    warning="#d29922",
    added="#3fb950",
    removed="#f85149",
    muted="#8b949e",
    punctuation="#8b949e",
    operator="#79c0ff",
    attribute="#d2a8ff",
    namespace="#d2a8ff",
    tag="#7ee787",
    regex="#a5d6ff",
    escape="#79c0ff",
)

BENGAL_BLUE = SyntaxPalette(
    name="bengal-blue",
    background="#0d1117",
    background_highlight="#161b22",
    text="#c9d1d9",
    control_flow="#79c0ff",  # Light blue
    declaration="#79c0ff",
    import_="#79c0ff",
    string="#a5d6ff",
    number="#79c0ff",
    boolean="#79c0ff",
    type_="#79c0ff",
    function="#d2a8ff",  # Purple for functions
    variable="#c9d1d9",
    constant="#79c0ff",
    comment="#8b949e",
    docstring="#8b949e",
    error="#f85149",
    warning="#d29922",
    added="#3fb950",
    removed="#f85149",
    muted="#8b949e",
    punctuation="#8b949e",
    operator="#79c0ff",
    attribute="#d2a8ff",
    namespace="#79c0ff",
    tag="#7ee787",
    regex="#a5d6ff",
    escape="#79c0ff",
)

# =============================================================================
# Third-Party Palettes
# =============================================================================

MONOKAI = SyntaxPalette(
    name="monokai",
    background="#272822",
    background_highlight="#49483e",
    text="#f8f8f2",
    control_flow="#f92672",  # Pink
    declaration="#66d9ef",  # Cyan
    import_="#f92672",
    string="#e6db74",  # Yellow
    number="#ae81ff",  # Purple
    boolean="#ae81ff",
    type_="#a6e22e",  # Green
    function="#a6e22e",
    variable="#f8f8f2",
    constant="#ae81ff",
    comment="#75715e",  # Gray
    docstring="#75715e",
    error="#f92672",
    warning="#e6db74",
    added="#a6e22e",
    removed="#f92672",
    muted="#75715e",
    punctuation="#f8f8f2",
    operator="#f92672",
    attribute="#a6e22e",
    namespace="#66d9ef",
    tag="#f92672",
    regex="#e6db74",
    escape="#ae81ff",
)

DRACULA = SyntaxPalette(
    name="dracula",
    background="#282a36",
    background_highlight="#44475a",
    text="#f8f8f2",
    control_flow="#ff79c6",  # Pink
    declaration="#8be9fd",  # Cyan
    import_="#ff79c6",
    string="#f1fa8c",  # Yellow
    number="#bd93f9",  # Purple
    boolean="#bd93f9",
    type_="#50fa7b",  # Green
    function="#50fa7b",
    variable="#f8f8f2",
    constant="#bd93f9",
    comment="#6272a4",  # Comment blue
    docstring="#6272a4",
    error="#ff5555",  # Red
    warning="#ffb86c",  # Orange
    added="#50fa7b",
    removed="#ff5555",
    muted="#6272a4",
    punctuation="#f8f8f2",
    operator="#ff79c6",
    attribute="#50fa7b",
    namespace="#8be9fd",
    tag="#ff79c6",
    regex="#f1fa8c",
    escape="#bd93f9",
)

GITHUB_LIGHT = SyntaxPalette(
    name="github-light",
    background="#ffffff",
    background_highlight="#fffbdd",
    text="#24292e",
    control_flow="#d73a49",  # Red
    declaration="#6f42c1",  # Purple
    import_="#d73a49",
    string="#032f62",  # Dark blue
    number="#005cc5",  # Blue
    boolean="#005cc5",
    type_="#6f42c1",
    function="#6f42c1",
    variable="#24292e",
    constant="#005cc5",
    comment="#6a737d",  # Gray
    docstring="#6a737d",
    error="#cb2431",
    warning="#b08800",
    added="#22863a",
    removed="#cb2431",
    muted="#6a737d",
    punctuation="#24292e",
    operator="#d73a49",
    attribute="#6f42c1",
    namespace="#6f42c1",
    tag="#22863a",
    regex="#032f62",
    escape="#005cc5",
)

GITHUB_DARK = SyntaxPalette(
    name="github-dark",
    background="#0d1117",
    background_highlight="#161b22",
    text="#c9d1d9",
    control_flow="#ff7b72",  # Coral
    declaration="#d2a8ff",  # Light purple
    import_="#ff7b72",
    string="#a5d6ff",  # Light blue
    number="#79c0ff",  # Blue
    boolean="#79c0ff",
    type_="#d2a8ff",
    function="#d2a8ff",
    variable="#c9d1d9",
    constant="#79c0ff",
    comment="#8b949e",  # Gray
    docstring="#8b949e",
    error="#f85149",
    warning="#d29922",
    added="#3fb950",
    removed="#f85149",
    muted="#8b949e",
    punctuation="#c9d1d9",
    operator="#ff7b72",
    attribute="#d2a8ff",
    namespace="#d2a8ff",
    tag="#7ee787",
    regex="#a5d6ff",
    escape="#79c0ff",
)

GITHUB = AdaptivePalette(
    name="github",
    light=GITHUB_LIGHT,
    dark=GITHUB_DARK,
)
