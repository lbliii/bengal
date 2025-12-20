"""Navigation directives for breadcrumbs, siblings, prev-next, related."""

from __future__ import annotations

from bengal.rendering.plugins.directives.navigation import (
    BreadcrumbsDirective,
    PrevNextDirective,
    RelatedDirective,
    SiblingsDirective,
)

__all__ = [
    "BreadcrumbsDirective",
    "SiblingsDirective",
    "PrevNextDirective",
    "RelatedDirective",
]

DIRECTIVE_NAMES = (
    BreadcrumbsDirective.DIRECTIVE_NAMES
    + SiblingsDirective.DIRECTIVE_NAMES
    + PrevNextDirective.DIRECTIVE_NAMES
    + RelatedDirective.DIRECTIVE_NAMES
)
