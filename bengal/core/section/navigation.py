"""
Section Navigation Mixin - URL generation and version-aware navigation.

Provides URL generation (href, _path, absolute_href) and version-aware
filtering methods for sections. Handles versioned content path transformation.

Required Host Attributes:
- name: str
- path: Path | None
- parent: Section | None
- subsections: list[Section]
- metadata: dict[str, Any]
- index_page: Page | None
- _virtual: bool
- _relative_url_override: str | None
- _site: Site | None
- _diagnostics: DiagnosticsSink | None
- sorted_pages: list[Page] (from SectionQueryMixin)
- sorted_subsections: list[Section] (from SectionHierarchyMixin)

Related Modules:
bengal.core.section: Section dataclass using this mixin
bengal.core.section.hierarchy: Tree structure methods
bengal.utils.url_normalization: URL normalization utilities

Example:
    >>> section = site.get_section("docs")
    >>> section.href
    '/docs/'
    >>> section.pages_for_version("v2")
[<Page 'getting-started'>, <Page 'configuration'>]

"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.diagnostics import DiagnosticsSink
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


class SectionNavigationMixin:
    """
    URL generation and version-aware navigation.
    
    This mixin handles:
    - URL properties (href, _path, absolute_href)
    - Subsection index URL tracking
    - Navigation children detection
    - Version-aware page/subsection filtering
    - Versioned path transformation
        
    """

    # =========================================================================
    # HOST CLASS ATTRIBUTES
    # =========================================================================
    # Type hints for attributes provided by the host dataclass.
    # These are NOT defined here - they're declared for type checking only.

    name: str
    path: Path | None
    parent: Section | None
    subsections: list[Section]
    metadata: dict[str, Any]
    index_page: Page | None
    _virtual: bool
    _relative_url_override: str | None
    _site: Site | None
    _diagnostics: DiagnosticsSink | None

    # From other mixins
    sorted_pages: list[Page]
    sorted_subsections: list[Section]

    # =========================================================================
    # URL PROPERTIES
    # =========================================================================

    @cached_property
    def href(self) -> str:
        """
        URL for template href attributes. Includes baseurl.

        Use this in templates for all links:
            <a href="{{ section.href }}">

        Returns:
            URL path with baseurl prepended (if configured)
        """
        # Get site-relative path first
        rel = self._path or "/"

        baseurl = ""
        try:
            site = getattr(self, "_site", None)
            if site is not None:
                baseurl = site.baseurl or ""
        except Exception:
            baseurl = ""

        if not baseurl:
            return rel

        baseurl = baseurl.rstrip("/")
        rel = "/" + rel.lstrip("/")
        return f"{baseurl}{rel}"

    @cached_property
    def _path(self) -> str:
        """
        Internal site-relative path. NO baseurl.

        Use for internal operations only:
        - Cache keys
        - Active trail detection
        - URL comparisons
        - Link validation

        NEVER use in templates - use .href instead.

        For versioned content in _versions/<id>/, the path is transformed:
        - _versions/v1/docs/about → /docs/v1/about/ (non-latest)
        - _versions/v3/docs/about → /docs/about/ (latest)
        """
        from bengal.utils.paths.url_normalization import join_url_paths, normalize_url

        if self._virtual:
            if not self._relative_url_override:
                if self._diagnostics:
                    self._diagnostics.emit(
                        self,  # type: ignore[arg-type]
                        "error",
                        "virtual_section_missing_url",
                        section_name=self.name,
                        tip="Virtual sections must have a _relative_url_override set.",
                    )
                return "/"
            return normalize_url(self._relative_url_override)

        if self.path is None:
            return "/"

        parent_rel = self.parent._path if self.parent else "/"
        url = join_url_paths(parent_rel, self.name)

        # Apply version path transformation for _versions/ content
        url = self._apply_version_path_transform(url)

        return url

    @property
    def absolute_href(self) -> str:
        """
        Fully-qualified URL for meta tags and sitemaps when available.
        """
        if not self._site or not self._site.config.get("url"):
            return self.href
        site_url = self._site.config["url"].rstrip("/")
        return f"{site_url}{self._path}"

    # =========================================================================
    # NAVIGATION HELPERS
    # =========================================================================

    @cached_property
    def subsection_index_urls(self) -> set[str]:
        """
        Get set of URLs for all subsection index pages (CACHED).

        This pre-computed set enables O(1) membership checks for determining
        if a page is a subsection index. Used in navigation templates to avoid
        showing subsection indices twice (once as page, once as subsection link).

        Performance:
            - First access: O(m) where m = number of subsections
            - Subsequent lookups: O(1) set membership check
            - Memory cost: O(m) URLs

        Returns:
            Set of URL strings for subsection index pages

        Example:
            {% if page._path not in section.subsection_index_urls %}
              <a href="{{ url_for(page) }}">{{ page.title }}</a>
            {% endif %}
        """
        return {
            getattr(subsection.index_page, "_path", None)
            for subsection in self.subsections
            if subsection.index_page
        }

    @cached_property
    def has_nav_children(self) -> bool:
        """
        Check if this section has navigable children (CACHED).

        A section has navigable children if it contains either:
        - Regular pages (excluding the index page itself)
        - Subsections

        This property is used by navigation templates to determine whether
        to render a section as an expandable group (with toggle button) or
        as a simple link. Sections without children should not show an
        expand/collapse toggle since there's nothing to expand.

        Performance:
            - First access: O(1) - uses cached sorted_pages/sorted_subsections
            - Subsequent accesses: O(1) cached lookup

        Returns:
            True if section has pages or subsections to display in nav

        Example:
            {% if section.has_nav_children %}
              {# Render as expandable group with toggle #}
            {% else %}
              {# Render as simple link #}
            {% endif %}
        """
        return bool(self.sorted_pages or self.sorted_subsections)

    # =========================================================================
    # VERSION-AWARE NAVIGATION
    # =========================================================================

    def pages_for_version(self, version_id: str | None) -> list[Page]:
        """
        Get pages matching the specified version.

        Filters sorted_pages to return only pages whose version attribute
        matches the given version_id. If version_id is None, returns all
        sorted pages (useful when versioning is disabled).

        Args:
            version_id: Version to filter by (e.g., "v1", "latest"), or None
                        to return all pages

        Returns:
            Sorted list of pages matching the version

        Example:
            {% set version_id = current_version.id if site.versioning_enabled else none %}
            {% for page in section.pages_for_version(version_id) %}
              <a href="{{ page.href }}">{{ page.title }}</a>
            {% endfor %}
        """
        if version_id is None:
            return self.sorted_pages
        return [p for p in self.sorted_pages if getattr(p, "version", None) == version_id]

    def subsections_for_version(self, version_id: str | None) -> list[Section]:
        """
        Get subsections that have content for the specified version.

        A subsection is included if has_content_for_version returns True,
        meaning either its index page matches the version or it contains
        pages matching the version.

        Args:
            version_id: Version to filter by, or None to return all subsections

        Returns:
            Sorted list of subsections with content for the version

        Example:
            {% set version_id = current_version.id if site.versioning_enabled else none %}
            {% for subsection in section.subsections_for_version(version_id) %}
              <h3>{{ subsection.title }}</h3>
            {% endfor %}
        """
        if version_id is None:
            return self.sorted_subsections
        return [s for s in self.sorted_subsections if s.has_content_for_version(version_id)]

    def has_content_for_version(self, version_id: str | None) -> bool:
        """
        Check if this section has any content for the specified version.

        A section has content for a version if:
        - Its index_page exists and matches the version, OR
        - Any of its sorted_pages match the version, OR
        - Any of its subsections recursively have content for the version

        Args:
            version_id: Version to check, or None (always returns True)

        Returns:
            True if section has matching content at any level

        Example:
            {% if section.has_content_for_version(current_version.id) %}
              {# Show this section in navigation #}
            {% endif %}
        """
        if version_id is None:
            return True

        # Check index page first
        if self.index_page and getattr(self.index_page, "version", None) == version_id:
            return True

        # Check any regular page in this section
        if any(getattr(p, "version", None) == version_id for p in self.sorted_pages):
            return True

        # Recursively check subsections (needed for versioned content in _versions/<id>/...)
        return any(s.has_content_for_version(version_id) for s in self.subsections)

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _apply_version_path_transform(self, url: str) -> str:
        """
        Transform versioned section URL to proper output structure.

        For sections inside _versions/<id>/, transforms the URL:
        - /_versions/v1/docs/about/ → /docs/v1/about/ (non-latest)
        - /_versions/v3/docs/about/ → /docs/about/ (latest)

        This matches the transformation applied to pages in URLStrategy.

        Args:
            url: Raw section URL (may contain _versions prefix)

        Returns:
            Transformed URL with version placed after section
        """
        # Fast path: not versioned content
        if "/_versions/" not in url:
            return url

        # Get site and version config
        site = getattr(self, "_site", None)
        if not site or not getattr(site, "versioning_enabled", False):
            return url

        version_config = getattr(site, "version_config", None)
        if not version_config:
            return url

        # Parse the URL: /_versions/<id>/<section>/...
        # Split on /_versions/ to get parts after
        parts = url.split("/_versions/", 1)
        if len(parts) < 2:
            return url

        remainder = parts[1]  # e.g., "v1/docs/about/"
        remainder_parts = remainder.strip("/").split("/")

        if len(remainder_parts) < 2:
            # Just /_versions/<id>/ with no section - shouldn't happen for real sections
            return url

        version_id = remainder_parts[0]  # e.g., "v1"
        section_name = remainder_parts[1]  # e.g., "docs"
        rest = remainder_parts[2:]  # e.g., ["about"]

        # Check if this is the latest version
        version_obj = version_config.get_version(version_id)
        if not version_obj:
            return url

        if version_obj.latest:
            # Latest version: strip version prefix entirely
            # /_versions/v3/docs/about/ → /docs/about/
            if rest:
                return f"/{section_name}/" + "/".join(rest) + "/"
            else:
                return f"/{section_name}/"
        else:
            # Non-latest version: insert version after section
            # /_versions/v1/docs/about/ → /docs/v1/about/
            if rest:
                return f"/{section_name}/{version_id}/" + "/".join(rest) + "/"
            else:
                return f"/{section_name}/{version_id}/"
