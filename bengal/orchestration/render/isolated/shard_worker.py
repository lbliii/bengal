"""
Phase-2 shard worker — the parse leg (issue #350, saga S13).

The persistent two-phase shard build forks workers from a *small* parent (it has
only enumerated content *files* via :func:`~bengal.orchestration.render.isolated.partition.discover_content_files`,
never parsed them). Each worker then:

1. **parse-shard (this module's :func:`parse_shard`)** — parses its OWN ~1/N of the
   content files into fully body-filled live pages *in its own heap*, and
2. emits a lightweight, picklable :class:`~bengal.snapshots.render_plan.ShardPageMeta`
   (via :func:`~bengal.snapshots.render_plan.shard_meta_from_live_pages`, S13.1) for
   the barrier reduce.

Keeping the parsed bodies worker-local is the whole point: Phase 1 forked a parent
holding every parsed page and paid a copy-on-write tax (+39% render) reading that
shared mutable graph; here the parent holds no parsed pages, so there is nothing to
copy. (Saga S13.3 adds the render leg; S13.4 the persistent-actor protocol + barrier.)

The parse leg reproduces the in-process build's discovery + parsing phases exactly,
restricted to one shard:

- **construction** reuses :meth:`ContentDiscovery._create_page` unchanged (frontmatter
  parse, collection validation, i18n metadata, source-page record, versioning) so the
  resulting page is byte-identical to what full discovery produces — the only new work
  is reconstructing each file's owning :class:`Section` from its path (the small parent
  shipped a flat file list, not the section tree);
- **body-fill** reuses ``RenderingPipeline._parse_content`` — the exact call
  ``build/parsing.phase_parse_content`` makes — to populate ``html_content``/``toc``/
  ``excerpt``/``word_count`` (the fields :class:`PageView` needs);
- **output_path** is computed worker-side (``URLStrategy``), since the small parent
  never set it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .transport import RenderChunkResult

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import SectionLike, SiteLike
    from bengal.protocols.core import PageLike

    from .partition import ContentFile

__all__ = ["parse_shard", "render_shard"]


def parse_shard(
    files: Sequence[ContentFile],
    site: SiteLike,
    *,
    content_dir: Path | None = None,
    current_lang: str | None = None,
    quiet: bool = True,
) -> list[PageLike]:
    """
    Parse a shard of content files into fully body-filled live pages (S13 phase 1).

    Reproduces the in-process discovery + parsing phases for just this shard, into the
    caller's own heap. The returned pages carry ``html_content``/``toc``/``excerpt``/
    ``word_count``/``output_path`` — everything :func:`shard_meta_from_live_pages` needs
    to emit a :class:`ShardPageMeta`, and everything the render leg needs to render them
    without re-parsing. The bodies never leave this heap.

    Args:
        files: this worker's shard of discovered content files (from S12).
        site: the worker-local site context the parse reads (config, cascade, xref
            index, version config). In a real shard build this is reconstructed from a
            RenderPlan (S13.3); the tests pass the live built site, which is the parity
            oracle.
        content_dir: the content root (defaults to ``site.root_path / "content"``);
            used to decide which files are top-level (no section) vs sectioned.
        current_lang: language for i18n metadata enrichment (None for non-i18n sites).
        quiet: suppress per-page parse logging.

    Returns:
        The shard's fully-parsed live pages, in input order.
    """
    from bengal.content.discovery.content_discovery import ContentDiscovery
    from bengal.content.discovery.section_builder import SectionBuilder
    from bengal.rendering.pipeline import RenderingPipeline
    from bengal.utils.paths.url_strategy import URLStrategy

    root = content_dir if content_dir is not None else (site.root_path / "content")

    discovery = ContentDiscovery(root, site)
    section_builder = SectionBuilder(site)
    # One Section per shard directory: a page's section is its immediate parent dir
    # (Bengal nests a section per content subdirectory); top-level files (directly
    # under the content root) have no section, matching discovery's behaviour.
    section_cache: dict[Path, SectionLike] = {}

    def _section_for(source_path: Path) -> SectionLike | None:
        parent = source_path.parent
        if parent == root:
            return None
        section = section_cache.get(parent)
        if section is None:
            section = section_builder.create_section(parent)
            section_cache[parent] = section
        return section

    pages: list[PageLike] = [
        discovery._create_page(
            cf.source_path,
            current_lang=current_lang,
            section=_section_for(cf.source_path),
        )
        for cf in files
    ]

    # Body-fill: the markdown→HTML parse leg (shortcode expansion, parse_with_toc,
    # highlighting, HTML transform) that populates html_content/toc/excerpt/word_count.
    # Exactly the call build/parsing.phase_parse_content makes per page.
    pipeline = RenderingPipeline(site, quiet=quiet, build_stats=None, build_context=None)
    for page in pages:
        if not getattr(page, "output_path", None):
            page.output_path = URLStrategy.compute_regular_page_output_path(page, site)
        pipeline._parse_content(page)

    return pages


def render_shard(
    pages: Sequence[PageLike],
    site: SiteLike,
    build_context: BuildContext,
    *,
    chunk_index: int = 0,
    asset_ctx: Any = None,
    quiet: bool = True,
    changed_sources: set[Path] | None = None,
    block_cache: Any = None,
    highlight_cache: Any = None,
) -> RenderChunkResult:
    """
    Render a shard's OWN parsed pages → HTML on disk + a picklable RenderChunkResult
    (the S13 phase-2 render leg).

    The reusable render core for the persistent shard actor (S13.4): it takes *any*
    site object the render path will accept — the worker's reconstructed ``WorkerSite``
    (S13.3) in production, or the live built site in the parity tests — and renders the
    pages already living in this heap (from :func:`parse_shard`). HTML is written
    straight to ``page.output_path``; only the small accumulation (page data, asset
    deps, unresolved external refs, errors) crosses back, for the parent's serial merge
    (``merge.merge_chunk_results``, unchanged from S4).

    This mirrors the proven render body of ``worker.fork_render_chunk`` (S3) but decoupled
    from the fork-state module global — the persistent two-phase actor does not fork per
    chunk. (``worker.py`` is retired once S13.4 wires the actor; the brief overlap is
    intentional, to avoid a cross-import with the to-be-deleted Phase-1 module.)

    Args:
        pages: this shard's fully-parsed live pages (their bodies live in this heap).
        site: the render world — must answer the live-site reads the pipeline makes.
        build_context: per-shard accumulator (reset here; its accumulations are the
            return payload).
        chunk_index: this shard's index (for deterministic merge ordering).
        asset_ctx: AssetManifestContext for fingerprinted asset URLs / dep tracking.
        quiet: suppress per-page render logging.
        changed_sources: incremental hint (None for cold builds — render everything).
        block_cache / highlight_cache: per-worker caches; built here if not supplied.
    """
    import threading
    import time

    from bengal.orchestration.render.pipeline_runner import process_page_with_pipeline
    from bengal.orchestration.render.tracking import clear_thread_local_pipelines
    from bengal.rendering.assets import asset_manifest_context
    from bengal.rendering.template_functions.memo import set_build_context

    # Start clean: drop any inherited thread-local pipeline and reset the per-shard
    # accumulators + external-ref resolvers so the result is exactly this shard's
    # contribution (correct even if one worker process handles more than one shard).
    clear_thread_local_pipelines()
    build_context.clear_accumulated_page_data()
    build_context.clear_accumulated_assets()
    site._external_ref_resolvers = []
    site._external_ref_resolvers_lock = threading.Lock()

    if block_cache is None or highlight_cache is None:
        built_block, built_highlight = _build_worker_caches(site)
        block_cache = block_cache if block_cache is not None else built_block
        highlight_cache = highlight_cache if highlight_cache is not None else built_highlight

    set_build_context(build_context)

    errors: list[tuple[str, str]] = []
    rendered = 0
    start = time.perf_counter()
    manifest_cm = asset_manifest_context(asset_ctx) if asset_ctx is not None else _nullcontext()
    try:
        # process_page_with_pipeline enters icon_resolver.site_context(site) per page,
        # so only the asset-manifest context is needed here.
        with manifest_cm:
            for page in pages:
                try:
                    process_page_with_pipeline(
                        page,
                        site=site,
                        quiet=quiet,
                        stats=None,
                        build_context=build_context,
                        changed_sources=changed_sources,
                        block_cache=block_cache,
                        highlight_cache=highlight_cache,
                        output_collector=None,
                    )
                    rendered += 1
                except Exception as e:  # isolate per-page failures
                    src = getattr(getattr(page, "source_path", None), "name", "?")
                    errors.append((str(src), f"{type(e).__name__}: {e}"))
    finally:
        set_build_context(None)

    render_time_ms = (time.perf_counter() - start) * 1000

    page_data = tuple(build_context.get_accumulated_page_data())
    assets = tuple(
        (str(src), tuple(sorted(refs))) for src, refs in build_context.get_accumulated_assets()
    )
    external_refs: list[Any] = []
    resolvers = getattr(site, "_external_ref_resolvers", None)
    if isinstance(resolvers, list):
        for resolver in resolvers:
            external_refs.extend(getattr(resolver, "unresolved", ()))

    return RenderChunkResult(
        chunk_index=chunk_index,
        pages_rendered=rendered,
        render_time_ms=render_time_ms,
        errors=tuple(errors),
        page_data=page_data,
        assets=assets,
        external_refs=tuple(external_refs),
    )


def _build_worker_caches(site: SiteLike) -> tuple[Any, Any]:
    """Build this worker's block + highlight caches (best-effort; never fatal)."""
    block_cache: Any = None
    highlight_cache: Any = None
    try:
        from bengal.orchestration.render.block_cache import create_and_warm_block_cache

        block_cache = create_and_warm_block_cache(site)
    except Exception:
        block_cache = None
    try:
        from bengal.rendering.highlighting.cache import HighlightCache

        highlight_cache = HighlightCache(enabled=True)
    except Exception:
        highlight_cache = None
    return block_cache, highlight_cache


class _nullcontext:
    """Tiny no-op context manager (avoids importing contextlib for one use)."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> bool:
        return False
