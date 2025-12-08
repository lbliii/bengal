"""
Link Transformer - Prepends baseurl to internal links in rendered HTML.

This module handles the transformation of internal links (those starting with /)
to include the configured baseurl. This is essential for deployments where the
site is not at the root of the domain (e.g., GitHub Pages project sites).

Example:
    With baseurl="/bengal"::

        href="/docs/guide/"     -> href="/bengal/docs/guide/"
        href="https://ext.com/" -> unchanged (external)
        href="guide/"           -> unchanged (relative)
        href="#section"         -> unchanged (anchor)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def transform_internal_links(html: str, baseurl: str) -> str:
    """
    Transform internal links to include baseurl prefix.

    This function finds all ``<a href="/...">`` and ``<img src="/...">`` tags
    where the path starts with "/" and prepends the baseurl.

    Args:
        html: Rendered HTML content
        baseurl: Base URL prefix (e.g., "/bengal" or "https://example.com/bengal")

    Returns:
        HTML with transformed internal links

    Examples:
        >>> transform_internal_links('<a href="/docs/">Docs</a>', '/bengal')
        '<a href="/bengal/docs/">Docs</a>'

        >>> transform_internal_links('<a href="https://ext.com/">X</a>', '/bengal')
        '<a href="https://ext.com/">X</a>'  # External link unchanged

        >>> transform_internal_links('<a href="#top">Top</a>', '/bengal')
        '<a href="#top">Top</a>'  # Anchor unchanged
    """
    if not baseurl:
        return html

    if not html:
        return html

    # Normalize baseurl (strip trailing slash, ensure leading slash for path-only)
    baseurl = baseurl.rstrip("/")
    if not baseurl.startswith(("http://", "https://", "file://", "/")):
        # Path-only baseurl without leading slash - add it
        baseurl = "/" + baseurl

    # Pattern to match href="/..." or src="/..." attributes
    # Captures: (attribute_name)(quote)(path)
    # Does NOT match:
    # - href="https://..." (external URLs)
    # - href="#..." (anchors)
    # - href="relative/..." (relative paths without leading /)
    # - href="/baseurl/..." (already has baseurl)

    def replace_link(match: re.Match) -> str:
        """Replace internal link with baseurl-prefixed version."""
        attr = match.group(1)  # href or src
        quote = match.group(2)  # ' or "
        path = match.group(3)  # /path/to/page/

        # Skip if path already starts with baseurl
        if path.startswith(baseurl + "/") or path == baseurl:
            return str(match.group(0))

        # Prepend baseurl
        new_path = f"{baseurl}{path}"
        return f"{attr}={quote}{new_path}{quote}"

    # Match href="/..." or src="/..." (internal absolute paths)
    # Negative lookahead to avoid matching external URLs
    pattern = r'(href|src)=(["\'])(/(?!/)(?:[^"\'#][^"\']*)?)\2'

    transformed = re.sub(pattern, replace_link, html)

    return transformed


def should_transform_links(config: dict) -> bool:
    """
    Check if link transformation should be applied.

    Link transformation is enabled when:
    1. baseurl is configured (non-empty)
    2. transform_links is not explicitly disabled

    Args:
        config: Site configuration dict

    Returns:
        True if links should be transformed
    """
    baseurl = config.get("baseurl", "")
    if not baseurl:
        return False

    # Allow explicit opt-out via config
    # Default to True if baseurl is set
    build_config = config.get("build", {}) or {}
    if isinstance(build_config, dict):
        return bool(build_config.get("transform_links", True))
    return True


def get_baseurl(config: dict) -> str:
    """
    Get normalized baseurl from config.

    Args:
        config: Site configuration dict

    Returns:
        Normalized baseurl string or empty string
    """
    baseurl = config.get("baseurl", "") or ""
    return baseurl.rstrip("/")
