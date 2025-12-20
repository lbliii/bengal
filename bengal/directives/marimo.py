"""Marimo directive for executable Python cells."""

from __future__ import annotations

from bengal.rendering.plugins.directives.marimo import MarimoCellDirective

__all__ = ["MarimoCellDirective"]

DIRECTIVE_NAMES = MarimoCellDirective.DIRECTIVE_NAMES
