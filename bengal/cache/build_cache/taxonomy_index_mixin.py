"""
Taxonomy indexing mixin for BuildCache.

Provides methods for maintaining bidirectional tag/page indexes for fast
taxonomy reconstruction during incremental builds.

Key Concepts:
    - Forward index: page_path → set[tag_slug]
    - Inverted index: tag_slug → set[page_path]
    - O(1) taxonomy reconstruction from cache
    - Efficient tag change detection

Related Modules:
    - bengal.cache.build_cache.core: Main BuildCache class
    - bengal.orchestration.taxonomy: Taxonomy orchestration
    - bengal.cache.taxonomy_index: TaxonomyIndex utilities
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class TaxonomyIndexMixin:
    """
    Mixin providing taxonomy indexing for fast incremental builds.

    Requires these attributes on the host class:
        - taxonomy_deps: dict[str, set[str]]
        - page_tags: dict[str, set[str]]
        - tag_to_pages: dict[str, set[str]]
        - known_tags: set[str]
    """

    # Type hints for mixin attributes (provided by host class)
    taxonomy_deps: dict[str, set[str]]
    page_tags: dict[str, set[str]]
    tag_to_pages: dict[str, set[str]]
    known_tags: set[str]

    def add_taxonomy_dependency(self, taxonomy_term: str, page: Path) -> None:
        """
        Record that a taxonomy term affects a page.

        Args:
            taxonomy_term: Taxonomy term (e.g., "tag:python")
            page: Page that uses this taxonomy term
        """
        if taxonomy_term not in self.taxonomy_deps:
            self.taxonomy_deps[taxonomy_term] = set()

        self.taxonomy_deps[taxonomy_term].add(str(page))

    def get_previous_tags(self, page_path: Path) -> set[str]:
        """
        Get tags from previous build for a page.

        Args:
            page_path: Path to page

        Returns:
            Set of tags from previous build (empty set if new page)
        """
        return self.page_tags.get(str(page_path), set())

    def update_tags(self, page_path: Path, tags: set[str]) -> None:
        """
        Store current tags for a page (for next build's comparison).

        Args:
            page_path: Path to page
            tags: Current set of tags for the page
        """
        self.page_tags[str(page_path)] = tags

    def update_page_tags(self, page_path: Path, tags: set[str]) -> set[str]:
        """
        Update tag index when a page's tags change.

        Maintains bidirectional index:
        - page_tags: path → tags (forward)
        - tag_to_pages: tag → paths (inverted)

        This is the key method that enables O(1) taxonomy reconstruction.

        Args:
            page_path: Path to page source file
            tags: Current set of tags for this page (original case, e.g., "Python", "Web Dev")

        Returns:
            Set of affected tag slugs (tags added, removed, or modified)
        """
        page_path_str = str(page_path)
        affected_tags = set()

        # Get old tags for this page
        old_tags = self.page_tags.get(page_path_str, set())
        old_slugs = {tag.lower().replace(" ", "-") for tag in old_tags}
        new_slugs = {tag.lower().replace(" ", "-") for tag in tags}

        # Find changes
        removed_slugs = old_slugs - new_slugs
        added_slugs = new_slugs - old_slugs
        unchanged_slugs = old_slugs & new_slugs

        # Remove page from old tags
        for tag_slug in removed_slugs:
            if tag_slug in self.tag_to_pages:
                self.tag_to_pages[tag_slug].discard(page_path_str)
                # Remove empty tag entries
                if not self.tag_to_pages[tag_slug]:
                    del self.tag_to_pages[tag_slug]
                    self.known_tags.discard(tag_slug)
            affected_tags.add(tag_slug)

        # Add page to new tags
        for tag_slug in added_slugs:
            self.tag_to_pages.setdefault(tag_slug, set()).add(page_path_str)
            self.known_tags.add(tag_slug)
            affected_tags.add(tag_slug)

        # Mark unchanged tags as affected if page content changed
        # (affects sort order, which affects tag page rendering)
        affected_tags.update(unchanged_slugs)

        # Update forward index
        self.page_tags[page_path_str] = tags

        return affected_tags

    def get_pages_for_tag(self, tag_slug: str) -> set[str]:
        """
        Get all page paths for a given tag.

        Args:
            tag_slug: Tag slug (e.g., 'python', 'web-dev')

        Returns:
            Set of page path strings
        """
        return self.tag_to_pages.get(tag_slug, set()).copy()

    def get_all_tags(self) -> set[str]:
        """
        Get all known tag slugs from previous build.

        Returns:
            Set of tag slugs
        """
        return self.known_tags.copy()
