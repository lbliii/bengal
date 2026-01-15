"""Patitas renderers.

Renderers convert typed AST nodes into output formats.

Available Renderers:
- HtmlRenderer: Renders AST to HTML using StringBuilder pattern

Module Structure (RFC: rfc-code-health-improvements Phase 3):
- html.py: Core HtmlRenderer class
- blocks.py: Block-level rendering mixin
- inline.py: Inline dispatch handlers and table
- directives.py: Directive rendering mixin
- utils.py: Helper functions (escape, encode, slugify)

Thread Safety:
All renderers use StringBuilder local to each render() call.
Safe for concurrent use from multiple threads.

"""

from __future__ import annotations

from bengal.parsing.backends.patitas.renderers.html import HeadingInfo, HtmlRenderer

__all__ = ["HtmlRenderer", "HeadingInfo"]
