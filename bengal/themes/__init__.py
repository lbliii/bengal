"""
Theme configuration, design tokens, and style generation for Bengal SSG.

This package provides the complete theming infrastructure for Bengal sites,
ensuring visual consistency between web output and terminal interfaces:

Configuration Models:
    ThemeConfig: Complete theme configuration loaded from theme.yaml
    FeatureFlags: Enable/disable theme features by category
    AppearanceConfig: Theme mode (light/dark/system) and palette
    IconConfig: Icon library selection and semantic aliases

Design Tokens:
    BengalPalette: Brand and semantic color tokens (WCAG AA compliant)
    BengalMascots: ASCII mascots and status icons for terminal output
    PaletteVariant: Named color palette variants (default, blue-bengal, etc.)

Generation Utilities:
    generate_web_css: Create CSS custom properties from tokens
    generate_tcss_reference: Create TCSS validation reference
    write_generated_css: Write generated CSS to theme assets
    validate_tcss_tokens: Verify terminal styles match token definitions

Token Instances:
    BENGAL_PALETTE: Default color palette instance
    BENGAL_MASCOT: Default mascots instance
    PALETTE_VARIANTS: Dict of available palette variants

Example:
    >>> from bengal.themes import ThemeConfig, BENGAL_PALETTE
    >>> config = ThemeConfig.load(Path("themes/default"))
    >>> print(config.features.has_feature("navigation.toc"))
    True
    >>> print(BENGAL_PALETTE.primary)
    #FF9D00

Related:
    bengal/themes/default/: Default theme assets and templates
    bengal/cli/dashboard/: Terminal dashboard using theme tokens
    bengal/themes/default/assets/css/tokens/: Generated web CSS tokens
"""

from __future__ import annotations

from bengal.themes.config import (
    AppearanceConfig,
    FeatureFlags,
    IconConfig,
    ThemeConfig,
)
from bengal.themes.generate import (
    generate_tcss_reference,
    generate_web_css,
    validate_tcss_tokens,
    write_generated_css,
)
from bengal.themes.tokens import (
    BENGAL_MASCOT,
    BENGAL_PALETTE,
    PALETTE_VARIANTS,
    BengalMascots,
    BengalPalette,
    PaletteVariant,
    get_palette,
)

__all__ = [
    # Config models
    "AppearanceConfig",
    "FeatureFlags",
    "IconConfig",
    "ThemeConfig",
    # Token dataclasses
    "BengalMascots",
    "BengalPalette",
    "PaletteVariant",
    # Token instances
    "BENGAL_MASCOT",
    "BENGAL_PALETTE",
    "PALETTE_VARIANTS",
    # Token utilities
    "get_palette",
    # Generation utilities
    "generate_tcss_reference",
    "generate_web_css",
    "validate_tcss_tokens",
    "write_generated_css",
]
