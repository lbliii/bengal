"""
Cross-reference functions for templates.

Provides 4 functions for Sphinx-style cross-referencing with O(1) performance.
"""

from typing import TYPE_CHECKING, Optional, List
from markupsafe import Markup

if TYPE_CHECKING:
    from jinja2 import Environment
    from bengal.core.site import Site
    from bengal.core.page import Page


def register(env: 'Environment', site: 'Site') -> None:
    """Register cross-reference functions with Jinja2 environment."""
    
    # Create closures that have access to site's xref_index
    def ref_with_site(path: str, text: str = None) -> Markup:
        return ref(path, site.xref_index, text)
    
    def doc_with_site(path: str) -> Optional['Page']:
        return doc(path, site.xref_index)
    
    def anchor_with_site(heading: str, page_path: str = None) -> Markup:
        return anchor(heading, site.xref_index, page_path)
    
    def relref_with_site(path: str) -> str:
        return relref(path, site.xref_index)
    
    env.globals.update({
        'ref': ref_with_site,       # Link with custom text
        'doc': doc_with_site,       # Get page by path
        'anchor': anchor_with_site,  # Link to heading
        'xref': ref_with_site,      # Alias for compatibility
        'relref': relref_with_site,  # Get relative URL (Hugo-style)
    })


def ref(path: str, index: dict, text: str = None) -> Markup:
    """
    Generate cross-reference link (like Sphinx :doc: or :ref:).
    
    O(1) lookup - zero performance impact!
    
    Args:
        path: Path to reference ('docs/installation', 'id:my-page', or slug)
        index: Cross-reference index from site
        text: Optional custom link text (defaults to page title)
    
    Returns:
        Safe HTML link or broken reference indicator
    
    Examples:
        In templates:
            {{ ref('docs/getting-started') }}
            {{ ref('docs/getting-started', 'Get Started') }}
            {{ ref('id:install-guide') }}
        
        In Markdown (with variable substitution enabled):
            Check out {{ ref('docs/api') }} for details.
    """
    if not path:
        return Markup('<span class="broken-ref" data-ref="">[empty ref]</span>')
    
    # Try different lookup strategies
    page = None
    
    # Strategy 1: Custom ID (id:xxx)
    if path.startswith('id:'):
        ref_id = path[3:]
        page = index.get('by_id', {}).get(ref_id)
    
    # Strategy 2: Path lookup (docs/installation)
    elif '/' in path or path.endswith('.md'):
        # Normalize path (remove .md extension if present)
        clean_path = path.replace('.md', '')
        page = index.get('by_path', {}).get(clean_path)
    
    # Strategy 3: Slug lookup (installation)
    else:
        pages = index.get('by_slug', {}).get(path, [])
        page = pages[0] if pages else None
    
    if not page:
        # Return broken reference indicator
        return Markup(
            f'<span class="broken-ref" data-ref="{path}" '
            f'title="Reference not found: {path}">[{text or path}]</span>'
        )
    
    # Generate link
    link_text = text or page.title
    url = page.url if hasattr(page, 'url') else f'/{page.slug}/'
    
    return Markup(f'<a href="{url}">{link_text}</a>')


def doc(path: str, index: dict) -> Optional['Page']:
    """
    Get page object by path (like Hugo's .GetPage).
    
    O(1) lookup - zero performance impact!
    Useful for accessing page metadata in templates.
    
    Args:
        path: Path to page ('docs/installation', 'id:my-page', or slug)
        index: Cross-reference index from site
    
    Returns:
        Page object or None if not found
    
    Examples:
        {% set install_page = doc('docs/installation') %}
        {% if install_page %}
          <a href="{{ url_for(install_page) }}">{{ install_page.title }}</a>
          <p>{{ install_page.metadata.description }}</p>
        {% endif %}
        
        {# Access any page property #}
        {% set api = doc('docs/api') %}
        Last updated: {{ api.metadata.date | date_format('%Y-%m-%d') }}
    """
    if not path:
        return None
    
    # Try different lookup strategies
    if path.startswith('id:'):
        return index.get('by_id', {}).get(path[3:])
    elif '/' in path or path.endswith('.md'):
        clean_path = path.replace('.md', '')
        return index.get('by_path', {}).get(clean_path)
    else:
        pages = index.get('by_slug', {}).get(path, [])
        return pages[0] if pages else None


def anchor(heading: str, index: dict, page_path: str = None) -> Markup:
    """
    Link to a heading (anchor) in a page.
    
    Args:
        heading: Heading text to link to
        index: Cross-reference index from site
        page_path: Optional page path to restrict search (default: search all)
    
    Returns:
        Safe HTML link to heading or broken reference indicator
    
    Examples:
        {{ anchor('Installation') }}
        {{ anchor('Configuration', 'docs/getting-started') }}
        
        {# Find and link to any heading in the site #}
        Jump to {{ anchor('API Reference') }}
    """
    if not heading:
        return Markup('<span class="broken-ref">[empty anchor]</span>')
    
    # Normalize heading text for lookup
    heading_key = heading.lower()
    results = index.get('by_heading', {}).get(heading_key, [])
    
    if not results:
        return Markup(
            f'<span class="broken-ref" data-anchor="{heading}" '
            f'title="Heading not found: {heading}">[{heading}]</span>'
        )
    
    # If page_path specified, filter to that page
    if page_path:
        target_page = doc(page_path, index)
        if target_page:
            results = [(p, a) for p, a in results if p == target_page]
    
    if not results:
        return Markup(
            f'<span class="broken-ref" data-anchor="{heading}" '
            f'data-page="{page_path}">[{heading}]</span>'
        )
    
    # Use first match
    page, anchor_id = results[0]
    url = page.url if hasattr(page, 'url') else f'/{page.slug}/'
    
    return Markup(f'<a href="{url}#{anchor_id}">{heading}</a>')


def relref(path: str, index: dict) -> str:
    """
    Get relative URL for a page (Hugo-style relref).
    
    Returns just the URL without generating a full link.
    Useful for custom link generation.
    
    Args:
        path: Path to page
        index: Cross-reference index from site
    
    Returns:
        URL string or empty string if not found
    
    Examples:
        <a href="{{ relref('docs/api') }}" class="btn">API Docs</a>
        
        {% set api_url = relref('docs/api') %}
        {% if api_url %}
          <link rel="preload" href="{{ api_url }}" as="document">
        {% endif %}
    """
    page = doc(path, index)
    if not page:
        return ''
    
    return page.url if hasattr(page, 'url') else f'/{page.slug}/'

