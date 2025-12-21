"""
Content phases for build orchestration.

Phases 6-11: Sections, taxonomies, menus, related posts, query indexes, update pages list.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.output import CLIOutput


def phase_sections(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    incremental: bool,
    affected_sections: set[str] | None,
) -> None:
    """
    Phase 6: Section Finalization.

    Ensures all sections have index pages and validates section structure.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        incremental: Whether this is an incremental build
        affected_sections: Set of section paths affected by changes (or None for full build)

    Side effects:
        - May create generated index pages for sections without them
        - Invalidates regular_pages cache
    """
    with orchestrator.logger.phase("section_finalization"):
        # If incremental and there are no affected sections, skip noisy finalization/validation
        if not (incremental and isinstance(affected_sections, set) and len(affected_sections) == 0):
            orchestrator.sections.finalize_sections(affected_sections=affected_sections)

            # Invalidate regular_pages cache (section finalization may add generated index pages)
            orchestrator.site.invalidate_regular_pages_cache()

            # Validate section structure
            section_errors = orchestrator.sections.validate_sections()
            if section_errors:
                orchestrator.logger.warning(
                    "section_validation_errors",
                    error_count=len(section_errors),
                    errors=section_errors[:3],
                )
                strict_mode = orchestrator.site.config.get("strict_mode", False)
                if strict_mode:
                    cli.blank()
                    cli.error("Section validation errors:")
                    for error in section_errors:
                        cli.detail(str(error), indent=1, icon="•")
                    from bengal.errors import BengalContentError

                    raise BengalContentError(
                        f"Build failed: {len(section_errors)} section validation error(s)",
                        suggestion="Review section validation errors above and fix section structure, or disable strict mode",
                    )
                else:
                    # Warn but continue in non-strict mode
                    for error in section_errors[:3]:  # Show first 3
                        cli.warning(str(error))
                    if len(section_errors) > 3:
                        cli.warning(f"... and {len(section_errors) - 3} more errors")
        else:
            orchestrator.logger.info("section_finalization_skipped", reason="no_affected_sections")


def phase_taxonomies(
    orchestrator: BuildOrchestrator,
    cache: BuildCache,
    incremental: bool,
    parallel: bool,
    pages_to_build: list[Any],
) -> set[str]:
    """
    Phase 7: Taxonomies & Dynamic Pages.

    Collects taxonomy terms (tags, categories) and generates taxonomy pages.
    Optimized for incremental builds - only processes changed pages.

    Args:
        orchestrator: Build orchestrator instance
        cache: Build cache
        incremental: Whether this is an incremental build
        parallel: Whether to use parallel processing
        pages_to_build: List of pages being built (for incremental)

    Returns:
        Set of affected tag slugs

    Side effects:
        - Populates orchestrator.site.taxonomies
        - Creates taxonomy pages in orchestrator.site.pages
        - Invalidates regular_pages cache
        - Updates orchestrator.stats.taxonomy_time_ms
    """
    affected_tags = set()

    with orchestrator.logger.phase("taxonomies"):
        taxonomy_start = time.time()

        if incremental and pages_to_build:
            # Incremental: Only update taxonomies for changed pages
            # This is O(changed) instead of O(all) - major optimization!
            affected_tags = orchestrator.taxonomy.collect_and_generate_incremental(
                pages_to_build, cache
            )

            # Store affected tags for later use (related posts, etc.)
            orchestrator.site._affected_tags = affected_tags

        elif incremental and not pages_to_build:
            # Incremental but no pages changed: Still need to regenerate taxonomy pages
            # because site.pages was cleared (dev server case)
            # Use cache to rebuild taxonomies efficiently
            affected_tags = orchestrator.taxonomy.collect_and_generate_incremental([], cache)
            orchestrator.site._affected_tags = affected_tags

        elif not incremental:
            # Full build: Collect and generate everything
            orchestrator.taxonomy.collect_and_generate(parallel=parallel)

            # Mark all tags as affected (for Phase 6 - adding to pages_to_build)
            if hasattr(orchestrator.site, "taxonomies") and "tags" in orchestrator.site.taxonomies:
                affected_tags = set(orchestrator.site.taxonomies["tags"].keys())

            # Update cache with full taxonomy data (for next incremental build)
            for page in orchestrator.site.pages:
                if not page.metadata.get("_generated") and page.tags:
                    cache.update_page_tags(page.source_path, set(page.tags))

        orchestrator.stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
        if hasattr(orchestrator.site, "taxonomies"):
            orchestrator.logger.info(
                "taxonomies_built",
                taxonomy_count=len(orchestrator.site.taxonomies),
                total_terms=sum(len(terms) for terms in orchestrator.site.taxonomies.values()),
            )

        # Invalidate regular_pages cache (taxonomy generation adds tag/category pages)
        orchestrator.site.invalidate_regular_pages_cache()

    return affected_tags


def phase_taxonomy_index(orchestrator: BuildOrchestrator) -> None:
    """
    Phase 8: Save Taxonomy Index.

    Persists tag-to-pages mapping for incremental builds.

    Side effects:
        - Writes taxonomy index to .bengal/taxonomy_index.json
    """
    with orchestrator.logger.phase("save_taxonomy_index", enabled=True):
        try:
            from bengal.cache.taxonomy_index import TaxonomyIndex

            index = TaxonomyIndex(orchestrator.site.paths.taxonomy_cache)

            # Populate index from collected taxonomies
            if hasattr(orchestrator.site, "taxonomies") and "tags" in orchestrator.site.taxonomies:
                tags_dict = orchestrator.site.taxonomies["tags"]

                for tag_slug, tag_data in tags_dict.items():
                    # tag_data is a dict like {"name": "Programming", "slug": "programming", "pages": [...]}
                    if not isinstance(tag_data, dict):
                        continue

                    tag_name = tag_data.get("name", tag_slug)
                    pages = tag_data.get("pages", [])

                    # Extract source paths from page objects, handling various types
                    page_paths = []
                    for p in pages:
                        if isinstance(p, str):
                            page_paths.append(p)
                        elif hasattr(p, "source_path"):
                            page_paths.append(str(p.source_path))

                    # Update index with tag mapping if we have valid paths
                    if page_paths:
                        index.update_tag(tag_slug, tag_name, page_paths)

            # Persist taxonomy index to disk
            index.save_to_disk()

            orchestrator.logger.info(
                "taxonomy_index_saved",
                tags=len(index.tags),
                path=str(index.cache_path),
            )
        except Exception as e:
            orchestrator.logger.warning(
                "taxonomy_index_save_failed",
                error=str(e),
            )


def phase_menus(
    orchestrator: BuildOrchestrator, incremental: bool, changed_page_paths: set[str]
) -> None:
    """
    Phase 9: Menu Building.

    Builds navigation menus. Optimized for incremental builds.

    Args:
        orchestrator: Build orchestrator instance
        incremental: Whether this is an incremental build
        changed_page_paths: Set of paths for pages that changed

    Side effects:
        - Populates orchestrator.site.menu
        - Updates orchestrator.stats.menu_time_ms
    """
    with orchestrator.logger.phase("menus"):
        menu_start = time.time()
        # Check if config changed (forces menu rebuild)
        config_changed = incremental and orchestrator.incremental.check_config_changed()

        # Build menus (or reuse cached if unchanged)
        menu_rebuilt = orchestrator.menu.build(
            changed_pages=changed_page_paths if incremental else None,
            config_changed=config_changed,
        )

        orchestrator.stats.menu_time_ms = (time.time() - menu_start) * 1000
        orchestrator.logger.info(
            "menus_built",
            menu_count=len(orchestrator.site.menu),
            rebuilt=menu_rebuilt,
        )


def phase_related_posts(
    orchestrator: BuildOrchestrator,
    incremental: bool,
    parallel: bool,
    pages_to_build: list[Any],
) -> None:
    """
    Phase 10: Related Posts Index.

    Pre-computes related posts for O(1) template access.
    Skipped for large sites (>5K pages) or sites without tags.

    Args:
        orchestrator: Build orchestrator instance
        incremental: Whether this is an incremental build
        parallel: Whether to use parallel processing
        pages_to_build: List of pages being built (for incremental optimization)

    Side effects:
        - Populates page.related_posts for each page
        - Updates orchestrator.stats.related_posts_time_ms
    """
    should_build_related = (
        hasattr(orchestrator.site, "taxonomies")
        and "tags" in orchestrator.site.taxonomies
        and len(orchestrator.site.pages) < 5000  # Skip for large sites (>5K pages)
    )

    if should_build_related:
        with orchestrator.logger.phase("related_posts_index"):
            from bengal.orchestration.related_posts import RelatedPostsOrchestrator

            related_posts_start = time.time()
            related_posts_orchestrator = RelatedPostsOrchestrator(orchestrator.site)
            # OPTIMIZATION: In incremental builds, only update related posts for changed pages
            related_posts_orchestrator.build_index(
                limit=5,
                parallel=parallel,
                affected_pages=pages_to_build if incremental else None,
            )

            # Log statistics
            pages_with_related = sum(
                1
                for p in orchestrator.site.pages
                if hasattr(p, "related_posts")
                and p.related_posts
                and not p.metadata.get("_generated")
            )
            orchestrator.stats.related_posts_time_ms = (time.time() - related_posts_start) * 1000
            orchestrator.logger.info(
                "related_posts_built",
                pages_with_related=pages_with_related,
                total_pages=len(orchestrator.site.regular_pages),
            )
    else:
        # Skip related posts for large sites or sites without tags
        for page in orchestrator.site.pages:
            page.related_posts = []
        orchestrator.logger.info(
            "related_posts_skipped",
            reason="large_site_or_no_tags",
            page_count=len(orchestrator.site.pages),
            threshold=5000,
        )


def phase_query_indexes(
    orchestrator: BuildOrchestrator,
    cache: BuildCache,
    incremental: bool,
    pages_to_build: list[Any],
) -> None:
    """
    Phase 11: Query Indexes.

    Builds pre-computed indexes for O(1) template lookups.

    Args:
        orchestrator: Build orchestrator instance
        cache: Build cache
        incremental: Whether this is an incremental build
        pages_to_build: List of pages being built (for incremental)

    Side effects:
        - Builds/updates site.indexes
    """
    with orchestrator.logger.phase("query_indexes"):
        query_indexes_start = time.time()

        if incremental and pages_to_build:
            # Incremental: only update affected indexes
            affected_keys = orchestrator.site.indexes.update_incremental(
                pages_to_build,
                cache,
            )
            total_affected = sum(len(keys) for keys in affected_keys.values())
            orchestrator.logger.info(
                "query_indexes_updated_incremental",
                affected_keys=total_affected,
                indexes=len(affected_keys),
            )
        else:
            # Full build: rebuild all indexes
            orchestrator.site.indexes.build_all(
                orchestrator.site.pages,
                cache,
            )
            stats = orchestrator.site.indexes.stats()
            orchestrator.logger.info(
                "query_indexes_built",
                indexes=stats["total_indexes"],
            )

        query_indexes_time = (time.time() - query_indexes_start) * 1000
        orchestrator.logger.debug(
            "query_indexes_complete",
            duration_ms=query_indexes_time,
        )


def phase_update_pages_list(
    orchestrator: BuildOrchestrator,
    incremental: bool,
    pages_to_build: list[Any],
    affected_tags: set[str],
) -> list[Any]:
    """
    Phase 12: Update Pages List.

    Updates the pages_to_build list to include newly generated taxonomy pages.

    Args:
        orchestrator: Build orchestrator instance
        incremental: Whether this is an incremental build
        pages_to_build: Current list of pages to build
        affected_tags: Set of affected tag slugs

    Returns:
        Updated pages_to_build list including generated taxonomy pages

    Side effects:
        - Invalidates page caches
    """
    # Convert to set for O(1) membership and automatic deduplication
    pages_to_build_set = set(pages_to_build) if pages_to_build else set()

    # Ensure cache is fresh before accessing generated_pages
    # (Tag pages were just added in Phase 4, so cache might be stale)
    orchestrator.site.invalidate_page_caches()

    # Add newly generated tag pages to rebuild set
    # OPTIMIZATION: Use site.generated_pages (cached) instead of filtering all pages
    for page in orchestrator.site.generated_pages:
        if page.metadata.get("type") in ("tag", "tag-index"):
            # For full builds, add all taxonomy pages
            # For incremental builds, add only affected tag pages + tag index
            tag_slug = page.metadata.get("_tag_slug")
            should_include = (
                not incremental  # Full build: include all
                or page.metadata.get("type") == "tag-index"  # Always include tag index
                or (affected_tags and tag_slug in affected_tags)  # Include affected tag pages
            )

            if should_include:
                pages_to_build_set.add(page)  # O(1) + automatic dedup

    # Convert back to list for rendering
    return list(pages_to_build_set)
