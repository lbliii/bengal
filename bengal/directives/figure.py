"""Figure and audio directives for semantic images and audio."""

from __future__ import annotations

from bengal.rendering.plugins.directives.figure import AudioDirective, FigureDirective

__all__ = ["FigureDirective", "AudioDirective"]

DIRECTIVE_NAMES = FigureDirective.DIRECTIVE_NAMES + AudioDirective.DIRECTIVE_NAMES
