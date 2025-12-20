"""Admonition directives (note, tip, warning, danger, etc.)."""

from __future__ import annotations

from bengal.rendering.plugins.directives.admonitions import AdmonitionDirective

__all__ = ["AdmonitionDirective"]

# Directive names for registry
DIRECTIVE_NAMES = AdmonitionDirective.DIRECTIVE_NAMES
