"""
SEO helper functions for templates.

Provides 4 functions for generating SEO-friendly meta tags and content.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: 'Environment', site: 'Site') -> None:
    """Register SEO helper functions with Jinja2 environment."""

    # Create closures that have access to site
    def canonical_url_with_site(path: str) -> str:
        return canonical_url(path, site.config.get('baseurl', ''))

    def og_image_with_site(image_path: str) -> str:
        return og_image(image_path, site.config.get('baseurl', ''))

    env.filters.update({
        'meta_description': meta_description,
        'meta_keywords': meta_keywords,
    })

    env.globals.update({
        'canonical_url': canonical_url_with_site,
        'og_image': og_image_with_site,
    })


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
        return ''

    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) <= length:
        return text

    # Truncate to length
    truncated = text[:length]

    # Try to end at sentence boundary
    sentence_end = max(
        truncated.rfind('. '),
        truncated.rfind('! '),
        truncated.rfind('? ')
    )

    if sentence_end > length * 0.6:  # At least 60% of desired length
        return truncated[:sentence_end + 1].strip()

    # Try to end at word boundary
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space].strip() + '…'

    return truncated + '…'


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
        return ''

    # Limit count
    keywords = tags[:max_count]

    # Join with commas
    return ', '.join(keywords)


def canonical_url(path: str, base_url: str) -> str:
    """
    Generate canonical URL for SEO.

    Args:
        path: Page path (relative or absolute)
        base_url: Site base URL

    Returns:
        Full canonical URL

    Example:
        <link rel="canonical" href="{{ canonical_url(page.url) }}">
    """
    if not path:
        return base_url or ''

    # Already absolute
    if path.startswith(('http://', 'https://')):
        return path

    # Ensure base URL
    if not base_url:
        return path

    base_url = base_url.rstrip('/')
    path = '/' + path.lstrip('/')

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
        return ''

    # Already absolute
    if image_path.startswith(('http://', 'https://')):
        return image_path

    # Ensure base URL
    if not base_url:
        return image_path

    base_url = base_url.rstrip('/')

    # Handle assets directory
    if not image_path.startswith('/'):
        image_path = f"/assets/{image_path}"

    return base_url + image_path

