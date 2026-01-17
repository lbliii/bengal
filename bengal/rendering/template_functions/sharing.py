"""
Social sharing URL generation functions for templates.

Provides template functions for generating share URLs for popular social
platforms. All URLs are properly encoded for safe sharing.

Template Usage:
<a href="{{ share_url('twitter', page) }}">Share on Twitter</a>
<a href="{{ share_url('linkedin', page) }}">Share on LinkedIn</a>
<a href="{{ share_url('facebook', page) }}">Share on Facebook</a>

{# Or use individual functions #}
<a href="{{ twitter_share_url(page.absolute_href, page.title) }}">Tweet</a>

Related Modules:
- bengal.rendering.template_functions.seo: SEO meta tag generation
- bengal.rendering.template_functions.urls: URL manipulation

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """Register functions with template environment."""

    # Create closure for share_url with access to site
    def share_url_with_site(
        platform: str,
        page: Any,
        text: str | None = None,
        via: str | None = None,
    ) -> str:
        return share_url(platform, page, text, via, site)

    env.globals.update(
        {
            "share_url": share_url_with_site,
            "twitter_share_url": twitter_share_url,
            "linkedin_share_url": linkedin_share_url,
            "facebook_share_url": facebook_share_url,
            "reddit_share_url": reddit_share_url,
            "hackernews_share_url": hackernews_share_url,
            "email_share_url": email_share_url,
            "mastodon_share_text": mastodon_share_text,
        }
    )


def share_url(
    platform: str,
    page: Any,
    text: str | None = None,
    via: str | None = None,
    site: SiteLike | None = None,
) -> str:
    """
    Generate share URL for a given platform and page.
    
    Convenience function that routes to platform-specific generators.
    Uses page properties (absolute_href, title) for URL and text defaults.
    
    Args:
        platform: Social platform name (twitter, linkedin, facebook, reddit, hackernews, email)
        page: Page object with absolute_href and title attributes
        text: Optional custom share text (defaults to page.title)
        via: Optional attribution handle (for Twitter)
        site: Site instance for config access
    
    Returns:
        Share URL for the specified platform
    
    Example:
        {{ share_url('twitter', page) }}
        {{ share_url('twitter', page, via='myblog') }}
        {{ share_url('linkedin', page, text='Check this out!') }}
        
    """
    # Extract URL and text from page
    url = getattr(page, "absolute_href", "") or getattr(page, "href", "")
    title = text or getattr(page, "title", "")

    # Get site-level Twitter handle if via not specified
    if via is None and site is not None:
        via = site.config.get("social", {}).get("twitter", "")

    platform_lower = platform.lower()

    handlers = {
        "twitter": lambda: twitter_share_url(url, title, via),
        "x": lambda: twitter_share_url(url, title, via),  # X is Twitter
        "linkedin": lambda: linkedin_share_url(url, title),
        "facebook": lambda: facebook_share_url(url),
        "reddit": lambda: reddit_share_url(url, title),
        "hackernews": lambda: hackernews_share_url(url, title),
        "hn": lambda: hackernews_share_url(url, title),  # Alias
        "email": lambda: email_share_url(url, title),
        "mastodon": lambda: mastodon_share_text(url, title),
    }

    handler = handlers.get(platform_lower)
    if handler:
        return handler()

    # Unknown platform - return empty string
    return ""


def twitter_share_url(
    url: str,
    text: str = "",
    via: str = "",
    hashtags: list[str] | None = None,
) -> str:
    """
    Generate Twitter/X share URL.
    
    Args:
        url: URL to share
        text: Tweet text
        via: Twitter handle for attribution (without @)
        hashtags: List of hashtags (without #)
    
    Returns:
        Twitter intent URL
    
    Example:
        {{ twitter_share_url(page.absolute_href, page.title, via='myblog') }}
        → https://twitter.com/intent/tweet?url=...&text=...&via=myblog
        
    """
    params: dict[str, str] = {"url": url}

    if text:
        params["text"] = text

    if via:
        # Remove @ if present
        params["via"] = via.lstrip("@")

    if hashtags:
        params["hashtags"] = ",".join(h.lstrip("#") for h in hashtags)

    return f"https://twitter.com/intent/tweet?{urlencode(params)}"


def linkedin_share_url(url: str, title: str = "", summary: str = "") -> str:
    """
    Generate LinkedIn share URL.
    
    Args:
        url: URL to share
        title: Article title (optional)
        summary: Article summary (optional)
    
    Returns:
        LinkedIn share URL
    
    Example:
        {{ linkedin_share_url(page.absolute_href, page.title) }}
        → https://www.linkedin.com/sharing/share-offsite/?url=...
        
    """
    # LinkedIn now primarily uses the simple share URL format
    params = {"url": url}
    return f"https://www.linkedin.com/sharing/share-offsite/?{urlencode(params)}"


def facebook_share_url(url: str) -> str:
    """
    Generate Facebook share URL.
    
    Args:
        url: URL to share
    
    Returns:
        Facebook share dialog URL
    
    Example:
        {{ facebook_share_url(page.absolute_href) }}
        → https://www.facebook.com/sharer/sharer.php?u=...
        
    """
    return f"https://www.facebook.com/sharer/sharer.php?u={quote(url, safe='')}"


def reddit_share_url(url: str, title: str = "") -> str:
    """
    Generate Reddit submit URL.
    
    Args:
        url: URL to share
        title: Post title
    
    Returns:
        Reddit submit URL
    
    Example:
        {{ reddit_share_url(page.absolute_href, page.title) }}
        → https://www.reddit.com/submit?url=...&title=...
        
    """
    params: dict[str, str] = {"url": url}
    if title:
        params["title"] = title
    return f"https://www.reddit.com/submit?{urlencode(params)}"


def hackernews_share_url(url: str, title: str = "") -> str:
    """
    Generate Hacker News submit URL.
    
    Args:
        url: URL to share
        title: Post title
    
    Returns:
        HN submit URL
    
    Example:
        {{ hackernews_share_url(page.absolute_href, page.title) }}
        → https://news.ycombinator.com/submitlink?u=...&t=...
        
    """
    params: dict[str, str] = {"u": url}
    if title:
        params["t"] = title
    return f"https://news.ycombinator.com/submitlink?{urlencode(params)}"


def email_share_url(url: str, subject: str = "", body: str = "") -> str:
    """
    Generate mailto: URL for email sharing.
    
    Args:
        url: URL to share
        subject: Email subject
        body: Email body (URL appended if not in body)
    
    Returns:
        mailto: URL
    
    Example:
        {{ email_share_url(page.absolute_href, page.title) }}
        → mailto:?subject=...&body=...
        
    """
    params: dict[str, str] = {}

    if subject:
        params["subject"] = subject

    if body:
        params["body"] = body
    else:
        # Default body includes just the URL
        params["body"] = url

    return f"mailto:?{urlencode(params)}"


def mastodon_share_text(url: str, text: str = "") -> str:
    """
    Generate pre-formatted text for Mastodon sharing.
    
    Mastodon doesn't have a universal share URL since it's decentralized.
    This returns the share text that can be used with a Mastodon web+share
    intent or copied manually.
    
    Args:
        url: URL to share
        text: Share text
    
    Returns:
        Formatted share text with URL
    
    Example:
        {{ mastodon_share_text(page.absolute_href, page.title) }}
        → "Page Title https://example.com/page/"
    
    Usage:
        <a href="https://mastodon.social/share?text={{ mastodon_share_text(page.absolute_href, page.title) | urlencode }}">
          Share on Mastodon
        </a>
        
    """
    if text:
        return f"{text} {url}"
    return url
