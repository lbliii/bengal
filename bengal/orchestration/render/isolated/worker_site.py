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

    # Register every section in the ContentRegistry. ``__post_init__`` builds an EMPTY
    # registry (no discovery runs in a worker), but a live page's ``_section`` resolves
    # lazily via ``site.get_section_by_path`` → ``registry.get_section`` — so without this,
    # ``get_page_section(page)`` returns None and the renderer misroutes every section-index
    # page through its *root-home* branch (top-level tiles instead of the section's own
    # children). We register the **tree** (top_level → subsections, recursively) because
    # only those SectionSnapshots carry ``.parent`` links — the flat ``plan.sections`` tuple
    # is parent-less (the snapshot stores hierarchy via subsections, not the flat list), and
    # a parent-less ancestor breaks ``page.ancestors`` → breadcrumbs drop intermediate crumbs.
    # The flat pass first guarantees completeness (any section not reachable from a top-level
    # root still resolves); the recursive pass then overwrites tree-reachable entries with
    # their parent-linked versions (registry is keyed by path, last write wins).
    # SectionSnapshots stand in for live Sections here (same rationale as ``top_level``).
    all_sections: list[Any] = list(plan.sections)
    for section in all_sections:
        site.registry.register_section(section)
    for section in top_level:
        site.registry.register_sections_recursive(section)

    site.taxonomies = dict(plan.taxonomy.taxonomies)
    site.xref_index = dict(plan.xref_index)

    # Menus (S13.3d). The plan's menus were snapshotted AFTER the in-process menu phase,
    # so they are the FINAL assembled hierarchy (auto-nav + dev-bundle + dropdowns, or the
    # config [[menus.main]] menu), already page-view-ified. The render engine builds the
    # template menu via ``[item.to_dict() for item in site.menu[name]]`` — MenuItemSnapshot
    # answers ``to_dict()`` byte-identically to the live MenuItem. We assign the snapshots
    # directly: re-running MenuOrchestrator here would re-derive auto-nav against
    # SectionSnapshots (which lack ``_site``/``_path``) and diverge. ``_dev_menu_metadata``
    # is left at its ``__post_init__`` default (None) — these menus already bake in any
    # dev-bundle decision the parent made, and base.html reads it null-safe.
    # MenuItemSnapshot stands in for the live MenuItem (both answer ``to_dict()``); the
    # Any-typed locals keep ty's invariant ``dict[str, list[MenuItem]]`` attribute happy.
    worker_menu: dict[str, list[Any]] = {
        name: list(items) for name, items in plan.navigation.menus.items()
    }
    site.menu = worker_menu
    worker_menu_localized: dict[str, dict[str, list[Any]]] = {
        name: {lang: list(items) for lang, items in langs.items()}
        for name, langs in plan.menu_localized.items()
    }
    site.menu_localized = worker_menu_localized

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
