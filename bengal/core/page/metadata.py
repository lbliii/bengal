"""
Page Metadata Mixin - Basic properties and type checking.
"""

from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.page.page_core import PageCore


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
    _site: Any
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
        # Core has authoritative version
        if self.core is not None and self.core.version:
            return self.core.version
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

    @cached_property
    def relative_url(self) -> str:
        """
        Get relative URL without baseurl (for comparisons).

        This is the identity URL - use for comparisons, menu activation, etc.
        Always returns a relative path without baseurl.
        """
        # Fallback if no output path set
        if not self.output_path:
            return self._fallback_url()

        # Need site reference to compute relative path
        if not self._site:
            return self._fallback_url()

        try:
            # Compute relative path from actual output directory
            rel_path = self.output_path.relative_to(self._site.output_dir)
        except ValueError:
            # output_path not under output_dir - can happen during page initialization
            # when output_path hasn't been properly set yet, or for pages with unusual
            # configurations. Fall back to slug-based URL silently.
            #
            # Only log at debug level since this is a known/expected edge case during
            # page construction (PageInitializer checks URL generation early).
            emit_diagnostic(
                self,
                "debug",
                "page_output_path_fallback",
                output_path=str(self.output_path),
                output_dir=str(self._site.output_dir),
                page_source=str(getattr(self, "source_path", "unknown")),
            )
            return self._fallback_url()

        # Convert Path to URL components
        url_parts = list(rel_path.parts)

        # Remove 'index.html' from end (it's implicit in URLs)
        if url_parts and url_parts[-1] == "index.html":
            url_parts = url_parts[:-1]
        elif url_parts and url_parts[-1].endswith(".html"):
            # For non-index pages, remove .html extension
            # e.g., about.html -> about
            url_parts[-1] = url_parts[-1][:-5]

        # Construct URL with leading and trailing slashes
        if not url_parts:
            # Root index page
            return "/"

        url = "/" + "/".join(url_parts)

        # Ensure trailing slash for directory-like URLs
        if not url.endswith("/"):
            url += "/"

        return url

    @cached_property
    def url(self) -> str:
        """
        Get URL with baseurl applied (cached after first access).

        This is the primary URL property for templates - automatically includes
        baseurl when available. Use .relative_url for comparisons.

        Returns:
            URL path with baseurl prepended (if configured)
        """
        # Get relative URL first
        rel = self.relative_url or "/"

        # Best-effort baseurl lookup; remain robust if site/config is missing
        baseurl = ""
        try:
            baseurl = self._site.config.get("baseurl", "") if getattr(self, "_site", None) else ""
        except Exception as e:
            emit_diagnostic(self, "debug", "page_baseurl_lookup_failed", error=str(e))
            baseurl = ""

        if not baseurl:
            return rel

        baseurl = baseurl.rstrip("/")
        rel = "/" + rel.lstrip("/")
        return f"{baseurl}{rel}"

    @cached_property
    def permalink(self) -> str:
        """
        Alias for url (for backward compatibility).

        Both url and permalink now return the same value (with baseurl).
        Use .relative_url for comparisons.
        """
        return self.url

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
        return self.url == "/" or self.slug in ("index", "_index", "home")

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
        Get visual variant from core (preferred) or legacy layout/hero_style fields.

        This normalizes 'layout' and 'hero_style' into the new Component Model 'variant'.

        Component Model: Mode.

        Returns:
            Variant string or None
        """
        if self.core is not None and self.core.variant:
            return self.core.variant

        # Legacy fallbacks
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
