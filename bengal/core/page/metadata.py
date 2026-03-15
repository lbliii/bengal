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
from functools import cached_property
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.page.types import TOCItem
from bengal.core.utils.shared import resolve_nav_title, sortable_weight
from bengal.core.utils.url import apply_baseurl, get_baseurl, get_site_origin

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
    # Note: metadata is a property returning CascadeView, _raw_metadata is the dict
    metadata: Any  # CascadeView or dict (Mapping[str, Any])
    _raw_metadata: dict[str, Any]
    source_path: Path
    output_path: Path | None
    toc: str | None
    core: PageCore | None
    _site: Site | None
    _toc_items_cache: list[TOCItem] | None
    # slug is defined as a property below - no declaration needed here

    @property
    def title(self) -> str:
        """Get page title from metadata or generate intelligently from context.

        Cost: O(1) cached — CascadeView dict lookup after first metadata access.

        For index pages (_index.md or index.md) without explicit titles,
        uses the parent directory name humanized instead of showing "Index"
        which is not user-friendly in menus, navigation, or page titles.
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
        """Get navigation title (shorter title for menus/sidebar).

        Cost: O(1) cached — core field or CascadeView lookup + resolve_nav_title.

        Falls back to regular title if nav_title not specified in frontmatter.
        """
        nav = (
            self.core.nav_title
            if self.core is not None and self.core.nav_title
            else self.metadata.get("nav_title")
        )
        return resolve_nav_title(str(nav) if nav is not None else None, self.title)

    @property
    def weight(self) -> float:
        """Get page weight for sorting (always returns sortable value).

        Cost: O(1) cached — core field or CascadeView lookup + sortable_weight.
        """
        w = (
            self.core.weight
            if self.core is not None and self.core.weight is not None
            else self.metadata.get("weight")
        )
        return sortable_weight(w)

    @property
    def date(self) -> datetime | None:
        """Get page date from metadata.

        Cost: O(1) cached — CascadeView lookup + parse_date.
        """
        from bengal.utils.primitives.dates import parse_date

        date_value = self.metadata.get("date")
        return parse_date(date_value)

    @property
    def version(self) -> str | None:
        """Get version ID for this page (e.g., 'v3', 'v2').

        Cost: O(1) cached — core field or CascadeView lookup.
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
        """Get URL slug for the page.

        Cost: O(1) cached — CascadeView lookup or filename stem.
        """
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
        """URL for template href attributes. Includes baseurl.

        Cost: O(1) cached — cached after first computation via _href_cache.

        Hot-path alternative: page.identity.href (pre-computed, no property chain).
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
        try:
            site = getattr(self, "_site", None)
            baseurl = get_baseurl(site) if site else ""
        except Exception as e:
            emit_diagnostic(self, "debug", "page_baseurl_lookup_failed", error=str(e))
            baseurl = ""

        result = apply_baseurl(rel, baseurl)

        # Only cache if _path was properly computed (has its own cache)
        if "_path_cache" in self.__dict__:
            self.__dict__["_href_cache"] = result

        return result

    @property
    def _path(self) -> str:
        """Internal site-relative path. NO baseurl.

        Cost: O(1) cached — cached via _path_cache after first computation.
        First access: O(n) pathlib.relative_to if output_path is set.

        NEVER use in templates — use .href instead.
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
        """Fully-qualified URL for meta tags and sitemaps when available.

        Cost: O(1) cached — delegates to cached href / _path.
        """
        origin = get_site_origin(self._site) if self._site else ""
        if not origin:
            return self.href
        return f"{origin}{self._path}"

    def _fallback_url(self) -> str:
        """
        Generate fallback URL when output_path or site not available.

        Used during page construction before output_path is determined.

        Returns:
            URL based on slug
        """
        return f"/{self.slug}/"

    @property
    def toc_items(self) -> list[TOCItem]:
        """Get structured TOC data (lazy evaluation).

        Cost: O(1) cached after first extraction. First access: O(n) HTMLParser
        over page.toc HTML. Does NOT cache empty results to allow re-evaluation.
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
    def is_generated(self) -> bool:
        """Check if this is a generated page (tag indexes, archives, pagination).

        Cost: O(1) — reads _raw_metadata dict directly, no cascade resolution.

        Hot-path alternative: page.identity.is_generated (frozen, no property chain).
        """
        raw = getattr(self, "_raw_metadata", None)
        if raw is not None:
            return bool(raw.get("_generated"))
        return bool(self.metadata.get("_generated"))

    @property
    def is_home(self) -> bool:
        """Check if this page is the home page.

        Cost: O(1) cached — _path lookup + slug comparison.

        Hot-path alternative: page.identity.kind == "home".
        """
        return self._path == "/" or self.slug in ("index", "_index", "home")

    @property
    def is_section(self) -> bool:
        """Check if this page is a section page.

        Cost: O(1) — isinstance check.
        """
        # Import here to avoid circular import
        from bengal.core.section import Section

        return isinstance(self, Section)

    @property
    def is_page(self) -> bool:
        """Check if this is a regular page (not a section).

        Cost: O(1) — negated isinstance check.
        """
        return not self.is_section

    @property
    def kind(self) -> str:
        """Get the kind of page: 'home', 'section', or 'page'.

        Cost: O(1) cached — delegates to is_home/is_section.

        Hot-path alternative: page.identity.kind (frozen string).
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
        """Get page type from metadata (frontmatter or cascade, already merged).

        Cost: O(1) cached — CascadeView dict lookup.
        """
        return self.metadata.get("type")

    @property
    def description(self) -> str:
        """Get page description from core metadata (preferred) or frontmatter.

        Cost: O(1) cached — core field or CascadeView lookup.
        """
        if self.core is not None and self.core.description:
            return self.core.description
        return str(self.metadata.get("description", ""))

    @property
    def variant(self) -> str | None:
        """Get visual variant from metadata (frontmatter or cascade, already merged).

        Cost: O(1) cached — CascadeView lookup with layout/hero_style fallback.
        """
        return (
            self.metadata.get("variant")
            or self.metadata.get("layout")
            or self.metadata.get("hero_style")
        )

    @property
    def props(self) -> dict[str, Any]:
        """Get page props (alias for metadata). Component Model: Data.

        Cost: O(1) cached — returns metadata CascadeView.
        """
        return self.metadata

    @property
    def params(self) -> dict[str, Any]:
        """Get page params (alias for metadata).

        Cost: O(1) cached — returns metadata CascadeView.
        """
        return self.metadata

    @property
    def draft(self) -> bool:
        """Check if page is marked as draft.

        Cost: O(1) cached — CascadeView dict lookup.
        """
        return bool(self.metadata.get("draft", False))

    @property
    def keywords(self) -> list[str]:
        """Get page keywords from metadata.

        Cost: O(k) — CascadeView lookup + list normalization where k = len(keywords).
        """
        keywords = self.metadata.get("keywords", [])
        if isinstance(keywords, str):
            # Split comma-separated keywords
            return [k.strip() for k in keywords.split(",") if k.strip()]
        if isinstance(keywords, list):
            # Sanitize: filter None, convert to strings, filter empty (compute strip once)
            return [s for s in (str(k).strip() for k in keywords if k is not None) if s]
        return []

    # =========================================================================
    # Visibility System
    # =========================================================================

    @property
    def hidden(self) -> bool:
        """Check if page is hidden (unlisted).

        Cost: O(1) cached — CascadeView dict lookup.
        """
        return bool(self.metadata.get("hidden", False))

    def _get_content_signal_defaults(self) -> dict[str, Any]:
        """Get site-level content signal defaults from config."""
        site = getattr(self, "_site", None)
        if site is None:
            return {}
        config = getattr(site, "config", None)
        if config is None:
            return {}
        try:
            cs = config.get("content_signals", {})
            return cs if isinstance(cs, dict) else {}
        except Exception:
            return {}

    @cached_property
    def visibility(self) -> dict[str, Any]:
        """Get visibility settings with defaults.

        Cost: O(1) cached — computed once, then dict lookup for 8 sub-properties.
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
                "ai_train": False,
                "ai_input": False,
            }

        # Otherwise, get visibility object with permissive defaults
        vis = self.metadata.get("visibility", {})
        cs = self._get_content_signal_defaults()
        return {
            "menu": vis.get("menu", True),
            "listings": vis.get("listings", True),
            "sitemap": vis.get("sitemap", True),
            "robots": vis.get("robots", "index, follow"),
            "render": vis.get("render", "always"),
            "search": vis.get("search", cs.get("search", True)),
            "rss": vis.get("rss", True),
            "ai_train": vis.get("ai_train", cs.get("ai_train", False)),
            "ai_input": vis.get("ai_input", cs.get("ai_input", True)),
        }

    @property
    def in_listings(self) -> bool:
        """Check if page should appear in listings/queries.

        Cost: O(1) — delegates to visibility + draft.
        """
        return self.visibility["listings"] and not self.draft

    @property
    def in_sitemap(self) -> bool:
        """Check if page should appear in sitemap.

        Cost: O(1) — delegates to visibility + draft.
        """
        return self.visibility["sitemap"] and not self.draft

    @property
    def in_search(self) -> bool:
        """Check if page should appear in search index.

        Cost: O(1) — delegates to visibility + draft.
        """
        return self.visibility["search"] and not self.draft

    @property
    def in_rss(self) -> bool:
        """Check if page should appear in RSS feeds.

        Cost: O(1) — delegates to visibility + draft.
        """
        return self.visibility["rss"] and not self.draft

    @property
    def in_ai_train(self) -> bool:
        """Check if page content may be used for AI training.

        Cost: O(1) — delegates to visibility + draft.
        """
        return self.visibility["ai_train"] and not self.draft

    @property
    def in_ai_input(self) -> bool:
        """Check if page content may be used for AI input (RAG, grounding).

        Cost: O(1) — delegates to visibility + draft.
        """
        return self.visibility["ai_input"] and not self.draft

    @property
    def robots_meta(self) -> str:
        """Get robots meta content for this page.

        Cost: O(1) — delegates to visibility.
        """
        return str(self.visibility["robots"])

    @property
    def should_render(self) -> bool:
        """Check if page should be rendered based on visibility.render setting.

        Cost: O(1) — delegates to visibility.
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

    # =========================================================================
    # Variant / Edition Filtering (multi-variant builds)
    # =========================================================================

    @property
    def edition(self) -> list[str]:
        """Get edition/variant list from frontmatter for multi-variant builds.

        Cost: O(k) — CascadeView lookup + list normalization where k = len(editions).
        """
        val = self.metadata.get("edition")
        if val is None:
            return []
        if isinstance(val, str):
            return [val] if val else []
        if isinstance(val, list):
            return [str(v).strip() for v in val if v is not None and str(v).strip()]
        return []

    def in_variant(self, variant: str | None) -> bool:
        """
        Check if page should be included when building for the given variant.

        When params.edition is set, pages are excluded if their edition list
        does not include that value. Pages with no edition are included in all.

        Args:
            variant: Current build variant (e.g. "oss", "enterprise"). None = no filter.

        Returns:
            True if page should be included in this build

        Example:
            >>> page.in_variant(None)
            True
            >>> page.in_variant("enterprise")  # page has edition: [enterprise]
            True
            >>> page.in_variant("oss")  # page has edition: [enterprise]
            False
        """
        if variant is None or not str(variant).strip():
            return True
        editions = self.edition
        if not editions:
            return True
        return variant in editions

    # =========================================================================
    # Metadata Access Helpers
    # =========================================================================

    def get_user_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get user-defined frontmatter value.

        Does NOT return internal keys (prefixed with `_`).
        Use for accessing author-provided frontmatter.

        Args:
            key: Metadata key to retrieve
            default: Default value if key not found

        Returns:
            Metadata value or default

        Example:
            >>> page.get_user_metadata("author", "Unknown")
            "Jane Doe"
            >>> page.get_user_metadata("_generated")  # Returns default
            None
        """
        if key.startswith("_"):
            return default
        return self.metadata.get(key, default)

    def get_internal_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get internal metadata value.

        Only returns keys prefixed with `_`.
        Auto-prefixes key if not already prefixed.

        Args:
            key: Metadata key (with or without `_` prefix)
            default: Default value if key not found

        Returns:
            Internal metadata value or default

        Example:
            >>> page.get_internal_metadata("generated")  # Looks up "_generated"
            True
            >>> page.get_internal_metadata("_version")  # Works with prefix too
            "v3"
        """
        if not key.startswith("_"):
            key = f"_{key}"
        return self.metadata.get(key, default)

    @property
    def assigned_template(self) -> str | None:
        """Template explicitly assigned to this page via frontmatter.

        Cost: O(1) cached — CascadeView dict lookup.
        """
        return self.metadata.get("template")

    @property
    def content_type_name(self) -> str | None:
        """Content type assigned to this page.

        Cost: O(1) cached — CascadeView dict lookup.
        """
        return self.metadata.get("content_type")

    # =========================================================================
    # Canonical Internal Flag Accessors
    # =========================================================================
    # Internal build flags (_generated, _tag_slug, _autodoc_template, etc.)
    # MUST be accessed via these properties, never through metadata.get("_...").
    # This avoids triggering the full cascade resolution chain for simple
    # boolean/string checks.

    @property
    def tag_slug(self) -> str | None:
        """Tag slug for generated tag pages.

        Cost: O(1) — _raw_metadata dict lookup, no cascade.
        """
        raw = getattr(self, "_raw_metadata", None)
        if raw is not None:
            return raw.get("_tag_slug")
        return self.metadata.get("_tag_slug")

    @property
    def autodoc_template(self) -> str | None:
        """Autodoc template override for auto-generated API doc pages.

        Cost: O(1) — _raw_metadata dict lookup, no cascade.
        """
        raw = getattr(self, "_raw_metadata", None)
        if raw is not None:
            return raw.get("_autodoc_template")
        return self.metadata.get("_autodoc_template")
