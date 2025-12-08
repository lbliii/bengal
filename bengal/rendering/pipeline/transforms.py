"""
Content transformation utilities for rendering pipeline.

Provides HTML transformations including template syntax escaping,
link transformation, and Jinja2 block escaping.

Related Modules:
    - bengal.rendering.pipeline.core: Uses these transformations
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
    except Exception:
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
    except Exception:
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

