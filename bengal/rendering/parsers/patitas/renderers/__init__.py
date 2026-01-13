"""Patitas renderers.

Renderers convert typed AST nodes into output formats.

Available Renderers:
- HtmlRenderer: Renders AST to HTML using StringBuilder pattern

Thread Safety:
All renderers use StringBuilder local to each render() call.
Safe for concurrent use from multiple threads.

"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

__all__ = ["HtmlRenderer"]
