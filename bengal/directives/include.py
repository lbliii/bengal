"""Include directive for including markdown files."""

from __future__ import annotations

from bengal.rendering.plugins.directives.include import IncludeDirective

__all__ = ["IncludeDirective"]

DIRECTIVE_NAMES = IncludeDirective.DIRECTIVE_NAMES
