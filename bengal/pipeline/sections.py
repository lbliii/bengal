"""
Sections stream for finalizing sections and creating index pages.

This module provides stream-based section processing that replaces
SectionOrchestrator with a declarative, reactive approach.

Flow:
    pages → finalize_sections → generate_index_pages → pages_with_indexes
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.content_types.registry import detect_content_type, get_strategy
from bengal.pipeline.core import Stream
from bengal.utils.logger import get_logger
from bengal.utils.page_initializer import PageInitializer
from bengal.utils.url_strategy import URLStrategy

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_sections_stream(
    pages_stream: Stream[Page],
    site: Site,
) -> Stream[Page]:
    """
    Create a stream that finalizes sections and generates index pages.

    This stream:
    1. Collects all pages
    2. Finalizes sections (ensures all have index pages)
    3. Generates archive pages for sections without indexes
    4. Enriches existing index pages with section context
    5. Returns pages (including generated archive pages)

    Args:
        pages_stream: Stream of Page objects
        site: Site instance (sections are stored here)

    Returns:
        Stream emitting all pages (original + generated archive pages)

    Example:
        >>> pages = Stream.from_iterable(site.pages)
        >>> sections_stream = create_sections_stream(pages, site)
        >>> # After iterating, all sections have index pages
        >>> list(sections_stream.iterate())
    """
    # Collect all pages first (barrier operation)
    collected_pages = pages_stream.collect(name="collect_pages_for_sections")

    # Finalize sections and return pages (including generated archive pages)
    def finalize_sections(pages: list[Page]) -> list[Page]:
        """
        Finalize sections and generate index pages.

        This function:
        1. Ensures all sections have index pages
        2. Generates archive pages for sections without indexes
        3. Enriches existing index pages with section context
        4. Returns pages (including generated archive pages)

        Args:
            pages: List of all pages

        Returns:
            List of all pages (original + generated archive pages)
        """
        # Populate site.pages temporarily (section finalization expects this)
        original_pages = site.pages
        site.pages = pages

        try:
            # Finalize sections (may add generated archive pages to site.pages)
            archive_count = _finalize_all_sections(site)

            if archive_count > 0:
                # Invalidate page caches after adding generated pages
                site.invalidate_page_caches()
                logger.info("section_finalization_complete", archives_created=archive_count)

            # Return all pages (including generated archive pages)
            return list(site.pages)
        finally:
            # Restore original pages
            site.pages = original_pages

    # Finalize sections and flatten back to individual pages
    processed_stream = collected_pages.map(finalize_sections, name="finalize_sections")

    # Flatten back to individual pages
    flattened_stream = processed_stream.flat_map(
        lambda pages: iter(pages), name="flatten_section_pages"
    )

    return flattened_stream


def _finalize_all_sections(site: Site) -> int:
    """
    Finalize all sections by ensuring they have index pages.

    Args:
        site: Site instance

    Returns:
        Number of archive pages created
    """
    logger.info("section_finalization_start", section_count=len(site.sections))

    url_strategy = URLStrategy()
    initializer = PageInitializer(site)
    archive_count = 0

    for section in site.sections:
        archive_count += _finalize_recursive(section, site, url_strategy, initializer)

    return archive_count


def _finalize_recursive(
    section: Section, site: Site, url_strategy: URLStrategy, initializer: PageInitializer
) -> int:
    """
    Recursively finalize a section and its subsections.

    Args:
        section: Section to finalize
        site: Site instance
        url_strategy: URL strategy for computing paths
        initializer: Page initializer

    Returns:
        Number of archive pages created
    """
    archive_count = 0

    # Skip root section (no index needed)
    if section.name == "root":
        # Still process subsections
        for subsection in section.subsections:
            archive_count += _finalize_recursive(subsection, site, url_strategy, initializer)
        return archive_count

    # Ensure this section has an index page
    if not section.index_page:
        # Generate archive index
        archive_page = _create_archive_index(section, site, url_strategy, initializer)
        section.index_page = archive_page
        site.pages.append(archive_page)
        archive_count += 1

        logger.debug(
            "section_archive_created",
            section_name=section.name,
            section_path=str(section.path),
            page_count=len(section.pages),
        )
    else:
        # Section has an existing index page - enrich it if it needs section context
        _enrich_existing_index(section, site)

    # Recursively finalize subsections
    for subsection in section.subsections:
        archive_count += _finalize_recursive(subsection, site, url_strategy, initializer)

    return archive_count


def _create_archive_index(
    section: Section, site: Site, url_strategy: URLStrategy, initializer: PageInitializer
) -> Page:
    """
    Create an auto-generated index page for a section.

    Args:
        section: Section that needs an index page
        site: Site instance
        url_strategy: URL strategy for computing paths
        initializer: Page initializer

    Returns:
        Page object representing the section index
    """
    from bengal.core.page import Page
    from bengal.utils.pagination import Paginator

    # Create virtual path for generated archive
    virtual_path = url_strategy.make_virtual_path(site, "archives", section.name)

    # Detect content type
    content_type = detect_content_type(section, site.config)

    # Determine template
    strategy = get_strategy(content_type)
    template = strategy.get_template()

    # Base metadata
    metadata = {
        "title": section.title,
        "template": template,
        "type": content_type,
        "_generated": True,
        "_virtual": True,
        "_section": section,
        # Filter and sort pages using content type strategy
        "_posts": _prepare_posts_list(section, content_type, site),
        "_subsections": section.subsections,
        "_content_type": content_type,
    }

    # Add pagination only if appropriate
    if _should_paginate(section, content_type, site):
        paginator = Paginator(
            items=section.pages,
            per_page=site.config.get("pagination", {}).get("per_page", 10),
        )
        metadata.update(
            {
                "_paginator": paginator,
                "_page_num": 1,
            }
        )

    # Create archive page
    archive_page = Page(source_path=virtual_path, content="", metadata=metadata)

    # Compute output path using centralized logic
    archive_page.output_path = url_strategy.compute_archive_output_path(
        section=section, page_num=1, site=site
    )

    # Ensure page is correctly initialized (sets _site, validates)
    initializer.ensure_initialized_for_section(archive_page, section)

    return archive_page


def _enrich_existing_index(section: Section, site: Site) -> None:
    """
    Enrich an existing user-created index page with section context.

    Args:
        section: Section with an existing index page
        site: Site instance
    """
    index_page = section.index_page
    if not index_page:
        return

    page_type = index_page.metadata.get("type", "")

    # Only enrich pages that need section context (blog, archive, etc.)
    if page_type in ("blog", "archive", "api-reference", "cli-reference", "tutorial"):
        # Add section context metadata if not already present
        if "_section" not in index_page.metadata:
            index_page.metadata["_section"] = section

        if "_posts" not in index_page.metadata:
            # Use content type strategy to filter and sort pages
            content_type = page_type or "list"
            strategy = get_strategy(content_type)

            # Filter out index page
            filtered_pages = strategy.filter_display_pages(
                section.regular_pages, section.index_page
            )

            # Sort according to content type
            sorted_pages = strategy.sort_pages(filtered_pages)

            index_page.metadata["_posts"] = sorted_pages

        if "_subsections" not in index_page.metadata:
            index_page.metadata["_subsections"] = section.subsections

        # Add pagination if appropriate and not already present
        if "_paginator" not in index_page.metadata and _should_paginate(section, page_type, site):
            from bengal.utils.pagination import Paginator

            paginator = Paginator(
                items=section.pages,
                per_page=site.config.get("pagination", {}).get("per_page", 10),
            )
            index_page.metadata["_paginator"] = paginator
            index_page.metadata["_page_num"] = 1

        logger.debug(
            "section_index_enriched",
            section_name=section.name,
            page_type=page_type,
            post_count=len(section.pages),
        )


def _should_paginate(section: Section, content_type: str, site: Site) -> bool:
    """
    Determine if section should have pagination.

    Args:
        section: Section to check
        content_type: Detected content type
        site: Site instance

    Returns:
        True if section should have pagination
    """
    # Get strategy and ask if pagination is appropriate
    strategy = get_strategy(content_type)

    # Allow explicit override
    if "paginate" in section.metadata:
        return section.metadata["paginate"]

    # Use strategy's logic
    page_count = len(section.pages)
    return strategy.should_paginate(page_count, site.config)


def _prepare_posts_list(section: Section, content_type: str, site: Site) -> list[Page]:
    """
    Prepare the posts list for a section using content type strategy.

    Args:
        section: Section to prepare posts for
        content_type: Content type of the section
        site: Site instance

    Returns:
        Filtered and sorted list of pages
    """
    strategy = get_strategy(content_type)

    # Filter out index page (for auto-generated, index_page may not exist yet)
    filtered_pages = strategy.filter_display_pages(
        section.regular_pages, section.index_page if hasattr(section, "index_page") else None
    )

    # Sort according to content type
    return strategy.sort_pages(filtered_pages)
