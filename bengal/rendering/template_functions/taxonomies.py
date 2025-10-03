"""
Taxonomy helper functions for templates.

Provides 4 functions for working with tags, categories, and related content.
"""

from typing import TYPE_CHECKING, List, Dict, Any, Optional

if TYPE_CHECKING:
    from jinja2 import Environment
    from bengal.core.site import Site


def register(env: 'Environment', site: 'Site') -> None:
    """Register taxonomy helper functions with Jinja2 environment."""
    
    # Create closures that have access to site
    def related_posts_with_site(page: Any, limit: int = 5) -> List[Any]:
        return related_posts(page, site.pages, limit)
    
    def popular_tags_with_site(limit: int = 10) -> List[tuple]:
        return popular_tags(site.taxonomies.get('tags', {}), limit)
    
    def tag_url_with_site(tag: str) -> str:
        return tag_url(tag)
    
    env.filters.update({
        'has_tag': has_tag,
    })
    
    env.globals.update({
        'related_posts': related_posts_with_site,
        'popular_tags': popular_tags_with_site,
        'tag_url': tag_url_with_site,
    })


def related_posts(page: Any, all_pages: List[Any], limit: int = 5) -> List[Any]:
    """
    Find related posts based on shared tags.
    
    Args:
        page: Current page
        all_pages: All site pages
        limit: Maximum number of related posts
    
    Returns:
        List of related pages sorted by relevance
    
    Example:
        {% set related = related_posts(page, limit=3) %}
        {% for post in related %}
          <a href="{{ url_for(post) }}">{{ post.title }}</a>
        {% endfor %}
    """
    if not hasattr(page, 'tags') or not page.tags:
        return []
    
    page_tags = set(page.tags)
    scored_pages = []
    
    for other_page in all_pages:
        # Skip the current page
        if other_page == page:
            continue
        
        # Skip pages without tags
        if not hasattr(other_page, 'tags') or not other_page.tags:
            continue
        
        # Calculate relevance score (number of shared tags)
        other_tags = set(other_page.tags)
        shared_tags = page_tags & other_tags
        
        if shared_tags:
            score = len(shared_tags)
            scored_pages.append((score, other_page))
    
    # Sort by score (descending) and return top N
    scored_pages.sort(key=lambda x: x[0], reverse=True)
    return [page for score, page in scored_pages[:limit]]


def popular_tags(tags_dict: Dict[str, List[Any]], limit: int = 10) -> List[tuple]:
    """
    Get most popular tags sorted by count.
    
    Args:
        tags_dict: Dictionary of tag -> pages
        limit: Maximum number of tags
    
    Returns:
        List of (tag, count) tuples
    
    Example:
        {% set top_tags = popular_tags(limit=5) %}
        {% for tag, count in top_tags %}
          <a href="{{ tag_url(tag) }}">{{ tag }} ({{ count }})</a>
        {% endfor %}
    """
    if not tags_dict:
        return []
    
    # Count pages per tag
    tag_counts = [(tag, len(pages)) for tag, pages in tags_dict.items()]
    
    # Sort by count (descending)
    tag_counts.sort(key=lambda x: x[1], reverse=True)
    
    return tag_counts[:limit]


def tag_url(tag: str) -> str:
    """
    Generate URL for a tag page.
    
    Args:
        tag: Tag name
    
    Returns:
        URL path to tag page
    
    Example:
        <a href="{{ tag_url('python') }}">Python</a>
        # <a href="/tags/python/">Python</a>
    """
    if not tag:
        return '/tags/'
    
    # Convert tag to URL-safe slug
    import re
    slug = tag.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    
    return f"/tags/{slug}/"


def has_tag(page: Any, tag: str) -> bool:
    """
    Check if page has a specific tag.
    
    Args:
        page: Page to check
        tag: Tag to look for
    
    Returns:
        True if page has the tag
    
    Example:
        {% if page | has_tag('tutorial') %}
          <span class="badge">Tutorial</span>
        {% endif %}
    """
    if not hasattr(page, 'tags') or not page.tags:
        return False
    
    # Case-insensitive comparison
    page_tags = [t.lower() for t in page.tags]
    return tag.lower() in page_tags

