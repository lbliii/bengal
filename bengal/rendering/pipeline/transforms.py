"""
Content transformation utilities for the rendering pipeline.

This module provides individual transformation functions for HTML content.
For production use, prefer the unified `HybridHTMLTransformer` which combines
multiple transformations into a single optimized pass (~27% faster).

Active Functions:
    escape_template_syntax_in_html():
    Converts ``{{`` and ``}}`` to HTML entities. Prevents Jinja2 from
    processing template syntax that should appear literally in output.

Deprecated Functions (use HybridHTMLTransformer instead):
    escape_jinja_blocks():
    Deprecated. Use HybridHTMLTransformer.transform() instead.

    transform_internal_links():
    Deprecated. Use HybridHTMLTransformer.transform() instead.

    normalize_markdown_links():
    Deprecated. Use HybridHTMLTransformer.transform() instead.

Related Modules:
- bengal.rendering.pipeline.unified_transform: Optimized unified transformer
- bengal.rendering.pipeline.core: Uses HybridHTMLTransformer for rendering
- bengal.rendering.link_transformer: Low-level link transformation utilities

See Also:
- plan/drafted/rfc-rendering-package-optimizations.md: Performance RFC

"""

from __future__ import annotations

from typing import Any

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


def escape_jinja_blocks(html: str) -> str:
    """
    Escape Jinja2 block delimiters in already-rendered HTML content.

    .. deprecated::
        Use `HybridHTMLTransformer.transform()` from
        `bengal.rendering.pipeline.unified_transform` instead.
        This function is retained for backward compatibility and benchmarking.

    Converts "{%" and "%}" to HTML entities to avoid leaking raw
    control-flow markers into final HTML outside template processing.

    Args:
        html: HTML content to escape

    Returns:
        HTML with escaped Jinja2 blocks

    """
    try:
        return html.replace("{%", "&#123;%").replace("%}", "%&#125;")
    except Exception as e:
        logger.debug(
            "jinja_block_escape_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="returning_original_html",
        )
        return html


def transform_internal_links(html: str, config: dict[str, Any]) -> str:
    """
    Transform internal links to include baseurl prefix.

    .. deprecated::
        Use `HybridHTMLTransformer.transform()` from
        `bengal.rendering.pipeline.unified_transform` instead.
        This function is retained for backward compatibility and benchmarking.

    This handles standard markdown links like [text](/path/) by prepending
    the configured baseurl. Essential for GitHub Pages project sites and
    similar deployments where the site is not at the domain root.

    Args:
        html: Rendered HTML content
        config: Site configuration dict

    Returns:
        HTML with transformed internal links

    """
    try:
        from bengal.rendering.link_transformer import (
            get_baseurl,
            should_transform_links,
        )
        from bengal.rendering.link_transformer import (
            transform_internal_links as do_transform,
        )

        if not should_transform_links(config):
            return html

        baseurl = get_baseurl(config)
        return do_transform(html, baseurl)
    except Exception as e:
        # Never fail the build on link transformation errors
        logger.debug("link_transformation_error", error=str(e))
        return html


def normalize_markdown_links(html: str) -> str:
    """
    Transform .md links to clean URLs.

    .. deprecated::
        Use `HybridHTMLTransformer.transform()` from
        `bengal.rendering.pipeline.unified_transform` instead.
        This function is retained for backward compatibility and benchmarking.

    Converts markdown-style file links (e.g., ./page.md) to clean URLs
    (e.g., ./page/). This allows users to write natural markdown links
    that work in both GitHub/editors and the rendered site.

    Args:
        html: Rendered HTML content

    Returns:
        HTML with .md links transformed to clean URLs

    """
    try:
        from bengal.rendering.link_transformer import normalize_md_links

        return normalize_md_links(html)
    except Exception as e:
        # Never fail the build on link normalization errors
        logger.debug("md_link_normalization_error", error=str(e))
        return html
