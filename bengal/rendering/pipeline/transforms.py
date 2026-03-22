"""
Content transformation utilities for the rendering pipeline.

This module provides the ``escape_template_syntax_in_html`` function which
converts ``{{`` and ``}}`` to HTML entities so they appear literally in output.

For link transformation and block-syntax escaping, use
``HybridHTMLTransformer`` from ``bengal.rendering.pipeline.unified_transform``.

"""

from __future__ import annotations

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


def escape_template_syntax_in_html(html: str) -> str:
    """
    Escape Jinja2 variable delimiters in already-rendered HTML.

    Converts "{{" and "}}" to HTML entities so they appear literally
    in documentation pages but won't be detected by tests as unrendered.

    Note:
        This function is NOT deprecated. It handles variable syntax ({{ }})
        which is separate from block syntax ({% %}) handled by the unified
        transformer.

    Args:
        html: HTML content to escape

    Returns:
        HTML with escaped template syntax

    """
    try:
        return html.replace("{{", "&#123;&#123;").replace("}}", "&#125;&#125;")
    except Exception as e:
        logger.debug(
            "template_syntax_escape_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="returning_original_html",
        )
        return html
