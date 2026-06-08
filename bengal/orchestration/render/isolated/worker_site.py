"""
WorkerSite — reconstruct a real :class:`~bengal.core.site.Site` from a RenderPlan
(issue #350, saga S13.3b).

A Phase-2 shard worker parses its OWN ~1/N of the corpus into its own heap, then has
to *render* those pages — which means it needs a site object the render pipeline will
accept. :func:`build_worker_site` produces that object from the picklable
:class:`~bengal.snapshots.render_plan.RenderPlan` the parent shipped at the barrier.

**It is a real ``Site``, not a facade or subclass — deliberately.** The render path
reads the world through ``SiteContext``, whose ``__getattr__`` silently returns ``""``
for any missing attribute. A facade that forgot a field would therefore produce *blank
HTML that passes the build but fails the byte-diff with no stack trace* — the hardest
class of shard bug to find. A real ``Site`` has every attribute or raises. And it is
nearly free: ``Site.__post_init__`` rebuilds theme / config_service / page_cache /
version_config / registries from ``config`` + ``root_path`` **alone, with zero content
discovery** — so the worker constructs an empty ``Site`` and then assigns the plan's
already-reduced state (pages, sections, taxonomy, xref index, ...) onto it.

This is the rung-b core (empty Site + the site-stable read surface base templates need).
Later rungs assign onto the same object: heterogeneous pages + NavTree precompute
(S13.3c), reconstructed menus + per-worker indexes (S13.3d), taxonomy/related/generated
(S13.3e). The per-worker process-global reset (caches, directive cache) is the caller's
job — it is process state, not site state (see ``plan/epic-shard-parallel-build.md``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.core.site import Site
    from bengal.protocols.core import PageLike
    from bengal.snapshots.render_plan import PageView, RenderPlan

__all__ = ["build_worker_site", "merge_shard_pages"]


def build_worker_site(
    plan: RenderPlan,
    shard_pages: Sequence[PageLike] = (),
    *,
    shard_index: int = 0,
) -> Site:
    """
    Build a real :class:`~bengal.core.site.Site` that renders a worker's shard.

    Constructs an empty ``Site`` from the plan's ``config`` + ``root_path`` (which
    ``__post_init__`` turns into theme/config_service/page_cache/version_config with no
    discovery), then assigns the plan's reduced global state. ``site.pages`` is the
    *heterogeneous* render world: this worker's freshly-parsed live pages for its own
    shard, and body-free :class:`~bengal.snapshots.render_plan.PageView` stand-ins for
    every page another worker owns — in the plan's canonical order, so listings and
    lookups are identical to the in-process build.

    The real worker flow is two-phase, because parsing needs a site and the site needs
    the parsed pages: call ``build_worker_site(plan)`` (no shard_pages → ``site.pages``
    is the plan's PageViews), ``parse_shard(files, worker_site)`` against the returned
    site (so each parsed page's ``_site`` — which ``get_path`` reads to relativise
    ``output_path`` — is the worker site, keeping URLs consistent), then assign
    ``site.pages = merge_shard_pages(plan.pages, shard_pages)``. The one-shot
    ``build_worker_site(plan, shard_pages)`` form is for callers that already parsed
    against a site sharing this plan's ``root_path``/``output_dir``.

    Args:
        plan: the barrier-assembled global render plan (shipped by the parent).
        shard_pages: this worker's own fully-parsed live pages (from ``parse_shard``);
            their bodies live in this heap and are what actually gets rendered. Defaults
            to empty for the parse-then-merge flow above.
        shard_index: this worker's index (carried for diagnostics / per-worker paths).

    Returns:
        A populated ``Site`` ready to pass to ``render_shard`` as the render world.
    """
    from bengal.core.site import Site

    # root_path MUST be the real project root: __post_init__ resolves the theme
    # (themes/<name>/theme.yaml) and the data/ directory from it, so a redirected root
    # would diverge from the parent's render output. build_time + current_language are
    # the two render-visible fields __post_init__ does NOT derive from config.
    site = Site(
        root_path=plan.root_path,
        config=plan.config,
        build_time=plan.build_time,
        current_language=plan.current_language,
    )
    site.output_dir = plan.output_dir

    # The render world. The page_cache lambda (`lambda: self.pages`) reads this live;
    # its token auto-builds on first access, so no explicit invalidate() is needed.
    site.pages = merge_shard_pages(plan.pages, shard_pages)
    # Live ``site.sections`` is the TOP-LEVEL *real* sections (subsections nested via
    # ``.subsections``). The plan's navigation.top_level_sections is that set EXCEPT it
    # also carries the synthetic content-root container (the snapshot keeps a ``root``
    # section whose ``path`` is the content dir, which the live ``site.sections`` never
    # holds). Drop it by path — otherwise ``get_auto_nav`` emits a bogus ``/root/`` nav
    # item and ``base.html`` crashes on its absent ``_path``. Verified to reproduce the
    # live ``site.sections`` exactly across test-basic/product/navigation/taxonomy.
    content_dir = plan.root_path / "content"
    # SectionSnapshots stand in for live Sections here (the render path consumes them
    # uniformly), so the element type is open — same rationale as merge_shard_pages.
    top_level: list[Any] = [s for s in plan.navigation.top_level_sections if s.path != content_dir]
    site.sections = top_level
    site.taxonomies = dict(plan.taxonomy.taxonomies)
    site.xref_index = dict(plan.xref_index)

    return site


def merge_shard_pages(
    plan_pages: Sequence[PageView],
    shard_pages: Sequence[PageLike],
) -> list[Any]:
    """
    Merge a worker's live shard pages into the plan's full, ordered page list.

    Returns ``plan_pages`` with each :class:`PageView` whose ``source_path`` this worker
    parsed replaced *in place* by the corresponding live page. The result is deliberately
    *heterogeneous* — live ``PageLike`` pages for this shard, body-free ``PageView`` stand-ins
    for the rest — which is why the element type is open: ``PageCacheManager`` and the render
    readers treat both uniformly (they touch only ``source_path``/``metadata``). The plan's
    order is the in-process build's canonical ``(weight, str(source_path))`` order, so the
    merged list is byte-parity-faithful for every reader that iterates ``site.pages``.
    """
    live_by_path = {page.source_path: page for page in shard_pages}
    return [live_by_path.get(pv.source_path, pv) for pv in plan_pages]
