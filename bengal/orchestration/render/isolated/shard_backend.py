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

Generated pages (tags / tag-index / auto-archives) are sharded too (S13.4e): the parent balances
them across the same workers (``generated_page_assignments``) and each worker renders its slice
in its own heap, against its WorkerSite — so the ~23%-of-render generated fraction is no longer a
serial parent tail. They are live parent objects inherited via fork COW; rendering them against
the WorkerSite resolves their listings through the worker's own PageViews + the immortalized
snapshot (the COW-free path), so the bulk (tag pages) parallelizes without the Phase-1 COW tax.

What this version does NOT yet do (tracked):
- Spawn (no COW): the generated-page list + cross-shard content registry are fork-COW-inherited,
  so the spawn backend stays deferred (it would need them serialized).
- render_isolation stays OFF by default until the full S17 idle-box E2E A/B + content-aware gate.
"""

from __future__ import annotations

import heapq
import multiprocessing as mp
from dataclasses import dataclass, replace
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
    generated_pages: list[Any]  # all generated pages (tag/archive/pagination), assigned per S13.4e
    asset_ctx: Any
    quiet: bool


# Installed in the parent BEFORE the fork pool is created; inherited (not pickled) by every
# forked worker. ``None`` in the parent outside a shard render.
_SHARD_STATE: _ShardForkState | None = None

# Base cost for a generated page in the LPT balance below; the cost proxy is the number of
# items the page lists (a tag page over 200 posts renders far more cards than one over 2),
# so the base only matters for tie-breaking near-empty listings.
_GENERATED_BASE_COST = 1


def _estimate_generated_cost(page: Any) -> int:
    """Relative render cost of a generated page — proxied by the number of items it lists.

    Tag/archive pages render one card per listed post, so the listing length dominates the
    template work; tag-index pages list one entry per term. Falls back to the base cost when
    neither is present, so the estimate never raises."""
    metadata = getattr(page, "metadata", None) or {}
    for key in ("_posts", "_tags"):
        items = metadata.get(key)
        if items is not None:
            try:
                return _GENERATED_BASE_COST + len(items)
            except TypeError:  # not sized — fall through to the base cost
                pass
    return _GENERATED_BASE_COST


def _assign_generated_pages(pages: Any, num_workers: int) -> dict[Path, int]:
    """Deterministically LPT-balance generated pages across exactly ``num_workers`` bins.

    Returns ``{source_path: worker_index}``. Pages are ordered by ``source_path.parts`` first,
    so the assignment is independent of the parent's page-list order *and* the OS path
    separator (the same cross-OS-stable key the content sharder uses); the LPT pass then packs
    them by :func:`_estimate_generated_cost` so each worker gets a comparable listing load.
    """
    assignment: dict[Path, int] = {}
    if num_workers <= 0 or not pages:
        return assignment
    ordered = sorted(pages, key=lambda p: p.source_path.parts)
    costed = sorted(
        ((_estimate_generated_cost(p), i) for i, p in enumerate(ordered)),
        key=lambda ci: (-ci[0], ci[1]),
    )
    heap: list[tuple[int, int]] = [(0, worker) for worker in range(num_workers)]
    heapq.heapify(heap)
    for cost, i in costed:
        load, worker = heapq.heappop(heap)
        assignment[ordered[i].source_path] = worker
        heapq.heappush(heap, (load + cost, worker))
    return assignment


def _render_shard_worker(shard_index: int) -> RenderChunkResult:
    """Fork worker: reconstruct a WorkerSite, parse THIS shard, render its own + generated pages.

    The proven S13.3c/d recipe: build an empty real ``Site`` from the plan, parse this
    worker's content files against it (so each page's ``_site`` is the worker site), merge
    the heterogeneous page list, reset process-globals + install the precomputed nav trees,
    then render — both this shard's content pages AND the generated pages the parent assigned
    to this worker (S13.4e). Bodies never leave this heap; only a picklable
    ``RenderChunkResult`` returns.
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

    # S13.4e: this worker also renders its assigned slice of the GENERATED pages
    # (tag / tag-index / auto-archive), which used to render serially in the parent. They are
    # live parent objects inherited via fork COW; the parent balanced them across workers and
    # recorded the split in ``plan.generated_page_assignments``. Rendering them against the
    # WorkerSite (not the parent's live site) resolves their listings through the worker's own
    # PageViews + the immortalized snapshot — the same COW-free path content pages use — so the
    # bulk (tag pages) parallelizes without re-introducing the Phase-1 shared-graph COW tax.
    assignments = plan.generated_page_assignments
    assigned_generated = [
        p for p in state.generated_pages if assignments.get(p.source_path) == shard_index
    ]
    render_pages = [*worker_pages, *assigned_generated]

    ctx = BuildContext(site=ws, pages=render_pages)
    ctx.snapshot = state.snapshot  # section tiles render from it (inherited, immortalized)
    return render_shard(
        render_pages,
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

        # --- Phase 2 (parallel): content + assigned generated pages across worker heaps ----
        results: list[RenderChunkResult] = []
        if content_pages:
            workers = max(1, min(num_workers, len(files)))
            idx_lists = partition_content_files(files, workers, strategy="balanced")
            shards = [[files[i] for i in idxs] for idxs in idx_lists]
            # S13.4e: balance the generated pages across the SAME workers (each worker renders
            # its content shard AND its assigned generated pages, in its own heap). Record the
            # split in the plan's reserved ``generated_page_assignments`` field so the workers
            # — which inherit the full generated-page list via fork COW — can each pick out
            # exactly their slice (the field was empty scaffolding before this).
            plan = replace(
                plan,
                generated_page_assignments=_assign_generated_pages(generated_pages, len(shards)),
            )
            _SHARD_STATE = _ShardForkState(
                plan=plan,
                snapshot=snapshot,
                content_dir=content_dir,
                output_dir=site.output_dir,
                shards=shards,
                generated_pages=list(generated_pages),
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
        elif generated_pages:
            # No content files to shard onto (e.g. an autodoc-only / generated-only build):
            # render the generated pages serially in the parent (the pre-S13.4e fallback). With
            # no content shards there are no worker heaps to host the generated render, so there
            # is nothing to parallelize onto — correctness over a non-existent win.
            from bengal.orchestration.render.isolated.shard_worker import render_shard

            results.append(
                render_shard(
                    list(generated_pages),
                    site,
                    build_context,
                    chunk_index=-1,
                    asset_ctx=asset_ctx,
                    quiet=quiet,
                )
            )

        merged = merge_chunk_results(build_context, results)
        if stats is not None:
            stats.pages_rendered = merged.pages_rendered
            stats.render_isolation_used = True

        if merged.pages_rendered == 0 and n > 0:
            raise RuntimeError("shard render produced no pages (all shards failed)")
        return merged.pages_rendered
