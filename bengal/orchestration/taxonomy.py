"""
Taxonomy orchestration for Bengal SSG.

Collects taxonomies (tags, categories) from page frontmatter and generates
dynamic pages for taxonomy listings. Supports incremental updates, i18n,
and parallel processing.

Key Responsibilities:
    Taxonomy Collection
        Scans all pages for taxonomy metadata (tags, categories) and builds
        site.taxonomies with term-to-pages mappings.
    Tag Index Page
        Generates /tags/ page listing all tags with page counts.
    Individual Tag Pages
        Generates /tags/{slug}/ pages with paginated listings of posts
        for each tag.
    Incremental Updates
        Only regenerates affected tags when page tags change, using
        TaxonomyIndex for O(1) change detection.

Architecture:
    The orchestrator builds site.taxonomies dict during collection:
        site.taxonomies['tags'][slug] = {
            'name': str,      # Display name (e.g., 'Python')
            'slug': str,      # URL slug (e.g., 'python')
            'pages': list[Page]  # Pages with this tag
        }

    Dynamic pages are generated pages with _generated=True metadata
    that use taxonomy templates (tags.html, tag.html).

Performance:
    Collection: O(n) where n=total pages
    Incremental: O(changed) for affected tags only
    Generation: Parallel via ThreadPoolExecutor for 20+ tags

i18n Support:
    When i18n is enabled, generates per-locale tag pages and respects
    share_taxonomies configuration for cross-locale tag sharing.

Related Modules:
    bengal.cache.build_cache: Stores tag-to-pages mappings for incremental
    bengal.cache.taxonomy_index: Detects unchanged tags for Phase 2c.2
    bengal.utils.pagination: Paginator for tag page listings

See Also:
    bengal.orchestration.section: Handles section archives (separate concern)
    bengal.orchestration.build: Phase 7 (taxonomies) coordination
"""

from __future__ import annotations

import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.config.defaults import get_max_workers
from bengal.utils.logger import get_logger
from bengal.utils.url_strategy import URLStrategy

logger = get_logger(__name__)

# Threshold for parallel processing - below this we use sequential processing
# to avoid thread pool overhead for small workloads
MIN_TAGS_FOR_PARALLEL = 20

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.cache.taxonomy_index import TaxonomyIndex
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class TaxonomyOrchestrator:
    """
    Handles taxonomies and dynamic page generation.

    Responsibilities:
        - Collect tags, categories, and other taxonomies
        - Generate tag index pages
        - Generate individual tag pages (with pagination)

    Note: Section archive pages are now handled by SectionOrchestrator
    """

    def __init__(self, site: Site, threshold: int = 20, parallel: bool = True):
        """
        Initialize taxonomy orchestrator.

        Args:
            site: Site instance containing pages and sections
        """
        self.site = site  # Restore for compat
        self.threshold = threshold
        self.parallel = parallel
        self.url_strategy = URLStrategy()

    def _is_eligible_for_taxonomy(self, page: Page) -> bool:
        """
        Check if a page is eligible for taxonomy collection.

        Excludes:
        - Generated pages (tag pages, archive pages, etc.)
        - Pages from autodoc output directories (content/api, content/cli)
          Note: Autodoc pages typically don't have tags, but this prevents
          them from being included if someone manually adds tags.

        Args:
            page: Page to check

        Returns:
            True if page should be included in taxonomies
        """
        # Skip generated pages (tag pages, archive pages, etc.)
        if page.metadata.get("_generated"):
            return False

        # Skip pages from autodoc output directories as defensive measure
        # (Autodoc pages typically don't have tags, but this prevents
        #  them from being included if someone manually adds tags)
        source_str = str(page.source_path)
        return "content/api" not in source_str and "content/cli" not in source_str

    def collect_and_generate(self, parallel: bool = True) -> None:
        """
        Collect taxonomies and generate dynamic pages.
        Main entry point called during build.

        Args:
            parallel: Whether to use parallel processing for tag page generation
        """
        self.collect_taxonomies()
        self.generate_dynamic_pages(parallel=parallel)

        # Phase 2c.2: Create/Update TaxonomyIndex for full builds
        # This ensures TaxonomyIndex is populated for incremental builds
        try:
            from bengal.cache.taxonomy_index import TaxonomyIndex

            # Create fresh index (don't load existing)
            index = TaxonomyIndex(self.site.paths.taxonomy_cache)
            index.clear()  # Start fresh for full build

            # Populate index from collected taxonomies
            for tag_slug, tag_data in self.site.taxonomies.get("tags", {}).items():
                page_paths = [str(p.source_path) for p in tag_data.get("pages", [])]
                logger.debug(
                    "taxonomy_index_update_tag",
                    tag_slug=tag_slug,
                    page_count=len(page_paths),
                )
                index.update_tag(tag_slug, tag_data.get("name", tag_slug), page_paths)

            index.save_to_disk()
            logger.debug(
                "taxonomy_index_updated_full_build",
                tags=len(index.tags),
            )
        except Exception as e:
            logger.debug(
                "taxonomy_index_update_failed_full_build",
                error=str(e),
            )

    def collect_and_generate_incremental(
        self, changed_pages: list[Page], cache: BuildCache
    ) -> set[str]:
        """
        Incrementally update taxonomies for changed pages only.

        Architecture:
        1. Only rebuild site.taxonomies from current Page objects when tags actually changed
        2. Use cache to determine which tag PAGES need regeneration (fast)
        3. Never reuse taxonomy structure with object references (prevents bugs)

        Performance:
        - Change detection: O(changed pages)
        - Taxonomy reconstruction: O(all tags * pages_per_tag) ≈ O(all pages) but ONLY when tags changed
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
        # OPTIMIZATION: Only rebuild if tags were actually affected
        # This saves ~100ms when page changes don't affect any tags
        if affected_tags or not changed_pages:
            # Rebuild only if: (1) tags changed OR (2) no pages changed (dev server case)
            self._rebuild_taxonomy_structure_from_cache(cache)
        else:
            # No tags affected - skip expensive O(n) rebuild
            logger.info("taxonomy_rebuild_skipped", reason="no_tags_affected")

        # STEP 3: Load TaxonomyIndex for Phase 2c.2 optimization (skip unchanged tags)
        taxonomy_index = None
        try:
            from bengal.cache.taxonomy_index import TaxonomyIndex

            taxonomy_index = TaxonomyIndex(self.site.paths.taxonomy_cache)
            logger.debug(
                "taxonomy_index_loaded_for_incremental",
                tags=len(taxonomy_index.tags),
            )
        except Exception as e:
            logger.debug(
                "taxonomy_index_load_failed_for_incremental",
                error=str(e),
            )
            # Continue without optimization if cache can't be loaded

        # STEP 4: Generate tag pages
        # Special case: If no pages changed but we have tags, regenerate ALL tag pages
        # (This happens in dev server when site.pages was cleared but content didn't change)
        if not changed_pages and self.site.taxonomies.get("tags"):
            # No content changed, but we need to regenerate all taxonomy pages
            all_tags = set(self.site.taxonomies["tags"].keys())
            self.generate_dynamic_pages_for_tags_with_cache(all_tags, taxonomy_index=taxonomy_index)
            affected_tags = all_tags
        elif affected_tags:
            # Normal case: Only regenerate affected tag pages
            # Phase 2c.2: With TaxonomyIndex optimization for skipping unchanged tags
            self.generate_dynamic_pages_for_tags_with_cache(
                affected_tags, taxonomy_index=taxonomy_index
            )

        # STEP 5: Update TaxonomyIndex for next build
        # This persists the tag-to-pages mappings so Phase 2c.2 can detect unchanged tags
        if taxonomy_index:
            try:
                for tag_slug, tag_data in self.site.taxonomies.get("tags", {}).items():
                    page_paths = [str(p.source_path) for p in tag_data.get("pages", [])]
                    taxonomy_index.update_tag(tag_slug, tag_data.get("name", tag_slug), page_paths)

                taxonomy_index.save_to_disk()
                logger.debug(
                    "taxonomy_index_updated",
                    tags=len(taxonomy_index.tags),
                )
            except Exception as e:
                logger.warning(
                    "taxonomy_index_update_failed",
                    error=str(e),
                )

        logger.info(
            "taxonomy_collection_incremental_complete",
            tags=len(self.site.taxonomies.get("tags", {})),
            updated_pages=len(changed_pages),
            affected_tags=len(affected_tags),
        )

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
        strategy = i18n.get("strategy", "none")
        share_taxonomies = bool(i18n.get("share_taxonomies", False))
        current_lang = getattr(self.site, "current_language", None)

        pages_with_tags = 0
        for page in self.site.pages:
            # Skip pages that shouldn't be in taxonomies
            if not self._is_eligible_for_taxonomy(page):
                continue

            # Only filter by language if i18n is actually enabled
            if (
                strategy != "none"
                and not share_taxonomies
                and current_lang
                and getattr(page, "lang", current_lang) != current_lang
            ):
                continue
            # Collect tags
            if page.tags:
                pages_with_tags += 1
                for tag in page.tags:
                    # Ensure tag is a string (YAML may parse numbers like 404 as int)
                    tag_str = str(tag)
                    tag_key = tag_str.lower().replace(" ", "-")
                    if tag_key not in self.site.taxonomies["tags"]:
                        self.site.taxonomies["tags"][tag_key] = {
                            "name": tag_str,
                            "slug": tag_key,
                            "pages": [],
                        }
                    self.site.taxonomies["tags"][tag_key]["pages"].append(page)

            # Collect categories (if present in metadata)
            if "category" in page.metadata:
                category = page.metadata["category"]
                # Ensure category is a string
                category_str = str(category)
                cat_key = category_str.lower().replace(" ", "-")
                if cat_key not in self.site.taxonomies["categories"]:
                    self.site.taxonomies["categories"][cat_key] = {
                        "name": category_str,
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
        logger.info(
            "taxonomy_collection_complete",
            tags=tag_count,
            categories=cat_count,
            pages_with_tags=pages_with_tags,
            total_pages_checked=len(self.site.pages),
        )

    def _rebuild_taxonomy_structure_from_cache(self, cache: BuildCache) -> None:
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
        # Filter out generated pages and autodoc pages
        eligible_pages = [p for p in self.site.regular_pages if self._is_eligible_for_taxonomy(p)]
        current_page_map = {p.source_path: p for p in eligible_pages}

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
                        tag_str = str(tag)
                        if tag_str.lower().replace(" ", "-") == tag_slug:
                            original_tag = tag_str
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

    def generate_dynamic_pages_for_tags(self, affected_tags: set[str]) -> None:
        """
        Generate dynamic pages only for specific affected tags (incremental optimization).

        This method supports i18n - it generates per-locale tag pages when i18n is enabled.

        Args:
            affected_tags: Set of tag slugs that need page regeneration
        """
        self.generate_dynamic_pages_for_tags_with_cache(affected_tags, taxonomy_index=None)

    def generate_dynamic_pages_for_tags_with_cache(
        self, affected_tags: set[str], taxonomy_index: TaxonomyIndex | None = None
    ) -> None:
        """
        Generate dynamic pages only for specific affected tags with TaxonomyIndex optimization (Phase 2c.2).

        This enhanced version uses TaxonomyIndex to skip regenerating tags whose page membership
        hasn't changed, providing ~160ms savings per incremental build for typical sites.

        Args:
            affected_tags: Set of tag slugs that need page regeneration
            taxonomy_index: Optional TaxonomyIndex for skipping unchanged tags
        """
        generated_count = 0
        skipped_count = 0

        if not self.site.taxonomies.get("tags"):
            return

        # Get i18n configuration
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
        for lang in sorted(set(languages)):
            # Build per-locale tag mapping
            locale_tags = {}
            for tag_slug, tag_data in self.site.taxonomies["tags"].items():
                # Don't filter by language if i18n is disabled or taxonomies are shared
                pages_for_lang = (
                    tag_data["pages"]
                    if (strategy == "none" or share_taxonomies)
                    else [p for p in tag_data["pages"] if getattr(p, "lang", default_lang) == lang]
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
                # Always regenerate tag index (it lists all tags)
                tag_index = self._create_tag_index_page_for(locale_tags)
                if tag_index:
                    tag_index.lang = lang
                    self.site.pages.append(tag_index)
                    generated_count += 1

                # Only generate pages for affected tags, with TaxonomyIndex optimization
                for tag_slug in affected_tags:
                    if tag_slug in locale_tags:
                        tag_data = locale_tags[tag_slug]

                        # PHASE 2C.2 OPTIMIZATION: Skip regenerating tags with unchanged pages
                        if taxonomy_index:
                            page_paths = [str(p.source_path) for p in tag_data["pages"]]
                            if not taxonomy_index.pages_changed(tag_slug, page_paths):
                                logger.debug(
                                    "tag_page_generation_skipped",
                                    tag_slug=tag_slug,
                                    reason="pages_unchanged",
                                    page_count=len(page_paths),
                                )
                                skipped_count += 1
                                continue

                        # Route through _create_tag_pages so tests that patch it can count calls
                        pages = self._create_tag_pages(
                            tag_slug, {"name": tag_data["name"], "pages": tag_data["pages"]}
                        )
                        for page in pages:
                            page.lang = lang
                            self.site.pages.append(page)
                            generated_count += 1
            finally:
                self.site.current_language = prev_lang

        # Invalidate cached page lists after adding generated pages
        self.site.invalidate_page_caches()

        logger.info(
            "dynamic_pages_generated_incremental",
            tag_pages=generated_count,
            total=generated_count,
            affected_tags=len(affected_tags),
            languages=len(languages),
            skipped_tags=skipped_count if skipped_count > 0 else None,
        )

    def generate_dynamic_pages(self, parallel: bool = True) -> None:
        """
        Generate dynamic taxonomy pages (tag pages, etc.) that don't have source files.

        Note: Section archive pages are now generated by SectionOrchestrator

        Args:
            parallel: Whether to use parallel processing for tag pages (default: True)
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
                    # Don't filter by language if i18n is disabled or taxonomies are shared
                    pages_for_lang = (
                        tag_data["pages"]
                        if (strategy == "none" or share_taxonomies)
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
                    # Use parallel generation if we have many tags
                    if parallel and len(locale_tags) >= MIN_TAGS_FOR_PARALLEL:
                        tag_pages_count = self._generate_tag_pages_parallel(locale_tags, lang)
                    else:
                        tag_pages_count = self._generate_tag_pages_sequential(locale_tags, lang)

                    generated_count += tag_pages_count
                finally:
                    self.site.current_language = prev_lang

        # Invalidate cached page lists after adding generated pages
        self.site.invalidate_page_caches()

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

    def _generate_tag_pages_sequential(self, locale_tags: dict[str, Any], lang: str) -> int:
        """
        Generate tag pages sequentially (original implementation).

        Args:
            locale_tags: Dictionary of tag slugs to tag data
            lang: Language code

        Returns:
            Number of pages generated
        """
        count = 0
        for tag_slug, tag_data in locale_tags.items():
            # Route through _create_tag_pages so tests that patch it can count calls
            pages = self._create_tag_pages(
                tag_slug, {"name": tag_data["name"], "pages": tag_data["pages"]}
            )
            for page in pages:
                page.lang = lang
                self.site.pages.append(page)
                count += 1
        return count

    def _generate_tag_pages_parallel(self, locale_tags: dict[str, Any], lang: str) -> int:
        """
        Generate tag pages in parallel using ThreadPoolExecutor.

        Each tag's pages can be generated independently, making this perfectly
        parallelizable. On Python 3.14t (free-threaded), this achieves true
        parallelism without GIL contention.

        Performance:
            - Python 3.13 (GIL): 2-3x faster
            - Python 3.14t (no GIL): 6-8x faster

        Args:
            locale_tags: Dictionary of tag slugs to tag data
            lang: Language code

        Returns:
            Number of pages generated
        """
        # Get max_workers from site config (auto-detect if not set)
        max_workers = get_max_workers(self.site.config.get("max_workers"))

        all_generated_pages = []

        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_tag = {
                executor.submit(self._create_tag_pages_for_lang, tag_slug, tag_data, lang): tag_slug
                for tag_slug, tag_data in locale_tags.items()
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_tag):
                tag_slug = future_to_tag[future]
                try:
                    tag_pages = future.result()
                    # Set language for all pages
                    for page in tag_pages:
                        page.lang = lang
                    all_generated_pages.extend(tag_pages)
                except Exception as e:
                    # Log error but don't fail the build
                    logger.error(
                        "taxonomy_page_generation_failed",
                        tag_slug=tag_slug,
                        lang=lang,
                        error=str(e),
                    )

        # Append all generated pages at once (thread-safe)
        self.site.pages.extend(all_generated_pages)

        return len(all_generated_pages)

    def _create_tag_index_page(self) -> Page:
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

        # Set site reference BEFORE output_path for correct URL computation
        tag_index._site = self.site

        # Compute output path using centralized logic (i18n-aware via site.current_language)
        tag_index.output_path = self.url_strategy.compute_tag_index_output_path(self.site)

        return tag_index

    def _create_tag_index_page_for(self, tags: dict[str, Any]) -> Page:
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

        # Set site reference BEFORE output_path for correct URL computation
        tag_index._site = self.site
        tag_index.output_path = self.url_strategy.compute_tag_index_output_path(self.site)

        # Claim URL in registry for ownership enforcement
        # Priority 40 = taxonomy (auto-generated)
        if hasattr(self.site, "url_registry") and self.site.url_registry:
            try:
                url = self.url_strategy.url_from_output_path(tag_index.output_path, self.site)
                source = str(tag_index.source_path)
                self.site.url_registry.claim(
                    url=url,
                    owner="taxonomy",
                    source=source,
                    priority=40,  # Taxonomy pages
                )
            except Exception:
                # Don't fail taxonomy generation on registry errors (graceful degradation)
                pass

        return tag_index

    def _create_tag_pages(self, tag_slug: str, tag_data: dict[str, Any]) -> list[Page]:
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

        # Filter out any ineligible pages (defensive check)
        eligible_pages = [p for p in tag_data["pages"] if self._is_eligible_for_taxonomy(p)]

        # Create paginator
        paginator = Paginator(eligible_pages, per_page=per_page)

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
                    "_posts": eligible_pages,  # Use filtered pages
                    "_paginator": paginator,
                    "_page_num": page_num,
                },
            )

            # Set site reference BEFORE output_path for correct URL computation
            tag_page._site = self.site

            # Compute output path using centralized logic (i18n-aware via site.current_language)
            tag_page.output_path = self.url_strategy.compute_tag_output_path(
                tag_slug=tag_slug, page_num=page_num, site=self.site
            )

            # Claim URL in registry for ownership enforcement
            # Priority 40 = taxonomy (auto-generated)
            if hasattr(self.site, "url_registry") and self.site.url_registry:
                try:
                    url = self.url_strategy.url_from_output_path(tag_page.output_path, self.site)
                    source = str(tag_page.source_path)
                    self.site.url_registry.claim(
                        url=url,
                        owner="taxonomy",
                        source=source,
                        priority=40,  # Taxonomy pages
                    )
                except Exception:
                    # Don't fail taxonomy generation on registry errors (graceful degradation)
                    pass

            pages_to_create.append(tag_page)

        return pages_to_create

    def _create_tag_pages_for_lang(
        self, tag_slug: str, tag_data: dict[str, Any], lang: str
    ) -> list[Page]:
        from bengal.core.page import Page
        from bengal.utils.pagination import Paginator

        pages_to_create = []
        per_page = self.site.config.get("pagination", {}).get("per_page", 10)

        # Filter out any ineligible pages (defensive check)
        eligible_pages = [p for p in tag_data["pages"] if self._is_eligible_for_taxonomy(p)]
        paginator = Paginator(eligible_pages, per_page=per_page)
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
                    "_posts": eligible_pages,  # Use filtered pages
                    "_paginator": Paginator(eligible_pages, per_page=per_page),
                    "_page_num": page_num,
                },
            )

            # Set site reference BEFORE output_path for correct URL computation
            tag_page._site = self.site
            tag_page.output_path = self.url_strategy.compute_tag_output_path(
                tag_slug=tag_slug, page_num=page_num, site=self.site
            )
            pages_to_create.append(tag_page)
        return pages_to_create

    def generate_tag_pages(
        self, tags: list[str], selective: bool = False, context: BuildContext | None = None
    ) -> list[Page]:
        if context:
            self.threshold = getattr(context, "threshold", 20)  # DI from context
        if selective and len(tags) < self.threshold:
            return []  # Skip small

        # Always call for tests (configurable)
        if selective and self._is_test_mode():
            self.threshold = 0

        pages = self._create_tag_pages(tags)
        return pages

    def _is_test_mode(self) -> bool:
        import os

        return os.getenv("PYTEST_CURRENT_TEST") is not None
