"""
Token generator for Bengal web CSS and terminal TCSS.

Generates consistent CSS custom properties and Textual CSS variables
from the shared token definitions in tokens.py.

Usage:
    python -m bengal.themes.generate

This outputs:
    - bengal/themes/default/assets/css/tokens/generated.css (web)
    - Updates validation that TCSS matches tokens

Related:
    - bengal/themes/tokens.py: Source token definitions
    - bengal/cli/dashboard/bengal.tcss: Terminal styles
"""

from __future__ import annotations

from pathlib import Path

from bengal.themes.tokens import BENGAL_PALETTE, PALETTE_VARIANTS


def generate_web_css() -> str:
    """
    Generate CSS custom properties from Bengal tokens.

    Returns:
        CSS string with :root variables
    """
    lines = [
        "/* Generated from bengal/themes/tokens.py - DO NOT EDIT */",
        "/* Run: python -m bengal.themes.generate */",
        "",
        ":root {",
        "  /* Brand Colors */",
        f"  --bengal-primary: {BENGAL_PALETTE.primary};",
        f"  --bengal-secondary: {BENGAL_PALETTE.secondary};",
        f"  --bengal-accent: {BENGAL_PALETTE.accent};",
        "",
        "  /* Semantic Colors */",
        f"  --bengal-success: {BENGAL_PALETTE.success};",
        f"  --bengal-warning: {BENGAL_PALETTE.warning};",
        f"  --bengal-error: {BENGAL_PALETTE.error};",
        f"  --bengal-info: {BENGAL_PALETTE.info};",
        f"  --bengal-muted: {BENGAL_PALETTE.muted};",
        "",
        "  /* Surface Colors */",
        f"  --bengal-surface: {BENGAL_PALETTE.surface};",
        f"  --bengal-surface-light: {BENGAL_PALETTE.surface_light};",
        f"  --bengal-background: {BENGAL_PALETTE.background};",
        f"  --bengal-foreground: {BENGAL_PALETTE.foreground};",
        "",
        "  /* Border Colors */",
        f"  --bengal-border: {BENGAL_PALETTE.border};",
        f"  --bengal-border-focus: {BENGAL_PALETTE.border_focus};",
        "",
        "  /* Text Colors */",
        f"  --bengal-text-primary: {BENGAL_PALETTE.text_primary};",
        f"  --bengal-text-secondary: {BENGAL_PALETTE.text_secondary};",
        f"  --bengal-text-muted: {BENGAL_PALETTE.text_muted};",
        "}",
        "",
    ]

    # Generate palette variant classes
    for name, variant in PALETTE_VARIANTS.items():
        if name == "default":
            continue
        lines.extend(
            [
                f"/* Palette: {name} */",
                f".palette-{name} {{",
                f"  --bengal-primary: {variant.primary};",
                f"  --bengal-accent: {variant.accent};",
                f"  --bengal-success: {variant.success};",
                f"  --bengal-error: {variant.error};",
                f"  --bengal-surface: {variant.surface};",
                f"  --bengal-background: {variant.background};",
                "}",
                "",
            ]
        )

    return "\n".join(lines)


def generate_tcss_reference() -> str:
    """
    Generate TCSS color reference comment.

    This is used to validate that bengal.tcss uses correct token values.

    Returns:
        TCSS comment with color reference
    """
    lines = [
        "/* Bengal Token Reference (from bengal/themes/tokens.py)",
        " *",
        " * Use these values in bengal.tcss:",
        " *",
        f" *   primary:   {BENGAL_PALETTE.primary}",
        f" *   secondary: {BENGAL_PALETTE.secondary}",
        f" *   accent:    {BENGAL_PALETTE.accent}",
        f" *   success:   {BENGAL_PALETTE.success}",
        f" *   warning:   {BENGAL_PALETTE.warning}",
        f" *   error:     {BENGAL_PALETTE.error}",
        f" *   info:      {BENGAL_PALETTE.info}",
        f" *   surface:   {BENGAL_PALETTE.surface}",
        f" *   background: {BENGAL_PALETTE.background}",
        " */",
    ]
    return "\n".join(lines)


def write_generated_css(output_dir: Path | None = None) -> Path:
    """
    Write generated CSS to file.

    Args:
        output_dir: Output directory (defaults to themes/default/assets/css/tokens/)

    Returns:
        Path to generated file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "default" / "assets" / "css" / "tokens"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "generated.css"

    css_content = generate_web_css()
    output_file.write_text(css_content)

    return output_file


def validate_tcss_tokens() -> list[str]:
    """
    Validate that bengal.tcss uses correct token values.

    Returns:
        List of validation errors (empty if valid)
    """
    tcss_path = Path(__file__).parent.parent / "cli" / "dashboard" / "bengal.tcss"

    if not tcss_path.exists():
        return [f"TCSS file not found: {tcss_path}"]

    tcss_content = tcss_path.read_text()
    errors: list[str] = []

    # Check that primary color is used correctly
    if BENGAL_PALETTE.primary not in tcss_content:
        errors.append(f"Primary color {BENGAL_PALETTE.primary} not found in TCSS")

    if BENGAL_PALETTE.success not in tcss_content:
        errors.append(f"Success color {BENGAL_PALETTE.success} not found in TCSS")

    if BENGAL_PALETTE.error not in tcss_content:
        errors.append(f"Error color {BENGAL_PALETTE.error} not found in TCSS")

    return errors


def main() -> None:
    """CLI entry point for token generation."""
    import sys

    print("Bengal Token Generator")
    print("=" * 40)

    # Generate web CSS
    output_path = write_generated_css()
    print(f"✓ Generated web CSS: {output_path}")

    # Validate TCSS
    errors = validate_tcss_tokens()
    if errors:
        print("\n⚠ TCSS validation warnings:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✓ TCSS tokens validated")

    print("\nDone!")


if __name__ == "__main__":
    main()
