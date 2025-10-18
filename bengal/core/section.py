"""
Section Object - Represents a folder or logical grouping of pages.
"""

from dataclasses import dataclass, field
from functools import cached_property
from operator import attrgetter
from pathlib import Path
from typing import Any

from bengal.core.page import Page
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WeightedPage:
    page: Page
    weight: float = float("inf")
    title_lower: str = ""

    def __lt__(self, other):
        if self.weight != other.weight:
            return self.weight < other.weight
        return self.title_lower < other.title_lower


@dataclass
class Section:
    """
    Represents a folder or logical grouping of pages.

    HASHABILITY:
    ============
    Sections are hashable based on their path, allowing them to be stored
    in sets and used as dictionary keys. This enables:
    - Fast membership tests and lookups
    - Type-safe Set[Section] collections
    - Set operations for section analysis

    Two sections with the same path are considered equal. The hash is stable
    throughout the section lifecycle because path is immutable.

    Attributes:
        name: Section name
        path: Path to the section directory
        pages: List of pages in this section
        subsections: Child sections
        metadata: Section-level metadata
        index_page: Optional index page for the section
        parent: Parent section (if nested)
    """

    name: str = "root"
    path: Path = Path(".")
    pages: list[Page] = field(default_factory=list)
    subsections: list["Section"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    index_page: Page | None = None
    parent: "Section | None" = None

    # Reference to site (set during site building)
    _site: Any | None = field(default=None, repr=False)

    @property
    def title(self) -> str:
        """Get section title from metadata or generate from name."""
        return self.metadata.get("title", self.name.replace("-", " ").title())

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
    def root(self) -> "Section":
        """
        Get the root section of this section's hierarchy.

        Returns:
            The topmost ancestor section

        Example:
            {% set root_section = page._section.root %}
        """
        current = self
        while current.parent:
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
    def sections(self) -> list["Section"]:
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
    def sorted_subsections(self) -> list["Section"]:
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
            {% if page.url not in section.subsection_index_urls %}
              <a href="{{ url_for(page) }}">{{ page.title }}</a>
            {% endif %}
        """
        return {
            subsection.index_page.url for subsection in self.subsections if subsection.index_page
        }

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
    def url(self) -> str:
        """
        Get the URL for this section (cached after first access).

        Section URLs are stable after index pages have output_path set.
        Caching eliminates redundant recalculation - previously this was
        computed ~5× per page during health checks.

        Returns:
            URL path for the section
        """
        # If we have an index page with a proper output_path, use its URL
        if (
            self.index_page
            and hasattr(self.index_page, "output_path")
            and self.index_page.output_path
        ):
            url = self.index_page.url
            logger.debug("section_url_from_index", section=self.name, url=url)
            return url

        # Otherwise, construct from section hierarchy
        # This handles the case before pages have output_paths set
        # Nested section includes parent URL, top-level section starts with /
        url = f"{self.parent.url}{self.name}/" if self.parent else f"/{self.name}/"

        logger.debug(
            "section_url_constructed", section=self.name, url=url, has_parent=bool(self.parent)
        )

        return url

    def add_page(self, page: Page) -> None:
        """
        Add a page to this section.

        Args:
            page: Page to add
        """
        is_index = page.source_path.stem in ("index", "_index")

        logger.debug(
            "adding_page_to_section",
            section=self.name,
            page=str(page.source_path),
            is_index=is_index,
            total_pages=len(self.pages) + 1,
        )

        self.pages.append(page)

        # Set as index page if it's named index.md or _index.md
        if is_index:
            # Detect collision: both index.md and _index.md exist
            if self.index_page is not None:
                existing_name = self.index_page.source_path.stem
                new_name = page.source_path.stem

                logger.warning(
                    "index_file_collision",
                    section=self.name,
                    section_path=str(self.path),
                    existing_file=f"{existing_name}.md",
                    new_file=f"{new_name}.md",
                    action="preferring_underscore_version",
                    suggestion="Remove one of the index files - only _index.md or index.md should exist",
                )

                # Prefer _index.md over index.md (Hugo convention)
                if new_name == "_index":
                    self.index_page = page
                # else: keep existing _index.md
            else:
                self.index_page = page

            # Copy metadata from index page to section
            # This allows sections to have weight, description, and other metadata
            self.metadata.update(page.metadata)

            logger.debug(
                "section_metadata_inherited",
                section=self.name,
                metadata_keys=list(page.metadata.keys()),
            )

    def add_subsection(self, section: "Section") -> None:
        """
        Add a subsection to this section.

        Args:
            section: Child section to add
        """
        logger.debug(
            "adding_subsection",
            parent_section=self.name,
            child_section=section.name,
            depth=self.depth + 1,
            total_subsections=len(self.subsections) + 1,
        )

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

        logger.debug(
            "section_children_sorted",
            section=self.name,
            pages_count=len(self.pages),
            subsections_count=len(self.subsections),
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

        logger.debug(
            "section_content_aggregated",
            section=self.name,
            page_count=result["page_count"],
            total_pages=result["total_page_count"],
            unique_tags=len(all_tags),
        )

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

    def walk(self) -> list["Section"]:
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

    def __hash__(self) -> int:
        """
        Hash based on section path for stable identity.

        The hash is computed from the section's path, which is immutable
        throughout the section lifecycle. This allows sections to be stored
        in sets and used as dictionary keys.

        Returns:
            Integer hash of the section path
        """
        return hash(self.path)

    def __eq__(self, other: Any) -> bool:
        """
        Sections are equal if they have the same path.

        Equality is based on path only, not on pages or other mutable fields.
        This means two Section objects representing the same directory are
        considered equal, even if their contents differ.

        Args:
            other: Object to compare with

        Returns:
            True if other is a Section with the same path
        """
        if not isinstance(other, Section):
            return NotImplemented
        return self.path == other.path

    def __repr__(self) -> str:
        return f"Section(name='{self.name}', pages={len(self.pages)}, subsections={len(self.subsections)})"
