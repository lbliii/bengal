"""Page/section references, cascades, output paths, and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.page_site import set_page_site
from bengal.core.section.utils import get_page_section, set_page_section
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SectionLike, SiteLike

logger = get_logger("bengal.orchestration.content")


def _setup_page_references(orchestrator: Any) -> None:
    """
    Set up page references for navigation (next, prev, parent, etc.).

    Sets _site and _section references on all pages. Must be called after
    content discovery and section registry building, but before cascade
    application.
    """
    for page in orchestrator.site.pages:
        set_page_site(page, orchestrator.site)

    for section in orchestrator.site.sections:
        section._site = orchestrator.site

        if section.index_page:
            set_page_section(section.index_page, section)

        for page in section.pages:
            set_page_section(page, section)

        orchestrator._setup_section_references(section)


def _setup_section_references(orchestrator: Any, section: SectionLike) -> None:
    """Recursively set up references for a section and its subsections."""
    for subsection in section.subsections:
        subsection._site = orchestrator.site

        if subsection.index_page:
            set_page_section(subsection.index_page, subsection)

        for page in subsection.pages:
            set_page_section(page, subsection)

        orchestrator._setup_section_references(subsection)


def _apply_cascades(orchestrator: Any) -> None:
    """
    Build cascade snapshot for view-based resolution.

    Section _index.md files can define metadata that automatically applies to all
    descendant pages. This allows setting common metadata at the section level
    rather than repeating it on every page.

    Cascade metadata is defined in a section's _index.md frontmatter:

    Example:
        ---
        title: "Products"
        cascade:
          type: "product"
          version: "2.0"
          show_price: true
        ---

    All pages under this section will inherit these values unless they
    define their own values (page values take precedence over cascaded values).

    Implementation:
        Builds immutable CascadeSnapshot with pre-merged cascade per section.
        Page.metadata property returns CascadeView that resolves frontmatter + cascade.
        No mutation of page.metadata needed - resolution happens on access.
    """
    # Build immutable cascade snapshot with pre-merged data for O(1) resolution
    # Page.metadata property returns CascadeView using this snapshot
    orchestrator.site.build_cascade_snapshot()
    logger.debug(
        "cascade_snapshot_built",
        sections_with_cascade=len(orchestrator.site.cascade),
    )


def _set_output_paths(orchestrator: Any) -> None:
    """Set output paths for all discovered pages."""
    from bengal.utils.paths.url_strategy import URLStrategy

    for page in orchestrator.site.pages:
        if page.output_path:
            continue

        output_path = URLStrategy.compute_regular_page_output_path(
            page, cast("SiteLike", orchestrator.site)
        )
        page.output_path = output_path

        if getattr(orchestrator.site, "url_registry", None):
            # Pre-bind so the best-effort diagnostic handler can always
            # reference these, even if url_from_output_path() raises before
            # they are assigned. Preserves the original silent swallow; we
            # only add a breadcrumb (no happy-path behavior change).
            url = None
            source = None
            try:
                url = URLStrategy.url_from_output_path(
                    output_path, cast("SiteLike", orchestrator.site)
                )
                source = str(getattr(page, "source_path", page.title))
                version = getattr(page, "version", None)
                lang = getattr(page, "lang", None)
                orchestrator.site.url_registry.claim(
                    url=url,
                    owner="content",
                    source=source,
                    priority=100,
                    version=version,
                    lang=lang,
                )
            except Exception as e:  # claim is best-effort; URLCollisionValidator backstops
                # Detection is not lost: URLCollisionValidator recomputes
                # collisions from site.pages post-hoc. Leave a breadcrumb so
                # claim-time failures are diagnosable rather than invisible.
                logger.debug(
                    "url_claim_failed",
                    url=url,
                    owner="content",
                    source=source,
                    error=str(e),
                    error_type=type(e).__name__,
                )


def _validate_page_section_references(orchestrator: Any) -> None:
    """
    Validate that pages in sections have correct _section references.

    Logs warnings for pages that are in a section's pages list but have
    _section = None, which would cause navigation to fall back to flat mode.
    """
    pages_without_section: list[tuple[PageLike, SectionLike]] = []

    for section in orchestrator.site.sections:
        pages_without_section.extend(
            (page, section) for page in section.pages if get_page_section(page) is None
        )
        orchestrator._validate_subsection_references(section, pages_without_section)

    if pages_without_section:
        sample_pages = [(str(p.source_path), s.name) for p, s in pages_without_section[:5]]
        emit_diagnostic(
            orchestrator.site,
            "warning",
            "pages_missing_section_reference",
            count=len(pages_without_section),
            samples=sample_pages,
            note="These pages are in sections but have _section=None, navigation may be flat",
        )


def _validate_subsection_references(
    orchestrator: Any,
    section: SectionLike,
    pages_without_section: list[tuple[PageLike, SectionLike]],
) -> None:
    """Recursively validate page-section references in subsections."""
    for subsection in section.subsections:
        pages_without_section.extend(
            (page, subsection) for page in subsection.pages if get_page_section(page) is None
        )
        orchestrator._validate_subsection_references(subsection, pages_without_section)


def _check_weight_metadata(orchestrator: Any) -> None:
    """
    Check for documentation pages without weight metadata.

    Weight is important for sequential content like docs and tutorials
    to ensure correct navigation order. This logs info (not a warning)
    to educate users about weight metadata.
    """
    doc_types = {"doc", "tutorial", "autodoc-python", "autodoc-cli", "changelog"}

    missing_weight_pages = []
    for page in orchestrator.site.pages:
        content_type = page.metadata.get("type")
        # Skip index pages (they don't need weight for navigation)
        if (
            content_type in doc_types
            and "weight" not in page.metadata
            and page.source_path.stem not in ("_index", "index")
        ):
            missing_weight_pages.append(page)

    if missing_weight_pages:
        # Log info (not warning - it's not an error, just helpful guidance)
        page_samples = [
            str(p.source_path.relative_to(orchestrator.site.root_path))
            for p in missing_weight_pages[:5]
        ]

        logger.info(
            "pages_without_weight",
            count=len(missing_weight_pages),
            content_types=list(doc_types),
            samples=page_samples[:5],  # Limit to 5 samples for brevity
        )
