"""WCAG contrast validation for Rosettes palettes.

Ensures palettes meet accessibility requirements for syntax highlighting.
Uses WCAG 2.1 contrast ratio calculations.

Thread-safe: All functions are pure (no side effects).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rosettes.themes._palette import SyntaxPalette

__all__ = [
    "contrast_ratio",
    "validate_palette",
    "ContrastWarning",
    "WCAG_AA_NORMAL",
    "WCAG_AA_LARGE",
    "WCAG_AAA_NORMAL",
]

# WCAG contrast ratio thresholds
WCAG_AA_NORMAL = 4.5  # Normal text (< 18pt or < 14pt bold)
WCAG_AA_LARGE = 3.0  # Large text (>= 18pt or >= 14pt bold)
WCAG_AAA_NORMAL = 7.0  # Enhanced contrast


def _relative_luminance(hex_color: str) -> float:
    """Calculate relative luminance per WCAG 2.1.

    Formula: L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    where R, G, B are linearized sRGB values.

    Args:
        hex_color: Color in #RRGGBB format.

    Returns:
        Relative luminance value between 0 and 1.
    """
    hex_color = hex_color.lstrip("#")

    # Handle short hex (#RGB)
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    def linearize(c: int) -> float:
        """Convert 8-bit sRGB to linear RGB."""
        c_normalized = c / 255
        if c_normalized <= 0.03928:
            return c_normalized / 12.92
        return ((c_normalized + 0.055) / 1.055) ** 2.4

    r_lin = linearize(r)
    g_lin = linearize(g)
    b_lin = linearize(b)

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(fg: str, bg: str) -> float:
    """Calculate WCAG contrast ratio between foreground and background.

    Args:
        fg: Foreground color in #RRGGBB format.
        bg: Background color in #RRGGBB format.

    Returns:
        Contrast ratio between 1 and 21.
    """
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)


@dataclass(frozen=True)
class ContrastWarning:
    """Warning about insufficient contrast.

    Attributes:
        role: The role with insufficient contrast.
        color: The color value.
        background: The background color.
        ratio: The calculated contrast ratio.
        required: The minimum required ratio.
    """

    role: str
    color: str
    background: str
    ratio: float
    required: float

    def __str__(self) -> str:
        return (
            f"{self.role}: {self.color} has contrast {self.ratio:.2f}:1 "
            f"against {self.background} (needs {self.required}:1 for WCAG AA)"
        )


def validate_palette(
    palette: SyntaxPalette,
    *,
    min_ratio: float = WCAG_AA_NORMAL,
    check_all_roles: bool = False,
) -> list[ContrastWarning]:
    """Validate palette meets WCAG contrast requirements.

    Checks that all token colors have sufficient contrast against
    the background color.

    Args:
        palette: The palette to validate.
        min_ratio: Minimum contrast ratio (default: WCAG AA 4.5:1).
        check_all_roles: If True, check all roles. If False, check critical roles.

    Returns:
        List of ContrastWarning objects for roles that fail.
    """
    warnings: list[ContrastWarning] = []
    filled = palette.with_defaults()

    # Critical roles that must pass (always visible, frequently used)
    critical_roles = [
        ("control_flow", filled.control_flow),
        ("declaration", filled.declaration),
        ("string", filled.string),
        ("number", filled.number),
        ("comment", filled.comment),
        ("text", filled.text),
        ("function", filled.function),
        ("type", filled.type_),
    ]

    # All roles for comprehensive check
    all_roles = [
        *critical_roles,
        ("import", filled.import_),
        ("boolean", filled.boolean),
        ("variable", filled.variable),
        ("constant", filled.constant),
        ("docstring", filled.docstring),
        ("error", filled.error),
        ("warning", filled.warning),
        ("added", filled.added),
        ("removed", filled.removed),
        ("muted", filled.muted),
        ("punctuation", filled.punctuation),
        ("operator", filled.operator),
        ("attribute", filled.attribute),
        ("namespace", filled.namespace),
        ("tag", filled.tag),
        ("regex", filled.regex),
        ("escape", filled.escape),
    ]

    roles_to_check = all_roles if check_all_roles else critical_roles

    for role_name, color in roles_to_check:
        try:
            ratio = contrast_ratio(color, filled.background)
            if ratio < min_ratio:
                warnings.append(
                    ContrastWarning(
                        role=role_name,
                        color=color,
                        background=filled.background,
                        ratio=ratio,
                        required=min_ratio,
                    )
                )
        except (ValueError, IndexError):
            # Invalid color format, skip
            warnings.append(
                ContrastWarning(
                    role=role_name,
                    color=color,
                    background=filled.background,
                    ratio=0.0,
                    required=min_ratio,
                )
            )

    return warnings


def is_dark_palette(palette: SyntaxPalette) -> bool:
    """Determine if a palette is dark (light text on dark background).

    Args:
        palette: The palette to check.

    Returns:
        True if the palette is dark-themed.
    """
    bg_luminance = _relative_luminance(palette.background)
    return bg_luminance < 0.5


def suggest_contrast_fix(
    fg: str,
    bg: str,
    target_ratio: float = WCAG_AA_NORMAL,
) -> str | None:
    """Suggest an adjusted foreground color to meet contrast requirements.

    Simple adjustment that lightens or darkens the color.

    Args:
        fg: Current foreground color.
        bg: Background color.
        target_ratio: Target contrast ratio.

    Returns:
        Adjusted hex color, or None if already meets requirements.
    """
    current_ratio = contrast_ratio(fg, bg)
    if current_ratio >= target_ratio:
        return None

    bg_luminance = _relative_luminance(bg)
    is_dark_bg = bg_luminance < 0.5

    # Parse current color
    fg = fg.lstrip("#")
    r = int(fg[0:2], 16)
    g = int(fg[2:4], 16)
    b = int(fg[4:6], 16)

    # Adjust in direction of better contrast
    step = 10 if is_dark_bg else -10
    max_iterations = 50

    for _ in range(max_iterations):
        r = max(0, min(255, r + step))
        g = max(0, min(255, g + step))
        b = max(0, min(255, b + step))

        new_color = f"#{r:02x}{g:02x}{b:02x}"
        new_ratio = contrast_ratio(new_color, f"#{bg}")

        if new_ratio >= target_ratio:
            return new_color

        # Reached bounds without meeting target
        if (is_dark_bg and r >= 255 and g >= 255 and b >= 255) or (
            not is_dark_bg and r <= 0 and g <= 0 and b <= 0
        ):
            break

    return None
