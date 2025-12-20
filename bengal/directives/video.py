"""Video directives for YouTube, Vimeo, and self-hosted videos."""

from __future__ import annotations

from bengal.rendering.plugins.directives.video import (
    SelfHostedVideoDirective,
    VimeoDirective,
    YouTubeDirective,
)

__all__ = [
    "YouTubeDirective",
    "VimeoDirective",
    "SelfHostedVideoDirective",
]

DIRECTIVE_NAMES = (
    YouTubeDirective.DIRECTIVE_NAMES
    + VimeoDirective.DIRECTIVE_NAMES
    + SelfHostedVideoDirective.DIRECTIVE_NAMES
)
