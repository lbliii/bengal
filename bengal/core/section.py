"""
Section representation for organizing pages into hierarchical groups.

Sections represent directories in the content tree and provide navigation,
sorting, and hierarchical query interfaces. Sections can be nested and
maintain parent-child relationships. Each section can have an index page
and contains both regular pages and subsections.

Public API:
    Section: Content directory representation with pages and subsections
    WeightedPage: Helper for weight-based page sorting

Key Concepts:
    Hierarchy: Sections form a tree structure with parent-child relationships.
        Access via section.parent, section.subsections, section.root.

    Index Pages: Special pages (_index.md or index.md) that represent the section.
        Provides section-level metadata (title, description, cascade values).

    Weight-based Sorting: Pages and subsections sorted by weight metadata.
        Lower weights appear first; unweighted items sort to end.

    Virtual Sections: Sections without a disk directory (e.g., autodoc API docs).
        Created via Section.create_virtual() for dynamically-generated content.

    Hashability: Sections hashable by path for set operations and dict keys.
        Two sections with same path are considered equal.

Related Packages:
    bengal.core.page: Page objects contained within sections
    bengal.core.site: Site container that manages all sections
    bengal.orchestration.content: Content discovery that builds section hierarchy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from operator import attrgetter
from pathlib import Path
from typing import Any

from bengal.core.diagnostics import DiagnosticEvent, DiagnosticsSink
from bengal.core.page import Page


@dataclass
class WeightedPage:
    page: Page
    weight: float = float("inf")
    title_lower: str = ""

    def __lt__(self, other: WeightedPage) -> bool:
        if self.weight != other.weight:
            return self.weight < other.weight
        return self.title_lower < other.title_lower


@dataclass
class Section:
    """
    Represents a folder or logical grouping of pages.

    HASHABILITY:
    ============
    Sections are hashable based on their path (or name for virtual sections),
    allowing them to be stored in sets and used as dictionary keys. This enables:
    - Fast membership tests and lookups
    - Type-safe Set[Section] collections
    - Set operations for section analysis

    Two sections with the same path are considered equal. The hash is stable
    throughout the section lifecycle because path is immutable.

    VIRTUAL SECTIONS:
    =================
    Virtual sections represent API documentation or other dynamically-generated
    content that doesn't have a corresponding directory on disk. Virtual sections:
    - Have _virtual=True and path=None
    - Are discovered via VirtualAutodocOrchestrator during build
    - Work with menu system via name-based lookups
    - Don't write intermediate markdown files

    Attributes:
        name: Section name
        path: Path to the section directory (None for virtual sections)
        pages: List of pages in this section
        subsections: Child sections
        metadata: Section-level metadata
        index_page: Optional index page for the section
        parent: Parent section (if nested)
        _virtual: True if this is a virtual section (no disk directory)
    """

    name: str = "root"
    path: Path | None = field(default_factory=lambda: Path("."))
    pages: list[Page] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    index_page: Page | None = None
    parent: Section | None = None

    # Virtual section support (for API docs, generated content)
    _virtual: bool = False
    _relative_url_override: str | None = field(default=None, repr=False)

    # Reference to site (set during site building)
    _site: Any | None = field(default=None, repr=False)
    # Optional diagnostics sink (for unit tests or if no site is available yet)
    _diagnostics: DiagnosticsSink | None = field(default=None, repr=False)

    def _emit_diagnostic(self, event: DiagnosticEvent) -> None:
        """
        Emit a diagnostic event if a sink is available.

        Core models must not log; orchestrators decide how to surface diagnostics.
        """
        sink: Any | None = self._diagnostics
        if sink is None:
            site = getattr(self, "_site", None)
            sink = getattr(site, "diagnostics", None) if site is not None else None

        if sink is None:
            return

        try:
            sink.emit(event)
        except Exception:
            # Diagnostics must never break core behavior.
            return

    @property
    def is_virtual(self) -> bool:
        """
        Check if this is a virtual section (no disk directory).

        Virtual sections are used for:
        - API documentation generated from Python source code
        - Dynamically-generated content from external sources
        - Content that doesn't have a corresponding content/ directory

        Returns:
            True if this section is virtual (not backed by a disk directory)
        """
        return self._virtual or self.path is None

    @classmethod
    def create_virtual(
        cls,
        name: str,
        relative_url: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Section:
        """
        Create a virtual section for dynamically-generated content.

        Virtual sections are not backed by a disk directory but integrate
        with the site's section hierarchy, navigation, and menu system.

        Args:
            name: Section name (used for lookups, e.g., "api")
            relative_url: URL for this section (e.g., "/api/")
            title: Display title (defaults to titlecase of name)
            metadata: Optional section metadata

        Returns:
            A new virtual Section instance

        Example:
            api_section = Section.create_virtual(
                name="api",
                relative_url="/api/",
                title="API Reference",
            )
        """
        section_metadata = metadata or {}
        if title:
            section_metadata["title"] = title

        # Normalize URL at construction time
        from bengal.utils.url_normalization import normalize_url

        normalized_url = normalize_url(relative_url, ensure_trailing_slash=True)

        return cls(
            name=name,
            path=None,
            metadata=section_metadata,
            _virtual=True,
            _relative_url_override=normalized_url,
        )

    @property
    def slug(self) -> str:
        """
        URL-friendly identifier for this section.

        For virtual sections, uses the name directly.
        For physical sections, uses the directory name.

        Returns:
            Section slug (e.g., "api", "core", "bengal-core")
        """
        if self._virtual:
            return self.name
        return self.path.name if self.path else self.name

    @property
    def title(self) -> str:
        """Get section title from metadata or generate from name."""
        return str(self.metadata.get("title", self.name.replace("-", " ").title()))

    @property
    def nav_title(self) -> str:
        """
        Get short navigation title (falls back to title).

        Use this in menus and sidebars for compact display.

        Example in _index.md:
            ---
            title: Content Authoring Guide
            nav_title: Authoring
            ---
        """
        if "nav_title" in self.metadata:
            return str(self.metadata["nav_title"])
        # Also check index page for nav_title
        if self.index_page is not None:
            index_nav = getattr(self.index_page, "nav_title", None)
            if index_nav and index_nav != self.index_page.title:
                return index_nav
        return self.title

    @cached_property
    def icon(self) -> str | None:
        """
        Get section icon from index page metadata (cached).

        Icons can be specified in a section's _index.md frontmatter:

            ---
            title: API Reference
            icon: book
            ---

        The icon name should match a Phosphor icon in the icon library
        (e.g., 'book', 'folder', 'terminal', 'code').

        Returns:
            Icon name string, or None if no icon is specified

        Example:
            {% if section.icon %}
              {{ icon(section.icon, size=16) }}
            {% endif %}

        Performance:
            Uses @cached_property to avoid repeated dict lookups on each access.
        """
        # First check index page metadata (preferred source)
        if (
            self.index_page
            and hasattr(self.index_page, "metadata")
            and (icon_value := self.index_page.metadata.get("icon"))
        ):
            return str(icon_value) if icon_value else None
        # Fall back to section metadata (in case copied during add_page)
        result = self.metadata.get("icon")
        return str(result) if result else None

    @property
    def hierarchy(self) -> list[str]:
        """
        Get the full hierarchy path of this section.

        Returns:
            List of section names from root to this section
        """
        if self.parent:
            return [*self.parent.hierarchy, self.name]
        return [self.name]

    @property
    def depth(self) -> int:
        """Get the depth of this section in the hierarchy."""
        return len(self.hierarchy)

    @property
    def root(self) -> Section:
        """
        Get the root section of this section's hierarchy.

        Traverses up the parent chain until reaching either:
        - A section with no parent (topmost ancestor)
        - A section with nav_root: true metadata (navigation boundary)

        The nav_root metadata allows sections to act as their own navigation
        root, useful for autodoc collections (e.g., /api/python/) that should
        not show their parent aggregator (/api/) in the sidebar.

        Returns:
            The navigation root section

        Example:
            {% set root_section = page._section.root %}
        """
        current = self
        while current.parent:
            # Stop if current section declares itself as a nav root
            if current.metadata.get("nav_root"):
                return current
            current = current.parent
        return current

    # Section navigation properties

    @property
    def regular_pages(self) -> list[Page]:
        """
        Get only regular pages (non-sections) in this section.

        Returns:
            List of regular Page objects (excludes subsections)

        Example:
            {% for page in section.regular_pages %}
              <article>{{ page.title }}</article>
            {% endfor %}
        """
        return [p for p in self.pages if not isinstance(p, Section)]

    @property
    def sections(self) -> list[Section]:
        """
        Get immediate child sections.

        Returns:
            List of child Section objects

        Example:
            {% for subsection in section.sections %}
              <h3>{{ subsection.title }}</h3>
            {% endfor %}
        """
        return self.subsections

    @cached_property
    def sorted_pages(self) -> list[Page]:
        """
        Get pages sorted by weight (ascending), then by title (CACHED).

        This property is cached after first access for O(1) subsequent lookups.
        The sort is computed once and reused across all template renders.

        Pages without a weight field are treated as having weight=float('inf')
        and appear at the end of the sorted list, after all weighted pages.
        Lower weights appear first in the list. Pages with equal weight are sorted
        alphabetically by title.

        Performance:
            - First access: O(n log n) where n = number of pages
            - Subsequent accesses: O(1) cached lookup
            - Memory cost: O(n) to store sorted list

        Returns:
            List of pages sorted by weight, then title

        Example:
            {% for page in section.sorted_pages %}
              <article>{{ page.title }}</article>
            {% endfor %}
        """

        def is_index_page(p: Page) -> bool:
            return p.source_path.stem in ("_index", "index")

        weighted = [
            WeightedPage(p, p.metadata.get("weight", float("inf")), p.title.lower())
            for p in self.pages
            if not is_index_page(p)
        ]
        return [wp.page for wp in sorted(weighted, key=attrgetter("weight", "title_lower"))]

    @cached_property
    def sorted_subsections(self) -> list[Section]:
        """
        Get subsections sorted by weight (ascending), then by title (CACHED).

        This property is cached after first access for O(1) subsequent lookups.
        The sort is computed once and reused across all template renders.

        Subsections without a weight field in their index page metadata
        are treated as having weight=999999 (appear at end). Lower weights appear first.

        Performance:
            - First access: O(m log m) where m = number of subsections
            - Subsequent accesses: O(1) cached lookup
            - Memory cost: O(m) to store sorted list

        Returns:
            List of subsections sorted by weight, then title

        Example:
            {% for subsection in section.sorted_subsections %}
              <h3>{{ subsection.title }}</h3>
            {% endfor %}
        """
        return sorted(
            self.subsections, key=lambda s: (s.metadata.get("weight", 999999), s.title.lower())
        )

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

    # Version-aware navigation methods

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

    @property
    def regular_pages_recursive(self) -> list[Page]:
        """
        Get all regular pages recursively (including from subsections).

        Returns:
            List of all descendant regular pages

        Example:
            <p>Total pages: {{ section.regular_pages_recursive | length }}</p>
        """
        result = list(self.regular_pages)
        for subsection in self.subsections:
            result.extend(subsection.regular_pages_recursive)
        return result

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
            if site is not None and hasattr(site, "config") and site.config is not None:
                baseurl = site.config.get("baseurl", "")
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
        from bengal.utils.url_normalization import join_url_paths, normalize_url

        if self._virtual:
            if not self._relative_url_override:
                self._diagnostics.emit(
                    self,
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

    @property
    def absolute_href(self) -> str:
        """
        Fully-qualified URL for meta tags and sitemaps when available.
        """
        if not self._site or not self._site.config.get("url"):
            return self.href
        site_url = self._site.config["url"].rstrip("/")
        return f"{site_url}{self._path}"

    def add_page(self, page: Page) -> None:
        """
        Add a page to this section.

        Args:
            page: Page to add
        """
        is_index = page.source_path.stem in ("index", "_index")

        self.pages.append(page)

        # Set as index page if it's named index.md or _index.md
        if is_index:
            # Detect collision: both index.md and _index.md exist
            if self.index_page is not None:
                existing_name = self.index_page.source_path.stem
                new_name = page.source_path.stem
                self._emit_diagnostic(
                    DiagnosticEvent(
                        level="warning",
                        code="index_file_collision",
                        data={
                            "section": self.name,
                            "section_path": str(self.path),
                            "existing_file": f"{existing_name}.md",
                            "new_file": f"{new_name}.md",
                            "action": "preferring_underscore_version",
                            "suggestion": (
                                "Remove one of the index files - only _index.md or index.md should exist"
                            ),
                        },
                    )
                )

                # Prefer _index.md over index.md (section index convention)
                if new_name == "_index":
                    self.index_page = page
                # else: keep existing _index.md
            else:
                self.index_page = page

            # Copy metadata from index page to section
            # This allows sections to have weight, description, and other metadata
            self.metadata.update(page.metadata)

    def add_subsection(self, section: Section) -> None:
        """
        Add a subsection to this section.

        Args:
            section: Child section to add
        """
        section.parent = self
        self.subsections.append(section)

    def sort_children_by_weight(self) -> None:
        """
        Sort pages and subsections in this section by weight, then by title.

        This modifies the pages and subsections lists in place.
        Pages/sections without a weight field are treated as having weight=float('inf'),
        so they appear at the end (after all weighted items).
        Lower weights appear first in the sorted lists.

        This is typically called after content discovery is complete.
        """
        # Sort pages by weight (ascending), then title (alphabetically)
        # Unweighted pages use float('inf') to sort last
        self.pages.sort(key=lambda p: (p.metadata.get("weight", float("inf")), p.title.lower()))

        # Sort subsections by weight (ascending), then title (alphabetically)
        # Unweighted subsections use float('inf') to sort last
        self.subsections.sort(
            key=lambda s: (s.metadata.get("weight", float("inf")), s.title.lower())
        )

    def needs_auto_index(self) -> bool:
        """
        Check if this section needs an auto-generated index page.

        Returns:
            True if section needs auto-generated index (no explicit _index.md)
        """
        return self.name != "root" and self.index_page is None

    def has_index(self) -> bool:
        """
        Check if section has a valid index page.

        Returns:
            True if section has an index page (explicit or auto-generated)
        """
        return self.index_page is not None

    def get_all_pages(self, recursive: bool = True) -> list[Page]:
        """
        Get all pages in this section.

        Args:
            recursive: If True, include pages from subsections

        Returns:
            List of all pages
        """
        all_pages = list(self.pages)

        if recursive:
            for subsection in self.subsections:
                all_pages.extend(subsection.get_all_pages(recursive=True))

        return all_pages

    def aggregate_content(self) -> dict[str, Any]:
        """
        Aggregate content from all pages in this section.

        Returns:
            Dictionary with aggregated content information
        """
        pages = self.get_all_pages(recursive=False)

        # Collect all tags
        all_tags = set()
        for page in pages:
            all_tags.update(page.tags)

        result = {
            "page_count": len(pages),
            "total_page_count": len(self.get_all_pages(recursive=True)),
            "subsection_count": len(self.subsections),
            "tags": sorted(all_tags),
            "title": self.title,
            "hierarchy": self.hierarchy,
        }

        return result

    def apply_section_template(self, template_engine: Any) -> str:
        """
        Apply a section template to generate a section index page.

        Args:
            template_engine: Template engine instance

        Returns:
            Rendered HTML for the section index
        """
        {
            "section": self,
            "pages": self.pages,
            "subsections": self.subsections,
            "metadata": self.metadata,
            "aggregated": self.aggregate_content(),
        }

        # Use the index page if available, otherwise generate a listing
        if self.index_page:
            return self.index_page.rendered_html

        # Template rendering will be handled by the template engine
        return ""

    def walk(self) -> list[Section]:
        """
        Iteratively walk through all sections in the hierarchy.

        Returns:
            List of all sections (self and descendants)
        """
        sections = [self]
        stack = list(self.subsections)

        while stack:
            section = stack.pop()
            sections.append(section)
            stack.extend(section.subsections)

        return sections

    # =========================================================================
    # ERGONOMIC HELPER METHODS (for theme developers)
    # =========================================================================

    @cached_property
    def content_pages(self) -> list[Page]:
        """
        Get content pages (regular pages excluding index).

        This is useful for listing a section's pages without
        including the section's own index page in the list.

        Note:
            `sorted_pages` already excludes `_index.md`/`index.md` files
            (see sorted_pages implementation). This property is effectively
            an alias but provides semantic clarity for theme developers.

        Returns:
            Sorted list of pages, excluding the section's index page

        Example:
            {% for page in section.content_pages %}
              <a href="{{ page.href }}">{{ page.title }}</a>
            {% endfor %}
        """
        # sorted_pages already excludes index files, so this is a semantic alias
        return self.sorted_pages

    def recent_pages(self, limit: int = 10) -> list[Page]:
        """
        Get most recent pages by date.

        Returns pages that have a date, sorted newest first.
        Pages without dates are excluded.

        Args:
            limit: Maximum number of pages to return (default: 10)

        Returns:
            List of pages sorted by date descending

        Example:
            {% for post in section.recent_pages(5) %}
              <article>{{ post.title }} - {{ post.date }}</article>
            {% endfor %}
        """
        dated_pages = [p for p in self.sorted_pages if getattr(p, "date", None)]
        dated_pages.sort(key=lambda p: p.date, reverse=True)
        return dated_pages[:limit]

    def pages_with_tag(self, tag: str) -> list[Page]:
        """
        Get pages containing a specific tag.

        Filters sorted_pages to return only pages that have the given tag.
        Matching is case-insensitive.

        Args:
            tag: Tag to filter by (case-insensitive)

        Returns:
            Sorted list of pages with the tag

        Example:
            {% set python_posts = section.pages_with_tag('python') %}
            {% for post in python_posts %}
              <article>{{ post.title }}</article>
            {% endfor %}
        """
        tag_lower = tag.lower()
        return [
            p for p in self.sorted_pages if tag_lower in [t.lower() for t in getattr(p, "tags", [])]
        ]

    def __hash__(self) -> int:
        """
        Hash based on section path (or name for virtual sections) for stable identity.

        The hash is computed from the section's path, which is immutable
        throughout the section lifecycle. This allows sections to be stored
        in sets and used as dictionary keys.

        For virtual sections (path=None), uses the name and _relative_url_override
        for hashing to ensure stable identity.

        Returns:
            Integer hash of the section path or name
        """
        if self.path is None:
            # Virtual sections: hash by name and URL
            return hash((self.name, self._relative_url_override))
        return hash(self.path)

    def __eq__(self, other: Any) -> bool:
        """
        Sections are equal if they have the same path (or name+URL for virtual).

        Equality is based on path only, not on pages or other mutable fields.
        This means two Section objects representing the same directory are
        considered equal, even if their contents differ.

        For virtual sections (path=None), equality is based on name and URL.

        Args:
            other: Object to compare with

        Returns:
            True if other is a Section with the same path
        """
        if not isinstance(other, Section):
            return NotImplemented
        if self.path is None and other.path is None:
            # Both virtual: compare by name and URL
            return (self.name, self._relative_url_override) == (
                other.name,
                other._relative_url_override,
            )
        return self.path == other.path

    def __repr__(self) -> str:
        return f"Section(name='{self.name}', pages={len(self.pages)}, subsections={len(self.subsections)})"


# =========================================================================
# MODULE-LEVEL HELPER FUNCTIONS
# =========================================================================
# These were relocated from utils/sections.py during architecture refactoring.


def resolve_page_section_path(page: Any) -> str | None:
    """
    Resolve a page's section path as a string, handling multiple representations.

    The page may expose its section association in different ways depending on
    build phase or caching:
    - `page.section` may be a `Section` object with a `.path` attribute
    - `page.section` may already be a string path
    - It may be missing or falsy for root-level pages

    Args:
        page: Page-like object which may have a `section` attribute

    Returns:
        String path to the section (e.g., "docs/tutorials") or None if not set.

    Note:
        This function is intentionally silent on errors, falling back gracefully.
        Core modules do not log; orchestrators handle observability.
    """
    if page is None:
        return None

    # Some page proxies may raise on getattr; guard with try/except
    try:
        section_value = getattr(page, "section", None)
    except Exception:
        section_value = None

    if not section_value:
        return None

    # If it's a Section-like object with a `.path`, return its string form
    if hasattr(section_value, "path"):
        try:
            return str(section_value.path)
        except Exception:
            # Fallback to str(section_value) if `.path` isn't convertible
            return str(section_value)

    # Already a string or stringable value
    return str(section_value)
