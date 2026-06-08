"""
RenderPlan — the immutable, picklable global render world for shard-parallel builds.

Issue #350, Phase 2, saga **S11**. This is the map/reduce *contract* for the
shard-parallel cold build (see ``plan/epic-shard-parallel-build.md``):

- **map (per worker):** a worker parses its OWN ~1/N shard of content and emits a
  lightweight, picklable :class:`ShardPageMeta` — one :class:`PageView` per page
  plus the page-derived global edges (taxonomy memberships, xref entries, related
  pairs). The parsed page *bodies* never leave the worker's heap.
- **barrier (parent):** :func:`assemble_render_plan` reduces the union of every
  shard's metadata into one immutable :class:`RenderPlan` — the page-view map for
  ``get_page()``, taxonomy term→pages, the related index, the frozen xref index,
  navigation/menus, sections, and config/params/data. The parent ships this plan
  (pickled over IPC, or COW-shared on fork) to every worker for the render phase.

Why a *new* type rather than reusing :class:`SiteSnapshot` directly: the snapshot
holds full :class:`PageSnapshot` objects (with ``parsed_html`` bodies) and
``MappingProxyType`` config views. Shipping a 4,000-page snapshot with every body
to every worker would dwarf the parallelism win and ``MappingProxyType`` does not
pickle. RenderPlan *extends* the snapshot: it reuses every frozen container type
(:class:`SectionSnapshot`, :class:`MenuItemSnapshot`, ...) but page-view-ifies the
three places that hold bodies (the page tuples, taxonomy, menus) and flattens
config views to plain dicts.

Design decisions (deliberate, documented):

- **Unconditionally picklable.** Every mapping is collapsed to a plain ``dict`` via
  :func:`to_plain_data` at construction time — which both flattens
  ``MappingProxyType`` and drops injected runtime objects (live Page refs under keys
  like ``_tags``, plugin callables) that would otherwise break pickling. There is no
  fork-vs-spawn branch in the data: the fork backend just additionally *immortalizes*
  the plain graph for copy-on-write sharing (see ``immortalize_snapshot``), but
  correctness never depends on it.
- **PageView mirrors PageSnapshot's read surface** (``title``/``href``/``metadata``/
  ``tags``/... + ``params``/``type``/``variant`` properties) so it can substitute
  for a PageSnapshot anywhere a template iterates ``section.pages`` or a taxonomy
  term, while carrying only metadata — never a body.
- **``from_site`` is the single-shard case of ``assemble_render_plan``.** The reduce
  is order-independent (deterministic global sort), so a plan assembled from N
  shards is byte-equal to one assembled from a single whole-site shard — which is
  exactly what the S11 parity test proves.
- **nav_trees are excluded.** ``NavTree`` nodes reference the live mutable
  Page/Section graph and are not picklable; each worker rebuilds them from the
  plan's sections+pages at startup (saga S13). The plan carries the *inputs*
  (sections, pages, versioning) that ``NavTree.build`` needs.

S13 (the worker actor protocol) will extend :class:`ShardPageMeta` with the
section/menu metadata that today is sourced from the parent's already-built
snapshot; the per-page edges reduced here are the parts that genuinely come from
parsing a shard.

Worker reconstruction contract (S13/S14)
----------------------------------------
RenderPlan carries the *raw inputs*; the worker's site context rebuilds the derived
structures the in-process Site/render-context build, from those inputs — so the plan
stays small and picklable. The render path already rebuilds several of these from
raw config today, so the worker does no more than the main process:

- **ConfigContext / config_snapshot** ← rebuilt from ``config`` via
  ``ConfigSnapshot.from_dict`` (exactly as ``rendering/context`` does today).
- **version_config** ← rebuilt from ``config`` via ``VersionConfig.from_config``
  (exactly as ``Site.__init__`` does); ``versioning_enabled``/``versions`` are also
  carried directly.
- **get_page() lookup maps** ← built from ``pages_by_path``/``pages`` instead of a
  live ``site.pages`` (each PageView has source_path/slug — enough for every lookup
  variant).
- **site.indexes (QueryIndexRegistry)** ← rebuilt from PageView ``metadata``
  (author/date/series/status are plain scalars, carried).
- **nav_trees** ← rebuilt from ``sections``+``pages`` via ``NavTree.build`` (they
  hold live refs and are intentionally not shipped).
- **Generated-page render objects** (``_paginator``, resolved ``_posts``/``_tags``
  page lists) ← S14 reconstructs from ``taxonomy``/``pages_by_path``. Denormalized
  page references in metadata (``_tags``/``_posts``) are preserved as *source_paths*
  (see :func:`to_plain_data`), which the worker re-resolves to PageViews; the
  ``Paginator`` object itself is not transported.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from bengal.snapshots.types import (
    NO_SECTION,
    MenuItemSnapshot,
    SectionSnapshot,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.config.snapshot import ConfigSnapshot
    from bengal.protocols import PageLike, SiteLike
    from bengal.snapshots.types import PageSnapshot, SiteSnapshot


# Plain, pickle-safe leaf types that legitimately come out of YAML/TOML frontmatter
# or config. Anything else reachable in a metadata/config mapping (live Page/Section
# objects injected under keys like ``_tags``, callables from plugin eval, ...) is an
# internal runtime object that must NOT cross the heap boundary — it is dropped.
_PLAIN_SCALARS = (str, bytes, int, float, bool, type(None), datetime, date)
_DROP = object()


def _plain_value(obj: Any) -> Any:
    """Deep-convert a value to pickle-safe plain data; return ``_DROP`` to omit it."""
    # Any Mapping (dict, MappingProxyType, the live page's CascadeView, ...) flattens
    # to a plain dict — so this works on both snapshot and live-page metadata.
    if isinstance(obj, Mapping):
        out: dict[Any, Any] = {}
        for k, v in obj.items():
            pv = _plain_value(v)
            if pv is not _DROP and isinstance(k, (str, int, float, bool, bytes, type(None))):
                out[k] = pv
        return out
    if isinstance(obj, (list, tuple)):
        items = [v for v in (_plain_value(x) for x in obj) if v is not _DROP]
        return tuple(items) if isinstance(obj, tuple) else items
    if isinstance(obj, (set, frozenset)):
        items = [v for v in (_plain_value(x) for x in obj) if v is not _DROP]
        return type(obj)(items)
    if isinstance(obj, (Path, *_PLAIN_SCALARS)):
        return obj
    # Intra-site page references embedded in denormalized metadata (a generated
    # page's _tags/_posts hold live Page objects) are preserved as their
    # source_path, so a worker can re-resolve them to PageViews via
    # RenderPlan.pages_by_path — rather than silently dropping the reference.
    # Truly foreign objects (Paginator, plugin instances) still drop; reconstructing
    # generated-page render objects (_paginator) from the plan is S14's concern.
    src = getattr(obj, "source_path", None)
    if isinstance(src, Path):
        return src
    return _DROP


def to_plain_data(obj: Any) -> dict[str, Any]:
    """Pickle-safe plain ``dict`` projection of a mapping (drops runtime objects).

    The transport-safe replacement for a bare ``proxy_to_plain`` on metadata/config:
    it both flattens ``MappingProxyType`` and drops non-frontmatter leaves (live
    Page/Section refs, callables) that would make the plan unpicklable. Exposed so
    the parity test can compare a PageView's metadata against the live page's on the
    same plain-data footing.
    """
    result = _plain_value(obj)
    return result if isinstance(result, dict) else {}


__all__ = [
    "PageView",
    "RenderPlan",
    "RenderPlanNavigation",
    "RenderPlanTaxonomy",
    "ShardPageMeta",
    "XRefEntry",
    "assemble_render_plan",
    "assert_picklable",
    "page_view_from_live_page",
    "shard_meta_from_live_pages",
    "shard_meta_from_pages",
]


# ---------------------------------------------------------------------------
# Lightweight per-page view
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PageView:
    """
    A lightweight, picklable view of a page — everything a render worker needs to
    *link to / list / look up* a page in another shard, with no parsed body.

    Substitutable for :class:`PageSnapshot` wherever a template iterates a page
    collection (``section.pages``, a taxonomy term, the page-view map): it mirrors
    the snapshot's read surface but carries only metadata, never ``parsed_html``.

    Identity is ``(source_path, content_hash)`` (matching PageSnapshot); equality is
    structural (all fields) so the parity test catches any field drift.
    """

    # Identity / routing
    title: str
    href: str  # public URL WITH baseurl (== page.href)
    site_path: str  # site-relative path WITHOUT baseurl (== page._path)
    source_path: Path  # primary identity + get_page()/xref-by_path key
    output_path: Path
    slug: str
    ref_id: str | None  # frontmatter `id` (xref by_id); None when unset
    template_name: str

    # Ordering / taxonomy inputs
    date: datetime | None
    weight: float
    tags: tuple[str, ...]
    categories: tuple[str, ...]

    # Listing/SEO content surrogates
    excerpt: str
    meta_description: str
    reading_time: int
    word_count: int
    toc_items: tuple[dict[str, Any], ...]

    # Verification / arbitrary frontmatter
    content_hash: str
    metadata: dict[str, Any]  # always a plain (picklable) dict

    # Membership / scoping
    section_path: Path | None  # resolve to RenderPlan.sections by path (no back-ref)
    version: str | None
    is_generated: bool

    # --- PageSnapshot-compatible template surface -------------------------

    @property
    def params(self) -> dict[str, Any]:
        """Alias for metadata (template compatibility, matches PageSnapshot)."""
        return self.metadata

    @property
    def type(self) -> str | None:
        return self.metadata.get("type")

    @property
    def variant(self) -> str | None:
        return self.metadata.get("variant") or self.metadata.get("layout")

    @property
    def url(self) -> str:
        """Public URL (href). Convenience for templates that read ``page.url``."""
        return self.href

    def __hash__(self) -> int:
        # Identity hash (cheap, body-free); structural __eq__ still discriminates.
        return hash((self.source_path, self.content_hash))


def _safe_weight(value: Any) -> float:
    """Coerce a frontmatter weight to float (mirrors content._safe_weight)."""
    if value is None:
        return float("inf")
    try:
        return float(value)
    except ValueError, TypeError:
        return float("inf")


def page_view_from_snapshot(ps: PageSnapshot, *, site_path: str) -> PageView:
    """
    Build a :class:`PageView` from an already-built :class:`PageSnapshot`.

    Reuses the snapshot's coercion work (output_path, excerpt, hashes, ...). The
    one thing not on a PageSnapshot is the baseurl-free ``site_path`` (``page._path``),
    which the caller supplies from the live page.
    """
    metadata = to_plain_data(ps.metadata)
    section_path = (
        ps.section.path if ps.section is not None and ps.section is not NO_SECTION else None
    )
    return PageView(
        title=ps.title,
        href=ps.href,
        site_path=site_path,
        source_path=ps.source_path,
        output_path=ps.output_path,
        slug=_infer_slug(metadata, ps.source_path),
        ref_id=_coerce_ref_id(metadata.get("id")),
        template_name=ps.template_name,
        date=_parse_date(metadata.get("date")),
        weight=_safe_weight(metadata.get("weight")),
        tags=ps.tags,
        categories=ps.categories,
        excerpt=ps.excerpt,
        meta_description=ps.meta_description,
        reading_time=ps.reading_time,
        word_count=ps.word_count,
        toc_items=ps.toc_items,
        content_hash=ps.content_hash,
        metadata=metadata,
        section_path=section_path,
        version=metadata.get("version") or metadata.get("_version"),
        is_generated=bool(metadata.get("_generated")),
    )


def page_view_from_live_page(page: PageLike, site: SiteLike) -> PageView:
    """
    Build a :class:`PageView` directly from a freshly-parsed *live* page — the S13
    map step, with no :class:`PageSnapshot`/:class:`SiteSnapshot` in hand.

    A shard worker parses its own ~1/N of the corpus into its own heap; it never
    builds a whole-site snapshot. This reuses the per-page snapshot field
    derivations (``_snapshot_page_initial``: ``output_path``, ``template_name``,
    ``excerpt``, ``content_hash``, ``reading_time``, ...) so the view is
    byte-identical to :func:`page_view_from_snapshot` — then sources ``section_path``
    from the live page, because a transient per-page snapshot has no resolved section
    (sections are resolved only in the whole-site recursive pass, which a worker does
    not run). ``page._section_path`` is the same value the resolved snapshot section
    would carry.
    """
    from bengal.snapshots.content import _snapshot_page_initial

    ps = _snapshot_page_initial(page, site)
    pv = page_view_from_snapshot(ps, site_path=_live_path(page, ps))
    section_path = getattr(page, "_section_path", None)
    if section_path != pv.section_path:
        pv = dataclasses.replace(pv, section_path=section_path)
    return pv


def _infer_slug(metadata: Mapping[str, Any], source_path: Path) -> str:
    from bengal.core.page.metadata_helpers import infer_slug

    return infer_slug(metadata, source_path)


def _parse_date(value: Any) -> datetime | None:
    from bengal.utils.primitives.dates import parse_date

    return parse_date(value)


def _coerce_ref_id(value: Any) -> str | None:
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# Per-shard metadata (map output)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class XRefEntry:
    """A single picklable cross-reference edge a page contributes to the index.

    ``kind`` is one of ``by_path``/``by_slug``/``by_id``/``by_heading``/``by_anchor``
    (mirrors ``Site.xref_index``). The parent reduces these into the resolved index,
    mapping each edge's ``page_source_path`` to a :class:`PageView`.
    """

    kind: str
    key: str
    page_source_path: Path
    anchor_id: str | None = None
    version: str | None = None


@dataclass(frozen=True, slots=True)
class ShardPageMeta:
    """
    Lightweight, picklable metadata a worker returns after parsing ITS shard.

    Carries the per-page page-views plus the page-*derived* global edges the parent
    reduces into the RenderPlan. The section/menu structure is, for S11, sourced
    from the parent's already-built snapshot (see module docstring); S13 will add
    those fields here when the parent stops pre-building the snapshot.
    """

    shard_index: int
    page_views: tuple[PageView, ...]
    # (taxonomy_kind, term, page_source_path) membership edges.
    taxonomy_terms: tuple[tuple[str, str, Path], ...] = ()
    xref_entries: tuple[XRefEntry, ...] = ()
    # (page_source_path, ordered related page_source_paths) — related resolved from
    # metadata at the barrier (plan: related is metadata-only, not a body dependency).
    related_pairs: tuple[tuple[Path, tuple[Path, ...]], ...] = ()
    estimated_render_cost: float = 0.0


def shard_meta_from_pages(
    pages: Sequence[PageLike],
    snapshot: SiteSnapshot,
    *,
    shard_index: int,
    site: SiteLike,
) -> ShardPageMeta:
    """
    Build a :class:`ShardPageMeta` for a slice of pages (the map step).

    For S11 this derives the metadata from the already-built ``snapshot`` (so it is
    exercised without the S13 actor protocol). The shape is identical to what a
    real worker produces from its own parse — the worker swaps the snapshot lookup
    for its freshly-parsed pages.

    Args:
        pages: the live pages in this shard.
        snapshot: the whole-site snapshot (source of per-page PageSnapshots).
        shard_index: this shard's index (for deterministic bookkeeping).
        site: the live site (for ``page._path`` and ``root_path``).
    """
    snap_by_path: dict[Path, PageSnapshot] = {p.source_path: p for p in snapshot.pages}

    page_views: list[PageView] = []
    taxonomy_terms: list[tuple[str, str, Path]] = []
    xref_entries: list[XRefEntry] = []
    related_pairs: list[tuple[Path, tuple[Path, ...]]] = []
    cost = 0.0

    for page in pages:
        ps = snap_by_path.get(page.source_path)
        if ps is None:
            continue
        pv = page_view_from_snapshot(ps, site_path=_live_path(page, ps))
        page_views.append(pv)
        cost += ps.estimated_render_ms

        # Taxonomy membership edges (tags + categories).
        taxonomy_terms.extend(("tags", tag, pv.source_path) for tag in pv.tags)
        taxonomy_terms.extend(("categories", cat, pv.source_path) for cat in pv.categories)

        xref_entries.extend(_xref_entries_for(page, pv, site))

        related = _related_source_paths(page)
        if related:
            related_pairs.append((pv.source_path, related))

    return ShardPageMeta(
        shard_index=shard_index,
        page_views=tuple(page_views),
        taxonomy_terms=tuple(taxonomy_terms),
        xref_entries=tuple(xref_entries),
        related_pairs=tuple(related_pairs),
        estimated_render_cost=cost,
    )


def shard_meta_from_live_pages(
    pages: Sequence[PageLike],
    site: SiteLike,
    *,
    shard_index: int,
) -> ShardPageMeta:
    """
    Build a :class:`ShardPageMeta` from a worker's OWN freshly-parsed pages — the
    real S13 map step (vs :func:`shard_meta_from_pages`, which reads a pre-built
    parent snapshot and exists only to exercise the contract without the actor
    protocol).

    A shard worker parses ~1/N of the corpus into its own heap and emits this
    picklable, body-free metadata; the parsed bodies never leave the worker. The
    page-derived edges (page-views, taxonomy memberships, xref entries) are all
    worker-local, derived per page exactly as the snapshot path derives them.

    ``related_pairs`` are DEFERRED: ``related_posts`` is a global computation over
    the whole-site taxonomy union, so it is resolved at the barrier by the parent (a
    worker holding only its shard cannot compute it) — never here. This is the one
    deliberate divergence from :func:`shard_meta_from_pages`.
    """
    from bengal.snapshots.scheduling import _estimate_render_time

    page_views: list[PageView] = []
    taxonomy_terms: list[tuple[str, str, Path]] = []
    xref_entries: list[XRefEntry] = []
    cost = 0.0

    for page in pages:
        pv = page_view_from_live_page(page, site)
        page_views.append(pv)
        # Matches PageSnapshot.estimated_render_ms (the snapshot path's cost source).
        cost += _estimate_render_time(page)

        taxonomy_terms.extend(("tags", tag, pv.source_path) for tag in pv.tags)
        taxonomy_terms.extend(("categories", cat, pv.source_path) for cat in pv.categories)
        xref_entries.extend(_xref_entries_for(page, pv, site))

    return ShardPageMeta(
        shard_index=shard_index,
        page_views=tuple(page_views),
        taxonomy_terms=tuple(taxonomy_terms),
        xref_entries=tuple(xref_entries),
        related_pairs=(),  # barrier-computed (global); see docstring
        estimated_render_cost=cost,
    )


def _live_path(page: PageLike, ps: PageSnapshot) -> str:
    """Site-relative path (page._path); fall back to the snapshot href."""
    value = getattr(page, "_path", None)
    if isinstance(value, str) and value:
        return value
    return ps.href


def _xref_entries_for(page: PageLike, pv: PageView, site: SiteLike) -> list[XRefEntry]:
    """Cross-reference edges a page contributes (mirrors content._build_xref_index).

    Generated pages (tag/archive/pagination) are skipped: the live xref index is
    built in the content phase *before* those pages exist, so they are never xref
    targets — matching that keeps the plan's index byte-faithful to ``site.xref_index``.
    """
    if pv.is_generated:
        return []

    from bengal.build.contracts.keys import xref_path_key

    entries: list[XRefEntry] = []
    src = pv.source_path

    content_dir = site.root_path / "content"
    try:
        src.relative_to(content_dir)
    except ValueError:
        pass  # generated/out-of-tree page — not path-indexed
    else:
        entries.append(XRefEntry("by_path", xref_path_key(src, site.root_path), src))

    if pv.slug:
        entries.append(XRefEntry("by_slug", pv.slug, src))
    if pv.ref_id:
        entries.append(XRefEntry("by_id", pv.ref_id, src))

    for toc_item in pv.toc_items:
        heading_text = (toc_item.get("title") or "").lower()
        anchor_id = toc_item.get("id") or ""
        if heading_text and anchor_id:
            entries.append(XRefEntry("by_heading", heading_text, src, anchor_id=anchor_id))
            entries.append(
                XRefEntry(
                    "by_anchor", anchor_id.lower(), src, anchor_id=anchor_id, version=pv.version
                )
            )
    return entries


def _related_source_paths(page: PageLike) -> tuple[Path, ...]:
    """Ordered source_paths of a page's pre-computed related posts (metadata-only)."""
    related = getattr(page, "related_posts", None)
    if not related:
        return ()
    out: list[Path] = []
    for r in related:
        sp = getattr(r, "source_path", None)
        if sp is not None:
            out.append(sp)
    return tuple(out)


# ---------------------------------------------------------------------------
# Page-view-ified plan components
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RenderPlanNavigation:
    """Page-view-ified analog of :class:`NavigationPlan` (no nav_trees).

    ``nav_trees`` are intentionally excluded — they hold live Page/Section refs and
    are rebuilt worker-side from ``sections``+``pages`` (saga S13).
    """

    menus: dict[str, tuple[MenuItemSnapshot, ...]]
    top_level_pages: tuple[PageView, ...]
    top_level_sections: tuple[SectionSnapshot, ...]


@dataclass(frozen=True, slots=True)
class RenderPlanTaxonomy:
    """Page-view-ified taxonomy, mirroring the live ``Site.taxonomies`` shape.

    ``taxonomies`` is ``{kind: {slug: {"name", "slug", "pages": tuple[PageView]}}}`` —
    the exact structure template functions read off ``site.taxonomies`` (``tag_data
    ['pages']``/``['name']``/``['slug']``). NB: this is built from the *live*
    ``site.taxonomies`` (slug-keyed), **not** from ``SiteSnapshot.taxonomy``, whose
    page lists are silently empty because ``_snapshot_taxonomies`` mis-iterates the
    ``{name,slug,pages}`` term dict (a pre-existing latent bug; the live render path
    reads ``site.taxonomies`` directly, so it is unaffected — and so is this).
    ``tag_pages`` is the filtered tag→pages cache (matches builder._compute_tag_pages).
    """

    taxonomies: dict[str, dict[str, dict[str, Any]]]
    tag_pages: dict[str, tuple[PageView, ...]]


# ---------------------------------------------------------------------------
# The assembled global plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RenderPlan:
    """The immutable, picklable global render world shipped to every shard worker."""

    # Content (page-view-ified — no bodies)
    pages: tuple[PageView, ...]
    regular_pages: tuple[PageView, ...]
    pages_by_path: dict[Path, PageView]  # get_page() / xref by_path lookups
    sections: tuple[SectionSnapshot, ...]
    root_section: SectionSnapshot

    # Cross-page indexes
    navigation: RenderPlanNavigation
    taxonomy: RenderPlanTaxonomy
    xref_index: dict[str, Any]  # {by_path/by_slug/by_id/by_heading/by_anchor: ...}
    related_index: dict[Path, tuple[Path, ...]]  # source_path -> related source_paths

    # Config (plain dicts — proxy-flattened)
    config: dict[str, Any]
    params: dict[str, Any]
    data: dict[str, Any]
    config_snapshot: ConfigSnapshot | None

    # i18n / versioning
    menu_localized: dict[str, dict[str, tuple[MenuItemSnapshot, ...]]]
    current_language: str | None
    versioning_enabled: bool
    versions: tuple[dict[str, Any], ...]

    # Scalars / paths / metadata
    baseurl: str
    root_path: Path
    output_dir: Path
    bengal_metadata: dict[str, Any]
    schedule_template_groups: dict[str, tuple[Path, ...]]
    generated_page_assignments: dict[Path, int]
    snapshot_time: float = 0.0

    @classmethod
    def from_site(cls, site: SiteLike, snapshot: SiteSnapshot) -> RenderPlan:
        """
        Build a RenderPlan directly from a built site + snapshot (the whole-site
        reduce). Equivalent to :func:`assemble_render_plan` over a single shard
        covering every page — the canonical oracle for the S11 parity test, and the
        path the S13 parent uses once it has merged whole-site metadata.
        """
        whole = shard_meta_from_pages(list(site.pages), snapshot, shard_index=0, site=site)
        return assemble_render_plan([whole], snapshot=snapshot, site=site)


def assemble_render_plan(
    shard_metas: Sequence[ShardPageMeta],
    *,
    snapshot: SiteSnapshot,
    site: SiteLike,
) -> RenderPlan:
    """
    Reduce per-shard metadata into one immutable :class:`RenderPlan` (the barrier).

    The page-derived indexes (page-view map, taxonomy, xref, related) are assembled
    from the union of ``shard_metas`` with a single deterministic global ordering, so
    the result is independent of how pages were sharded. The section/menu/config
    structure is page-view-ified from the parent's ``snapshot`` (see module docstring).
    """
    # --- 1. Global page-view map + deterministic ordering ----------------
    pv_by_path: dict[Path, PageView] = {}
    for meta in shard_metas:
        for pv in meta.page_views:
            pv_by_path[pv.source_path] = pv

    # The reduce assumes shards are disjoint (a page is parsed by exactly one
    # worker). Enforce it at the barrier: silent last-wins overwrite would drop a
    # page from the cover and corrupt output, the hardest class of S13 bug to debug.
    total_views = sum(len(m.page_views) for m in shard_metas)
    if total_views != len(pv_by_path):
        counts: dict[Path, int] = {}
        for m in shard_metas:
            for pv in m.page_views:
                counts[pv.source_path] = counts.get(pv.source_path, 0) + 1
        dupes = sorted(sp for sp, c in counts.items() if c > 1)
        raise ValueError(
            f"overlapping shards: {total_views} page-views collapsed to "
            f"{len(pv_by_path)} unique source_paths (duplicates: {dupes[:5]})"
        )

    # Deterministic global order: (weight, source_path). Independent of how pages
    # were sharded, so the plan is identical across worker counts.
    ordered_pages = tuple(
        sorted(pv_by_path.values(), key=lambda pv: (pv.weight, str(pv.source_path)))
    )

    regular_pages = tuple(
        pv
        for pv in ordered_pages
        if not pv.is_generated and pv.source_path.stem not in ("index", "_index")
    )

    # --- 2. Taxonomy (page-view-ified from the live site.taxonomies) -----
    # The barrier reuses the parent's collected taxonomy (slug-keyed
    # {name,slug,pages}); we only swap the live Page lists for body-free
    # PageViews. The per-shard taxonomy_terms edges are the S13 input for when the
    # parent rebuilds taxonomies from scratch; for S11 the parent already has them.
    taxonomies = _page_view_ify_taxonomies(getattr(site, "taxonomies", {}) or {}, pv_by_path)
    tag_pages = _tag_pages(taxonomies)

    # --- 3. Frozen xref index --------------------------------------------
    xref_index = _assemble_xref_index(shard_metas, pv_by_path)

    # --- 4. Related index -------------------------------------------------
    related_index: dict[Path, tuple[Path, ...]] = {
        sp: related for meta in shard_metas for sp, related in meta.related_pairs
    }

    # --- 5. Sections (page-view-ified) -----------------------------------
    sections, root_section = _relink_all_sections(snapshot, pv_by_path)

    # --- 6. Navigation (menus + top-level, page-view-ified) --------------
    navigation = _relink_navigation(snapshot, pv_by_path, sections)

    # --- 7. Config / i18n / versioning / scalars -------------------------
    config = to_plain_data(snapshot.config)
    params = to_plain_data(snapshot.params)
    data = to_plain_data(snapshot.data)

    menu_localized = _relink_menu_localized(site, pv_by_path, sections)
    bengal_metadata = _build_bengal_metadata(site)

    schedule_template_groups = {
        name: tuple(p.source_path for p in pages)
        for name, pages in snapshot.schedule.template_groups.items()
    }

    return RenderPlan(
        pages=ordered_pages,
        regular_pages=regular_pages,
        pages_by_path=dict(pv_by_path),
        sections=sections,
        root_section=root_section,
        navigation=navigation,
        taxonomy=RenderPlanTaxonomy(taxonomies=taxonomies, tag_pages=tag_pages),
        xref_index=xref_index,
        related_index=related_index,
        config=config,
        params=params,
        data=data,
        # Not shipped: the render context rebuilds ConfigContext from the raw config
        # itself (rendering/context/__init__.py: ConfigSnapshot.from_dict(site.config)),
        # and ConfigSnapshot holds a MappingProxyType (unpicklable). The worker
        # rebuilds it from `config` the same way — so carrying it would be redundant
        # and break spawn transport.
        config_snapshot=None,
        menu_localized=menu_localized,
        current_language=getattr(site, "current_language", None),
        versioning_enabled=bool(getattr(site, "versioning_enabled", False)),
        versions=tuple(getattr(site, "versions", []) or []),
        baseurl=getattr(site, "baseurl", "") or "",
        root_path=site.root_path,
        output_dir=site.output_dir,
        bengal_metadata=bengal_metadata,
        schedule_template_groups=schedule_template_groups,
        generated_page_assignments={},  # populated by the S12 sharder
        snapshot_time=snapshot.snapshot_time,
    )


# ---------------------------------------------------------------------------
# Reduce helpers
# ---------------------------------------------------------------------------


def _page_view_ify_taxonomies(
    site_taxonomies: Mapping[str, Any],
    pv_by_path: dict[Path, PageView],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Convert live ``site.taxonomies`` to a body-free, picklable PageView structure.

    Preserves the ``{kind: {slug: {"name","slug","pages": tuple[PageView]}}}`` shape
    and the live page ordering within each term (so render output matches), swapping
    each live Page for its PageView. Tolerant of either the ``{name,slug,pages}`` term
    dict (the real shape) or a bare page list (defensive).
    """
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for kind, terms in site_taxonomies.items():
        if not hasattr(terms, "items"):
            continue
        kind_out: dict[str, dict[str, Any]] = {}
        for slug, term_data in terms.items():
            if isinstance(term_data, dict):
                page_list = term_data.get("pages", ())
                name = term_data.get("name", slug)
            else:
                page_list = term_data
                name = slug
            views = _pv_tuple(list(page_list), pv_by_path)
            kind_out[slug] = {"name": name, "slug": slug, "pages": views}
        out[kind] = kind_out
    return out


def _tag_pages(
    taxonomies: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, tuple[PageView, ...]]:
    """Filtered tag->pages (mirrors builder._compute_tag_pages filtering)."""
    out: dict[str, tuple[PageView, ...]] = {}
    for tag_slug, term_data in taxonomies.get("tags", {}).items():
        views = term_data.get("pages", ())
        filtered = tuple(
            pv
            for pv in views
            if not pv.is_generated
            and "content/api" not in str(pv.source_path)
            and "content/cli" not in str(pv.source_path)
        )
        out[tag_slug] = filtered
    return out


def _assemble_xref_index(
    shard_metas: Sequence[ShardPageMeta],
    pv_by_path: dict[Path, PageView],
) -> dict[str, Any]:
    """Reduce xref edges into the 5-index structure, keyed to PageViews.

    Mirrors ``Site.xref_index`` shape:
      by_path: key -> PageView; by_slug: slug -> [PageView];
      by_id: id -> PageView; by_heading: text -> [(PageView, anchor)];
      by_anchor: anchor -> [(PageView, anchor, version)].
    Multi-valued indexes are ordered by source_path for determinism.
    """
    by_path: dict[str, PageView] = {}
    by_slug: dict[str, list[PageView]] = {}
    by_id: dict[str, PageView] = {}
    by_heading: dict[str, list[tuple[PageView, str]]] = {}
    by_anchor: dict[str, list[tuple[PageView, str, str | None]]] = {}

    # Stable iteration: sort edges by (kind, key, source_path) so list order is
    # deterministic regardless of shard arrival order.
    edges: list[XRefEntry] = []
    for meta in shard_metas:
        edges.extend(meta.xref_entries)
    edges.sort(key=lambda e: (e.kind, e.key, str(e.page_source_path), e.anchor_id or ""))

    for e in edges:
        pv = pv_by_path.get(e.page_source_path)
        if pv is None:
            continue
        if e.kind == "by_path":
            by_path[e.key] = pv
        elif e.kind == "by_slug":
            by_slug.setdefault(e.key, []).append(pv)
        elif e.kind == "by_id":
            by_id[e.key] = pv
        elif e.kind == "by_heading":
            by_heading.setdefault(e.key, []).append((pv, e.anchor_id or ""))
        elif e.kind == "by_anchor":
            by_anchor.setdefault(e.key, []).append((pv, e.anchor_id or "", e.version))

    return {
        "by_path": by_path,
        "by_slug": {k: tuple(v) for k, v in by_slug.items()},
        "by_id": by_id,
        "by_heading": {k: tuple(v) for k, v in by_heading.items()},
        "by_anchor": {k: tuple(v) for k, v in by_anchor.items()},
    }


def _relink_all_sections(
    snapshot: SiteSnapshot,
    pv_by_path: dict[Path, PageView],
) -> tuple[tuple[SectionSnapshot, ...], SectionSnapshot]:
    """Page-view-ify every SectionSnapshot, preserving the tree (mirrors builder).

    Returns ``(all_sections, root_section)``. Page tuples and ``index_page`` are
    swapped to PageViews; ``metadata`` proxies are flattened; the subsection tree is
    rebuilt depth-first with the same parent/root staleness profile the builder
    produces, so section *data* is faithful.
    """
    cache: dict[int, SectionSnapshot] = {}

    def relink(orig: SectionSnapshot, parent_new: SectionSnapshot | None) -> SectionSnapshot:
        if id(orig) in cache:
            return cache[id(orig)]
        shallow = dataclasses.replace(
            orig,
            pages=_pv_tuple(orig.pages, pv_by_path),
            sorted_pages=_pv_tuple(orig.sorted_pages, pv_by_path),
            regular_pages=_pv_tuple(orig.regular_pages, pv_by_path),
            index_page=_pv_one(orig.index_page, pv_by_path),
            metadata=to_plain_data(orig.metadata),
            parent=parent_new,
            root=None,  # recomputed in the post-pass against relinked objects
            subsections=(),
            sorted_subsections=(),
        )
        cache[id(orig)] = shallow
        subs = tuple(relink(s, shallow) for s in orig.subsections)
        sorted_subs = tuple(relink(s, shallow) for s in orig.sorted_subsections)
        full = dataclasses.replace(shallow, subsections=subs, sorted_subsections=sorted_subs)
        cache[id(orig)] = full
        return full

    roots = [s for s in snapshot.sections if s.parent is None]
    for r in roots:
        relink(r, None)
    # Relink any disconnected sections too (defensive; mirrors builder).
    for s in snapshot.sections:
        if id(s) not in cache:
            relink(s, None)

    # Set root references (post-pass, like builder).
    def find_root(s: SectionSnapshot) -> SectionSnapshot:
        cur = s
        while cur.parent is not None:
            cur = cur.parent
        return cur

    for orig_id, new in list(cache.items()):
        if new.root is None:
            cache[orig_id] = dataclasses.replace(new, root=find_root(new))

    all_sections = tuple(cache[id(s)] for s in snapshot.sections if id(s) in cache)
    root_new = cache.get(id(snapshot.root_section))
    if root_new is None:
        root_new = _relink_one_section(snapshot.root_section, pv_by_path)
    return all_sections, root_new


def _relink_one_section(orig: SectionSnapshot, pv_by_path: dict[Path, PageView]) -> SectionSnapshot:
    """Relink a single SectionSnapshot's page tuples as a standalone (no tree).

    Used only as a defensive fallback for sections not reached by the recursive
    relink; null out the tree refs so original (proxy-carrying) parent/root/
    subsection objects can never leak into the picklable plan.
    """
    return dataclasses.replace(
        orig,
        pages=_pv_tuple(orig.pages, pv_by_path),
        sorted_pages=_pv_tuple(orig.sorted_pages, pv_by_path),
        regular_pages=_pv_tuple(orig.regular_pages, pv_by_path),
        index_page=_pv_one(orig.index_page, pv_by_path),
        metadata=to_plain_data(orig.metadata),
        parent=None,
        root=None,
        subsections=(),
        sorted_subsections=(),
    )


def _pv_tuple(pages: Sequence[Any], pv_by_path: dict[Path, PageView]) -> tuple[PageView, ...]:
    return tuple(pv for pv in (_pv_one(p, pv_by_path) for p in pages) if pv is not None)


def _pv_one(page: Any, pv_by_path: dict[Path, PageView]) -> PageView | None:
    """Resolve a page-like (or PageSnapshot) to its PageView by source_path."""
    sp = getattr(page, "source_path", None) if page is not None else None
    return pv_by_path.get(sp) if sp is not None else None


def _relink_navigation(
    snapshot: SiteSnapshot,
    pv_by_path: dict[Path, PageView],
    sections: tuple[SectionSnapshot, ...],
) -> RenderPlanNavigation:
    sec_by_path = {s.path: s for s in sections if s.path is not None}
    menus = {
        name: tuple(_relink_menu_item(item, pv_by_path, sec_by_path) for item in items)
        for name, items in snapshot.navigation.menus.items()
    }
    top_pages = _pv_tuple(snapshot.navigation.top_level_pages, pv_by_path)
    top_sections = tuple(
        (sec_by_path.get(s.path) if s.path is not None else None)
        or _relink_one_section(s, pv_by_path)
        for s in snapshot.navigation.top_level_sections
    )
    return RenderPlanNavigation(
        menus=menus,
        top_level_pages=top_pages,
        top_level_sections=top_sections,
    )


def _relink_menu_item(
    item: MenuItemSnapshot,
    pv_by_path: dict[Path, PageView],
    sec_by_path: dict[Path, SectionSnapshot],
) -> MenuItemSnapshot:
    """Swap a menu item's page/section refs to body-free views; recurse children."""
    page_view = _pv_one(item.page, pv_by_path)
    section_view = (
        sec_by_path.get(item.section.path)
        if item.section is not None and item.section.path is not None
        else None
    )
    children = tuple(_relink_menu_item(c, pv_by_path, sec_by_path) for c in item.children)
    return dataclasses.replace(item, page=page_view, section=section_view, children=children)


def _relink_menu_localized(
    site: SiteLike,
    pv_by_path: dict[Path, PageView],
    sections: tuple[SectionSnapshot, ...],
) -> dict[str, dict[str, tuple[MenuItemSnapshot, ...]]]:
    """Snapshot + page-view-ify site.menu_localized (empty for non-i18n sites)."""
    from bengal.snapshots.scheduling import _snapshot_menu_item

    raw = getattr(site, "menu_localized", None) or {}
    if not raw:
        return {}

    sec_by_path = {s.path: s for s in sections if s.path is not None}
    page_cache: dict[int, Any] = {}
    section_cache: dict[int, Any] = {}
    out: dict[str, dict[str, tuple[MenuItemSnapshot, ...]]] = {}
    for lang, menus in raw.items():
        lang_menus: dict[str, tuple[MenuItemSnapshot, ...]] = {}
        for menu_name, items in menus.items():
            snapped = tuple(_snapshot_menu_item(item, page_cache, section_cache) for item in items)
            lang_menus[menu_name] = tuple(
                _relink_menu_item(item, pv_by_path, sec_by_path) for item in snapped
            )
        out[lang] = lang_menus
    return out


def _build_bengal_metadata(site: SiteLike) -> dict[str, Any]:
    try:
        from bengal.rendering.metadata import build_template_metadata

        meta = build_template_metadata(site)
        # Deep-flatten to picklable plain data (a theme could inject an object).
        return to_plain_data(meta) if isinstance(meta, Mapping) else {}
    except Exception:
        return {"engine": {"name": "Bengal SSG", "version": "unknown"}}


# ---------------------------------------------------------------------------
# Serialization guard (tests / debug only)
# ---------------------------------------------------------------------------


def assert_picklable(plan: RenderPlan) -> None:
    """
    Assert a RenderPlan is fully picklable and free of body/proxy/live-object leaks.

    Pickles the plan (round-trip), then walks the graph (bounded to plan dataclasses
    + plain containers) asserting no ``MappingProxyType``, no ``PageSnapshot``, and no
    ``NavTree`` survived the page-view-ification. Debug/test only — never the hot path.
    """
    import pickle

    pickle.loads(pickle.dumps(plan))  # raises if anything is unpicklable

    from bengal.snapshots.types import PageSnapshot as _PageSnapshot

    seen: set[int] = set()
    stack: list[Any] = [plan]
    containers = (tuple, list, set, frozenset, dict)
    while stack:
        obj = stack.pop()
        oid = id(obj)
        if oid in seen:
            continue
        seen.add(oid)

        if isinstance(obj, MappingProxyType):
            raise AssertionError("RenderPlan contains a MappingProxyType (won't pickle on spawn)")  # noqa: TRY004
        if isinstance(obj, _PageSnapshot):
            raise AssertionError("RenderPlan leaks a PageSnapshot (body not page-view-ified)")  # noqa: TRY004
        if type(obj).__name__ == "NavTree":
            raise AssertionError(
                "RenderPlan contains a NavTree (holds live refs; rebuild worker-side)"
            )

        if isinstance(obj, dict):
            stack.extend(obj.keys())
            stack.extend(obj.values())
        elif isinstance(obj, containers):
            stack.extend(obj)
        elif dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            stack.extend(getattr(obj, f.name) for f in dataclasses.fields(obj))
