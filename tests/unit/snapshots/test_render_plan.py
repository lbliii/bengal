"""
RenderPlan contract tests — issue #350, Phase 2, saga S11.

Proves the three invariants the shard-parallel build depends on, at the data level
(without the S13 actor protocol):

1. **Picklable + body-free.** A RenderPlan round-trips through pickle and contains no
   ``MappingProxyType``, no ``PageSnapshot`` (bodies), and no ``NavTree`` — so it can
   be shipped over IPC to a spawn worker, and the parsed page bodies stay in the
   worker that parsed them.
2. **Reduce is shard-order-independent.** A plan assembled from N shards is byte-equal
   (on every reduced field) to one assembled from a single whole-site shard — so
   output is deterministic across worker counts (the S16 thread==shard guard in the
   small).
3. **Completeness / parity vs the live site.** The plan reproduces the live page-view
   map, taxonomy, xref index, related index, and config — so a render worker reading
   the plan resolves every global lookup identically to the in-process path. A new
   global read that is not carried by the plan surfaces here as a parity failure.

These run on small deterministic fixtures (NOT test-large, which has a random-posts
widget). Each fixture is built once and all assertions reuse the build.
"""

from __future__ import annotations

import pickle
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

import pytest

from bengal.orchestration.build.options import BuildOptions
from bengal.snapshots import create_site_snapshot
from bengal.snapshots.render_plan import (
    PageView,
    RenderPlan,
    assemble_render_plan,
    assert_picklable,
    shard_meta_from_live_pages,
    shard_meta_from_pages,
    to_plain_data,
)
from bengal.snapshots.types import PageSnapshot

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.snapshots.types import SiteSnapshot

# Deterministic fixtures spanning the global-read surface: minimal, taxonomy
# (tags/categories/related/xref/generated pages), products (nested sections), and
# navigation (menus + sections).
ROOTS = ["test-basic", "test-taxonomy", "test-product", "test-navigation"]


def _built(site_factory, root: str) -> tuple[Site, SiteSnapshot]:
    """Build a fixture site once (sequential, quiet) and snapshot it."""
    site = site_factory(root)
    site.build(BuildOptions(quiet=True, force_sequential=True))
    return site, create_site_snapshot(site)


def _assemble_in_shards(site: Site, snapshot: SiteSnapshot, n: int) -> RenderPlan:
    """Assemble a plan by splitting the pages round-robin into ``n`` shards."""
    pages = list(site.pages)
    groups = [pages[i::n] for i in range(n)]
    metas = [
        shard_meta_from_pages(g, snapshot, shard_index=i, site=site) for i, g in enumerate(groups)
    ]
    return assemble_render_plan(metas, snapshot=snapshot, site=site)


def _reduced_fields(plan: RenderPlan) -> dict:
    """The page-derived fields the reduce assembles (all cycle-free, structural-eq).

    Excludes sections/navigation (SectionSnapshot has parent/root cycles that make
    ``==`` recurse infinitely, and they are sourced from the same snapshot regardless
    of sharding anyway).
    """
    return {
        "pages": plan.pages,
        "regular_pages": plan.regular_pages,
        "pages_by_path": plan.pages_by_path,
        "taxonomies": plan.taxonomy.taxonomies,
        "tag_pages": plan.taxonomy.tag_pages,
        "xref_index": plan.xref_index,
        "related_index": plan.related_index,
    }


# ---------------------------------------------------------------------------
# 1. Picklable + body-free
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("root", ROOTS)
def test_render_plan_is_picklable_and_body_free(site_factory, root):
    site, snapshot = _built(site_factory, root)
    plan = RenderPlan.from_site(site, snapshot)

    # Round-trips + no proxy/PageSnapshot/NavTree anywhere in the graph.
    assert_picklable(plan)

    # PageView carries no body field (the whole point of the view).
    field_names = set(PageView.__dataclass_fields__)
    assert "parsed_html" not in field_names
    assert "content" not in field_names

    # And no PageSnapshot survived into any page collection.
    for pv in plan.pages:
        assert isinstance(pv, PageView)
        assert not isinstance(pv, PageSnapshot)


@pytest.mark.parametrize("root", ROOTS)
def test_pickle_round_trip_preserves_reduced_data(site_factory, root):
    site, snapshot = _built(site_factory, root)
    plan = RenderPlan.from_site(site, snapshot)

    restored = pickle.loads(pickle.dumps(plan))

    # Reduced fields survive the round-trip unchanged (structural equality).
    assert _reduced_fields(restored) == _reduced_fields(plan)
    assert restored.config == plan.config
    assert restored.baseurl == plan.baseurl


# ---------------------------------------------------------------------------
# 2. Reduce is shard-order-independent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("root", ROOTS)
def test_reduce_is_shard_order_independent(site_factory, root):
    site, snapshot = _built(site_factory, root)
    whole = RenderPlan.from_site(site, snapshot)

    n_pages = len(site.pages)
    for n in (2, 3, 5, 7):
        if n > n_pages:
            break
        sharded = _assemble_in_shards(site, snapshot, n)
        # Every page-derived field is identical regardless of how many shards
        # produced it — the determinism the at-scale thread==shard guard relies on.
        assert _reduced_fields(sharded) == _reduced_fields(whole), (
            f"reduce diverged for {root} at {n} shards"
        )


@pytest.mark.parametrize("root", ROOTS)
def test_page_view_map_covers_every_page(site_factory, root):
    site, snapshot = _built(site_factory, root)
    plan = RenderPlan.from_site(site, snapshot)

    live_paths = {p.source_path for p in site.pages}
    assert set(plan.pages_by_path) == live_paths
    # No collisions: one view per distinct source_path.
    assert len(plan.pages_by_path) == len(live_paths)
    assert len(plan.pages) == len(live_paths)


# ---------------------------------------------------------------------------
# 3. Completeness / parity vs the live site
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("root", ROOTS)
def test_page_view_fields_match_live_pages(site_factory, root):
    site, snapshot = _built(site_factory, root)
    plan = RenderPlan.from_site(site, snapshot)
    snap_by_path = {p.source_path: p for p in snapshot.pages}

    for page in site.pages:
        pv = plan.pages_by_path[page.source_path]
        ps = snap_by_path[page.source_path]
        # Identity / routing
        assert pv.title == page.title
        assert pv.href == page.href
        assert pv.site_path == page._path
        assert pv.source_path == page.source_path
        assert pv.output_path == ps.output_path
        assert pv.slug == page.slug
        assert pv.template_name == ps.template_name
        # Ordering / taxonomy inputs
        assert pv.tags == tuple(page.metadata.get("tags", []) or [])
        assert pv.categories == tuple(page.metadata.get("categories", []) or [])
        # Listing / SEO surrogates — must match the snapshot (the render-source).
        assert pv.excerpt == ps.excerpt
        assert pv.meta_description == ps.meta_description
        assert pv.reading_time == ps.reading_time
        assert pv.word_count == ps.word_count
        # toc_items drives xref by_heading/by_anchor; a silent drop must be caught.
        assert pv.toc_items == ps.toc_items
        # Verification / scoping
        assert pv.content_hash == ps.content_hash
        assert pv.is_generated == bool(page.metadata.get("_generated"))
        assert pv.ref_id == (
            str(page.metadata["id"]) if page.metadata.get("id") is not None else None
        )

        # Metadata: assert against an INDEPENDENT ground truth (not to_plain_data on
        # both sides — that would be vacuous). Every plain *scalar* frontmatter value
        # the live page carries must survive into the view with its value intact.
        for key, value in page.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                assert pv.metadata.get(key) == value, f"metadata[{key!r}] lost for {pv.source_path}"


@pytest.mark.parametrize("root", ROOTS)
def test_config_params_data_parity(site_factory, root):
    site, snapshot = _built(site_factory, root)
    plan = RenderPlan.from_site(site, snapshot)

    assert plan.config == to_plain_data(snapshot.config)
    assert plan.params == to_plain_data(snapshot.params)
    assert plan.data == to_plain_data(snapshot.data)
    # No proxy leaked into config.
    assert not isinstance(plan.config, MappingProxyType)
    assert all(not isinstance(v, MappingProxyType) for v in plan.config.values())


def test_taxonomy_parity_vs_live(site_factory):
    site, snapshot = _built(site_factory, "test-taxonomy")
    plan = RenderPlan.from_site(site, snapshot)

    live = site.taxonomies
    assert set(plan.taxonomy.taxonomies) == set(live)
    for kind, terms in live.items():
        plan_terms = plan.taxonomy.taxonomies[kind]
        assert set(plan_terms) == set(terms), f"taxonomy {kind} term keys differ"
        for slug, term_data in terms.items():
            live_pages = [p.source_path for p in term_data["pages"]]
            plan_pages = [pv.source_path for pv in plan_terms[slug]["pages"]]
            # Same membership and same (live) order — render output depends on order.
            assert plan_pages == live_pages, f"taxonomy {kind}/{slug} pages differ"
            assert plan_terms[slug]["name"] == term_data["name"]
            assert plan_terms[slug]["slug"] == term_data["slug"]


def test_xref_index_parity_vs_live(site_factory):
    site, snapshot = _built(site_factory, "test-taxonomy")
    plan = RenderPlan.from_site(site, snapshot)
    live = site.xref_index

    # by_path / by_id: single page per key — resolved view must match the live page.
    for index_name in ("by_path", "by_id"):
        assert set(plan.xref_index[index_name]) == set(live[index_name]), (
            f"{index_name} key set differs"
        )
        for key, live_page in live[index_name].items():
            assert plan.xref_index[index_name][key].source_path == live_page.source_path

    # by_slug: multi-valued — same key set and same source_path membership per slug.
    assert set(plan.xref_index["by_slug"]) == set(live["by_slug"])
    for slug, live_pages in live["by_slug"].items():
        plan_paths = {pv.source_path for pv in plan.xref_index["by_slug"][slug]}
        assert plan_paths == {p.source_path for p in live_pages}

    # by_heading / by_anchor: derived from PageView.toc_items. Same key set and the
    # same (page, anchor) membership as the live index. (These are empty on fixtures
    # without TOC headings, but the assertion guards the reduce + toc_items pipeline
    # whenever a heading-bearing page is present.)
    assert set(plan.xref_index["by_heading"]) == set(live["by_heading"])
    for heading, live_entries in live["by_heading"].items():
        plan_entries = {
            (pv.source_path, anchor) for pv, anchor in plan.xref_index["by_heading"][heading]
        }
        assert plan_entries == {(p.source_path, anchor) for p, anchor in live_entries}
    assert set(plan.xref_index["by_anchor"]) == set(live["by_anchor"])


def test_generated_taxonomy_page_refs_preserved(site_factory):
    """Generated tag/archive pages carry page lists (``_tags``/``_posts``) in metadata.

    These are live Page objects in the source; the view must preserve them as
    source_path references (not silently drop them) so S14 can resolve them. This is
    the discriminating guard for the metadata page-ref drop the review caught.
    """
    site, snapshot = _built(site_factory, "test-taxonomy")
    plan = RenderPlan.from_site(site, snapshot)

    checked = 0
    for page in site.pages:
        if not page.metadata.get("_generated"):
            continue
        pv = plan.pages_by_path[page.source_path]

        # _tags: {slug: {name, slug, pages: [Page]}} -> pages preserved as source_paths.
        live_tags = page.metadata.get("_tags")
        if isinstance(live_tags, dict):
            for slug, term in live_tags.items():
                live_count = len(term.get("pages", ()))
                plan_pages = pv.metadata.get("_tags", {}).get(slug, {}).get("pages", [])
                assert len(plan_pages) == live_count, f"_tags[{slug!r}] page refs dropped"
                assert all(isinstance(p, Path) for p in plan_pages)
                if live_count:
                    checked += 1

        # _posts: [Page] -> [source_path].
        live_posts = page.metadata.get("_posts")
        if isinstance(live_posts, (list, tuple)) and live_posts:
            plan_posts = pv.metadata.get("_posts", [])
            assert len(plan_posts) == len(live_posts), "_posts page refs dropped"
            assert all(isinstance(p, Path) for p in plan_posts)
            checked += 1

    assert checked, "test-taxonomy produced no generated page with _tags/_posts refs"


def test_assemble_render_plan_rejects_overlapping_shards(site_factory):
    """The barrier must reject shards that double-assign a page (silent loss)."""
    site, snapshot = _built(site_factory, "test-taxonomy")
    pages = list(site.pages)
    # Two overlapping shards: the first page appears in both.
    meta_a = shard_meta_from_pages(pages[:2], snapshot, shard_index=0, site=site)
    meta_b = shard_meta_from_pages(pages[1:], snapshot, shard_index=1, site=site)

    with pytest.raises(ValueError, match="overlapping shards"):
        assemble_render_plan([meta_a, meta_b], snapshot=snapshot, site=site)


def test_related_index_parity_vs_live(site_factory):
    site, snapshot = _built(site_factory, "test-taxonomy")
    plan = RenderPlan.from_site(site, snapshot)

    found_related = False
    for page in site.pages:
        related = getattr(page, "related_posts", None) or []
        expected = tuple(r.source_path for r in related)
        if expected:
            found_related = True
            assert plan.related_index.get(page.source_path) == expected, (
                f"related index differs for {page.source_path}"
            )
        else:
            assert page.source_path not in plan.related_index
    # Guard against a vacuous test: the fixture must actually exercise related posts.
    assert found_related, "test-taxonomy fixture produced no related posts"


# ---------------------------------------------------------------------------
# S13: the from-live-page map step (worker parses its own shard, no snapshot)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("root", ROOTS)
def test_shard_meta_from_live_pages_matches_snapshot_path(site_factory, root):
    """The S13 map step: a worker deriving ShardPageMeta from its OWN freshly-parsed
    live pages (no SiteSnapshot) must produce the same page-views / taxonomy edges /
    xref edges / cost as the S11 snapshot path. This is the load-bearing parity
    claim for the persistent shard worker — if a PageView field can only be derived
    from a whole-site snapshot, it surfaces here.

    ``related_pairs`` deliberately diverge (live defers to the barrier; the snapshot
    path inlines them), so they are asserted separately, not via meta equality.
    """
    site, snapshot = _built(site_factory, root)
    pages = list(site.pages)

    live_meta = shard_meta_from_live_pages(pages, site, shard_index=0)
    snap_meta = shard_meta_from_pages(pages, snapshot, shard_index=0, site=site)

    assert live_meta.page_views == snap_meta.page_views, f"page-views diverged for {root}"
    assert live_meta.taxonomy_terms == snap_meta.taxonomy_terms, f"taxonomy edges diverged: {root}"
    assert live_meta.xref_entries == snap_meta.xref_entries, f"xref edges diverged for {root}"
    assert live_meta.estimated_render_cost == snap_meta.estimated_render_cost

    # The one intentional divergence: related is barrier-only in the live path.
    assert live_meta.related_pairs == ()

    # Non-vacuous: the fixture really produced page-views.
    assert live_meta.page_views


@pytest.mark.parametrize("root", ROOTS)
def test_render_plan_from_live_pages_matches_from_site(site_factory, root):
    """End-to-end: a plan assembled from the from-LIVE map step is byte-equal (on
    every page-derived field except related, which the live path defers) to the
    whole-site ``from_site`` oracle. Proves the worker's map output reduces to the
    same global render world the in-process build produces."""
    site, snapshot = _built(site_factory, root)
    oracle = RenderPlan.from_site(site, snapshot)

    live_meta = shard_meta_from_live_pages(list(site.pages), site, shard_index=0)
    live_plan = assemble_render_plan([live_meta], snapshot=snapshot, site=site)

    fields = _reduced_fields(oracle)
    live_fields = _reduced_fields(live_plan)
    # related_index is barrier-computed and not yet folded in from the live map step;
    # compare every other reduced field. (Folding related at the barrier is a later
    # S13 increment; this isolates the map-step parity.)
    del fields["related_index"], live_fields["related_index"]
    assert live_fields == fields, f"live-derived plan diverged from from_site for {root}"
    assert live_plan.related_index == {}  # deferred


def test_from_live_section_path_sourced_from_page_not_snapshot(site_factory):
    """``section_path`` is the one PageView field the from-live builder cannot read
    off a transient per-page snapshot (sections resolve only in the whole-site pass),
    so it is sourced from ``page._section_path``. On a sectioned fixture, prove the
    live builder populates section_path AND matches the snapshot path — making the
    override correct and the parametrized parity above non-vacuous on this field."""
    site, snapshot = _built(site_factory, "test-product")
    pages = list(site.pages)
    live = shard_meta_from_live_pages(pages, site, shard_index=0)
    snap = shard_meta_from_pages(pages, snapshot, shard_index=0, site=site)

    snap_by = {pv.source_path: pv for pv in snap.page_views}
    sectioned = [pv for pv in live.page_views if pv.section_path is not None]
    assert sectioned, "test-product produced no sectioned page — section_path test is vacuous"
    for pv in sectioned:
        assert pv.section_path == snap_by[pv.source_path].section_path


def test_sections_carry_page_views_not_snapshots(site_factory):
    """Section page collections are page-view-ified (no bodies leak via sections)."""
    site, snapshot = _built(site_factory, "test-product")
    plan = RenderPlan.from_site(site, snapshot)

    seen_section = False
    for section in plan.sections:
        for collection in (section.pages, section.sorted_pages, section.regular_pages):
            for pv in collection:
                seen_section = True
                assert isinstance(pv, PageView)
                assert not isinstance(pv, PageSnapshot)
        if section.index_page is not None:
            assert isinstance(section.index_page, PageView)
    assert seen_section, "test-product fixture produced no section pages"


# ---------------------------------------------------------------------------
# S13.4a: barrier-owns-globals — taxonomy + related recomputed from the PageView
# union (no built site.taxonomies / page.related_posts). Gated against both the
# snapshot-sourced from_site oracle AND the live site as independent ground truth.
# ---------------------------------------------------------------------------


def _assemble_meta_reduced(site: Site, snapshot: SiteSnapshot, n: int) -> RenderPlan:
    """Round-robin into ``n`` shards and assemble with taxonomy/related meta-reduced."""
    pages = list(site.pages)
    groups = [pages[i::n] for i in range(n)]
    metas = [
        shard_meta_from_pages(g, snapshot, shard_index=i, site=site) for i, g in enumerate(groups)
    ]
    return assemble_render_plan(
        metas, snapshot=snapshot, site=site, reduce_taxonomy_from_metas=True
    )


@pytest.mark.parametrize("root", ROOTS)
def test_meta_reduced_taxonomy_and_related_match_from_site(site_factory, root):
    """The barrier reduce (``reduce_taxonomy_from_metas=True``) produces the SAME
    taxonomies / tag_pages / related_index as the snapshot-sourced ``from_site`` oracle,
    independent of shard count — so the small parent can stop building site.taxonomies
    and page.related_posts. (Sections/menus/config still snapshot-sourced; later rungs.)"""
    site, snapshot = _built(site_factory, root)
    oracle = RenderPlan.from_site(site, snapshot)

    n_pages = len(site.pages)
    for n in (1, 2, 3, 5, 7):
        if n > n_pages:
            break
        plan = _assemble_meta_reduced(site, snapshot, n)
        assert plan.taxonomy.taxonomies == oracle.taxonomy.taxonomies, f"{root} N={n} taxonomy"
        assert plan.taxonomy.tag_pages == oracle.taxonomy.tag_pages, f"{root} N={n} tag_pages"
        assert plan.related_index == oracle.related_index, f"{root} N={n} related"


@pytest.mark.parametrize("root", ROOTS)
def test_meta_reduced_from_live_map_step_recovers_related(site_factory, root):
    """The REAL map step (``shard_meta_from_live_pages``) emits ``related_pairs=()``
    because related is a whole-site computation. With ``reduce_taxonomy_from_metas`` the
    barrier recomputes it from scratch — closing the gap that
    ``test_render_plan_from_live_pages_matches_from_site`` documents (related_index=={}).
    This is the load-bearing S13.4a proof: a worker's body-free map output reduces to the
    same taxonomy + related world the in-process build produced."""
    site, snapshot = _built(site_factory, root)
    oracle = RenderPlan.from_site(site, snapshot)

    live_meta = shard_meta_from_live_pages(list(site.pages), site, shard_index=0)
    plan = assemble_render_plan(
        [live_meta], snapshot=snapshot, site=site, reduce_taxonomy_from_metas=True
    )

    assert plan.taxonomy.taxonomies == oracle.taxonomy.taxonomies, f"{root} taxonomy"
    assert plan.related_index == oracle.related_index, f"{root} related"


def test_meta_reduced_related_matches_live_and_is_nonvacuous(site_factory):
    """Related index reduced from the real (related-free) live map step matches the live
    ``page.related_posts`` as INDEPENDENT ground truth — and the fixture actually has
    related posts, so the gate is not vacuously comparing two empty dicts."""
    site, snapshot = _built(site_factory, "test-taxonomy")
    live_meta = shard_meta_from_live_pages(list(site.pages), site, shard_index=0)
    plan = assemble_render_plan(
        [live_meta], snapshot=snapshot, site=site, reduce_taxonomy_from_metas=True
    )

    found_related = False
    for page in site.pages:
        related = getattr(page, "related_posts", None) or []
        expected = tuple(r.source_path for r in related)
        if expected:
            found_related = True
            assert plan.related_index.get(page.source_path) == expected, (
                f"meta-reduced related diverged for {page.source_path}"
            )
        else:
            assert page.source_path not in plan.related_index
    assert found_related, "test-taxonomy produced no related posts — related gate is vacuous"
    assert plan.related_index, "barrier did not populate related_index from the live map step"


def test_meta_reduced_taxonomy_matches_live_site_taxonomies(site_factory):
    """Taxonomy reduced from the live map step matches live ``site.taxonomies`` as
    INDEPENDENT ground truth: same kinds, same term keys, same first-writer display name,
    same membership AND page order (the comparison is order-sensitive, so a membership or
    ordering regression goes red against the live build)."""
    site, snapshot = _built(site_factory, "test-taxonomy")
    live_meta = shard_meta_from_live_pages(list(site.pages), site, shard_index=0)
    plan = assemble_render_plan(
        [live_meta], snapshot=snapshot, site=site, reduce_taxonomy_from_metas=True
    )

    live = site.taxonomies
    assert set(plan.taxonomy.taxonomies) == set(live)

    checked_terms = 0
    for kind, terms in live.items():
        plan_terms = plan.taxonomy.taxonomies[kind]
        assert set(plan_terms) == set(terms), f"taxonomy {kind} term keys differ"
        for slug, term_data in terms.items():
            live_pages = [p.source_path for p in term_data["pages"]]
            plan_pages = [pv.source_path for pv in plan_terms[slug]["pages"]]
            assert plan_pages == live_pages, f"taxonomy {kind}/{slug} membership/order differs"
            assert plan_terms[slug]["name"] == term_data["name"]
            assert plan_terms[slug]["slug"] == term_data["slug"]
            checked_terms += 1
    assert checked_terms, "test-taxonomy produced no taxonomy terms — gate is vacuous"


def _mk_pv(
    source_path: str,
    *,
    tags: tuple[str, ...] = (),
    date: datetime | None = None,
    is_generated: bool = False,
    metadata: dict | None = None,
) -> PageView:
    """Minimal PageView for direct ``_reduce_taxonomies`` unit tests (no fixture build)."""
    return PageView(
        title=source_path,
        href=f"/{source_path}",
        site_path=f"/{source_path}",
        source_path=Path(source_path),
        output_path=Path(source_path),
        slug=source_path,
        ref_id=None,
        template_name="page.html",
        date=date,
        weight=0.0,
        tags=tags,
        categories=(),
        excerpt="",
        meta_description="",
        reading_time=0,
        word_count=0,
        toc_items=(),
        content_hash="",
        metadata=metadata or {},
        section_path=None,
        version=None,
        is_generated=is_generated,
    )


def test_reduce_taxonomies_sorts_date_desc_with_first_writer_name():
    """Discriminating unit test for the taxonomy reduce, independent of fixture data:
    pages sharing a slug are ordered date-DESC (NOT walk order), the display name is the
    first raw term seen in walk order, and case-variant raw terms collapse to one slug."""
    from bengal.snapshots.render_plan import _reduce_taxonomies

    # Fed in walk order old/new/mid; 'X' first (first-writer name), 'x' collapses to it.
    p_old = _mk_pv("a.md", tags=("X",), date=datetime(2020, 1, 1))
    p_new = _mk_pv("b.md", tags=("x",), date=datetime(2023, 1, 1))
    p_mid = _mk_pv("c.md", tags=("X",), date=datetime(2021, 1, 1))

    taxes = _reduce_taxonomies([p_old, p_new, p_mid], config={})

    term = taxes["tags"]["x"]
    assert term["name"] == "X", "first-writer-wins display name not preserved"
    # Date-DESC, NOT the walk order [a, b, c] — this is the discriminating assertion.
    assert [pv.source_path for pv in term["pages"]] == [Path("b.md"), Path("c.md"), Path("a.md")]


def test_reduce_taxonomies_eligibility_and_singular_category():
    """The reduce drops generated + content/api|cli pages and reads categories from the
    SINGULAR ``category`` frontmatter key (exactly as collect_taxonomies), not PageView.categories."""
    from bengal.snapshots.render_plan import _reduce_taxonomies

    gen = _mk_pv("g.md", tags=("x",), is_generated=True)
    api = _mk_pv("content/api/m.md", tags=("x",))
    ok = _mk_pv("ok.md", tags=("x",), metadata={"category": "Guides"})

    taxes = _reduce_taxonomies([gen, api, ok], config={})

    # Only the eligible page survives under tag 'x'.
    assert [pv.source_path for pv in taxes["tags"]["x"]["pages"]] == [Path("ok.md")]
    # Category from the singular key, slug-normalized, first-writer name preserved.
    assert taxes["categories"]["guides"]["name"] == "Guides"
    assert [pv.source_path for pv in taxes["categories"]["guides"]["pages"]] == [Path("ok.md")]
