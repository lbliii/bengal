"""
Unified template context system for Bengal SSG.

This module re-exports all context classes from the context/ subpackage
for backward compatibility. New code should import directly from
bengal.rendering.context (which resolves to the subpackage).

See bengal/rendering/context/__init__.py for full documentation.
"""

from __future__ import annotations

# Re-export everything from the context subpackage
from bengal.rendering.context import (
    CascadingParamsContext,
    ConfigContext,
    MenusContext,
    ParamsContext,
    SectionContext,
    SiteContext,
    SmartDict,
    ThemeContext,
    build_page_context,
    build_special_page_context,
    clear_global_context_cache,
)

__all__ = [
    # Data wrappers
    "SmartDict",
    "ParamsContext",
    "CascadingParamsContext",
    # Site wrappers
    "SiteContext",
    "ThemeContext",
    "ConfigContext",
    # Section wrapper
    "SectionContext",
    # Menu wrapper
    "MenusContext",
    # Context builders
    "build_page_context",
    "build_special_page_context",
    "clear_global_context_cache",
]
