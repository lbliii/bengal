"""
SEO helper functions for templates.

Provides 4 functions for generating SEO-friendly meta tags and content.

Extended for versioned documentation:
- canonical_url: Returns canonical URL (always points to latest version for versioned pages)
- Version-aware SEO for proper search engine indexing
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register SEO helper functions with Jinja2 environment."""

    # Create closures that have access to site
    def canonical_url_with_site(path: str, page: Any | None = None) -> str:
        return canonical_url(path, site.config.get("baseurl", ""), site, page)

    def og_image_with_site(image_path: str) -> str:
        return og_image(image_path, site.config.get("baseurl", ""))

    env.filters.update(
        {
            "meta_description": meta_description,
            "meta_keywords": meta_keywords,
        }
    )

    env.globals.update(
        {
            "canonical_url": canonical_url_with_site,
            "og_image": og_image_with_site,
        }
    )


def meta_description(text: str, length: int = 160) -> str:
    """
    Generate meta description from text.

    Creates SEO-friendly description by:
    - Stripping HTML
    - Truncating to length
    - Ending at sentence boundary if possible

    Args:
        text: Source text
        length: Maximum length (default: 160 chars)

    Returns:
        Meta description text

    Example:
        <meta name="description" content="{{ page.content | meta_description }}">
    """
    if not text:
        return ""

    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= length:
        return text

    # Truncate to length
    truncated = text[:length]

    # Try to end at sentence boundary
    sentence_end = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "))

    if sentence_end > length * 0.6:  # At least 60% of desired length
        return truncated[: sentence_end + 1].strip()

    # Try to end at word boundary
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space].strip() + "…"

    return truncated + "…"


def meta_keywords(tags: list[str], max_count: int = 10) -> str:
    """
    Generate meta keywords from tags.

    Args:
        tags: List of tags/keywords
        max_count: Maximum number of keywords (default: 10)

    Returns:
        Comma-separated keywords

    Example:
        <meta name="keywords" content="{{ page.tags | meta_keywords }}">
    """
    if not tags:
        return ""

    # Limit count
    keywords = tags[:max_count]

    # Join with commas
    return ", ".join(keywords)


def canonical_url(
    path: str,
    base_url: str,
    site: Any | None = None,
    page: Any | None = None,
) -> str:
    """
    Generate canonical URL for SEO.

    For versioned documentation, canonical URLs always point to the latest version.
    This prevents duplicate content issues and consolidates SEO value.

    Args:
        path: Page path (relative or absolute)
        base_url: Site base URL
        site: Optional site for versioning context
        page: Optional page for version detection

    Returns:
        Full canonical URL (pointing to latest version for versioned pages)

    Example:
        <link rel="canonical" href="{{ canonical_url(page.href, page=page) }}">
    """
    if not path:
        return base_url or ""

    # Already absolute
    if path.startswith(("http://", "https://")):
        return path

    # Ensure base URL
    if not base_url:
        base_url = ""

    base_url = base_url.rstrip("/")
    path = "/" + path.lstrip("/")

    # Handle versioned pages - canonical should point to latest version
    if site and page and getattr(site, "versioning_enabled", False):
        version_config = getattr(site, "version_config", None)
        page_version = getattr(page, "version", None)

        if version_config and page_version:
            # Get the version object
            version = version_config.get_version(page_version)
            if version and not version.latest:
                # This is an older version - canonical should point to latest
                # Remove version prefix from path to get canonical
                for section in version_config.sections:
                    # Path pattern: /section/version_id/rest -> /section/rest
                    version_pattern = f"/{section}/{version.id}/"
                    if path.startswith(version_pattern):
                        # Remove version prefix for canonical
                        rest = path[len(version_pattern) - 1 :]  # Keep trailing /
                        path = f"/{section}{rest}"
                        break

    return base_url + path


def og_image(image_path: str, base_url: str) -> str:
    """
    Generate Open Graph image URL.

    Args:
        image_path: Relative path to image
        base_url: Site base URL

    Returns:
        Full image URL for og:image

    Example:
        <meta property="og:image" content="{{ og_image('images/hero.jpg') }}">
    """
    if not image_path:
        return ""

    # Already absolute
    if image_path.startswith(("http://", "https://")):
        return image_path

    # Ensure base URL
    if not base_url:
        return image_path

    base_url = base_url.rstrip("/")

    # Handle assets directory
    if not image_path.startswith("/"):
        image_path = f"/assets/{image_path}"

    return base_url + image_path
