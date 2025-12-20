"""Embed directives for developer tools (gist, codepen, codesandbox, stackblitz)."""

from __future__ import annotations

from bengal.rendering.plugins.directives.embed import (
    CodePenDirective,
    CodeSandboxDirective,
    GistDirective,
    StackBlitzDirective,
)

__all__ = [
    "GistDirective",
    "CodePenDirective",
    "CodeSandboxDirective",
    "StackBlitzDirective",
]

DIRECTIVE_NAMES = (
    GistDirective.DIRECTIVE_NAMES
    + CodePenDirective.DIRECTIVE_NAMES
    + CodeSandboxDirective.DIRECTIVE_NAMES
    + StackBlitzDirective.DIRECTIVE_NAMES
)
