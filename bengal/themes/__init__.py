"""
Theme configuration, tokens, and generation utilities for Bengal SSG.

Provides the theming infrastructure including:
- Theme configuration models (ThemeConfig, FeatureFlags, etc.)
- Shared design tokens (color palettes, mascots)
- CSS/TCSS generation utilities

Modules:
    - config: Theme configuration dataclasses and YAML loader
    - tokens: Shared design tokens for web and terminal
    - generate: CSS/TCSS generation from tokens

Related:
    - bengal/themes/default/: Default theme assets and templates
    - bengal/cli/dashboard/: Terminal dashboard using theme tokens
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
