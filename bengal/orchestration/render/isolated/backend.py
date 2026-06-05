"""
Isolated (separate-heap) render backend driver — issue #350, saga S3.

Orchestrates a large *cold* build's render phase across separate-heap worker
processes, recovering the in-process→separate-heap throughput gap measured by
``benchmarks/probe_render_ceiling.py``. The flow:

1. **Partition** the render set into one cost-balanced chunk per worker
   (``partition.py``).
2. **Set output paths** on the parent's page objects so the parent (and the
   forked copies) agree on destinations, and postprocess can read them.
3. **Immortalize** the frozen snapshot so forked reads stay copy-on-write-shared
   (``snapshots/transport.py``; best-effort).
4. **Render each chunk in an isolated heap** — fork workers inherit the parsed
   world via COW and write HTML straight to disk (``worker.py``).
5. **Serial merge** (S4): replay each worker's accumulated page data + asset
   deps into the parent ``BuildContext`` so postprocess (search index, per-page
   JSON, llm-full, asset tracking) sees the whole site.

This backend is **cold-build / CLI / CI only** and is selected behind a
crossover gate (S5). The caller is expected to fall back to the in-process
thread path if :meth:`IsolatedRenderBackend.render` raises.
"""

from __future__ import annotations

import multiprocessing as mp
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

from .merge import merge_chunk_results
from .partition import partition_pages
from .worker import ForkRenderState, clear_fork_state, fork_render_chunk, install_fork_state

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats import BuildStats
    from bengal.protocols.core import PageLike

__all__ = ["IsolatedRenderBackend", "fork_available"]


def fork_available() -> bool:
    """Whether the fork start method is available on this platform."""
    return "fork" in mp.get_all_start_methods()


class IsolatedRenderBackend:
    """Renders a cold build's pages across separate-heap worker processes."""

    def __init__(self, site: Site) -> None:
        self.site = site

    def render(
        self,
        pages: Sequence[PageLike],
        *,
        build_context: BuildContext,
        num_workers: int,
        quiet: bool = True,
        stats: BuildStats | None = None,
        strategy: str = "balanced",
        immortalize: bool = True,
    ) -> int:
        """
        Render ``pages`` across ``num_workers`` separate heaps (fork).

        Returns the number of pages rendered. Raises on unrecoverable failure so
        the caller can fall back to the in-process render path.
        """
        n = len(pages)
        if n == 0:
            return 0
        num_workers = max(1, min(num_workers, n))

        chunks = partition_pages(pages, num_workers, strategy=strategy)
        logger.info(
            "isolated_render_start",
            pages=n,
            workers=num_workers,
            chunks=len(chunks),
            strategy=strategy,
            chunk_sizes=[len(c) for c in chunks],
        )

        self._set_output_paths(pages)

        if immortalize and build_context.snapshot is not None:
            self._immortalize_snapshot(build_context.snapshot)

        state = ForkRenderState(
            site=self.site,
            build_context=build_context,
            pages=pages,
            asset_ctx=getattr(build_context, "asset_manifest_ctx", None),
            quiet=quiet,
            changed_sources=None,  # cold build: render everything
        )

        results = self._run_fork_pool(chunks, state)

        merged = merge_chunk_results(build_context, results)
        logger.info(
            "isolated_render_complete",
            pages_rendered=merged.pages_rendered,
            errors=merged.error_count,
            page_data_merged=merged.page_data_count,
            external_refs_merged=merged.external_ref_count,
        )

        if stats is not None:
            stats.pages_rendered = merged.pages_rendered
            stats.render_isolation_used = True

        if merged.pages_rendered == 0 and n > 0:
            raise RuntimeError("isolated render produced no pages (all chunks failed)")

        for src, msg in merged.errors[:5]:
            logger.error("isolated_render_page_error", page=src, error=msg)

        return merged.pages_rendered

    def _run_fork_pool(self, chunks: list[list[int]], state: ForkRenderState) -> list[Any]:
        """Fork one worker per chunk, render, and collect picklable results."""
        ctx_mp = mp.get_context("fork")
        payloads = [(ci, chunk) for ci, chunk in enumerate(chunks)]

        # Install shared state BEFORE forking so workers inherit it via COW.
        install_fork_state(state)
        pool = ctx_mp.Pool(processes=len(chunks))
        try:
            results = pool.map(fork_render_chunk, payloads)
        finally:
            pool.close()
            pool.join()
            clear_fork_state()
        return results

    def _set_output_paths(self, pages: Sequence[PageLike]) -> None:
        """Pre-set output paths on the parent's pages (mirrors RenderOrchestrator).

        Forked workers inherit these, and the parent retains them for postprocess
        (sitemap/RSS/link health), which read ``page.output_path``.
        """
        from bengal.utils.paths.url_strategy import URLStrategy

        for page in pages:
            if getattr(page, "output_path", None):
                continue
            page.output_path = URLStrategy.compute_regular_page_output_path(page, self.site)

    def _immortalize_snapshot(self, snapshot: Any) -> None:
        try:
            from bengal.snapshots.transport import immortalize_snapshot

            count = immortalize_snapshot(snapshot)
            logger.debug("isolated_render_immortalized", objects=count)
        except Exception as e:  # immortalization is a perf nicety, never fatal
            logger.debug("isolated_render_immortalize_failed", error=str(e))
