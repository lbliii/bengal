"""
Navigation directives for Bengal SSG.

Provides directives that leverage the pre-computed site tree:
- breadcrumbs: Auto-generate breadcrumb navigation from page.ancestors
- siblings: Show other pages in the same section
- prev-next: Section-aware previous/next navigation
- related: Show related content based on tags

Architecture:
    All directives access renderer._current_page to walk the object tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "BreadcrumbsDirective",
    "BreadcrumbsOptions",
    "SiblingsDirective",
    "SiblingsOptions",
    "PrevNextDirective",
    "PrevNextOptions",
    "RelatedDirective",
    "RelatedOptions",
]


# =============================================================================
# Breadcrumbs Directive
# =============================================================================


@dataclass
class BreadcrumbsOptions(DirectiveOptions):
    """
    Options for breadcrumbs directive.

    Attributes:
        separator: Separator character between items (default: ›)
        show_home: Whether to show home link (default: true)
        home_text: Text for home link (default: Home)
        home_url: URL for home link (default: /)
    """

    separator: str = "›"
    show_home: bool = True
    home_text: str = "Home"
    home_url: str = "/"

    _field_aliases: ClassVar[dict[str, str]] = {
        "show-home": "show_home",
        "home-text": "home_text",
        "home-url": "home_url",
    }


class BreadcrumbsDirective(BengalDirective):
    """
    Auto-generate breadcrumb navigation from page ancestors.

    Syntax:
        :::{breadcrumbs}
        :separator: /
        :show-home: true
        :home-text: Home
        :::
    """

    NAMES: ClassVar[list[str]] = ["breadcrumbs"]
    TOKEN_TYPE: ClassVar[str] = "breadcrumbs"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = BreadcrumbsOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["breadcrumbs"]

    def parse_directive(
        self,
        title: str,
        options: BreadcrumbsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build breadcrumbs token."""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "separator": options.separator,
                "show_home": options.show_home,
                "home_text": options.home_text,
                "home_url": options.home_url,
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render breadcrumb navigation from page ancestors."""
        separator = attrs.get("separator", "›")
        show_home = attrs.get("show_home", True)
        home_text = attrs.get("home_text", "Home")
        home_url = attrs.get("home_url", "/")

        current_page = getattr(renderer, "_current_page", None)
        if not current_page:
            return '<nav class="breadcrumbs"><span class="breadcrumb-item">No page context</span></nav>'

        ancestors = getattr(current_page, "ancestors", [])
        items = []

        if show_home:
            items.append(
                f'<a class="breadcrumb-item" href="{self.escape_html(home_url)}">'
                f"{self.escape_html(home_text)}</a>"
            )

        for section in reversed(ancestors):
            title = getattr(section, "title", "")
            url = _get_section_url(section)
            if title:
                items.append(
                    f'<a class="breadcrumb-item" href="{self.escape_html(url)}">'
                    f"{self.escape_html(title)}</a>"
                )

        page_title = getattr(current_page, "title", "")
        if page_title:
            items.append(
                f'<span class="breadcrumb-item breadcrumb-current">'
                f"{self.escape_html(page_title)}</span>"
            )

        sep_html = f'<span class="breadcrumb-separator">{self.escape_html(separator)}</span>'
        content = sep_html.join(items)

        return f'<nav class="breadcrumbs" aria-label="Breadcrumb">{content}</nav>\n'


# =============================================================================
# Siblings Directive
# =============================================================================


@dataclass
class SiblingsOptions(DirectiveOptions):
    """
    Options for siblings directive.

    Attributes:
        limit: Maximum number of siblings to show (0 = no limit)
        exclude_current: Whether to exclude current page
        show_description: Whether to show page descriptions
    """

    limit: int = 0
    exclude_current: bool = True
    show_description: bool = False

    _field_aliases: ClassVar[dict[str, str]] = {
        "exclude-current": "exclude_current",
        "show-description": "show_description",
    }


class SiblingsDirective(BengalDirective):
    """
    Show other pages in the same section.

    Syntax:
        :::{siblings}
        :limit: 10
        :exclude-current: true
        :show-description: true
        :::
    """

    NAMES: ClassVar[list[str]] = ["siblings"]
    TOKEN_TYPE: ClassVar[str] = "siblings"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = SiblingsOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["siblings"]

    def parse_directive(
        self,
        title: str,
        options: SiblingsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build siblings token."""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "limit": options.limit,
                "exclude_current": options.exclude_current,
                "show_description": options.show_description,
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render sibling pages in the same section."""
        limit = attrs.get("limit", 0)
        exclude_current = attrs.get("exclude_current", True)
        show_description = attrs.get("show_description", False)

        current_page = getattr(renderer, "_current_page", None)
        if not current_page:
            return '<div class="siblings"><p><em>No page context</em></p></div>'

        section = getattr(current_page, "_section", None)
        if not section:
            return '<div class="siblings"><p><em>No section</em></p></div>'

        pages = getattr(section, "sorted_pages", []) or getattr(section, "pages", [])

        siblings = []
        for page in pages:
            source_str = str(getattr(page, "source_path", ""))
            if source_str.endswith("_index.md") or source_str.endswith("index.md"):
                continue
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

        if limit > 0:
            siblings = siblings[:limit]

        parts = ['<div class="siblings">', '<ul class="siblings-list">']

        for page in siblings:
            title = getattr(page, "title", "Untitled")
            url = getattr(page, "href", "/")
            description = ""
            if show_description and hasattr(page, "metadata"):
                description = page.metadata.get("description", "")

            parts.append("  <li>")
            parts.append(f'    <a href="{self.escape_html(url)}">{self.escape_html(title)}</a>')
            if description:
                parts.append(
                    f'    <span class="sibling-description">{self.escape_html(description)}</span>'
                )
            parts.append("  </li>")

        parts.append("</ul>")
        parts.append("</div>")

        return "\n".join(parts) + "\n"


# =============================================================================
# Prev-Next Directive
# =============================================================================


@dataclass
class PrevNextOptions(DirectiveOptions):
    """
    Options for prev-next directive.

    Attributes:
        show_title: Whether to show page titles
        show_section: Whether to show section names
    """

    show_title: bool = True
    show_section: bool = False

    _field_aliases: ClassVar[dict[str, str]] = {
        "show-title": "show_title",
        "show-section": "show_section",
    }


class PrevNextDirective(BengalDirective):
    """
    Section-aware previous/next navigation.

    Syntax:
        :::{prev-next}
        :show-title: true
        :show-section: false
        :::
    """

    NAMES: ClassVar[list[str]] = ["prev-next"]
    TOKEN_TYPE: ClassVar[str] = "prev_next"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = PrevNextOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["prev-next"]

    def parse_directive(
        self,
        title: str,
        options: PrevNextOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build prev-next token."""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "show_title": options.show_title,
                "show_section": options.show_section,
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render previous/next navigation links."""
        show_title = attrs.get("show_title", True)
        _ = attrs.get("show_section", False)  # Reserved for future use

        current_page = getattr(renderer, "_current_page", None)
        if not current_page:
            return '<nav class="prev-next"><span>No page context</span></nav>'

        prev_page = getattr(current_page, "prev_in_section", None)
        next_page = getattr(current_page, "next_in_section", None)

        if not prev_page and not next_page:
            return ""

        parts = ['<nav class="prev-next">']

        if prev_page:
            prev_url = getattr(prev_page, "href", "/")
            prev_title = getattr(prev_page, "title", "Previous") if show_title else "Previous"
            parts.append(
                f'  <a class="prev-next-link prev-link" href="{self.escape_html(prev_url)}">'
            )
            parts.append('    <span class="prev-next-label">← Previous</span>')
            if show_title:
                parts.append(
                    f'    <span class="prev-next-title">{self.escape_html(prev_title)}</span>'
                )
            parts.append("  </a>")
        else:
            parts.append('  <span class="prev-next-link prev-link disabled"></span>')

        if next_page:
            next_url = getattr(next_page, "href", "/")
            next_title = getattr(next_page, "title", "Next") if show_title else "Next"
            parts.append(
                f'  <a class="prev-next-link next-link" href="{self.escape_html(next_url)}">'
            )
            parts.append('    <span class="prev-next-label">Next →</span>')
            if show_title:
                parts.append(
                    f'    <span class="prev-next-title">{self.escape_html(next_title)}</span>'
                )
            parts.append("  </a>")
        else:
            parts.append('  <span class="prev-next-link next-link disabled"></span>')

        parts.append("</nav>")

        return "\n".join(parts) + "\n"


# =============================================================================
# Related Directive
# =============================================================================


@dataclass
class RelatedOptions(DirectiveOptions):
    """
    Options for related directive.

    Attributes:
        limit: Maximum number of related items (default: 5)
        title: Section title (default: Related Articles)
        show_tags: Whether to show tags
    """

    limit: int = 5
    title: str = "Related Articles"
    show_tags: bool = False

    _field_aliases: ClassVar[dict[str, str]] = {
        "show-tags": "show_tags",
    }


class RelatedDirective(BengalDirective):
    """
    Show related content based on tags.

    Syntax:
        :::{related}
        :limit: 5
        :title: Related Articles
        :show-tags: true
        :::
    """

    NAMES: ClassVar[list[str]] = ["related"]
    TOKEN_TYPE: ClassVar[str] = "related"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = RelatedOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["related"]

    def parse_directive(
        self,
        title: str,
        options: RelatedOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build related token."""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "limit": options.limit,
                "title": options.title,
                "show_tags": options.show_tags,
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render related content based on tags."""
        limit = attrs.get("limit", 5)
        title = attrs.get("title", "Related Articles")
        show_tags = attrs.get("show_tags", False)

        current_page = getattr(renderer, "_current_page", None)
        if not current_page:
            return '<aside class="related"><p><em>No page context</em></p></aside>'

        related = getattr(current_page, "related_posts", [])

        if not related:
            return ""

        if limit > 0:
            related = related[:limit]

        parts = ['<aside class="related">']
        if title:
            parts.append(f'  <h3 class="related-title">{self.escape_html(title)}</h3>')
        parts.append('  <ul class="related-list">')

        for page in related:
            page_title = getattr(page, "title", "Untitled")
            page_url = getattr(page, "href", "/")
            page_tags = getattr(page, "tags", [])

            parts.append("    <li>")
            parts.append(
                f'      <a href="{self.escape_html(page_url)}">{self.escape_html(page_title)}</a>'
            )

            if show_tags and page_tags:
                tags_html = ", ".join(self.escape_html(tag) for tag in page_tags[:3])
                parts.append(f'      <span class="related-tags">{tags_html}</span>')

            parts.append("    </li>")

        parts.append("  </ul>")
        parts.append("</aside>")

        return "\n".join(parts) + "\n"


# =============================================================================
# Helper Functions
# =============================================================================


def _get_section_url(section: Any) -> str:
    """Get URL for a section."""
    if hasattr(section, "index_page") and section.index_page:
        return getattr(section.index_page, "href", "/")
    path = getattr(section, "path", None)
    if path:
        return f"/{path}/"
    return "/"
