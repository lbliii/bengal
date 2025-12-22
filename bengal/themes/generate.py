"""
CSS and TCSS generation from Bengal design tokens.

Generates consistent CSS custom properties for web themes and validates
Textual CSS (TCSS) files against shared token definitions. Ensures visual
consistency between web output and terminal interfaces.

Functions:
    generate_web_css: Create CSS :root variables from BengalPalette
    generate_tcss_reference: Create TCSS validation comments
    write_generated_css: Write generated CSS to theme assets directory
    validate_tcss_tokens: Check TCSS file uses correct token values

Usage:
    # Generate CSS from command line
    python -m bengal.themes.generate

    # Programmatic usage
    >>> from bengal.themes.generate import generate_web_css, write_generated_css
    >>> css = generate_web_css()
    >>> output_path = write_generated_css()
    >>> print(f"Generated: {output_path}")

Output Files:
    bengal/themes/default/assets/css/tokens/generated.css

Architecture:
    This module reads from tokens.py (source of truth) and writes to CSS files.
    It does not modify TCSS files directly; use validate_tcss_tokens() to verify
    manual TCSS edits match the token definitions.

Related:
    bengal/themes/tokens.py: Source token definitions (BengalPalette, etc.)
    bengal/cli/dashboard/bengal.tcss: Terminal styles to validate
    bengal/themes/default/assets/css/tokens/: Generated CSS output
"""

from __future__ import annotations

from pathlib import Path

from bengal.themes.tokens import BENGAL_PALETTE, PALETTE_VARIANTS


def generate_web_css() -> str:
    """
    Generate CSS custom properties from Bengal design tokens.

    Creates a complete CSS string with :root variables for all Bengal palette
    colors, plus palette variant classes for theming support.

    Returns:
        CSS string containing:
        - :root block with --bengal-* custom properties
        - .palette-* classes for each variant in PALETTE_VARIANTS

    Example:
        >>> css = generate_web_css()
        >>> "--bengal-primary:" in css
        True
        >>> ".palette-blue-bengal" in css
        True
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
    Generate TCSS color reference as a comment block.

    Creates a formatted comment block listing all Bengal token values for
    reference when manually editing TCSS files. Used with validate_tcss_tokens()
    to ensure terminal styles match the canonical token definitions.

    Returns:
        Multi-line TCSS comment string with color hex values
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
    Write generated CSS custom properties to file.

    Creates the output directory if needed and writes the generated CSS
    containing all Bengal token values as CSS custom properties.

    Args:
        output_dir: Target directory for generated.css file. Defaults to
            bengal/themes/default/assets/css/tokens/ relative to this module.

    Returns:
        Absolute path to the written generated.css file

    Example:
        >>> path = write_generated_css()
        >>> path.name
        'generated.css'
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
    Validate that bengal.tcss uses correct token color values.

    Checks the terminal dashboard TCSS file to ensure it contains the
    canonical color values from BENGAL_PALETTE. This catches drift between
    the token definitions and manually-edited TCSS styles.

    Returns:
        List of validation error messages. Empty list indicates all
        required tokens were found in the TCSS file.

    Note:
        Checks for primary, success, and error colors. Additional tokens
        may be added as validation requirements expand.
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
    """
    CLI entry point for token generation and validation.

    Generates web CSS from tokens and validates TCSS files. Exits with
    code 1 if validation fails, code 0 on success.
    """
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
