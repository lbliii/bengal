"""
Separate-heap render workers for the isolated backend (issue #350, saga S3).

The **fork** worker is the efficient path: the parent installs its fully-parsed,
frozen render world as a module global *before* the fork pool is created, so each
forked worker inherits the entire Site/snapshot/BuildContext graph for free via
copy-on-write (no serialization). The worker renders only its assigned page
indices — writing HTML straight to disk — and returns a small picklable
``RenderChunkResult`` (per-page accumulations + stats + errors) for the parent's
serial merge phase.

Fork safety: the parent must install state and create the pool while no render
threads (or live-display threads) are running — see ``backend.py``. Each forked
worker is single-threaded, so thread-local pipelines and caches are naturally
per-worker.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .transport import RenderChunkResult

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols.core import PageLike

__all__ = ["ForkRenderState", "clear_fork_state", "fork_render_chunk", "install_fork_state"]


@dataclass
class ForkRenderState:
    """Parent-installed render world inherited by forked workers via COW."""

    site: Site
    build_context: BuildContext
    pages: Sequence[PageLike]
    asset_ctx: Any  # AssetManifestContext | None
    quiet: bool = True
    changed_sources: set[Path] | None = None


# Set in the parent BEFORE the fork pool is created; inherited (not pickled) by
# every forked worker. None in the parent outside an isolated render.
_FORK_STATE: ForkRenderState | None = None

# Per-worker caches, created lazily on first chunk and reused for the worker's
# lifetime. In a forked child these start unset (the parent has not rendered yet
# at fork time), so each worker builds its own — exactly the separate-heap model.
_WORKER_BLOCK_CACHE: Any = None
_WORKER_HIGHLIGHT_CACHE: Any = None
_WORKER_CACHES_READY = False


def install_fork_state(state: ForkRenderState) -> None:
    """Install the shared render world prior to forking workers."""
    global _FORK_STATE
    _FORK_STATE = state


def clear_fork_state() -> None:
    """Drop the parent's reference to the shared state after the render."""
    global _FORK_STATE
    _FORK_STATE = None


def _ensure_worker_caches(site: Site) -> tuple[Any, Any]:
    """Lazily build this worker's block + highlight caches (once per process)."""
    global _WORKER_BLOCK_CACHE, _WORKER_HIGHLIGHT_CACHE, _WORKER_CACHES_READY
    if not _WORKER_CACHES_READY:
        try:
            from bengal.orchestration.render.block_cache import create_and_warm_block_cache

            _WORKER_BLOCK_CACHE = create_and_warm_block_cache(site)
        except Exception:
            _WORKER_BLOCK_CACHE = None
        try:
            from bengal.rendering.highlighting.cache import HighlightCache

            _WORKER_HIGHLIGHT_CACHE = HighlightCache(enabled=True)
        except Exception:
            _WORKER_HIGHLIGHT_CACHE = None
        _WORKER_CACHES_READY = True
    return _WORKER_BLOCK_CACHE, _WORKER_HIGHLIGHT_CACHE


def fork_render_chunk(payload: tuple[int, list[int]]) -> RenderChunkResult:
    """
    Render one chunk in a forked worker. Returns a picklable result.

    Args:
        payload: ``(chunk_index, page_indices)`` — indices into the inherited
            ``ForkRenderState.pages`` sequence.

    Returns:
        ``RenderChunkResult`` with accumulations, stats, and per-page errors.
    """
    chunk_index, indices = payload
    state = _FORK_STATE
    if state is None:  # pragma: no cover - defensive; never happens under fork
        raise RuntimeError("fork render state not installed in worker")

    from bengal.orchestration.render.pipeline_runner import process_page_with_pipeline
    from bengal.orchestration.render.tracking import clear_thread_local_pipelines
    from bengal.rendering.template_functions.memo import set_build_context

    site = state.site
    ctx = state.build_context

    # This forked worker starts clean: drop any inherited thread-local pipeline
    # and reset the per-task accumulators so the returned result is exactly this
    # chunk's contribution (correct even if the pool hands one worker >1 chunk).
    clear_thread_local_pipelines()
    ctx.clear_accumulated_page_data()
    ctx.clear_accumulated_assets()
    # Reset the external-ref accumulator (and its lock) so this worker reports
    # only refs discovered in this run — not any inherited from the parent's
    # forked state (e.g. a prior build on a reused Site). The pipeline lazily
    # re-creates these on first use.
    import threading

    site._external_ref_resolvers = []
    site._external_ref_resolvers_lock = threading.Lock()

    block_cache, highlight_cache = _ensure_worker_caches(site)
    set_build_context(ctx)

    errors: list[tuple[str, str]] = []
    rendered = 0
    start = time.perf_counter()

    from bengal.rendering.assets import asset_manifest_context

    manifest_cm = (
        asset_manifest_context(state.asset_ctx) if state.asset_ctx is not None else _nullcontext()
    )
    try:
        # process_page_with_pipeline already enters icon_resolver.site_context(site)
        # per page, so we only need the asset-manifest context here.
        with manifest_cm:
            for i in indices:
                page = state.pages[i]
                try:
                    process_page_with_pipeline(
                        page,
                        site=site,
                        quiet=state.quiet,
                        stats=None,
                        build_context=ctx,
                        changed_sources=state.changed_sources,
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

    # Collect this chunk's accumulations for the parent's serial merge (S4).
    page_data = tuple(ctx.get_accumulated_page_data())
    assets = tuple((str(src), tuple(sorted(refs))) for src, refs in ctx.get_accumulated_assets())

    # Unresolved external references ([[ext:project:target]]) are accumulated per
    # rendering thread on site._external_ref_resolvers; collect this worker's so
    # the parent can reconcile them for the external-ref health validator. The
    # UnresolvedRef records are plain picklable dataclasses.
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


class _nullcontext:
    """Tiny no-op context manager (avoids importing contextlib for one use)."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> bool:
        return False
