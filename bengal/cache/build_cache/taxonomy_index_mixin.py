"""
Standalone taxonomy index for BuildCache.

Provides bidirectional tag/page indexes for fast taxonomy reconstruction
during incremental builds. Used via composition in BuildCache.

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


class BuildTaxonomyIndex:
    """
    Standalone taxonomy index for tag/page bidirectional mapping.

    Maintains forward (page → tags) and inverted (tag → pages) indexes
    for O(1) taxonomy reconstruction during incremental builds.

    Attributes:
        taxonomy_deps: Mapping of taxonomy terms to affected pages
        page_tags: Forward index mapping page paths to their tags
        tag_to_pages: Inverted index mapping tag slugs to page paths
        known_tags: Set of all tag slugs from previous build

    """

    def __init__(
        self,
        taxonomy_deps: dict[str, set[str]] | None = None,
        page_tags: dict[str, set[str]] | None = None,
        tag_to_pages: dict[str, set[str]] | None = None,
        known_tags: set[str] | None = None,
    ) -> None:
        self.taxonomy_deps = taxonomy_deps if taxonomy_deps is not None else {}
        self.page_tags = page_tags if page_tags is not None else {}
        self.tag_to_pages = tag_to_pages if tag_to_pages is not None else {}
        self.known_tags = known_tags if known_tags is not None else set()

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
        # Filter out None tags (YAML parses 'null' as None)
        old_tags = self.page_tags.get(page_path_str, set())
        old_slugs = {str(tag).lower().replace(" ", "-") for tag in old_tags if tag is not None}
        new_slugs = {str(tag).lower().replace(" ", "-") for tag in tags if tag is not None}

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

    def clear(self) -> None:
        """Clear all taxonomy index data."""
        self.taxonomy_deps.clear()
        self.page_tags.clear()
        self.tag_to_pages.clear()
        self.known_tags.clear()
