"""
Browser-overlay rendering for build errors (Sprint A3).

Public API:
    render_error_page: Render a self-contained HTML page that displays a
        :class:`TemplateRenderError` with code badge, source frame, caret
        marker, suggestions, and documentation link. Suitable for writing
        to ``public/<failed-page>.html`` so a developer hitting the URL
        sees the error in-place rather than a blank page.

The overlay is transport-agnostic: A3.1 produces the HTML body; A3.2
extends it with a live-reload listener that dismisses on ``build_ok``.
"""

from __future__ import annotations

from .renderer import render_error_page
from .transport import build_error_payload, build_ok_payload, error_to_dict

__all__ = [
    "build_error_payload",
    "build_ok_payload",
    "error_to_dict",
    "render_error_page",
]
