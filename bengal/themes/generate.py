"""
CSS generation from Bengal design tokens.

Generates consistent CSS custom properties for web themes.

Functions:
    generate_web_css: Create CSS :root variables from BengalPalette
    write_generated_css: Write generated CSS to theme assets directory

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

Related:
bengal/themes/tokens.py: Source token definitions (BengalPalette, etc.)
bengal/themes/default/assets/css/tokens/: Generated CSS output

"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bengal.errors import BengalAssetError, ErrorCode
from bengal.themes.tokens import BENGAL_PALETTE, PALETTE_VARIANTS
from bengal.themes.utils import DEFAULT_CSS_TOKENS_PATH
from bengal.utils.io.atomic_write import atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_DESIGN_TOKENS_PATH = DEFAULT_CSS_TOKENS_PATH.parent.parent / "design-tokens.json"


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


def generate_design_tokens_manifest() -> dict[str, object]:
    """
    Generate a JSON manifest of design tokens for LLM/agent theming consumers.

    Consumer: action-bar "Copy theme tokens" button (design-tokens.json).
    """
    palettes = {
        name: {
            "primary": variant.primary,
            "accent": variant.accent,
            "success": variant.success,
            "error": variant.error,
            "surface": variant.surface,
            "background": variant.background,
        }
        for name, variant in PALETTE_VARIANTS.items()
    }
    return {
        "$schema": "https://design-tokens.github.io/community-group/format/",
        "name": "bengal-default-theme",
        "version": "2.0.0",
        "description": "Pridelands default theme design tokens for LLM theming context",
        "consumer": "action-bar-copy-theme-tokens",
        "palettes": palettes,
        "css_variables": {
            "semantic": [
                "--color-primary",
                "--color-text-primary",
                "--color-bg-primary",
                "--color-border-focus",
                "--motion-signature-duration",
                "--motion-signature-ease",
            ],
            "activation": "Set data-palette on <html> for named palettes; data-theme for light/dark",
        },
        "default_palette": {
            "primary": BENGAL_PALETTE.primary,
            "secondary": BENGAL_PALETTE.secondary,
            "accent": BENGAL_PALETTE.accent,
            "success": BENGAL_PALETTE.success,
            "error": BENGAL_PALETTE.error,
        },
    }


def write_design_tokens_manifest(output_path: Path | None = None) -> Path:
    """Write design-tokens.json for the action-bar copy-theme-tokens consumer."""
    if output_path is None:
        output_path = DEFAULT_DESIGN_TOKENS_PATH

    manifest = generate_design_tokens_manifest()
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(output_path, json.dumps(manifest, indent=2) + "\n")
    except OSError as e:
        raise BengalAssetError(
            f"Failed to write design tokens manifest: {output_path}",
            code=ErrorCode.X004,
            file_path=output_path,
            suggestion="Check file permissions and disk space",
            original_error=e,
        ) from e
    return output_path


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

    Raises:
        BengalAssetError: If directory creation or file write fails

    Example:
            >>> path = write_generated_css()
            >>> path.name
            'generated.css'

    """
    if output_dir is None:
        output_dir = DEFAULT_CSS_TOKENS_PATH

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise BengalAssetError(
            f"Failed to create CSS output directory: {output_dir}",
            code=ErrorCode.X004,
            file_path=output_dir,
            suggestion="Check directory permissions and disk space",
            original_error=e,
        ) from e

    output_file = output_dir / "generated.css"
    css_content = generate_web_css()

    try:
        atomic_write_text(output_file, css_content)
    except OSError as e:
        raise BengalAssetError(
            f"Failed to write generated CSS: {output_file}",
            code=ErrorCode.X004,
            file_path=output_file,
            suggestion="Check file permissions and disk space",
            original_error=e,
        ) from e

    return output_file


def main() -> None:
    """
    CLI entry point for token generation and validation.

    Generates web CSS from tokens. Exits with code 1 if generation fails,
    code 0 on success.

    Raises:
        BengalAssetError: If CSS generation fails

    """
    import sys

    from bengal.output import get_cli_output

    cli = get_cli_output()
    cli.header("Bengal Token Generator")

    # Generate web CSS (may raise BengalAssetError)
    try:
        output_path = write_generated_css()
        cli.success(f"Generated web CSS: {output_path}")
        tokens_path = write_design_tokens_manifest()
        cli.success(f"Generated design tokens manifest: {tokens_path}")
    except BengalAssetError as e:
        cli.error(f"CSS generation failed: {e.message}")
        if e.suggestion:
            cli.tip(e.suggestion)
        sys.exit(1)

    cli.success("Done!")


if __name__ == "__main__":
    main()
