"""Steps directives for step-by-step guides."""

from __future__ import annotations

from bengal.rendering.plugins.directives.steps import StepDirective, StepsDirective

__all__ = ["StepsDirective", "StepDirective"]

DIRECTIVE_NAMES = StepsDirective.DIRECTIVE_NAMES + StepDirective.DIRECTIVE_NAMES
