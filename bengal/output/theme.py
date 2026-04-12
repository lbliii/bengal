"""Bengal CLI theme — milo ThemeStyle definitions.

Maps Bengal's visual identity to milo's theme system. These styles are used
by CLIOutput for all terminal coloring via ANSI SGR codes, replacing the
previous Rich-based theme.

Color palette:
    Primary (Orange):  #FF9D00 — headers, mascot, brand
    Success (Green):   #2ECC71 — success messages, phase icons
    Warning (Orange):  #E67E22 — warnings
    Error (Red):       #E74C3C — errors, mouse mascot
    Info (Silver):     #95A5A6 — informational text
    Path (Blue):       #3498DB — file paths, links
    Accent (Yellow):   #F1C40F — highlights, metric labels, prompts
    Tip (Gray):        #7F8C8D — tips, suggestions
"""

from __future__ import annotations

from milo.theme import DEFAULT_THEME, ThemeStyle

BENGAL_THEME: dict[str, ThemeStyle] = {
    **DEFAULT_THEME,
    # Brand
    "bengal": ThemeStyle(fg="#FF9D00", bold=True),
    "header": ThemeStyle(fg="#FF9D00", bold=True),
    # Status
    "success": ThemeStyle(fg="#2ECC71"),
    "warning": ThemeStyle(fg="#E67E22"),
    "error": ThemeStyle(fg="#E74C3C", bold=True),
    "info": ThemeStyle(fg="#95A5A6"),
    # Structural
    "phase": ThemeStyle(bold=True),
    "path": ThemeStyle(fg="#3498DB"),
    "dim": ThemeStyle(dim=True),
    "tip": ThemeStyle(fg="#7F8C8D", italic=True),
    # Metrics
    "highlight": ThemeStyle(fg="#F1C40F", bold=True),
    "metric_label": ThemeStyle(fg="#F1C40F", bold=True),
    "metric_value": ThemeStyle(),
    # Interaction
    "prompt": ThemeStyle(fg="#F1C40F"),
    # Error mascot
    "mouse": ThemeStyle(fg="#E74C3C", bold=True),
}
