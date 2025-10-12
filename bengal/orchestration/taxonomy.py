"""
Taxonomy orchestration for Bengal SSG.

Handles taxonomy collection (tags, categories) and dynamic page generation
(tag pages, archive pages, etc.).
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger
from bengal.utils.page_initializer import PageInitializer
from bengal.utils.url_strategy import URLStrategy

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.core.page import Page
    from bengal.core.site import Site


class TaxonomyOrchestrator:
    """
    Handles taxonomies and dynamic page generation.

    Responsibilities:
        - Collect tags, categories, and other taxonomies
        - Generate tag index pages
        - Generate individual tag pages (with pagination)

    Note: Section archive pages are now handled by SectionOrchestrator
    """

    def __init__(self, site: "Site"):
        """
        Initialize taxonomy orchestrator.

        Args:
            site: Site instance containing pages and sections
        """
        self.site = site
        self.url_strategy = URLStrategy()
        self.initializer = PageInitializer(site)

    def collect_and_generate(self) -> None:
        """
        Collect taxonomies and generate dynamic pages.
        Main entry point called during build.
        """
        self.collect_taxonomies()
        self.generate_dynamic_pages()

    def collect_and_generate_incremental(
        self, changed_pages: list["Page"], cache: "BuildCache"
    ) -> set[str]:
        """
        Incrementally update taxonomies for changed pages only.

        Architecture:
        1. Always rebuild site.taxonomies from current Page objects (correct)
        2. Use cache to determine which tag PAGES need regeneration (fast)
        3. Never reuse taxonomy structure with object references (prevents bugs)

        Performance:
        - Change detection: O(changed pages)
        - Taxonomy reconstruction: O(all tags * pages_per_tag) ≈ O(all pages) but fast
        - Tag page generation: O(affected tags)

        Args:
            changed_pages: List of pages that changed (NOT generated pages)
            cache: Build cache with tag index

        Returns:
            Set of affected tag slugs (for regenerating tag pages)
        """
        logger.info("taxonomy_collection_incremental_start", changed_pages=len(changed_pages))

        # STEP 1: Determine which tags are affected
        # This is the O(changed) optimization - only look at changed pages
        affected_tags = set()
        for page in changed_pages:
            if page.metadata.get("_generated"):
                continue

            # Update cache and get affected tags
            new_tags = set(page.tags) if page.tags else set()
            page_affected = cache.update_page_tags(page.source_path, new_tags)
            affected_tags.update(page_affected)

        # STEP 2: Rebuild taxonomy structure from current Page objects
        # This is ALWAYS done from scratch to avoid stale references
        # Performance: O(all pages) but very fast (just iteration + dict ops)
        self._rebuild_taxonomy_structure_from_cache(cache)

        logger.info(
            "taxonomy_collection_incremental_complete",
            tags=len(self.site.taxonomies.get("tags", {})),
            updated_pages=len(changed_pages),
            affected_tags=len(affected_tags),
        )

        # STEP 3: Generate tag pages only for affected tags
        if affected_tags:
            self.generate_dynamic_pages_for_tags(affected_tags)

        return affected_tags

    def collect_taxonomies(self) -> None:
        """
        Collect taxonomies (tags, categories, etc.) from all pages.
        Organizes pages by their taxonomic terms.
        """
        logger.info("taxonomy_collection_start", total_pages=len(self.site.pages))

        # Initialize taxonomy structure
        self.site.taxonomies = {"tags": {}, "categories": {}}

        # Collect from all pages, optionally per-locale
        i18n = self.site.config.get("i18n", {}) or {}
        share_taxonomies = bool(i18n.get("share_taxonomies", False))
        current_lang = getattr(self.site, "current_language", None)
        for page in self.site.pages:
            if (
                not share_taxonomies
                and current_lang
                and getattr(page, "lang", current_lang) != current_lang
            ):
                continue
            # Collect tags
            if page.tags:
                for tag in page.tags:
                    tag_key = tag.lower().replace(" ", "-")
                    if tag_key not in self.site.taxonomies["tags"]:
                        self.site.taxonomies["tags"][tag_key] = {
                            "name": tag,
                            "slug": tag_key,
                            "pages": [],
                        }
                    self.site.taxonomies["tags"][tag_key]["pages"].append(page)

            # Collect categories (if present in metadata)
            if "category" in page.metadata:
                category = page.metadata["category"]
                cat_key = category.lower().replace(" ", "-")
                if cat_key not in self.site.taxonomies["categories"]:
                    self.site.taxonomies["categories"][cat_key] = {
                        "name": category,
                        "slug": cat_key,
                        "pages": [],
                    }
                self.site.taxonomies["categories"][cat_key]["pages"].append(page)

        # Sort pages within each taxonomy by date (newest first)
        for taxonomy_type in self.site.taxonomies:
            for term_data in self.site.taxonomies[taxonomy_type].values():
                term_data["pages"].sort(
                    key=lambda p: p.date if p.date else datetime.min, reverse=True
                )

        tag_count = len(self.site.taxonomies.get("tags", {}))
        cat_count = len(self.site.taxonomies.get("categories", {}))
        logger.info("taxonomy_collection_complete", tags=tag_count, categories=cat_count)

    def _rebuild_taxonomy_structure_from_cache(self, cache: "BuildCache") -> None:
        """
        Rebuild site.taxonomies from cache using CURRENT Page objects.

        This is the key to avoiding stale references:
        1. Cache tells us which pages have which tags (paths only)
        2. We map paths to current Page objects (from site.pages)
        3. We reconstruct taxonomy dict with current objects

        Performance: O(tags * pages_per_tag) which is O(all pages) worst case,
        but in practice very fast because it's just dict lookups and list appends.

        CRITICAL: This always uses current Page objects, never cached references.
        """
        # Initialize fresh structure
        self.site.taxonomies = {"tags": {}, "categories": {}}

        # Build lookup map: path → current Page object
        current_page_map = {
            p.source_path: p for p in self.site.pages if not p.metadata.get("_generated")
        }

        # For each tag in cache, map paths to current Page objects
        for tag_slug in cache.get_all_tags():
            page_paths = cache.get_pages_for_tag(tag_slug)

            # Map paths to current Page objects
            current_pages = []
            for path_str in page_paths:
                path = Path(path_str)
                if path in current_page_map:
                    current_pages.append(current_page_map[path])

            if not current_pages:
                # Tag has no pages - skip it (was removed)
                continue

            # Get original tag name (not slug) from first page's tags
            # This handles "Python" vs "python" correctly
            original_tag = None
            for page in current_pages:
                if page.tags:
                    for tag in page.tags:
                        if tag.lower().replace(" ", "-") == tag_slug:
                            original_tag = tag
                            break
                if original_tag:
                    break

            if not original_tag:
                original_tag = tag_slug  # Fallback

            # Create tag entry with CURRENT page objects
            self.site.taxonomies["tags"][tag_slug] = {
                "name": original_tag,
                "slug": tag_slug,
                "pages": sorted(
                    current_pages, key=lambda p: p.date if p.date else datetime.min, reverse=True
                ),
            }

        # Handle categories (similar pattern if needed in future)

    def generate_dynamic_pages_for_tags(self, affected_tags: set) -> None:
        """
        Generate dynamic pages only for specific affected tags (incremental optimization).

        Args:
            affected_tags: Set of tag slugs that need page regeneration
        """
        generated_count = 0

        # Always regenerate tag index (it lists all tags)
        if self.site.taxonomies.get("tags"):
            tag_index = self._create_tag_index_page()
            if tag_index:
                self.site.pages.append(tag_index)
                generated_count += 1

            # Only generate pages for affected tags
            for tag_slug in affected_tags:
                if tag_slug in self.site.taxonomies["tags"]:
                    tag_data = self.site.taxonomies["tags"][tag_slug]
                    tag_pages = self._create_tag_pages(tag_slug, tag_data)
                    for page in tag_pages:
                        self.site.pages.append(page)
                        generated_count += 1

            logger.info(
                "dynamic_pages_generated_incremental",
                tag_index=1,
                tag_pages=generated_count - 1,
                total=generated_count,
                affected_tags=len(affected_tags),
            )

    def generate_dynamic_pages(self) -> None:
        """
        Generate dynamic taxonomy pages (tag pages, etc.) that don't have source files.

        Note: Section archive pages are now generated by SectionOrchestrator
        """
        generated_count = 0
        i18n = self.site.config.get("i18n", {}) or {}
        strategy = i18n.get("strategy", "none")
        share_taxonomies = bool(i18n.get("share_taxonomies", False))
        default_lang = i18n.get("default_language", "en")

        # Determine languages to generate for
        languages = [default_lang]
        if strategy != "none":
            languages = []
            langs_cfg = i18n.get("languages") or []
            for entry in langs_cfg:
                if isinstance(entry, dict) and "code" in entry:
                    languages.append(entry["code"])
                elif isinstance(entry, str):
                    languages.append(entry)
            if default_lang not in languages:
                languages.append(default_lang)

        # Generate per-locale tag pages
        if self.site.taxonomies.get("tags"):
            for lang in sorted(set(languages)):
                # Build per-locale tag mapping
                locale_tags = {}
                for tag_slug, tag_data in self.site.taxonomies["tags"].items():
                    pages_for_lang = (
                        tag_data["pages"]
                        if share_taxonomies
                        else [
                            p for p in tag_data["pages"] if getattr(p, "lang", default_lang) == lang
                        ]
                    )
                    if not pages_for_lang:
                        continue
                    locale_tags[tag_slug] = {
                        "name": tag_data["name"],
                        "slug": tag_slug,
                        "pages": pages_for_lang,
                    }
                if not locale_tags:
                    continue

                # Temporarily set language context for URL computation
                prev_lang = getattr(self.site, "current_language", None)
                self.site.current_language = lang
                try:
                    # Tag index for this language
                    tag_index = self._create_tag_index_page_for(locale_tags)
                    if tag_index:
                        tag_index.lang = lang
                        self.site.pages.append(tag_index)
                        generated_count += 1

                    # Individual tag pages for this language
                    for tag_slug, tag_data in locale_tags.items():
                        tag_pages = self._create_tag_pages_for_lang(tag_slug, tag_data, lang)
                        for page in tag_pages:
                            page.lang = lang
                            self.site.pages.append(page)
                            generated_count += 1
                finally:
                    self.site.current_language = prev_lang

        # Count types of generated pages
        tag_count = sum(
            1
            for p in self.site.pages
            if p.metadata.get("_generated") and p.output_path and "tag" in p.output_path.parts
        )
        pagination_count = sum(
            1
            for p in self.site.pages
            if p.metadata.get("_generated") and "/page/" in str(p.output_path)
        )

        if generated_count > 0:
            logger.info(
                "dynamic_pages_generated",
                tag_pages=tag_count,
                pagination_pages=pagination_count,
                total=generated_count,
            )

    def _create_tag_index_page(self) -> "Page":
        """
        Create the main tags index page.

        Returns:
            Generated tag index page
        """
        from bengal.core.page import Page

        # Create virtual path (delegate to utility)
        virtual_path = self.url_strategy.make_virtual_path(self.site, "tags")

        tag_index = Page(
            source_path=virtual_path,
            content="",
            metadata={
                "title": "All Tags",
                "template": "tags.html",
                "type": "tag-index",
                "_generated": True,
                "_virtual": True,
                "_tags": self.site.taxonomies["tags"],
            },
        )

        # Compute output path using centralized logic (i18n-aware via site.current_language)
        tag_index.output_path = self.url_strategy.compute_tag_index_output_path(self.site)

        # Ensure page is correctly initialized (sets _site, validates)
        self.initializer.ensure_initialized(tag_index)

        return tag_index

    def _create_tag_index_page_for(self, tags: dict[str, Any]) -> "Page":
        from bengal.core.page import Page

        virtual_path = self.url_strategy.make_virtual_path(self.site, "tags")
        tag_index = Page(
            source_path=virtual_path,
            content="",
            metadata={
                "title": "All Tags",
                "template": "tags.html",
                "type": "tag-index",
                "_generated": True,
                "_virtual": True,
                "_tags": tags,
            },
        )
        tag_index.output_path = self.url_strategy.compute_tag_index_output_path(self.site)
        self.initializer.ensure_initialized(tag_index)
        return tag_index

    def _create_tag_pages(self, tag_slug: str, tag_data: dict[str, Any]) -> list["Page"]:
        """
        Create pages for an individual tag (with pagination if needed).

        Args:
            tag_slug: URL-safe tag slug
            tag_data: Dictionary containing tag name and pages

        Returns:
            List of generated tag pages
        """
        from bengal.core.page import Page
        from bengal.utils.pagination import Paginator

        pages_to_create = []
        per_page = self.site.config.get("pagination", {}).get("per_page", 10)

        # Create paginator
        paginator = Paginator(tag_data["pages"], per_page=per_page)

        # Create a page for each pagination page
        for page_num in range(1, paginator.num_pages + 1):
            # Create virtual path (delegate to utility)
            virtual_path = self.url_strategy.make_virtual_path(
                self.site, "tags", tag_slug, f"page_{page_num}"
            )

            tag_page = Page(
                source_path=virtual_path,
                content="",
                metadata={
                    "title": f"Posts tagged '{tag_data['name']}'",
                    "template": "tag.html",
                    "type": "tag",
                    "_generated": True,
                    "_virtual": True,
                    "_tag": tag_data["name"],
                    "_tag_slug": tag_slug,
                    "_posts": tag_data["pages"],
                    "_paginator": paginator,
                    "_page_num": page_num,
                },
            )

            # Compute output path using centralized logic (i18n-aware via site.current_language)
            tag_page.output_path = self.url_strategy.compute_tag_output_path(
                tag_slug=tag_slug, page_num=page_num, site=self.site
            )

            # Ensure page is correctly initialized (sets _site, validates)
            self.initializer.ensure_initialized(tag_page)

            pages_to_create.append(tag_page)

        return pages_to_create

    def _create_tag_pages_for_lang(
        self, tag_slug: str, tag_data: dict[str, Any], lang: str
    ) -> list["Page"]:
        from bengal.core.page import Page
        from bengal.utils.pagination import Paginator

        pages_to_create = []
        per_page = self.site.config.get("pagination", {}).get("per_page", 10)
        paginator = Paginator(tag_data["pages"], per_page=per_page)
        for page_num in range(1, paginator.num_pages + 1):
            virtual_path = self.url_strategy.make_virtual_path(
                self.site, "tags", tag_slug, f"page_{page_num}"
            )
            tag_page = Page(
                source_path=virtual_path,
                content="",
                metadata={
                    "title": f"Posts tagged '{tag_data['name']}'",
                    "template": "tag.html",
                    "type": "tag",
                    "_generated": True,
                    "_virtual": True,
                    "_tag": tag_data["name"],
                    "_tag_slug": tag_slug,
                    "_posts": tag_data["pages"],
                    "_paginator": Paginator(tag_data["pages"], per_page=per_page),
                    "_page_num": page_num,
                },
            )
            tag_page.output_path = self.url_strategy.compute_tag_output_path(
                tag_slug=tag_slug, page_num=page_num, site=self.site
            )
            self.initializer.ensure_initialized(tag_page)
            pages_to_create.append(tag_page)
        return pages_to_create
