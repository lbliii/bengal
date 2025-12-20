"""Tab directives for tabbed content."""

from __future__ import annotations

from bengal.rendering.plugins.directives.tabs import TabItemDirective, TabSetDirective

__all__ = ["TabSetDirective", "TabItemDirective"]

DIRECTIVE_NAMES = TabSetDirective.DIRECTIVE_NAMES + TabItemDirective.DIRECTIVE_NAMES
