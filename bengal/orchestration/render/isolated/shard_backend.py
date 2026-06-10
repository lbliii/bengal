"""COW-free shard-parallel render backend — issue #350, S13.4g / S14.

The Phase-2 backend that *materialized* the render-scaling prize. Unlike the Phase-1
``IsolatedRenderBackend`` (which forked a big parent and rendered the parent's shared,
mutable parsed pages -> copy-on-write tax -> measured regression), each shard worker here
**re-parses its OWN shard** (parse is ~0.8% of a build) and renders **its own pages**, so no
shared mutable page graph is read or written across the fork boundary. The only shared
read-set is the *immortalized* ``SiteSnapshot`` (refcount-free reads -> COW-free). On
render-heavy content this captures the separate-process ceiling the probe measured
(~1.75x over the already-parallel thread path, idle-box; cheap content loses to fork
overhead, so the gate is content-cost-aware).

Cold-build / CLI / CI only; never the dev loop or incremental. On ANY failure the caller
falls back to the in-process thread path, so the shard backend can never break a build.

Cross-shard rendered-CONTENT access (the plan's "one true blocker") is RESOLVED for fork
(S14): a worker renders its shard against body-free ``PageView``s for other pages, and a
template that embeds another page's rendered body (e.g. the related-posts card's
``post.content`` fallback for an excerpt-less sibling) resolves it via ``PageView.content``,
which reads the parent's ``{source_path: content}`` registry inherited by the worker through
fork copy-on-write (the parent already holds every parsed page — a lookup, not extra memory).
Byte-identical to the thread path on test-product/basic/taxonomy/navigation
(``tests/integration/test_shard_render_parity.py``). The registry is fork-only; spawn has no
COW inheritance, so the spawn backend stays deferred.

What this version does NOT yet do (tracked):
- Generated pages (tags/archives/pagination) are rendered in the *parent* (global aggregations
  the content-file sharder does not cover); sharding them is S13.4e. So the parallel-render win
  is the content-render fraction only (generated pages are ~23% of render on taxonomied sites).
- render_isolation stays OFF by default until the full S17 idle-box E2E A/B + crossover gate.
"""

from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .merge import merge_chunk_results
from .partition import discover_content_files, partition_content_files

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols.core import PageLike
    from bengal.snapshots.render_plan import RenderPlan
    from bengal.snapshots.types import SiteSnapshot

    from .transport import RenderChunkResult

__all__ = ["ShardRenderBackend"]


@dataclass
class _ShardForkState:
    """Parent-installed render world inherited by forked shard workers via COW."""

    plan: RenderPlan
    snapshot: SiteSnapshot  # immortalized before fork
    content_dir: Path
    output_dir: Path
    shards: list[list[Any]]  # list[list[ContentFile]] indexed by worker
    asset_ctx: Any
    quiet: bool


# Installed in the parent BEFORE the fork pool is created; inherited (not pickled) by every
# forked worker. ``None`` in the parent outside a shard render.
_SHARD_STATE: _ShardForkState | None = None


def _render_shard_worker(shard_index: int) -> RenderChunkResult:
    """Fork worker: reconstruct a WorkerSite, parse THIS shard, render its own pages.

    The proven S13.3c/d recipe: build an empty real ``Site`` from the plan, parse this
    worker's content files against it (so each page's ``_site`` is the worker site), merge
    the heterogeneous page list, reset process-globals + install the precomputed nav trees,
    then render. Bodies never leave this heap; only a picklable ``RenderChunkResult`` returns.
    """
    state = _SHARD_STATE
    if state is None:  # pragma: no cover - defensive; never happens under fork
        raise RuntimeError("shard fork state not installed in worker")

    from bengal.cache import directive_cache
    from bengal.core.nav_tree import NavTreeCache
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.render.isolated.shard_worker import parse_shard, render_shard
    from bengal.orchestration.render.isolated.worker_site import (
        build_worker_site,
        merge_shard_pages,
    )
    from bengal.utils.cache_registry import clear_all_caches

    plan = state.plan
    files = state.shards[shard_index]

    ws = build_worker_site(plan, shard_index=shard_index)
    ws.output_dir = state.output_dir
    worker_pages = parse_shard(files, ws, content_dir=state.content_dir, quiet=state.quiet)
    ws.pages = merge_shard_pages(plan.pages, worker_pages)

    # related_posts is a WHOLE-SITE computation the parent reduced into plan.related_index
    # (source_path -> ordered related source_paths). The worker's freshly-parsed pages have it
    # unset, so the template's fast path (page.related_posts) would render nothing — populate it
    # from the plan, resolving each related path to its body-free PageView (title/href/excerpt
    # are all the related-posts partial reads). Reproduces what RelatedPostsOrchestrator set.
    pv_by_path = plan.pages_by_path
    for p in worker_pages:
        related = plan.related_index.get(p.source_path)
        if related:
            p.related_posts = [pv_by_path[sp] for sp in related if sp in pv_by_path]

    # Per-worker process-global reset + precomputed nav-tree install (the lock-free fast path
    # never calls NavTree.build, which needs live Sections the worker does not have).
    clear_all_caches()
    directive_cache.clear_cache()
    directive_cache.configure_for_site(ws)
    NavTreeCache.invalidate()
    NavTreeCache.set_precomputed(dict(plan.navigation.nav_trees))

    ctx = BuildContext(site=ws, pages=list(worker_pages))
    ctx.snapshot = state.snapshot  # section tiles render from it (inherited, immortalized)
    return render_shard(
        list(worker_pages),
        ws,
        ctx,
        chunk_index=shard_index,
        asset_ctx=state.asset_ctx,
        quiet=state.quiet,
    )


class ShardRenderBackend:
    """Renders a cold build across COW-free re-parsing shard workers."""

    def __init__(self, site: Site) -> None:
        self.site = site

    def render(
        self,
        pages: Sequence[PageLike],
        *,
        build_context: BuildContext,
        num_workers: int,
        quiet: bool = True,
        stats: Any = None,
    ) -> int:
        """Render ``pages`` across ``num_workers`` re-parsing shard workers (fork).

        Returns the number of pages rendered; raises on unrecoverable failure so the caller
        falls back to the in-process render path.
        """
        global _SHARD_STATE
        site = self.site
        snapshot = getattr(build_context, "snapshot", None)
        if snapshot is None:
            raise RuntimeError("shard backend requires a SiteSnapshot in the build context")

        n = len(pages)
        if n == 0:
            return 0

        from bengal.snapshots.render_plan import (
            RenderPlan,
            clear_worker_page_content,
            set_worker_page_content,
        )
        from bengal.snapshots.transport import immortalize_snapshot

        plan = RenderPlan.from_site(site, snapshot)
        immortalize_snapshot(snapshot)  # COW-free reads in forked workers

        content_dir = site.content_dir
        files = discover_content_files(content_dir, site=site)
        content_set = {f.source_path for f in files}
        content_pages = [p for p in pages if p.source_path in content_set]
        generated_pages = [p for p in pages if p.source_path not in content_set]

        asset_ctx = getattr(build_context, "asset_manifest_ctx", None)

        # Cross-shard content registry (S14): a worker that embeds another shard's rendered
        # body (PageView.content) resolves it from here, inherited via fork COW. The parent
        # already holds every parsed page, so this is a {path: body} lookup, not extra memory.
        set_worker_page_content({p.source_path: getattr(p, "content", "") or "" for p in pages})

        # --- Phase 2 (parallel): content pages across separate-heap workers --------------
        results: list[RenderChunkResult] = []
        if content_pages:
            workers = max(1, min(num_workers, len(files)))
            idx_lists = partition_content_files(files, workers, strategy="balanced")
            shards = [[files[i] for i in idxs] for idxs in idx_lists]
            _SHARD_STATE = _ShardForkState(
                plan=plan,
                snapshot=snapshot,
                content_dir=content_dir,
                output_dir=site.output_dir,
                shards=shards,
                asset_ctx=asset_ctx,
                quiet=quiet,
            )
            try:
                ctx = mp.get_context("fork")
                with ctx.Pool(processes=len(shards)) as pool:
                    results.extend(pool.map(_render_shard_worker, range(len(shards))))
            finally:
                _SHARD_STATE = None
                clear_worker_page_content()

        # --- Generated pages (tags/archives/pagination) rendered in the parent -----------
        # They are global aggregations the content-file sharder does not cover; sharding them
        # is S13.4e. The parent already holds them parsed, so render them on the live site.
        if generated_pages:
            from bengal.orchestration.render.isolated.shard_worker import render_shard

            gen_result = render_shard(
                list(generated_pages),
                site,
                build_context,
                chunk_index=-1,
                asset_ctx=asset_ctx,
                quiet=quiet,
            )
            results.append(gen_result)

        merged = merge_chunk_results(build_context, results)
        if stats is not None:
            stats.pages_rendered = merged.pages_rendered
            stats.render_isolation_used = True

        if merged.pages_rendered == 0 and n > 0:
            raise RuntimeError("shard render produced no pages (all shards failed)")
        return merged.pages_rendered
