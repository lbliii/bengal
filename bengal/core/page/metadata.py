"""
Page Metadata Mixin - Basic properties and type checking.

This mixin provides core metadata properties (title, date, slug, URL) and
type checking capabilities (is_home, is_section, kind) for pages. It also
implements the Component Model properties (type, variant, props) and the
visibility system for controlling page inclusion in listings/sitemap/search.

Key Properties:
    Metadata:
        - title, nav_title: Page titles for display and navigation
        - date, slug: Publication date and URL slug
        - href, _path: Public URL and internal path
        - toc_items: Structured table of contents data

    Type Checking:
        - is_home, is_section, is_page: Page type predicates
        - kind: Returns 'home', 'section', or 'page'

    Component Model:
        - type: Page type (routing/template selection)
        - variant: Visual variant (CSS/layout customization)
        - props: Custom properties dictionary

    Visibility:
        - hidden, draft: Basic visibility flags
        - visibility: Granular visibility settings
        - in_listings, in_sitemap, in_search, in_rss: Inclusion checks

Related Modules:
    - bengal.core.page.page_core: PageCore with cached metadata
    - bengal.utils.dates: Date parsing utilities

See Also:
    - bengal/core/page/__init__.py: Page class that uses this mixin
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.page.page_core import PageCore
    from bengal.core.site import Site


class PageMetadataMixin:
    """
    Mixin providing metadata properties and type checking for pages.

    This mixin handles:
    - Basic properties: title, date, slug, url
    - Type checking: is_home, is_section, is_page, kind
    - Simple metadata: description, draft, keywords
    - Component Model: type, variant, props
    - TOC access: toc_items (lazy evaluation)
    """

    # Declare attributes that will be provided by the dataclass this mixin is mixed into
    metadata: dict[str, Any]
    source_path: Path
    output_path: Path | None
    toc: str | None
    core: PageCore | None
    _site: Site | None
    _toc_items_cache: list[dict[str, Any]] | None
    # slug is defined as a property below - no declaration needed here

    @property
    def title(self) -> str:
        """
        Get page title from metadata or generate intelligently from context.

        For index pages (_index.md or index.md) without explicit titles,
        uses the parent directory name humanized instead of showing "Index"
        which is not user-friendly in menus, navigation, or page titles.

        Examples:
            api/_index.md → "Api"
            docs/index.md → "Docs"
            data-designer/_index.md → "Data Designer"
            my_module/index.md → "My Module"
            about.md → "About"
        """
        # Check metadata first (explicit titles always win)
        if "title" in self.metadata:
            return str(self.metadata["title"])

        # Special handling for index pages - use directory name instead of "Index"
        if self.source_path.stem in ("_index", "index"):
            dir_name = self.source_path.parent.name
            # Humanize: replace separators with spaces and title case
            return dir_name.replace("-", " ").replace("_", " ").title()

        # Regular pages use filename (humanized)
        return self.source_path.stem.replace("-", " ").title()

    @property
    def nav_title(self) -> str:
        """
        Get navigation title (shorter title for menus/sidebar).

        Falls back to regular title if nav_title not specified in frontmatter.
        Use this in navigation/menu templates for compact display.

        Example:
            ```yaml
            ---
            title: Content Authoring Guide
            nav_title: Authoring
            ---
            ```

        In templates:
            {{ page.nav_title }}  # "Authoring" (or title if not set)
        """
        # Check core first (cached)
        if self.core is not None and self.core.nav_title:
            return self.core.nav_title
        # Check metadata (fallback)
        if "nav_title" in self.metadata:
            return str(self.metadata["nav_title"])
        # Fall back to title
        return self.title

    @property
    def date(self) -> datetime | None:
        """
        Get page date from metadata.

        Uses bengal.utils.dates.parse_date for flexible date parsing.
        """
        from bengal.utils.dates import parse_date

        date_value = self.metadata.get("date")
        return parse_date(date_value)

    @property
    def version(self) -> str | None:
        """
        Get version ID for this page.

        Returns the version this page belongs to (e.g., 'v3', 'v2').
        Set during discovery based on content path or frontmatter override.

        Returns:
            Version ID string or None if not versioned
        """
        # Core has authoritative version (for cached pages)
        if self.core is not None and self.core.version:
            return self.core.version
        # Check internal version set during discovery
        if "_version" in self.metadata:
            return self.metadata.get("_version")
        # Check frontmatter override
        return self.metadata.get("version")

    @property
    def slug(self) -> str:
        """Get URL slug for the page."""
        # Check metadata first
        if "slug" in self.metadata:
            return str(self.metadata["slug"])

        # Special handling for _index.md files
        if self.source_path.stem == "_index":
            # Use the parent directory name as the slug
            return self.source_path.parent.name

        return self.source_path.stem

    @property
    def href(self) -> str:
        """
        URL for template href attributes. Includes baseurl.

        Use this in templates for all links:
            <a href="{{ page.href }}">
            <link href="{{ page.href }}">

        Returns:
            URL path with baseurl prepended (if configured)

        Note: Uses manual caching that only stores when _path is properly
        computed (not from fallback).
        """
        # Check for manually-set value first (tests use this pattern)
        # This allows __dict__['href'] = '/path/' to work
        manual_value = self.__dict__.get("href")
        if manual_value is not None:
            return manual_value

        # Check for cached value
        cached = self.__dict__.get("_href_cache")
        if cached is not None:
            return cached

        # Get site-relative path first
        rel = self._path or "/"

        # Best-effort baseurl lookup; remain robust if site/config is missing
        baseurl = ""
        try:
            baseurl = self._site.config.get("baseurl", "") if getattr(self, "_site", None) else ""
        except Exception as e:
            emit_diagnostic(self, "debug", "page_baseurl_lookup_failed", error=str(e))
            baseurl = ""

        # Normalize baseurl: treat "/" and "" as empty
        baseurl = (baseurl or "").rstrip("/")
        if baseurl == "/":
            baseurl = ""

        if not baseurl:
            result = rel
        else:
            rel = "/" + rel.lstrip("/")
            result = f"{baseurl}{rel}"

        # Only cache if _path was properly computed (has its own cache)
        if "_path_cache" in self.__dict__:
            self.__dict__["_href_cache"] = result

        return result

    @property
    def _path(self) -> str:
        """
        Internal site-relative path. NO baseurl.

        Use for internal operations only:
        - Cache keys
        - Active trail detection
        - URL comparisons
        - Link validation

        NEVER use in templates - use .href instead.
        """
        # Check for manually-set value first (tests use this pattern)
        manual_value = self.__dict__.get("_path")
        if manual_value is not None:
            return manual_value

        cached = self.__dict__.get("_path_cache")
        if cached is not None:
            return cached

        if not self.output_path:
            return self._fallback_url()

        if not self._site:
            return self._fallback_url()

        try:
            rel_path = self.output_path.relative_to(self._site.output_dir)
        except ValueError:
            emit_diagnostic(
                self,
                "debug",
                "page_output_path_fallback",
                output_path=str(self.output_path),
                output_dir=str(self._site.output_dir),
                page_source=str(getattr(self, "source_path", "unknown")),
            )
            return self._fallback_url()

        url_parts = list(rel_path.parts)
        if url_parts and url_parts[-1] == "index.html":
            url_parts = url_parts[:-1]
        elif url_parts and url_parts[-1].endswith(".html"):
            url_parts[-1] = url_parts[-1][:-5]

        if not url_parts:
            url = "/"
        else:
            url = "/" + "/".join(url_parts)
            if not url.endswith("/"):
                url += "/"

        self.__dict__["_path_cache"] = url
        return url

    @property
    def absolute_href(self) -> str:
        """
        Fully-qualified URL for meta tags and sitemaps when available.

        Bengal's configuration model uses `baseurl` as the public URL prefix. It may be:
        - Empty: "" (root-relative URLs)
        - Path-only: "/bengal" (GitHub Pages subpath)
        - Absolute: "https://example.com" (fully-qualified base)

        If `baseurl` is absolute, `href` is already absolute and this returns it.
        Otherwise, this falls back to `href` (root-relative) because no fully-qualified
        site origin is configured.
        """
        if not self._site or not self._site.config.get("url"):
            return self.href
        site_url = self._site.config["url"].rstrip("/")
        return f"{site_url}{self._path}"

    def _fallback_url(self) -> str:
        """
        Generate fallback URL when output_path or site not available.

        Used during page construction before output_path is determined.

        Returns:
            URL based on slug
        """
        return f"/{self.slug}/"

    @property
    def toc_items(self) -> list[dict[str, Any]]:
        """
        Get structured TOC data (lazy evaluation).

        Only extracts TOC structure when accessed by templates, saving
        HTMLParser overhead for pages that don't use toc_items.

        Important: This property does NOT cache empty results. This allows
        toc_items to be accessed before parsing (during xref indexing) without
        preventing extraction after parsing when page.toc is actually set.

        Returns:
            List of TOC items with id, title, and level
        """
        # Only extract and cache if we haven't extracted yet AND toc exists
        # Don't cache empty results - toc might be set later during parsing
        if self._toc_items_cache is None and self.toc:
            # Import here to avoid circular dependency
            from bengal.rendering.pipeline import extract_toc_structure

            self._toc_items_cache = extract_toc_structure(self.toc)

        # Return cached value if we have it, otherwise empty list
        # (but don't cache the empty list - allow re-evaluation when toc is set)
        return self._toc_items_cache if self._toc_items_cache is not None else []

    @property
    def is_home(self) -> bool:
        """
        Check if this page is the home page.

        Returns:
            True if this is the home page

        Example:
            {% if page.is_home %}
              <h1>Welcome to the home page!</h1>
            {% endif %}
        """
        return self._path == "/" or self.slug in ("index", "_index", "home")

    @property
    def is_section(self) -> bool:
        """
        Check if this page is a section page.

        Returns:
            True if this is a section (always False for Page, True for Section)

        Example:
            {% if page.is_section %}
              <h2>Section: {{ page.title }}</h2>
            {% endif %}
        """
        # Import here to avoid circular import
        from bengal.core.section import Section

        return isinstance(self, Section)

    @property
    def is_page(self) -> bool:
        """
        Check if this is a regular page (not a section).

        Returns:
            True if this is a regular page

        Example:
            {% if page.is_page %}
              <article>{{ page.content }}</article>
            {% endif %}
        """
        return not self.is_section

    @property
    def kind(self) -> str:
        """
        Get the kind of page: 'home', 'section', or 'page'.

        Returns:
            String indicating page kind

        Example:
            {% if page.kind == 'section' %}
              {# Render section template #}
            {% endif %}
        """
        if self.is_home:
            return "home"
        elif self.is_section:
            return "section"
        return "page"

    # =========================================================================
    # Component Model Properties
    # =========================================================================

    @property
    def type(self) -> str | None:
        """
        Get page type from core metadata (preferred) or frontmatter.

        Component Model: Identity.

        Returns:
            Page type or None
        """
        if self.core is not None and self.core.type:
            return self.core.type
        return self.metadata.get("type")

    @property
    def description(self) -> str:
        """
        Get page description from core metadata (preferred) or frontmatter.

        Returns:
            Page description or empty string
        """
        if self.core is not None and self.core.description:
            return self.core.description
        return str(self.metadata.get("description", ""))

    @property
    def variant(self) -> str | None:
        """
        Get visual variant from core (preferred) or layout/hero_style fields.

        Normalizes 'layout' and 'hero_style' into the Component Model 'variant'.

        Component Model: Mode.

        Returns:
            Variant string or None
        """
        if self.core is not None and self.core.variant:
            return self.core.variant

        # Fallbacks
        return self.metadata.get("layout") or self.metadata.get("hero_style")

    @property
    def props(self) -> dict[str, Any]:
        """
        Get page props (alias for metadata).

        Component Model: Data.

        Returns:
            Page metadata dictionary
        """
        return self.metadata

    @property
    def draft(self) -> bool:
        """
        Check if page is marked as draft.

        Returns:
            True if page is a draft
        """
        return bool(self.metadata.get("draft", False))

    @property
    def keywords(self) -> list[str]:
        """
        Get page keywords from metadata.

        Returns:
            List of keywords
        """
        keywords = self.metadata.get("keywords", [])
        if isinstance(keywords, str):
            # Split comma-separated keywords
            return [k.strip() for k in keywords.split(",")]
        return keywords if isinstance(keywords, list) else []

    # =========================================================================
    # Visibility System
    # =========================================================================

    @property
    def hidden(self) -> bool:
        """
        Check if page is hidden (unlisted).

        Hidden pages:
        - Are excluded from navigation menus
        - Are excluded from site.pages queries (listings)
        - Are excluded from sitemap.xml
        - Get noindex,nofollow robots meta
        - Still render and are accessible via direct URL

        Returns:
            True if page is hidden

        Example:
            ```yaml
            ---
            title: Secret Page
            hidden: true
            ---
            ```
        """
        return bool(self.metadata.get("hidden", False))

    @property
    def visibility(self) -> dict[str, Any]:
        """
        Get visibility settings with defaults.

        The visibility object provides granular control over page visibility:
        - menu: Include in navigation menus (default: True)
        - listings: Include in site.pages queries (default: True)
        - sitemap: Include in sitemap.xml (default: True)
        - robots: Robots meta directive (default: "index, follow")
        - render: When to render - "always", "local", "never" (default: "always")
        - search: Include in search index (default: True)
        - rss: Include in RSS feeds (default: True)

        If `hidden: true` is set, it expands to restrictive defaults.

        Returns:
            Dict with visibility settings

        Example:
            ```yaml
            ---
            title: Partially Hidden
            visibility:
                menu: false
                listings: true
                sitemap: true
            ---
            ```
        """
        # If hidden shorthand is used, return restrictive defaults
        if self.metadata.get("hidden", False):
            return {
                "menu": False,
                "listings": False,
                "sitemap": False,
                "robots": "noindex, nofollow",
                "render": "always",
                "search": False,
                "rss": False,
            }

        # Otherwise, get visibility object with permissive defaults
        vis = self.metadata.get("visibility", {})
        return {
            "menu": vis.get("menu", True),
            "listings": vis.get("listings", True),
            "sitemap": vis.get("sitemap", True),
            "robots": vis.get("robots", "index, follow"),
            "render": vis.get("render", "always"),
            "search": vis.get("search", True),
            "rss": vis.get("rss", True),
        }

    @property
    def in_listings(self) -> bool:
        """
        Check if page should appear in listings/queries.

        Excludes drafts and pages with visibility.listings=False.

        Returns:
            True if page should appear in site.pages queries
        """
        return self.visibility["listings"] and not self.draft

    @property
    def in_sitemap(self) -> bool:
        """
        Check if page should appear in sitemap.

        Excludes drafts and pages with visibility.sitemap=False.

        Returns:
            True if page should appear in sitemap.xml
        """
        return self.visibility["sitemap"] and not self.draft

    @property
    def in_search(self) -> bool:
        """
        Check if page should appear in search index.

        Excludes drafts and pages with visibility.search=False.

        Returns:
            True if page should appear in search index
        """
        return self.visibility["search"] and not self.draft

    @property
    def in_rss(self) -> bool:
        """
        Check if page should appear in RSS feeds.

        Excludes drafts and pages with visibility.rss=False.

        Returns:
            True if page should appear in RSS feeds
        """
        return self.visibility["rss"] and not self.draft

    @property
    def robots_meta(self) -> str:
        """
        Get robots meta content for this page.

        Returns:
            Robots directive string (e.g., "index, follow" or "noindex, nofollow")
        """
        return str(self.visibility["robots"])

    @property
    def should_render(self) -> bool:
        """
        Check if page should be rendered based on visibility.render setting.

        Note: This checks the render setting but doesn't know about environment.
        Use should_render_in_environment() for environment-aware checks.

        Returns:
            True if render is not "never"
        """
        return bool(self.visibility["render"] != "never")

    def should_render_in_environment(self, is_production: bool = False) -> bool:
        """
        Check if page should be rendered in the given environment.

        Args:
            is_production: True if building for production

        Returns:
            True if page should be rendered in this environment

        Example:
            ```yaml
            ---
            visibility:
                render: local  # Only in dev server
            ---
            ```
        """
        render = self.visibility["render"]

        if render == "never":
            return False
        return not (render == "local" and is_production)
