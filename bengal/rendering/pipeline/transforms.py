"""
Content transformation utilities for the rendering pipeline.

This module applies post-parsing transformations to HTML content before
template rendering. These transformations ensure content displays correctly
and links work properly across different deployment configurations.

Transformations:
    escape_template_syntax_in_html():
        Converts ``{{`` and ``}}`` to HTML entities. Prevents Jinja2 from
        processing template syntax that should appear literally in output
        (e.g., code examples showing template syntax).

    escape_jinja_blocks():
        Converts ``{%`` and ``%}`` to HTML entities. Prevents control flow
        markers from leaking into final output.

    transform_internal_links():
        Prepends baseurl to internal links starting with ``/``. Essential
        for sites deployed to subdirectories (e.g., GitHub Pages projects).

    normalize_markdown_links():
        Converts ``.md`` file extensions to clean URLs (e.g., ``./page.md``
        becomes ``./page/``). Enables natural markdown linking that works
        both in editors/GitHub and the rendered site.

Error Handling:
    All transformations use graceful degradation - errors are logged but
    never cause build failures. Original content is returned unchanged
    if transformation fails.

Related Modules:
    - bengal.rendering.pipeline.core: Calls transformations during rendering
    - bengal.rendering.link_transformer: Link transformation implementation
"""

from __future__ import annotations

from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def escape_template_syntax_in_html(html: str) -> str:
    """
    Escape Jinja2 variable delimiters in already-rendered HTML.

    Converts "{{" and "}}" to HTML entities so they appear literally
    in documentation pages but won't be detected by tests as unrendered.

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
