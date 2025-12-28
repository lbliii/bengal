"""Navigation directives for documentation.

Provides:
- breadcrumbs: Auto-generate breadcrumb navigation from page ancestors
- siblings: Show other pages in the same section
- prev-next: Section-aware previous/next navigation
- related: Show related content based on tags

Site Context:
    These directives require access to the current page and site tree.
    The renderer must provide a `get_page_context` callback that returns
    the current page object with ancestors, section, etc.

Thread Safety:
    Stateless handlers. Safe for concurrent use across threads.

HTML Output:
    Matches Bengal's navigation directives exactly for parity.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import DirectiveOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder

__all__ = [
    "BreadcrumbsDirective",
    "SiblingsDirective",
    "PrevNextDirective",
    "RelatedDirective",
]


# =============================================================================
# Page Context Protocol
# =============================================================================


class PageContext(Protocol):
    """Protocol for page context required by navigation directives."""

    title: str
    href: str
    ancestors: list[Any]  # List of Section objects
    prev_in_section: Any | None  # Page object
    next_in_section: Any | None  # Page object
    related_posts: list[Any]  # List of Page objects
    tags: list[str]


# Type alias for page context getter
PageContextGetter = Callable[[], PageContext | None]


# =============================================================================
# Breadcrumbs Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class BreadcrumbsOptions(DirectiveOptions):
    """Options for breadcrumbs directive."""

    separator: str = "›"
    show_home: bool = True
    home_text: str = "Home"
    home_url: str = "/"


class BreadcrumbsDirective:
    """
    Auto-generate breadcrumb navigation from page ancestors.

    Syntax:
        :::{breadcrumbs}
        :separator: /
        :show-home: true
        :home-text: Home
        :::

    Output:
        <nav class="breadcrumbs" aria-label="Breadcrumb">
          <a class="breadcrumb-item" href="/">Home</a>
          <span class="breadcrumb-separator">›</span>
          <a class="breadcrumb-item" href="/section/">Section</a>
          <span class="breadcrumb-separator">›</span>
          <span class="breadcrumb-item breadcrumb-current">Current Page</span>
        </nav>

    Requires:
        Page context with `ancestors` attribute.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("breadcrumbs",)
    token_type: ClassVar[str] = "breadcrumbs"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[BreadcrumbsOptions]] = BreadcrumbsOptions

    # Set by renderer for page context access
    get_page_context: PageContextGetter | None = None

    def parse(
        self,
        name: str,
        title: str | None,
        options: BreadcrumbsOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build breadcrumbs AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=(),
        )

    def render(
        self,
        node: Directive[BreadcrumbsOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        get_page_context: PageContextGetter | None = None,
    ) -> None:
        """Render breadcrumb navigation."""
        opts = node.options  # Direct typed access!

        separator = opts.separator
        show_home = opts.show_home
        home_text = opts.home_text
        home_url = opts.home_url

        # Get page context
        context_getter = get_page_context or self.get_page_context
        current_page = context_getter() if context_getter else None

        if not current_page:
            sb.append(
                '<nav class="breadcrumbs"><span class="breadcrumb-item">No page context</span></nav>'
            )
            return

        ancestors = getattr(current_page, "ancestors", [])
        items: list[str] = []

        if show_home:
            items.append(
                f'<a class="breadcrumb-item" href="{html_escape(home_url)}">'
                f"{html_escape(home_text)}</a>"
            )

        for section in reversed(ancestors):
            section_title = getattr(section, "title", "")
            section_url = _get_section_url(section)
            if section_title:
                items.append(
                    f'<a class="breadcrumb-item" href="{html_escape(section_url)}">'
                    f"{html_escape(section_title)}</a>"
                )

        page_title = getattr(current_page, "title", "")
        if page_title:
            items.append(
                f'<span class="breadcrumb-item breadcrumb-current">{html_escape(page_title)}</span>'
            )

        sep_html = f'<span class="breadcrumb-separator">{html_escape(separator)}</span>'
        content = sep_html.join(items)

        sb.append(f'<nav class="breadcrumbs" aria-label="Breadcrumb">{content}</nav>\n')


# =============================================================================
# Siblings Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class SiblingsOptions(DirectiveOptions):
    """Options for siblings directive."""

    limit: int = 0
    exclude_current: bool = True
    show_description: bool = False


class SiblingsDirective:
    """
    Show other pages in the same section.

    Syntax:
        :::{siblings}
        :limit: 10
        :exclude-current: true
        :show-description: true
        :::

    Output:
        <div class="siblings">
          <ul class="siblings-list">
            <li><a href="/page1/">Page 1</a></li>
            <li><a href="/page2/">Page 2</a></li>
          </ul>
        </div>

    Requires:
        Page context with `_section.sorted_pages` attribute.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("siblings",)
    token_type: ClassVar[str] = "siblings"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[SiblingsOptions]] = SiblingsOptions

    get_page_context: PageContextGetter | None = None

    def parse(
        self,
        name: str,
        title: str | None,
        options: SiblingsOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build siblings AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=(),
        )

    def render(
        self,
        node: Directive[SiblingsOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        get_page_context: PageContextGetter | None = None,
    ) -> None:
        """Render sibling pages."""
        opts = node.options  # Direct typed access!

        limit = opts.limit
        exclude_current = opts.exclude_current
        show_description = opts.show_description

        # Get page context
        context_getter = get_page_context or self.get_page_context
        current_page = context_getter() if context_getter else None

        if not current_page:
            sb.append('<div class="siblings"><p><em>No page context</em></p></div>')
            return

        section = getattr(current_page, "_section", None)
        if not section:
            sb.append('<div class="siblings"><p><em>No section</em></p></div>')
            return

        pages = getattr(section, "sorted_pages", []) or getattr(section, "pages", [])

        siblings: list[Any] = []
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
            sb.append('<div class="siblings"><p><em>No sibling pages</em></p></div>')
            return

        if limit > 0:
            siblings = siblings[:limit]

        sb.append('<div class="siblings">\n<ul class="siblings-list">\n')

        for page in siblings:
            page_title = getattr(page, "title", "Untitled")
            url = getattr(page, "href", "/")
            description = ""
            if show_description and hasattr(page, "metadata"):
                description = page.metadata.get("description", "")

            sb.append("  <li>\n")
            sb.append(f'    <a href="{html_escape(url)}">{html_escape(page_title)}</a>\n')
            if description:
                sb.append(
                    f'    <span class="sibling-description">{html_escape(description)}</span>\n'
                )
            sb.append("  </li>\n")

        sb.append("</ul>\n</div>\n")


# =============================================================================
# Prev-Next Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class PrevNextOptions(DirectiveOptions):
    """Options for prev-next directive."""

    show_title: bool = True
    show_section: bool = False


class PrevNextDirective:
    """
    Section-aware previous/next navigation.

    Syntax:
        :::{prev-next}
        :show-title: true
        :show-section: false
        :::

    Output:
        <nav class="prev-next">
          <a class="prev-next-link prev-link" href="/prev/">
            <span class="prev-next-label">← Previous</span>
            <span class="prev-next-title">Previous Page</span>
          </a>
          <a class="prev-next-link next-link" href="/next/">
            <span class="prev-next-label">Next →</span>
            <span class="prev-next-title">Next Page</span>
          </a>
        </nav>

    Requires:
        Page context with `prev_in_section` and `next_in_section` attributes.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("prev-next",)
    token_type: ClassVar[str] = "prev_next"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[PrevNextOptions]] = PrevNextOptions

    get_page_context: PageContextGetter | None = None

    def parse(
        self,
        name: str,
        title: str | None,
        options: PrevNextOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build prev-next AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=(),
        )

    def render(
        self,
        node: Directive[PrevNextOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        get_page_context: PageContextGetter | None = None,
    ) -> None:
        """Render previous/next navigation."""
        opts = node.options  # Direct typed access!

        show_title = opts.show_title

        # Get page context
        context_getter = get_page_context or self.get_page_context
        current_page = context_getter() if context_getter else None

        if not current_page:
            sb.append('<nav class="prev-next"><span>No page context</span></nav>')
            return

        prev_page = getattr(current_page, "prev_in_section", None)
        next_page = getattr(current_page, "next_in_section", None)

        if not prev_page and not next_page:
            return

        sb.append('<nav class="prev-next">\n')

        if prev_page:
            prev_url = getattr(prev_page, "href", "/")
            prev_title = getattr(prev_page, "title", "Previous") if show_title else "Previous"
            sb.append(f'  <a class="prev-next-link prev-link" href="{html_escape(prev_url)}">\n')
            sb.append('    <span class="prev-next-label">← Previous</span>\n')
            if show_title:
                sb.append(f'    <span class="prev-next-title">{html_escape(prev_title)}</span>\n')
            sb.append("  </a>\n")
        else:
            sb.append('  <span class="prev-next-link prev-link disabled"></span>\n')

        if next_page:
            next_url = getattr(next_page, "href", "/")
            next_title = getattr(next_page, "title", "Next") if show_title else "Next"
            sb.append(f'  <a class="prev-next-link next-link" href="{html_escape(next_url)}">\n')
            sb.append('    <span class="prev-next-label">Next →</span>\n')
            if show_title:
                sb.append(f'    <span class="prev-next-title">{html_escape(next_title)}</span>\n')
            sb.append("  </a>\n")
        else:
            sb.append('  <span class="prev-next-link next-link disabled"></span>\n')

        sb.append("</nav>\n")


# =============================================================================
# Related Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class RelatedOptions(DirectiveOptions):
    """Options for related directive."""

    limit: int = 5
    section_title: str = "Related Articles"
    show_tags: bool = False


class RelatedDirective:
    """
    Show related content based on tags.

    Syntax:
        :::{related}
        :limit: 5
        :title: Related Articles
        :show-tags: true
        :::

    Output:
        <aside class="related">
          <h3 class="related-title">Related Articles</h3>
          <ul class="related-list">
            <li><a href="/article1/">Article 1</a></li>
            <li><a href="/article2/">Article 2</a></li>
          </ul>
        </aside>

    Requires:
        Page context with `related_posts` attribute.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("related",)
    token_type: ClassVar[str] = "related"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[RelatedOptions]] = RelatedOptions

    get_page_context: PageContextGetter | None = None

    def parse(
        self,
        name: str,
        title: str | None,
        options: RelatedOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build related AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=(),
        )

    def render(
        self,
        node: Directive[RelatedOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        get_page_context: PageContextGetter | None = None,
    ) -> None:
        """Render related content."""
        opts = node.options  # Direct typed access!

        limit = opts.limit
        section_title = opts.section_title
        show_tags = opts.show_tags

        # Get page context
        context_getter = get_page_context or self.get_page_context
        current_page = context_getter() if context_getter else None

        if not current_page:
            sb.append('<aside class="related"><p><em>No page context</em></p></aside>')
            return

        related = getattr(current_page, "related_posts", [])

        if not related:
            return

        if limit > 0:
            related = related[:limit]

        sb.append('<aside class="related">\n')
        if section_title:
            sb.append(f'  <h3 class="related-title">{html_escape(section_title)}</h3>\n')
        sb.append('  <ul class="related-list">\n')

        for page in related:
            page_title = getattr(page, "title", "Untitled")
            page_url = getattr(page, "href", "/")
            page_tags = getattr(page, "tags", [])

            sb.append("    <li>\n")
            sb.append(f'      <a href="{html_escape(page_url)}">{html_escape(page_title)}</a>\n')

            if show_tags and page_tags:
                tags_html = ", ".join(html_escape(tag) for tag in page_tags[:3])
                sb.append(f'      <span class="related-tags">{tags_html}</span>\n')

            sb.append("    </li>\n")

        sb.append("  </ul>\n")
        sb.append("</aside>\n")


# =============================================================================
# Helper Functions
# =============================================================================


def _get_section_url(section: Any) -> str:
    """Get URL for a section (includes baseurl)."""
    if hasattr(section, "href"):
        return section.href
    if hasattr(section, "index_page") and section.index_page:
        return getattr(section.index_page, "href", "/")
    return "/"
