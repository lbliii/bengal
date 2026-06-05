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
