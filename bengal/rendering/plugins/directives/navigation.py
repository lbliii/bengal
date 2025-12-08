"""
Navigation directives for Bengal SSG.

Provides directives that leverage the pre-computed site tree:
- breadcrumbs: Auto-generate breadcrumb navigation from page.ancestors
- siblings: Show other pages in the same section
- prev-next: Section-aware previous/next navigation
- related: Show related content based on tags

All directives access renderer._current_page to walk the object tree.
"""

from __future__ import annotations

from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "BreadcrumbsDirective",
    "SiblingsDirective",
    "PrevNextDirective",
    "RelatedDirective",
    "render_breadcrumbs",
    "render_siblings",
    "render_prev_next",
    "render_related",
]


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# =============================================================================
# Breadcrumbs Directive
# =============================================================================


class BreadcrumbsDirective(DirectivePlugin):
    """
    Auto-generate breadcrumb navigation from page ancestors.

    Uses page.ancestors to build a breadcrumb trail from root to current page.

    Syntax:
        :::{breadcrumbs}
        :separator: /
        :show-home: true
        :home-text: Home
        :::

    Example output:
        Home / Docs / Content / Authoring
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["breadcrumbs"]

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """Parse breadcrumbs directive options."""
        options = dict(self.parse_options(m))

        separator = options.get("separator", "›")
        show_home = options.get("show-home", "true").lower() == "true"
        home_text = options.get("home-text", "Home")
        home_url = options.get("home-url", "/")

        return {
            "type": "breadcrumbs",
            "attrs": {
                "separator": separator,
                "show_home": show_home,
                "home_text": home_text,
                "home_url": home_url,
            },
            "children": [],
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("breadcrumbs", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("breadcrumbs", render_breadcrumbs)


def render_breadcrumbs(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render breadcrumb navigation from page ancestors.

    Args:
        renderer: Mistune renderer (has _current_page attribute)
        text: Unused
        attrs: Directive options

    Returns:
        HTML breadcrumb navigation
    """
    separator = attrs.get("separator", "›")
    show_home = attrs.get("show_home", True)
    home_text = attrs.get("home_text", "Home")
    home_url = attrs.get("home_url", "/")

    current_page = getattr(renderer, "_current_page", None)
    if not current_page:
        return '<nav class="breadcrumbs"><span class="breadcrumb-item">No page context</span></nav>'

    # Get ancestors (from immediate parent up to root)
    ancestors = getattr(current_page, "ancestors", [])

    # Build breadcrumb items (reversed: root first)
    items = []

    # Add home link if requested
    if show_home:
        items.append(
            f'<a class="breadcrumb-item" href="{_escape_html(home_url)}">{_escape_html(home_text)}</a>'
        )

    # Add ancestor sections (reversed so root is first)
    for section in reversed(ancestors):
        title = getattr(section, "title", "")
        url = _get_section_url(section)
        if title:
            items.append(
                f'<a class="breadcrumb-item" href="{_escape_html(url)}">{_escape_html(title)}</a>'
            )

    # Add current page (not linked)
    page_title = getattr(current_page, "title", "")
    if page_title:
        items.append(
            f'<span class="breadcrumb-item breadcrumb-current">{_escape_html(page_title)}</span>'
        )

    # Join with separator
    sep_html = f'<span class="breadcrumb-separator">{_escape_html(separator)}</span>'
    content = sep_html.join(items)

    return f'<nav class="breadcrumbs" aria-label="Breadcrumb">{content}</nav>\n'


def _get_section_url(section: Any) -> str:
    """Get URL for a section."""
    if hasattr(section, "index_page") and section.index_page:
        return getattr(section.index_page, "url", "/")
    path = getattr(section, "path", None)
    if path:
        return f"/{path}/"
    return "/"


# =============================================================================
# Siblings Directive
# =============================================================================


class SiblingsDirective(DirectivePlugin):
    """
    Show other pages in the same section.

    Uses page._section.sorted_pages to show sibling pages.

    Syntax:
        :::{siblings}
        :limit: 10
        :exclude-current: true
        :show-description: true
        :::
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["siblings"]

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """Parse siblings directive options."""
        options = dict(self.parse_options(m))

        limit = int(options.get("limit", "0")) or 0  # 0 = no limit
        exclude_current = options.get("exclude-current", "true").lower() == "true"
        show_description = options.get("show-description", "false").lower() == "true"

        return {
            "type": "siblings",
            "attrs": {
                "limit": limit,
                "exclude_current": exclude_current,
                "show_description": show_description,
            },
            "children": [],
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("siblings", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("siblings", render_siblings)


def render_siblings(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render sibling pages in the same section.

    Args:
        renderer: Mistune renderer
        text: Unused
        attrs: Directive options

    Returns:
        HTML list of sibling pages
    """
    limit = attrs.get("limit", 0)
    exclude_current = attrs.get("exclude_current", True)
    show_description = attrs.get("show_description", False)

    current_page = getattr(renderer, "_current_page", None)
    if not current_page:
        return '<div class="siblings"><p><em>No page context</em></p></div>'

    section = getattr(current_page, "_section", None)
    if not section:
        return '<div class="siblings"><p><em>No section</em></p></div>'

    # Get sorted pages in section
    pages = getattr(section, "sorted_pages", []) or getattr(section, "pages", [])

    # Filter out _index pages and optionally current page
    siblings = []
    for page in pages:
        source_str = str(getattr(page, "source_path", ""))
        # Skip index pages
        if source_str.endswith("_index.md") or source_str.endswith("index.md"):
            continue
        # Skip current page if requested
        if (
            exclude_current
            and hasattr(current_page, "source_path")
            and hasattr(page, "source_path")
            and page.source_path == current_page.source_path
        ):
            continue
        siblings.append(page)

    if not siblings:
        return '<div class="siblings"><p><em>No sibling pages</em></p></div>'

    # Apply limit
    if limit > 0:
        siblings = siblings[:limit]

    # Build HTML
    parts = ['<div class="siblings">', '<ul class="siblings-list">']

    for page in siblings:
        title = getattr(page, "title", "Untitled")
        url = getattr(page, "url", "/")
        description = ""
        if show_description and hasattr(page, "metadata"):
            description = page.metadata.get("description", "")

        parts.append("  <li>")
        parts.append(f'    <a href="{_escape_html(url)}">{_escape_html(title)}</a>')
        if description:
            parts.append(
                f'    <span class="sibling-description">{_escape_html(description)}</span>'
            )
        parts.append("  </li>")

    parts.append("</ul>")
    parts.append("</div>")

    return "\n".join(parts) + "\n"


# =============================================================================
# Prev-Next Directive
# =============================================================================


class PrevNextDirective(DirectivePlugin):
    """
    Section-aware previous/next navigation.

    Uses page.prev_in_section and page.next_in_section for navigation.

    Syntax:
        :::{prev-next}
        :show-title: true
        :show-section: false
        :::
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["prev-next"]

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """Parse prev-next directive options."""
        options = dict(self.parse_options(m))

        show_title = options.get("show-title", "true").lower() == "true"
        show_section = options.get("show-section", "false").lower() == "true"

        return {
            "type": "prev_next",
            "attrs": {
                "show_title": show_title,
                "show_section": show_section,
            },
            "children": [],
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("prev-next", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("prev_next", render_prev_next)


def render_prev_next(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render previous/next navigation links.

    Args:
        renderer: Mistune renderer
        text: Unused
        attrs: Directive options

    Returns:
        HTML prev/next navigation
    """
    show_title = attrs.get("show_title", True)
    # Note: show_section is parsed but not yet implemented (future enhancement)
    _ = attrs.get("show_section", False)

    current_page = getattr(renderer, "_current_page", None)
    if not current_page:
        return '<nav class="prev-next"><span>No page context</span></nav>'

    # Get prev/next pages
    prev_page = getattr(current_page, "prev_in_section", None)
    next_page = getattr(current_page, "next_in_section", None)

    if not prev_page and not next_page:
        return ""  # No navigation needed

    parts = ['<nav class="prev-next">']

    # Previous link
    if prev_page:
        prev_url = getattr(prev_page, "url", "/")
        prev_title = getattr(prev_page, "title", "Previous") if show_title else "Previous"
        parts.append(f'  <a class="prev-next-link prev-link" href="{_escape_html(prev_url)}">')
        parts.append('    <span class="prev-next-label">← Previous</span>')
        if show_title:
            parts.append(f'    <span class="prev-next-title">{_escape_html(prev_title)}</span>')
        parts.append("  </a>")
    else:
        parts.append('  <span class="prev-next-link prev-link disabled"></span>')

    # Next link
    if next_page:
        next_url = getattr(next_page, "url", "/")
        next_title = getattr(next_page, "title", "Next") if show_title else "Next"
        parts.append(f'  <a class="prev-next-link next-link" href="{_escape_html(next_url)}">')
        parts.append('    <span class="prev-next-label">Next →</span>')
        if show_title:
            parts.append(f'    <span class="prev-next-title">{_escape_html(next_title)}</span>')
        parts.append("  </a>")
    else:
        parts.append('  <span class="prev-next-link next-link disabled"></span>')

    parts.append("</nav>")

    return "\n".join(parts) + "\n"


# =============================================================================
# Related Directive
# =============================================================================


class RelatedDirective(DirectivePlugin):
    """
    Show related content based on tags.

    Uses page.related_posts (pre-computed during build).

    Syntax:
        :::{related}
        :limit: 5
        :title: Related Articles
        :show-tags: true
        :::
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["related"]

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """Parse related directive options."""
        options = dict(self.parse_options(m))

        limit = int(options.get("limit", "5"))
        title = options.get("title", "Related Articles")
        show_tags = options.get("show-tags", "false").lower() == "true"

        return {
            "type": "related",
            "attrs": {
                "limit": limit,
                "title": title,
                "show_tags": show_tags,
            },
            "children": [],
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("related", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("related", render_related)


def render_related(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render related content based on tags.

    Args:
        renderer: Mistune renderer
        text: Unused
        attrs: Directive options

    Returns:
        HTML list of related content
    """
    limit = attrs.get("limit", 5)
    title = attrs.get("title", "Related Articles")
    show_tags = attrs.get("show_tags", False)

    current_page = getattr(renderer, "_current_page", None)
    if not current_page:
        return '<aside class="related"><p><em>No page context</em></p></aside>'

    # Get pre-computed related posts
    related = getattr(current_page, "related_posts", [])

    if not related:
        return ""  # Don't render anything if no related posts

    # Apply limit
    if limit > 0:
        related = related[:limit]

    # Build HTML
    parts = ['<aside class="related">']
    if title:
        parts.append(f'  <h3 class="related-title">{_escape_html(title)}</h3>')
    parts.append('  <ul class="related-list">')

    for page in related:
        page_title = getattr(page, "title", "Untitled")
        page_url = getattr(page, "url", "/")
        page_tags = getattr(page, "tags", [])

        parts.append("    <li>")
        parts.append(f'      <a href="{_escape_html(page_url)}">{_escape_html(page_title)}</a>')

        if show_tags and page_tags:
            tags_html = ", ".join(_escape_html(tag) for tag in page_tags[:3])
            parts.append(f'      <span class="related-tags">{tags_html}</span>')

        parts.append("    </li>")

    parts.append("  </ul>")
    parts.append("</aside>")

    return "\n".join(parts) + "\n"
