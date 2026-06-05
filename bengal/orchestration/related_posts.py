"""
Related Posts orchestration for Bengal SSG.

Builds a pre-computed index of related posts during the build phase, enabling
O(1) template access at render time. Uses tag-based matching to identify
content relationships.

Algorithm:
For each page with tags, finds other pages that share tags and scores
them by the number of shared tags. Higher scores indicate stronger
relevance. The top N related posts are stored on each page.

Performance:
Build-time: O(n·t) where n=pages and t=average tags per page
Render-time: O(1) - pre-computed list on page.related_posts

This moves expensive computation from render-time O(n²) to build-time,
resulting in significant performance improvement for template access.

Parallel processing is used for sites with 100+ pages to avoid thread
pool overhead on smaller sites.

Usage in Templates:
{% for post in page.related_posts %}
  <a href="{{ post.href }}">{{ post.title }}</a>
{% endfor %}

Related Modules:
bengal.core.page: PageLike model with related_posts attribute
bengal.orchestration.build: Calls this during Phase 10

See Also:
bengal.orchestration.taxonomy: Provides taxonomy index used for matching

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.text import normalize_taxonomy_slug

logger = get_logger(__name__)

# Note: MIN_PAGES_FOR_PARALLEL is deprecated in favor of should_parallelize()
# Kept for backwards compatibility if accessed directly
MIN_PAGES_FOR_PARALLEL = 50

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.core.site import Site
    from bengal.protocols.core import PageLike


class RelatedPostsOrchestrator:
    """
    Builds related posts relationships during the build phase.

    Uses the taxonomy index for efficient tag-based matching. For each page,
    finds other pages with overlapping tags and scores by shared tag count.

    Complexity:
        Build: O(n·t) where n=pages, t=average tags per page (typically 2-5)
        Access: O(1) via page.related_posts attribute

    Creation:
        Direct instantiation: RelatedPostsOrchestrator(site)
            - Created by BuildOrchestrator during build
            - Requires Site instance with taxonomies populated

    Attributes:
        site: Site instance containing pages and taxonomies

    Relationships:
        - Uses: site.taxonomies['tags'] for tag-to-page mapping
        - Updates: page.related_posts for each processed page
        - Used by: BuildOrchestrator for Phase 10 (related posts)

    Thread Safety:
        Supports parallel processing for sites with 100+ pages.
        Each page's computation is independent and thread-safe.

    Example:
        orchestrator = RelatedPostsOrchestrator(site)
        orchestrator.build_index(limit=5, parallel=True)
        # page.related_posts now contains list of related Page objects

    """

    def __init__(self, site: Site):
        """
        Initialize related posts orchestrator.

        Args:
            site: Site instance
        """
        self.site = site

    def build_index(
        self,
        limit: int = 5,
        parallel: bool = True,
        affected_pages: Sequence[PageLike] | None = None,
    ) -> None:
        """
        Compute related posts for pages using tag-based matching.

        This is called once during the build phase. Each page gets a
        pre-computed list of related pages stored in page.related_posts.

        Args:
            limit: Maximum related posts per page (default: 5)
            parallel: Whether to use parallel processing (default: True)
            affected_pages: List of pages whose related posts should be recomputed.
                          If None, computes for all pages (full build).
                          If provided, only updates affected pages (incremental).
        """
        logger.info(
            "related_posts_build_start",
            total_pages=len(self.site.pages),
            incremental=affected_pages is not None,
        )

        # Skip if no taxonomies built yet
        if not hasattr(self.site, "taxonomies"):
            self._set_empty_related_posts()
            logger.debug("related_posts_skipped", reason="no_taxonomies")
            return

        tags_dict = self.site.taxonomies.get("tags", {})
        if not tags_dict:
            # No tags in site - nothing to relate
            self._set_empty_related_posts()
            logger.debug("related_posts_skipped", reason="no_tags")
            return

        # Build inverted index: page_id -> set of tag slugs
        # This is O(n) where n = number of pages
        page_tags_map = self._build_page_tags_map()

        # Determine which pages to process
        if affected_pages is not None:
            # Incremental: only process affected pages (filter out generated)
            pages_to_process = [p for p in affected_pages if not p.metadata.get("_generated")]
        else:
            # Full build: process all regular pages (use cached property)
            pages_to_process = list(self.site.regular_pages)

        # Use parallel processing for larger sites to avoid thread overhead
        # Related posts computation is CPU-bound (tag matching, scoring)
        # parallel is now always a boolean (computed from force_sequential in phase_related_posts)
        # so we can use it directly
        # Pre-compute the valid-candidate index ONCE (#350 S9). The candidate
        # filters (skip generated / home / section-index pages) and the
        # tie-break sort key are intrinsic to the candidate, so we apply them a
        # single time here instead of re-deriving them for every (page, tag,
        # candidate) in the scoring loop — turning the hot path from O(P·T·N)
        # string/getattr work into O(P·T·N) integer increments. Output unchanged.
        candidates_by_tag, sort_keys = self._build_candidate_index(tags_dict)

        if parallel:
            pages_with_related = self._build_parallel(
                pages_to_process, page_tags_map, candidates_by_tag, sort_keys, limit
            )
        else:
            pages_with_related = self._build_sequential(
                pages_to_process, page_tags_map, candidates_by_tag, sort_keys, limit
            )

        logger.info(
            "related_posts_build_complete",
            pages_with_related=pages_with_related,
            total_pages=len(self.site.pages),
            affected_pages=len(pages_to_process) if affected_pages else None,
            mode="parallel" if parallel else "sequential",
        )

    def _build_sequential(
        self,
        pages: Sequence[PageLike],
        page_tags_map: dict[PageLike, set[str]],
        candidates_by_tag: dict[str, list[PageLike]],
        sort_keys: dict[PageLike, str],
        limit: int,
    ) -> int:
        """
        Build related posts sequentially (original implementation).

        Args:
            pages: List of pages to process
            page_tags_map: Pre-built page -> tags mapping
            candidates_by_tag: Pre-filtered valid candidates per tag (#350 S9)
            sort_keys: Pre-computed stable tie-break key per candidate
            limit: Maximum related posts per page

        Returns:
            Number of pages with related posts found
        """
        pages_with_related = 0

        for page in pages:
            page.related_posts = self._find_related_posts(
                page, page_tags_map, candidates_by_tag, sort_keys, limit
            )
            if page.related_posts:
                pages_with_related += 1

        # Single finalization pass: clear generated pages' related_posts
        # (computed pages already set above, only generated pages need clearing)
        for page in self.site.pages:
            if page.metadata.get("_generated"):
                page.related_posts = []

        return pages_with_related

    def _build_parallel(
        self,
        pages: Sequence[PageLike],
        page_tags_map: dict[PageLike, set[str]],
        candidates_by_tag: dict[str, list[PageLike]],
        sort_keys: dict[PageLike, str],
        limit: int,
    ) -> int:
        """
        Build related posts in parallel using ThreadPoolExecutor.

        Each page's related posts computation is independent, making this
        perfectly parallelizable. On Python 3.14t (free-threaded), this
        achieves true parallelism without GIL contention.

        Performance:
            - Python 3.13 (GIL): 2-3x faster
            - Python 3.14t (no GIL): 6-8x faster

        Args:
            pages: List of pages to process
            page_tags_map: Pre-built page -> tags mapping
            tags_dict: Taxonomy tags dictionary
            limit: Maximum related posts per page

        Returns:
            Number of pages with related posts found
        """
        # Get optimal workers based on workload (CPU-bound tag matching)
        # Access from build section (supports both Config and dict)
        config = self.site.config
        if hasattr(config, "build"):
            max_workers_override = config.build.max_workers
        else:
            build_section = config.get("build", {})
            max_workers_override = (
                build_section.get("max_workers")
                if isinstance(build_section, dict)
                else config.get("max_workers")
            )

        max_workers = get_optimal_workers(
            len(pages),
            workload_type=WorkloadType.CPU_BOUND,
            config_override=max_workers_override,
        )

        pages_with_related = 0

        # Use WorkScope for safe shutdown on timeout/error
        from bengal.utils.concurrency.work_scope import WorkScope

        def _find_related_for_page(page):
            try:
                related = self._find_related_posts(
                    page, page_tags_map, candidates_by_tag, sort_keys, limit
                )
            except Exception as e:
                e.__page_source_path__ = page.source_path  # type: ignore[attr-defined]
                raise
            return page, related

        with WorkScope("related-posts", max_workers=max_workers) as scope:
            results = scope.map(_find_related_for_page, pages)

        for r in results:
            if r.error:
                page_path = getattr(r.error, "__page_source_path__", None)
                logger.error(
                    "related_posts_computation_failed",
                    page=str(page_path) if page_path is not None else None,
                    error=str(r.error),
                )
            elif r.value is not None:
                page, related_posts = r.value
                page.related_posts = related_posts
                if related_posts:
                    pages_with_related += 1

        # Single finalization pass: clear generated pages' related_posts
        for page in self.site.pages:
            if page.metadata.get("_generated"):
                page.related_posts = []

        return pages_with_related

    def _set_empty_related_posts(self) -> None:
        """Set empty related_posts list for all pages."""
        for page in self.site.pages:
            page.related_posts = []

    def _build_page_tags_map(self) -> dict[PageLike, set[str]]:
        """
        Build mapping of page -> set of tag slugs.

        This creates an efficient lookup structure for checking tag overlap.
        Now uses pages directly as keys (hashable based on source_path).

        Returns:
            Dictionary mapping Page to set of tag slugs
        """
        page_tags = {}
        for page in self.site.pages:
            if hasattr(page, "tags") and page.tags:
                # Convert tags to slugs for consistent matching (same as taxonomy)
                # Filter out None tags (YAML parses 'null' as None)
                page_tags[page] = {
                    normalize_taxonomy_slug(tag) for tag in page.tags if tag is not None
                }
            else:
                page_tags[page] = set()

        return page_tags

    @staticmethod
    def _is_valid_related_candidate(cand: PageLike) -> bool:
        """
        Whether a page may appear as a related post.

        Candidate-intrinsic filters (no dependency on the page being scored):
        skip generated pages (tag indexes, archives), the home page, and section
        index pages. Replicates the per-candidate filter that used to run inside
        the scoring loop; applied once via :meth:`_build_candidate_index`.
        """
        if cand.metadata.get("_generated"):
            return False
        path = getattr(cand, "_path", "") or getattr(cand, "href", "") or ""
        path_str = str(path).rstrip("/") if path else ""
        if path_str in ("", "/") or str(path) in ("/", "/index.html", ""):
            return False  # Home page
        return getattr(cand, "kind", None) != "index"  # Section indices

    def _build_candidate_index(
        self,
        tags_dict: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, list[PageLike]], dict[PageLike, str]]:
        """
        Pre-compute valid related-post candidates per tag + stable tie-break keys.

        Built once per build (#350 S9). Returns:
        - ``candidates_by_tag``: tag slug -> pages with that tag that pass the
          candidate filter (generated/home/index removed), preserving order.
        - ``sort_keys``: candidate -> ``str(source_path|_path|href)`` for the
          deterministic tie-break, computed once instead of per sort.

        Because the filter and the key are candidate-intrinsic, doing this once
        produces the exact same related-post lists the per-page loop did.
        """
        candidates_by_tag: dict[str, list[PageLike]] = {}
        sort_keys: dict[PageLike, str] = {}
        validity: dict[PageLike, bool] = {}

        for tag_slug, tag_data in tags_dict.items():
            valid: list[PageLike] = []
            for cand in tag_data.get("pages", []):
                cached = validity.get(cand)
                if cached is None:
                    cached = self._is_valid_related_candidate(cand)
                    validity[cand] = cached
                    if cached:
                        ident = (
                            getattr(cand, "source_path", None)
                            or getattr(cand, "_path", None)
                            or getattr(cand, "href", "")
                        )
                        sort_keys[cand] = str(ident)
                if cached:
                    valid.append(cand)
            candidates_by_tag[tag_slug] = valid

        return candidates_by_tag, sort_keys

    def _find_related_posts(
        self,
        page: PageLike,
        page_tags_map: dict[PageLike, set[str]],
        candidates_by_tag: dict[str, list[PageLike]],
        sort_keys: dict[PageLike, str],
        limit: int,
    ) -> list[PageLike]:
        """
        Find related posts for a single page using tag overlap scoring.

        Algorithm (#350 S9): for each tag on the page, walk the pre-filtered
        candidate list for that tag and count shared tags; return the top N by
        score, ties broken by the pre-computed stable source-path key. The
        per-candidate filtering and key derivation are hoisted into
        :meth:`_build_candidate_index`, so this loop is pure integer scoring.

        Args:
            page: PageLike to find related posts for
            page_tags_map: Pre-built page -> tags mapping
            candidates_by_tag: Pre-filtered valid candidates per tag
            sort_keys: Pre-computed stable tie-break key per candidate
            limit: Maximum related posts to return

        Returns:
            List of related pages sorted by relevance (most shared tags first)
        """
        page_tag_slugs = page_tags_map.get(page, set())
        if not page_tag_slugs:
            # Page has no tags - no related posts
            return []

        # Count shared tags against the pre-filtered candidate lists.
        scored: dict[PageLike, int] = {}
        for tag_slug in page_tag_slugs:
            for cand in candidates_by_tag.get(tag_slug, ()):
                if cand == page:
                    continue  # skip self
                scored[cand] = scored.get(cand, 0) + 1

        if not scored:
            return []

        # Sort by score (descending), ties broken by the stable source-path key
        # so related posts — and every page that renders them — are reproducible
        # regardless of thread scheduling.
        ordered = sorted(scored.items(), key=lambda kv: (-kv[1], sort_keys[kv[0]]))
        return [related_page for related_page, _ in ordered[:limit]]
