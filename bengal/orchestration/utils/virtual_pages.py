"""
Virtual page creation utilities for orchestrators.

Consolidates the common pattern for creating generated/virtual pages used by
TaxonomyOrchestrator and SectionOrchestrator. Provides a clean interface for
creating tag pages, archive pages, and other dynamically generated content.

Example:
    >>> spec = VirtualPageSpec(
    ...     title="Posts tagged 'python'",
    ...     template="tag.html",
    ...     page_type="tag",
    ...     metadata={"_tag": "python", "_posts": posts},
    ... )
    >>> page = create_virtual_page(
    ...     site=site,
    ...     url_strategy=url_strategy,
    ...     spec=spec,
    ...     path_segments=("tags", "python", "page_1"),
    ...     output_path=url_strategy.compute_tag_output_path("python", 1, site),
    ...     registry_owner="taxonomy",
    ...     registry_priority=40,
    ... )

"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.utils.paths.url_strategy import URLStrategy

logger = get_logger(__name__)


@dataclass
class VirtualPageSpec:
    """
    Specification for creating a virtual page.

    Attributes:
        title: Page title
        template: Template file to use (e.g., "tag.html", "archive.html")
        page_type: Type of page for content type detection
        metadata: Additional metadata to set on the page
        lang: Optional language code for i18n
    """

    title: str
    template: str
    page_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    lang: str | None = None


def create_virtual_page(
    site: Site,
    url_strategy: URLStrategy,
    spec: VirtualPageSpec,
    path_segments: tuple[str, ...],
    output_path: Path,
    registry_owner: str | None = None,
    registry_priority: int = 50,
) -> Page:
    """
    Create a virtual/generated page with proper initialization.

    This consolidates the common pattern for creating tag pages, archive pages,
    and other dynamically generated pages across orchestrators.

    Steps performed:
    1. Create virtual source path using url_strategy
    2. Create Page object with standard virtual page metadata
    3. Mark page as virtual (both attribute and metadata)
    4. Set site reference BEFORE output_path (required for URL computation)
    5. Set output path
    6. Optionally claim URL in registry

    Args:
        site: Site instance
        url_strategy: URLStrategy for path computation
        spec: VirtualPageSpec with page configuration
        path_segments: Segments for virtual path (e.g., ("tags", "python"))
        output_path: Pre-computed output path
        registry_owner: Owner name for URL registry (None to skip registration)
        registry_priority: Priority for URL claim (default 50)

    Returns:
        Fully initialized virtual Page object

    Example:
        >>> page = create_virtual_page(
        ...     site=site,
        ...     url_strategy=URLStrategy(),
        ...     spec=VirtualPageSpec(title="All Tags", template="tags.html", page_type="tag-index"),
        ...     path_segments=("tags",),
        ...     output_path=Path("tags/index.html"),
        ...     registry_owner="taxonomy",
        ...     registry_priority=40,
        ... )
    """
    from bengal.core.page import Page

    # Create virtual path
    virtual_path = url_strategy.make_virtual_path(site, *path_segments)

    # Build complete metadata
    metadata = {
        "title": spec.title,
        "template": spec.template,
        "type": spec.page_type,
        "_generated": True,
        "_virtual": True,
        **spec.metadata,
    }

    # Create page
    page = Page(
        source_path=virtual_path,
        _raw_content="",
        metadata=metadata,
    )

    # Mark as virtual page (attribute, not just metadata)
    page._virtual = True

    # Set site reference BEFORE output_path for correct URL computation
    page._site = site

    # Set output path
    page.output_path = output_path

    # Set language if provided
    if spec.lang:
        page.lang = spec.lang

    # Claim URL in registry
    if registry_owner:
        claim_url_gracefully(
            site=site,
            page=page,
            url_strategy=url_strategy,
            owner=registry_owner,
            priority=registry_priority,
        )

    return page


def claim_url_gracefully(
    site: Site,
    page: Page,
    url_strategy: URLStrategy,
    owner: str,
    priority: int,
) -> bool:
    """
    Claim URL in registry with graceful error handling.

    This consolidates the common URL claim pattern used across orchestrators.
    Failures are logged but don't prevent page creation (graceful degradation).

    Args:
        site: Site instance with url_registry
        page: Page to claim URL for
        url_strategy: URLStrategy for URL computation
        owner: Owner name (e.g., "taxonomy", "section_index")
        priority: Claim priority (lower = higher priority)

    Returns:
        True if claim succeeded, False if failed or no registry

    Example:
        >>> success = claim_url_gracefully(site, page, url_strategy, "taxonomy", 40)
    """
    if not hasattr(site, "url_registry") or not site.url_registry:
        return False

    if not page.output_path:
        return False

    try:
        url = url_strategy.url_from_output_path(page.output_path, site)
        source = str(page.source_path)
        site.url_registry.claim(
            url=url,
            owner=owner,
            source=source,
            priority=priority,
        )
        return True
    except Exception as e:
        # Log at debug level - this is graceful degradation, not an error
        logger.debug(
            "url_claim_failed",
            url=str(page.output_path),
            owner=owner,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False


def create_tag_page(
    site: Site,
    url_strategy: URLStrategy,
    tag_slug: str,
    tag_name: str,
    posts: list[Any],
    paginator: Any,
    page_num: int,
    lang: str | None = None,
) -> Page:
    """
    Create a tag listing page with pagination.

    Convenience function specifically for tag pages.

    Args:
        site: Site instance
        url_strategy: URLStrategy for path computation
        tag_slug: URL-safe tag slug
        tag_name: Display name for tag
        posts: List of posts with this tag
        paginator: Paginator instance
        page_num: Current page number
        lang: Optional language code

    Returns:
        Virtual tag page
    """
    spec = VirtualPageSpec(
        title=f"Posts tagged '{tag_name}'",
        template="tag.html",
        page_type="tag",
        metadata={
            "_tag": tag_name,
            "_tag_slug": tag_slug,
            "_taxonomy_term": tag_slug,
            "_posts": posts,
            "_paginator": paginator,
            "_page_num": page_num,
        },
        lang=lang,
    )

    output_path = url_strategy.compute_tag_output_path(
        tag_slug=tag_slug,
        page_num=page_num,
        site=site,
    )

    return create_virtual_page(
        site=site,
        url_strategy=url_strategy,
        spec=spec,
        path_segments=("tags", tag_slug, f"page_{page_num}"),
        output_path=output_path,
        registry_owner="taxonomy",
        registry_priority=40,
    )


def create_tag_index_page(
    site: Site,
    url_strategy: URLStrategy,
    tags: dict[str, Any],
    lang: str | None = None,
) -> Page:
    """
    Create the main tags index page.

    Args:
        site: Site instance
        url_strategy: URLStrategy for path computation
        tags: Dictionary of tag data
        lang: Optional language code

    Returns:
        Virtual tag index page
    """
    spec = VirtualPageSpec(
        title="All Tags",
        template="tags.html",
        page_type="tag-index",
        metadata={"_tags": tags},
        lang=lang,
    )

    output_path = url_strategy.compute_tag_index_output_path(site)

    return create_virtual_page(
        site=site,
        url_strategy=url_strategy,
        spec=spec,
        path_segments=("tags",),
        output_path=output_path,
        registry_owner="taxonomy",
        registry_priority=40,
    )
