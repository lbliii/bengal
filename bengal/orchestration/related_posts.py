"""
Related Posts orchestration for Bengal SSG.

Builds a pre-computed index of related posts during the build phase, enabling
O(1) template access at render time. Uses tag-based matching to identify
content relationships.

Algorithm (vectorized):
1. Build inverted index: tag_slug → frozenset of eligible page ids  [O(n·t)]
2. Pre-compute exclusion set of page ids (generated, home, indices) [O(n)]
3. For each page, use Counter over tag sets to score co-occurrences  [O(t·k)]
   where k = avg pages per tag (much less than n for real sites)
4. Extract top-N from Counter.most_common()                         [O(k·log(limit))]

Total complexity: O(n·t·k_avg) — linear in n when tag popularity is bounded.
Worst-case (single tag shared by all pages): O(n²), but this is pathological.

Render-time: O(1) - pre-computed list on page.related_posts

Parallel processing shards page list across threads for true parallelism
on Python 3.14t (free-threaded, no GIL). Each shard operates on read-only
shared data (tag index, exclusion set) with zero contention.

Usage in Templates:
{% for post in page.related_posts %}
  <a href="{{ post.href }}">{{ post.title }}</a>
{% endfor %}

Related Modules:
bengal.core.page: Page model with related_posts attribute
bengal.orchestration.build: Calls this during Phase 10

See Also:
bengal.orchestration.taxonomy: Provides taxonomy index used for matching

"""

from __future__ import annotations

import concurrent.futures
from collections import Counter
from typing import TYPE_CHECKING, Any

from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

MIN_PAGES_FOR_PARALLEL = 50

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site


class RelatedPostsOrchestrator:
    """
    Builds related posts relationships during the build phase.

    Uses a vectorized inverted-index algorithm with pre-computed exclusion sets.
    All expensive property access (metadata, kind, path) is resolved once during
    index construction, not inside the per-page scoring loop.

    Complexity:
        Build: O(n·t·k_avg) where n=pages, t=avg tags, k_avg=avg pages per tag
        Access: O(1) via page.related_posts attribute

    Thread Safety:
        Parallel mode shards pages across threads. Each thread reads from
        shared immutable data (tag index, exclusion set, id→page map).
        No locks needed — pure functional scoring.
    """

    def __init__(self, site: Site):
        self.site = site

    def build_index(
        self, limit: int = 5, parallel: bool = True, affected_pages: list[Page] | None = None
    ) -> None:
        """
        Compute related posts for pages using tag-based matching.

        Builds shared data structures once, then scores pages independently
        (parallelizable with zero contention on 3.14t).
        """
        logger.info(
            "related_posts_build_start",
            total_pages=len(self.site.pages),
            incremental=affected_pages is not None,
        )

        if not hasattr(self.site, "taxonomies"):
            self._set_empty_related_posts()
            logger.debug("related_posts_skipped", reason="no_taxonomies")
            return

        tags_dict = self.site.taxonomies.get("tags", {})
        if not tags_dict:
            self._set_empty_related_posts()
            logger.debug("related_posts_skipped", reason="no_tags")
            return

        # Phase 1: Build shared data structures (O(n) — done once)
        page_tags_map = self._build_page_tags_map()
        excluded_ids = self._build_exclusion_set()
        id_to_page = {id(p): p for p in self.site.pages}
        tag_to_page_ids = self._build_tag_index(tags_dict, excluded_ids)

        # Determine which pages to process
        if affected_pages is not None:
            pages_to_process = [p for p in affected_pages if id(p) not in excluded_ids]
        else:
            pages_to_process = list(self.site.regular_pages)

        # Phase 2: Score pages (embarrassingly parallel)
        if parallel and len(pages_to_process) > MIN_PAGES_FOR_PARALLEL:
            pages_with_related = self._build_parallel(
                pages_to_process, page_tags_map, tag_to_page_ids, id_to_page, limit
            )
        else:
            pages_with_related = self._build_sequential(
                pages_to_process, page_tags_map, tag_to_page_ids, id_to_page, limit
            )

        # Set empty for excluded pages
        for page in self.site.pages:
            if id(page) in excluded_ids:
                page.related_posts = []

        logger.info(
            "related_posts_build_complete",
            pages_with_related=pages_with_related,
            total_pages=len(self.site.pages),
            affected_pages=len(pages_to_process) if affected_pages else None,
            mode="parallel"
            if parallel and len(pages_to_process) > MIN_PAGES_FOR_PARALLEL
            else "sequential",
        )

    def _build_exclusion_set(self) -> frozenset[int]:
        """
        Pre-compute ids of pages to exclude from related posts.

        Resolves _generated, kind, and path checks ONCE instead of inside
        the inner scoring loop. Uses _raw_metadata for O(1) dict access
        (avoids the metadata property's cascade/relative_to overhead).
        """
        excluded = set()
        for page in self.site.pages:
            if page._raw_metadata.get("_generated"):
                excluded.add(id(page))
                continue

            path = getattr(page, "_path", "") or getattr(page, "href", "") or ""
            path_str = str(path).rstrip("/") if path else ""
            if path_str in ("", "/") or str(path) in ("/", "/index.html", ""):
                excluded.add(id(page))
                continue

            if getattr(page, "kind", None) == "index":
                excluded.add(id(page))

        return frozenset(excluded)

    def _build_tag_index(
        self,
        tags_dict: dict[str, dict[str, Any]],
        excluded_ids: frozenset[int],
    ) -> dict[str, frozenset[int]]:
        """
        Build inverted index: tag_slug → frozenset of eligible page ids.

        Uses frozenset for immutable sharing across threads (no copying needed).
        Excludes ineligible pages at index build time, not scoring time.
        """
        tag_to_page_ids: dict[str, frozenset[int]] = {}
        for tag_slug, tag_data in tags_dict.items():
            pages_with_tag = tag_data.get("pages", [])
            eligible = frozenset(id(p) for p in pages_with_tag if id(p) not in excluded_ids)
            if eligible:
                tag_to_page_ids[tag_slug] = eligible
        return tag_to_page_ids

    def _build_sequential(
        self,
        pages: list[Page],
        page_tags_map: dict[Page, set[str]],
        tag_to_page_ids: dict[str, frozenset[int]],
        id_to_page: dict[int, Page],
        limit: int,
    ) -> int:
        pages_with_related = 0
        for page in pages:
            related = self._score_page(page, page_tags_map, tag_to_page_ids, id_to_page, limit)
            page.related_posts = related
            if related:
                pages_with_related += 1
        return pages_with_related

    def _build_parallel(
        self,
        pages: list[Page],
        page_tags_map: dict[Page, set[str]],
        tag_to_page_ids: dict[str, frozenset[int]],
        id_to_page: dict[int, Page],
        limit: int,
    ) -> int:
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

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_page = {
                executor.submit(
                    self._score_page, page, page_tags_map, tag_to_page_ids, id_to_page, limit
                ): page
                for page in pages
            }

            for future in concurrent.futures.as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    related = future.result()
                    page.related_posts = related
                    if related:
                        pages_with_related += 1
                except Exception as e:
                    logger.error(
                        "related_posts_computation_failed",
                        page=str(page.source_path),
                        error=str(e),
                    )
                    page.related_posts = []

        return pages_with_related

    def _set_empty_related_posts(self) -> None:
        for page in self.site.pages:
            page.related_posts = []

    def _build_page_tags_map(self) -> dict[Page, set[str]]:
        """
        Build mapping of page → set of tag slugs.

        Returns:
            Dictionary mapping Page to set of tag slugs
        """
        page_tags: dict[Page, set[str]] = {}
        for page in self.site.pages:
            if hasattr(page, "tags") and page.tags:
                page_tags[page] = {
                    str(tag).lower().replace(" ", "-") for tag in page.tags if tag is not None
                }
            else:
                page_tags[page] = set()
        return page_tags

    @staticmethod
    def _score_page(
        page: Page,
        page_tags_map: dict[Page, set[str]],
        tag_to_page_ids: dict[str, frozenset[int]],
        id_to_page: dict[int, Page],
        limit: int,
    ) -> list[Page]:
        """
        Score related pages for a single page using Counter over tag sets.

        Pure function: reads only from immutable shared data structures.
        Safe for concurrent execution without locks on 3.14t.

        Counter.update() with frozensets is C-optimized — each tag's page set
        is counted in a single C-level pass, no Python-level per-element loop.
        """
        tag_slugs = page_tags_map.get(page, set())
        if not tag_slugs:
            return []

        page_id = id(page)
        scores: Counter[int] = Counter()

        for tag_slug in tag_slugs:
            page_ids = tag_to_page_ids.get(tag_slug)
            if page_ids is not None:
                scores.update(page_ids)

        # Remove self-reference
        scores.pop(page_id, None)

        if not scores:
            return []

        return [id_to_page[pid] for pid, _ in scores.most_common(limit) if pid in id_to_page]
