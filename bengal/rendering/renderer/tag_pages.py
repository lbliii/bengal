"""
Tag-page membership and generated-tag context for Renderer.

Snapshot/instance caches are language-blind. When taxonomies are per-language
(i18n enabled and share_taxonomies=False), the cache path returns empty so
``_posts`` on the generated tag page stays authoritative (#354).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike

logger = get_logger(__name__)


def compute_per_language_taxonomies(renderer: Any) -> bool:
    """Whether taxonomies are per-language (i18n enabled, taxonomies not shared).

    In that mode tag membership is language-narrowed per generated tag page (stored
    in its ``_posts`` metadata), so the language-blind tag-page cache must not be used.
    """
    # Read the two config keys directly (mirrors get_i18n_config's strategy /
    # share_taxonomies semantics) rather than importing it: rendering (layer 6) must
    # not depend on orchestration (layer 7). Use .get chains (Config + dict) and
    # isinstance guards so mock site.config objects do not hit bool(MagicMock) on 3.14t.
    config = getattr(renderer.site, "config", None)
    if config is None or not hasattr(config, "get"):
        return False
    i18n_raw = config.get("i18n", {}) or {}
    if not hasattr(i18n_raw, "get"):
        return False
    strategy_raw = i18n_raw.get("strategy")
    strategy = strategy_raw if isinstance(strategy_raw, str) else "none"
    share_raw = i18n_raw.get("share_taxonomies", False)
    share_taxonomies = share_raw if isinstance(share_raw, bool) else False
    return strategy != "none" and not share_taxonomies


def get_resolved_tag_pages(renderer: Any, tag_slug: str) -> list[PageLike]:
    """
    Get resolved and filtered pages for a tag (cached).

    Fast path (lock-free): If snapshot has pre-computed tag_pages,
    returns them directly — no lock needed.

    Fallback path: Cache is built once per Renderer instance (per build).
    Uses double-checked locking for thread-safe initialization.
    """
    # Per-language taxonomies (i18n enabled + share_taxonomies=False): the snapshot
    # and instance caches below are language-blind (built from the full cross-language
    # site.taxonomies), so returning them here would leak other languages' posts into a
    # per-language tag page. Defer to the per-page _posts path in
    # _add_tag_generated_page_context, which carries the language-narrowed membership
    # (#354 — before the snapshot fix, the now-live fast path masked this by returning []).
    if renderer._per_language_taxonomies is None:
        renderer._per_language_taxonomies = renderer._compute_per_language_taxonomies()
    if renderer._per_language_taxonomies:
        return []

    # Fast path: use pre-computed snapshot data (lock-free). The snapshot
    # supplies the filtered, ordered tag membership without taking a lock;
    # we resolve each PageSnapshot back to its live Page via the path map so
    # the rendered output (which reads Page.content == parsed HTML, not the
    # snapshot's raw-markdown .content) is byte-identical to the slow path.
    snapshot = getattr(renderer.build_context, "snapshot", None) if renderer.build_context else None
    if snapshot is not None and snapshot.taxonomy.tag_pages:
        tag_snapshots = snapshot.taxonomy.tag_pages.get(tag_slug, ())
        if not tag_snapshots:
            return []
        str_page_map = renderer.site.get_page_path_map()
        resolved: list[PageLike] = []
        for tax_page in tag_snapshots:
            live_page = str_page_map.get(str(tax_page.source_path))
            resolved.append(live_page if live_page is not None else tax_page)
        return resolved

    # Check instance cache
    if renderer._tag_pages_cache is not None:
        return renderer._tag_pages_cache.get(tag_slug, [])

    # Slow path: build cache under lock (thread-safe initialization)
    with renderer._cache_lock:
        # Double-check after acquiring lock
        if renderer._tag_pages_cache is None:
            renderer._tag_pages_cache = renderer._build_all_tag_pages_cache()

    return renderer._tag_pages_cache.get(tag_slug, [])


def build_all_tag_pages_cache(renderer: Any) -> dict[str, list[PageLike]]:
    """
    Build complete cache of resolved tag pages.

    Filters and resolves all tag pages once per build:
    - Excludes generated pages
    - Excludes API/CLI documentation pages
    - Resolves stale Page references via site's page path map
    """
    cache: dict[str, list[PageLike]] = {}
    str_page_map = renderer.site.get_page_path_map()
    tags_data = renderer.site.taxonomies.get("tags", {})

    for tag_slug, tag_info in tags_data.items():
        resolved_pages: list[PageLike] = []

        for tax_page in tag_info.get("pages", []):
            resolved_page = None
            if hasattr(tax_page, "source_path"):
                # Use cached string-keyed map for O(1) lookup
                resolved_page = str_page_map.get(str(tax_page.source_path))

            page_to_check = resolved_page if resolved_page else tax_page

            if page_to_check and hasattr(page_to_check, "source_path"):
                source_str = str(page_to_check.source_path)
                # Apply filtering rules: exclude generated, API, and CLI pages
                if (
                    not page_to_check.metadata.get("_generated")
                    and "content/api" not in source_str
                    and "content/cli" not in source_str
                ):
                    resolved_pages.append(page_to_check)

        cache[tag_slug] = resolved_pages

    logger.debug(
        "tag_pages_cache_built",
        total_tags=len(cache),
        total_pages=sum(len(pages) for pages in cache.values()),
    )

    return cache


def add_tag_generated_page_context(renderer: Any, page: PageLike, context: dict[str, Any]) -> None:
    """Add context for an individual tag page."""
    tag_name = page.metadata.get("_tag")
    tag_slug = page.metadata.get("_tag_slug")
    page_num = int(page.metadata.get("_page_num") or 1)

    # PERF: Use cached resolved tag pages instead of filtering on each render.
    # Cache is built once per Renderer instance and reused across all tag page renders.
    # Complexity: O(T × P) once at cache build, then O(1) lookup per render.
    all_posts = renderer._get_resolved_tag_pages(tag_slug) if tag_slug else []

    # Fallback: Try to resolve from stored metadata if cache yielded nothing
    if not all_posts and page.metadata is not None:
        stored_posts = page.metadata.get("_posts", [])
        if stored_posts:
            str_page_map = renderer.site.get_page_path_map()
            for stored_item in stored_posts:
                resolved_page = None
                if hasattr(stored_item, "source_path"):
                    resolved_page = str_page_map.get(str(stored_item.source_path))
                    if resolved_page:
                        all_posts.append(resolved_page)
                    else:
                        all_posts.append(stored_item)
                elif isinstance(stored_item, str):
                    resolved_page = str_page_map.get(stored_item)
                    if resolved_page:
                        all_posts.append(resolved_page)

    page_metadata = page.metadata if page.metadata is not None else {}
    paginator = page_metadata.get("_paginator")

    if all_posts:
        total_posts_count = len(all_posts)

        if paginator and hasattr(paginator, "per_page"):
            from bengal.utils.pagination import Paginator

            per_page = paginator.per_page
            fresh_paginator = Paginator(all_posts, per_page=per_page)
            try:
                posts = fresh_paginator.page(page_num)
                pagination = fresh_paginator.page_context(page_num, f"/tags/{tag_slug}/")
            except ValueError:
                posts = all_posts
                pagination = renderer._default_pagination(f"/tags/{tag_slug}/")
        else:
            posts = all_posts
            pagination = renderer._default_pagination(f"/tags/{tag_slug}/")
    elif paginator and hasattr(paginator, "items") and paginator.items:
        resolved_items = []
        str_page_map = renderer.site.get_page_path_map()
        for item in paginator.items:
            if hasattr(item, "source_path"):
                resolved = str_page_map.get(str(item.source_path))
                if resolved:
                    resolved_items.append(resolved)
                elif item and hasattr(item, "title"):
                    resolved_items.append(item)

        if resolved_items:
            all_posts = resolved_items
            from bengal.utils.pagination import Paginator

            fresh_paginator = Paginator(all_posts, per_page=paginator.per_page)
            posts = fresh_paginator.page(page_num)
            total_posts_count = len(all_posts)
            pagination = fresh_paginator.page_context(page_num, f"/tags/{tag_slug}/")
        else:
            posts = []
            total_posts_count = 0
            pagination = renderer._default_pagination(f"/tags/{tag_slug}/")
    else:
        posts = []
        total_posts_count = 0
        pagination = renderer._default_pagination(f"/tags/{tag_slug}/")

    logger.debug(
        "tag_page_context",
        tag_slug=tag_slug,
        posts_count=len(posts) if posts else 0,
        total_posts=total_posts_count,
        all_posts_count=len(all_posts) if all_posts else 0,
        page_num=page_num,
    )

    safe_pagination = renderer._coerce_pagination_ints(pagination)

    context.update(
        {
            "tag": tag_name,
            "tag_slug": tag_slug,
            "posts": posts,
            "total_posts": total_posts_count,
            **safe_pagination,
        }
    )


def add_tag_index_generated_page_context(
    renderer: Any, page: PageLike, context: dict[str, Any]
) -> None:
    """Add context for the tag index page."""
    tags = page.metadata.get("_tags", {})

    tags_list = [
        {
            "name": data["name"],
            "slug": data["slug"],
            "href": f"/tags/{data['slug']}/",
            "count": len(data["pages"]),
            "pages": data["pages"],
        }
        for data in tags.values()
    ]
    tags_list.sort(key=lambda t: (-t["count"], t["name"].lower()))

    context.update(
        {
            "tags": tags_list,
            "total_tags": len(tags_list),
        }
    )
