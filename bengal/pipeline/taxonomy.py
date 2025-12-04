"""
Taxonomy stream for collecting tags and generating taxonomy pages.

This module provides stream-based taxonomy processing that replaces
TaxonomyOrchestrator with a declarative, reactive approach.

Flow:
    pages → collect_tags → group_by_tag → generate_taxonomy_pages → taxonomy_pages
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.pipeline.core import Stream
from bengal.utils.logger import get_logger
from bengal.utils.url_strategy import URLStrategy

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_taxonomy_stream(
    pages_stream: Stream[Page],
    site: Site,
    *,
    parallel: bool = True,
) -> Stream[Page]:
    """
    Create a stream that collects taxonomies and generates taxonomy pages.

    This stream:
    1. Collects all tags from pages
    2. Groups pages by tag
    3. Generates tag index page
    4. Generates individual tag pages (with pagination)

    Args:
        pages_stream: Stream of Page objects
        site: Site instance (for config and URL strategy)
        parallel: Whether to use parallel processing for tag page generation

    Returns:
        Stream emitting all pages (original + generated taxonomy pages)

    Example:
        >>> pages = Stream.from_iterable(site.pages)
        >>> taxonomy_stream = create_taxonomy_stream(pages, site)
        >>> for page in taxonomy_stream.iterate():
        ...     print(page.output_path)
    """
    # Collect all pages first (barrier operation)
    collected_pages = pages_stream.collect(name="collect_pages")

    # Process taxonomies and generate pages
    def process_taxonomies(pages: list[Page]) -> list[Page]:
        """
        Collect taxonomies and generate taxonomy pages.

        This function:
        1. Collects tags from all pages
        2. Builds site.taxonomies dict
        3. Generates tag index page
        4. Generates individual tag pages

        Args:
            pages: List of all pages

        Returns:
            List of all pages (original + generated taxonomy pages)
        """
        # Initialize taxonomy structure
        site.taxonomies = {"tags": {}, "categories": {}}

        # Collect taxonomies from pages
        _collect_taxonomies_from_pages(pages, site)

        # Generate taxonomy pages
        taxonomy_pages = _generate_taxonomy_pages(site, parallel=parallel)

        # Return all pages (original + generated)
        return pages + taxonomy_pages

    # Process taxonomies and flatten back to individual pages
    processed_stream = collected_pages.map(process_taxonomies, name="process_taxonomies")

    # Flatten back to individual pages
    def flatten_pages(pages: list[Page]) -> list[Page]:
        """Flatten list of pages back to individual pages."""
        return pages

    flattened_stream = processed_stream.flat_map(
        lambda pages: iter(pages), name="flatten_taxonomy_pages"
    )

    return flattened_stream


def _collect_taxonomies_from_pages(pages: list[Page], site: Site) -> None:
    """
    Collect taxonomies (tags, categories) from all pages.

    This populates site.taxonomies with tag/category data.

    Args:
        pages: List of pages to collect from
        site: Site instance (taxonomies dict is populated here)
    """
    logger.info("taxonomy_collection_start", total_pages=len(pages))

    # Get i18n config
    i18n = site.config.get("i18n", {}) or {}
    strategy = i18n.get("strategy", "none")
    share_taxonomies = bool(i18n.get("share_taxonomies", False))
    current_lang = getattr(site, "current_language", None)

    pages_with_tags = 0

    for page in pages:
        # Skip pages that shouldn't be in taxonomies
        if not _is_eligible_for_taxonomy(page):
            continue

        # Filter by language if i18n is enabled
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
                tag_str = str(tag)
                tag_key = tag_str.lower().replace(" ", "-")
                if tag_key not in site.taxonomies["tags"]:
                    site.taxonomies["tags"][tag_key] = {
                        "name": tag_str,
                        "slug": tag_key,
                        "pages": [],
                    }
                site.taxonomies["tags"][tag_key]["pages"].append(page)

        # Collect categories (if present)
        if "category" in page.metadata:
            category = page.metadata["category"]
            category_str = str(category)
            cat_key = category_str.lower().replace(" ", "-")
            if cat_key not in site.taxonomies["categories"]:
                site.taxonomies["categories"][cat_key] = {
                    "name": category_str,
                    "slug": cat_key,
                    "pages": [],
                }
            site.taxonomies["categories"][cat_key]["pages"].append(page)

    # Sort pages within each taxonomy by date (newest first)
    for taxonomy_type in site.taxonomies:
        for term_data in site.taxonomies[taxonomy_type].values():
            term_data["pages"].sort(key=lambda p: p.date if p.date else datetime.min, reverse=True)

    tag_count = len(site.taxonomies.get("tags", {}))
    cat_count = len(site.taxonomies.get("categories", {}))
    logger.info(
        "taxonomy_collection_complete",
        tags=tag_count,
        categories=cat_count,
        pages_with_tags=pages_with_tags,
        total_pages_checked=len(pages),
    )


def _generate_taxonomy_pages(site: Site, *, parallel: bool = True) -> list[Page]:
    """
    Generate taxonomy pages (tag index + individual tag pages).

    Args:
        site: Site instance with populated taxonomies
        parallel: Whether to use parallel processing

    Returns:
        List of generated taxonomy pages
    """

    generated_pages = []

    if not site.taxonomies.get("tags"):
        return generated_pages

    # Get i18n config
    i18n = site.config.get("i18n", {}) or {}
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

    url_strategy = URLStrategy()

    # Generate per-locale tag pages
    for lang in sorted(set(languages)):
        # Build per-locale tag mapping
        locale_tags = {}
        for tag_slug, tag_data in site.taxonomies["tags"].items():
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
        prev_lang = getattr(site, "current_language", None)
        site.current_language = lang
        try:
            # Generate tag index page
            tag_index = _create_tag_index_page(site, locale_tags, url_strategy)
            if tag_index:
                tag_index.lang = lang
                generated_pages.append(tag_index)

            # Generate individual tag pages
            if parallel and len(locale_tags) >= 20:  # MIN_TAGS_FOR_PARALLEL
                tag_pages = _generate_tag_pages_parallel(site, locale_tags, lang, url_strategy)
            else:
                tag_pages = _generate_tag_pages_sequential(site, locale_tags, lang, url_strategy)

            generated_pages.extend(tag_pages)
        finally:
            site.current_language = prev_lang

    logger.info(
        "taxonomy_pages_generated",
        tag_index=sum(1 for p in generated_pages if p.metadata.get("type") == "tag-index"),
        tag_pages=sum(1 for p in generated_pages if p.metadata.get("type") == "tag"),
        total=len(generated_pages),
    )

    return generated_pages


def _create_tag_index_page(
    site: Site, locale_tags: dict[str, Any], url_strategy: URLStrategy
) -> Page | None:
    """
    Create the main tags index page.

    Args:
        site: Site instance
        locale_tags: Dictionary of tag slugs to tag data for current locale
        url_strategy: URL strategy for computing paths

    Returns:
        Generated tag index page, or None if no tags
    """
    from bengal.core.page import Page

    if not locale_tags:
        return None

    virtual_path = url_strategy.make_virtual_path(site, "tags")
    tag_index = Page(
        source_path=virtual_path,
        content="",
        metadata={
            "title": "All Tags",
            "template": "tags.html",
            "type": "tag-index",
            "_generated": True,
            "_virtual": True,
            "_tags": locale_tags,
        },
    )
    tag_index.output_path = url_strategy.compute_tag_index_output_path(site)
    return tag_index


def _generate_tag_pages_sequential(
    site: Site, locale_tags: dict[str, Any], lang: str, url_strategy: URLStrategy
) -> list[Page]:
    """
    Generate tag pages sequentially.

    Args:
        site: Site instance
        locale_tags: Dictionary of tag slugs to tag data
        lang: Language code
        url_strategy: URL strategy for computing paths

    Returns:
        List of generated tag pages
    """
    pages = []
    for tag_slug, tag_data in locale_tags.items():
        tag_pages = _create_tag_pages(site, tag_slug, tag_data, url_strategy)
        for page in tag_pages:
            page.lang = lang
        pages.extend(tag_pages)
    return pages


def _generate_tag_pages_parallel(
    site: Site, locale_tags: dict[str, Any], lang: str, url_strategy: URLStrategy
) -> list[Page]:
    """
    Generate tag pages in parallel.

    Args:
        site: Site instance
        locale_tags: Dictionary of tag slugs to tag data
        lang: Language code
        url_strategy: URL strategy for computing paths

    Returns:
        List of generated tag pages
    """
    import concurrent.futures

    from bengal.config.defaults import get_max_workers

    max_workers = get_max_workers(site.config.get("max_workers"))
    all_pages = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_tag = {
            executor.submit(_create_tag_pages, site, tag_slug, tag_data, url_strategy): tag_slug
            for tag_slug, tag_data in locale_tags.items()
        }

        for future in concurrent.futures.as_completed(future_to_tag):
            tag_slug = future_to_tag[future]
            try:
                tag_pages = future.result()
                for page in tag_pages:
                    page.lang = lang
                all_pages.extend(tag_pages)
            except Exception as e:
                logger.error(
                    "taxonomy_page_generation_failed",
                    tag_slug=tag_slug,
                    lang=lang,
                    error=str(e),
                )

    return all_pages


def _create_tag_pages(
    site: Site, tag_slug: str, tag_data: dict[str, Any], url_strategy: URLStrategy
) -> list[Page]:
    """
    Create pages for an individual tag (with pagination if needed).

    Args:
        site: Site instance
        tag_slug: URL-safe tag slug
        tag_data: Dictionary containing tag name and pages
        url_strategy: URL strategy for computing paths

    Returns:
        List of generated tag pages
    """
    from bengal.core.page import Page
    from bengal.utils.pagination import Paginator

    pages_to_create = []
    per_page = site.config.get("pagination", {}).get("per_page", 10)

    # Filter out ineligible pages
    eligible_pages = [p for p in tag_data["pages"] if _is_eligible_for_taxonomy(p)]

    # Create paginator
    paginator = Paginator(eligible_pages, per_page=per_page)

    # Create a page for each pagination page
    for page_num in range(1, paginator.num_pages + 1):
        virtual_path = url_strategy.make_virtual_path(site, "tags", tag_slug, f"page_{page_num}")

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
                "_posts": eligible_pages,
                "_paginator": paginator,
                "_page_num": page_num,
            },
        )

        tag_page.output_path = url_strategy.compute_tag_output_path(
            tag_slug=tag_slug, page_num=page_num, site=site
        )

        pages_to_create.append(tag_page)

    return pages_to_create


def _is_eligible_for_taxonomy(page: Page) -> bool:
    """
    Check if a page is eligible for taxonomy collection.

    Excludes:
    - Generated pages (tag pages, archive pages, etc.)
    - Pages from autodoc output directories

    Args:
        page: Page to check

    Returns:
        True if page should be included in taxonomies
    """
    # Skip generated pages
    if page.metadata.get("_generated"):
        return False

    # Skip pages from autodoc output directories
    source_str = str(page.source_path)
    return "content/api" not in source_str and "content/cli" not in source_str
