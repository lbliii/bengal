"""SiteSnapshot.taxonomy parity tests — issue #354.

``_snapshot_taxonomies`` (bengal/snapshots/scheduling.py) used to iterate the
``{name, slug, pages}`` term dict directly instead of its ``pages`` list, so every
term snapshotted to an empty tuple. The bug was masked at the render-output layer by
the ``_posts`` metadata fallback in ``Renderer._add_tag_generated_page_context``, so a
build-output byte-parity test alone does NOT discriminate it. These tests assert at the
DATA level that the snapshot's per-term page sets match the live ``site.taxonomies``,
and that the renderer fast path (which reads ``snapshot.taxonomy.tag_pages``) resolves
the same pages as the live slow path.

Run on the deterministic ``test-taxonomy`` fixture: post1=python+testing, post2=python,
post3=testing => tags/python=2, tags/testing=2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.build.options import BuildOptions
from bengal.snapshots import create_site_snapshot

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.snapshots.types import SiteSnapshot


def _built(site_factory, root: str) -> tuple[Site, SiteSnapshot]:
    """Build a fixture site once (sequential, quiet) and snapshot it."""
    site = site_factory(root)
    site.build(BuildOptions(quiet=True, force_sequential=True))
    return site, create_site_snapshot(site)


def test_snapshot_taxonomy_term_counts_match_live(site_factory):
    """Every live taxonomy term's page set must survive into the snapshot.

    DISCRIMINATING: with the pre-fix mis-iteration every snapshot term is an empty
    tuple, so ``len(snapshot...) == len(term_data['pages'])`` evaluates ``0 == 2`` and
    FAILS. The non-vacuity guard below proves the fixture actually carries tagged pages,
    so the assertion cannot pass on an empty taxonomy.
    """
    site, snapshot = _built(site_factory, "test-taxonomy")
    live = site.taxonomies

    # Non-vacuity: the fixture must actually have tagged pages, else the per-term
    # assertions below would be trivially satisfiable.
    assert any(td["pages"] for terms in live.values() for td in terms.values()), (
        "test-taxonomy produced no tagged pages; assertions would be vacuous"
    )

    assert set(snapshot.taxonomy.taxonomies) == set(live)
    for kind, terms in live.items():
        snap_terms = snapshot.taxonomy.taxonomies[kind]
        assert set(snap_terms) == set(terms), f"taxonomy {kind} term keys differ"
        for slug, term_data in terms.items():
            live_paths = {p.source_path for p in term_data["pages"]}
            snap_paths = {ps.source_path for ps in snap_terms[slug]}
            assert snap_paths == live_paths, f"taxonomy {kind}/{slug} page set differs"
            assert len(snap_terms[slug]) == len(term_data["pages"]), (
                f"taxonomy {kind}/{slug} page count differs"
            )


def test_snapshot_tag_pages_counts_match_live(site_factory):
    """``snapshot.taxonomy.tag_pages`` (the field the renderer fast path consumes) must
    carry the real per-tag page sets.

    DISCRIMINATING: pre-fix ``tag_pages`` is a truthy dict whose values are all empty
    tuples, so these explicit counts (2 for each tag on test-taxonomy) evaluate ``0 == 2``
    and FAIL. The fast-path guard ``if snapshot.taxonomy.tag_pages:`` is truthy in both
    states, so this is a real correctness gap the empty tuples hide.
    """
    _site, snapshot = _built(site_factory, "test-taxonomy")
    tag_pages = snapshot.taxonomy.tag_pages

    assert len(tag_pages.get("python", ())) == 2
    assert len(tag_pages.get("testing", ())) == 2
    assert {ps.source_path.name for ps in tag_pages["python"]} == {"post1.md", "post2.md"}
    assert {ps.source_path.name for ps in tag_pages["testing"]} == {"post1.md", "post3.md"}


def test_renderer_fast_path_matches_slow_path(site_factory):
    """The snapshot-backed fast path must resolve the same pages as the live slow path.

    Builds the site (so ``build_context.snapshot`` is populated), then a single Renderer
    instance is used to compare ``_get_resolved_tag_pages`` (fast path, fed by the
    snapshot) against ``_build_all_tag_pages_cache`` (slow path, fed by live
    ``site.taxonomies``).

    DISCRIMINATING: pre-fix the fast path returns ``[]`` (empty snapshot tuples) while
    the slow path returns the 2 live posts per tag, so the source_path sets DIVERGE.
    Post-fix the fast path resolves the snapshot's tag membership back to live pages,
    matching the slow path exactly.
    """
    from bengal.orchestration.build_context import BuildContext
    from bengal.rendering.renderer import Renderer
    from bengal.rendering.template_engine import TemplateEngine

    site = site_factory("test-taxonomy")
    site.build(BuildOptions(quiet=True, force_sequential=True))
    snapshot = create_site_snapshot(site)

    # A build_context whose .snapshot is set forces the fast path at renderer.py:262.
    build_context = BuildContext(site=site)
    build_context.snapshot = snapshot

    engine = TemplateEngine(site)
    renderer = Renderer(engine, build_context=build_context)
    slow_cache = renderer._build_all_tag_pages_cache()

    assert set(slow_cache), "slow-path cache empty; fixture has no tags"
    for tag_slug, slow_pages in slow_cache.items():
        fast_pages = renderer._get_resolved_tag_pages(tag_slug)
        assert [p.source_path for p in fast_pages] == [p.source_path for p in slow_pages], (
            f"fast vs slow tag-page set/order diverged for {tag_slug!r}"
        )
        # The fast path must surface live pages (parsed-HTML .content), not raw-markdown
        # snapshots, or the rendered excerpt would diverge byte-for-byte.
        for fast, slow in zip(fast_pages, slow_pages, strict=True):
            assert fast.content == slow.content


def test_i18n_per_language_tag_pages_stay_language_scoped(site_factory):
    """With i18n share_taxonomies=False, a per-language tag page must list only that
    language's posts — the now-populated snapshot tag-page cache is language-blind.

    The default-language (``en``) tag page at ``tags/shared/index.html`` is the
    discriminator: ``site.taxonomies['tags']['shared']`` holds BOTH posts (collection is
    language-blind), while the generated EN tag page's ``_posts`` is narrowed to the EN
    post via ``filter_pages_by_language``.

    DISCRIMINATING: the #354 snapshot fix activates the renderer fast path; without the
    per-language guard (``renderer._per_language_taxonomies``) the fast path returns the
    full cross-language set, so ``"Article Francais" not in en_html`` FAILS (the FR post
    leaks in). Before the #354 fix the empty snapshot masked this via the ``_posts``
    fallback. (The non-default ``fr`` tag page is not emitted to disk under the current
    i18n rendering path — a pre-existing behavior, independent of #354 — so this asserts
    on the EN page only.)
    """
    site = site_factory("test-i18n-taxonomy")
    site.build(BuildOptions(quiet=True, force_sequential=True))

    en_tag_page = site.output_dir / "tags" / "shared" / "index.html"
    assert en_tag_page.exists(), "EN tag page was not generated; fixture/build regressed"
    en_html = en_tag_page.read_text()

    assert "English Post" in en_html, "EN post missing from its own tag page"
    assert "Article Francais" not in en_html, "FR post leaked into the EN tag page (#354)"


def test_snapshot_taxonomies_handles_dict_and_bare_list_terms():
    """``_snapshot_taxonomies`` must read ``term_data['pages']`` for the real
    ``{name,slug,pages}`` term shape AND tolerate a bare page-list term.

    DISCRIMINATING (dict branch): the pre-#354 code iterated the term dict's string keys,
    so the dict term would snapshot to ``()`` and the ``== ("s1", "s2")`` assertion FAILS.
    DISCRIMINATING (bare-list branch): dropping the ``else term_data`` fallback (writing
    just ``term_data.get("pages", ())``) makes the bare list — which has no ``.get`` —
    raise ``AttributeError``, so this test pins the otherwise-dead defensive branch.
    """
    from types import SimpleNamespace

    from bengal.snapshots.scheduling import _snapshot_taxonomies

    p1, p2, p3 = object(), object(), object()
    page_cache = {id(p1): "s1", id(p2): "s2", id(p3): "s3"}
    site = SimpleNamespace(
        taxonomies={
            "tags": {"python": {"name": "python", "slug": "python", "pages": [p1, p2]}},
            "categories": {"guides": [p3]},  # bare-list term: the defensive fallback
        }
    )

    result = _snapshot_taxonomies(site, page_cache)

    assert result["tags"]["python"] == ("s1", "s2")
    assert result["categories"]["guides"] == ("s3",)
