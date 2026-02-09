"""
Parsing phase for build pipeline.

Parses markdown content for all pages before snapshot creation.
Uses snapshot cache to skip re-parsing unchanged pages.

RFC: rfc-bengal-snapshot-engine (Snapshot Persistence section)
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path as FilePath

    from bengal.core.page import Page
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.output import CLIOutput

logger = get_logger(__name__)


def phase_parse_content(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    pages_to_build: list[Page],
    parallel: bool = True,
    use_snapshot_cache: bool = True,
    changed_sources: set[FilePath] | None = None,
) -> int:
    """
    Parse markdown content for all pages before snapshot creation.

    Uses snapshot cache to skip re-parsing unchanged pages. This provides
    near-instant incremental builds by reusing pre-parsed HTML from the
    previous build.

    When changed_sources is provided, pages whose source file did NOT change
    are eligible for aggressive cache reuse — their markdown hasn't changed
    even though provenance expansion included them (e.g., taxonomy pages
    triggered by a related page's change). Only pages with changed sources
    are forced to re-parse.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        pages_to_build: List of pages to parse
        parallel: Whether to parse in parallel
        use_snapshot_cache: Whether to use snapshot cache for incremental parsing
        changed_sources: Optional set of changed file paths from file watcher.
                        Pages not in this set can reuse cached html_content.
                        (RFC: reactive-rebuild-architecture Phase 1b)

    Returns:
        Number of pages that were parsed (vs cache hits)

    Side effects:
        - Populates page.html_content with parsed HTML for all pages
        - Populates page.toc with table of contents
        - Updates orchestrator.stats.parsing_time_ms
        - Updates orchestrator.stats with cache hit statistics
    """
    if not pages_to_build:
        return 0

    from bengal.rendering.pipeline import RenderingPipeline
    from bengal.rendering.pipeline.thread_local import thread_local
    from bengal.snapshots.persistence import SnapshotCache, apply_cached_parsing

    parsing_start = time.time()

    # Try to load cached parsing data from previous build
    pages_to_parse = pages_to_build
    cache_hits = 0

    if use_snapshot_cache:
        cache_dir = orchestrator.site.root_path / ".bengal" / "cache" / "snapshots"
        snapshot_cache = SnapshotCache(cache_dir)
        cached_pages = snapshot_cache.load_page_cache()

        if cached_pages:
            pages_to_parse, pages_from_cache, cache_hits = apply_cached_parsing(
                pages_to_build, cached_pages
            )

            if cache_hits > 0:
                # Show cache effectiveness in verbose mode
                cli.info(
                    f"  Parsing cache: {cache_hits}/{len(pages_to_build)} pages from cache ({cache_hits / len(pages_to_build) * 100:.1f}%)"
                )

    # RFC: reactive-rebuild-architecture Phase 1b
    # When changed_sources is known, pages whose source file did NOT change
    # can skip re-parsing if they already have cached html_content from the
    # snapshot cache. Their markdown is identical — they're in pages_to_build
    # only because provenance cascade (e.g., taxonomy pages, navigation).
    if changed_sources and pages_to_parse:
        from pathlib import Path

        changed_set = {Path(p) for p in changed_sources}
        must_parse = []
        skipped = 0
        for page in pages_to_parse:
            src = getattr(page, "source_path", None)
            if src is not None and Path(src) not in changed_set:
                # Page's source didn't change — already has html_content from cache
                # or will get it from rendering (autodoc/generated pages)
                if getattr(page, "html_content", None):
                    skipped += 1
                    continue
            must_parse.append(page)

        if skipped > 0:
            cache_hits += skipped
            pages_to_parse = must_parse
            logger.info(
                "parsing_skipped_unchanged_sources",
                skipped=skipped,
                remaining=len(must_parse),
                changed_sources_count=len(changed_sources),
            )

    # Phase E: Load cached ASTs for pages that won't be re-parsed.
    # Pages with html_content from the snapshot cache still need their
    # _ast_cache populated for AST-first features (links, toc, plain_text)
    # and provenance hashing. Uses ContentASTCache loaded at build start.
    import hashlib

    from bengal.server.fragment_update import ContentASTCache

    _ast_cache_loaded = 0
    for page in pages_to_build:
        # Only populate AST for pages that already have cached html_content
        # (i.e., not in pages_to_parse — those will get ASTs from parsing)
        if page in pages_to_parse:
            continue
        raw = getattr(page, "_raw_content", None) or getattr(page, "content", None)
        if not isinstance(raw, str) or not raw:
            continue
        body_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        cached_ast = ContentASTCache.get_by_hash(page.source_path, body_hash)
        if cached_ast is not None:
            page._ast_cache = cached_ast  # type: ignore[attr-defined]
            _ast_cache_loaded += 1

    if _ast_cache_loaded > 0:
        logger.info(
            "ast_cache_loaded_for_cached_pages",
            loaded=_ast_cache_loaded,
            total_cached=len(pages_to_build) - len(pages_to_parse),
        )

    # Parse pages that need parsing
    def parse_page(page: Page) -> None:
        """Parse a single page's markdown content."""
        # Create thread-local pipeline if needed
        if not hasattr(thread_local, "pipeline"):
            thread_local.pipeline = RenderingPipeline(
                orchestrator.site,
                # No dependency tracking during parsing phase (EffectTracer handles this at render time)
                quiet=True,
                build_stats=None,
                build_context=None,
            )

        # Parse content (stores in page.html_content)
        thread_local.pipeline._parse_content(page)

    # RFC: reactive-rebuild-architecture Phase 3a
    # Wrap parsing with Patitas profiled_parse() when dev_mode is active.
    # This populates a ParseAccumulator with per-parse metrics (total_ms,
    # source_length, node_count) at zero overhead when disabled.
    _parse_metrics = None
    _use_profiling = getattr(orchestrator.site, "dev_mode", False)
    _profiler_ctx = None

    if _use_profiling and pages_to_parse:
        try:
            from patitas.profiling import profiled_parse

            _profiler_ctx = profiled_parse()
            _parse_metrics = _profiler_ctx.__enter__()
        except ImportError:
            _profiler_ctx = None

    try:
        if pages_to_parse:
            if parallel and len(pages_to_parse) > 1:
                # Parallel parsing
                max_workers = min(len(pages_to_parse), 8)  # Reasonable limit
                with ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="Bengal-Parse",
                ) as executor:
                    futures = {
                        executor.submit(parse_page, page): page for page in pages_to_parse
                    }

                    for future in as_completed(futures):
                        page = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(
                                "parsing_failed",
                                page=str(page.source_path),
                                error=str(e),
                                error_type=type(e).__name__,
                            )
                            if orchestrator.stats:
                                orchestrator.stats.add_error(
                                    Exception(f"Parsing failed for {page.source_path}: {e}"),
                                    category="parsing",
                                )
            else:
                # Sequential parsing
                for page in pages_to_parse:
                    try:
                        parse_page(page)
                    except Exception as e:
                        logger.error(
                            "parsing_failed",
                            page=str(page.source_path),
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        if orchestrator.stats:
                            orchestrator.stats.add_error(
                                Exception(f"Parsing failed for {page.source_path}: {e}"),
                                category="parsing",
                            )
    finally:
        if _profiler_ctx is not None:
            _profiler_ctx.__exit__(None, None, None)

    # Report profiling metrics if available
    if _parse_metrics is not None:
        summary = _parse_metrics.summary()
        logger.info(
            "patitas_parse_profiling",
            total_ms=summary.get("total_ms"),
            source_length=summary.get("source_length"),
            node_count=summary.get("node_count"),
            parse_calls=summary.get("parse_calls"),
            pages_parsed=len(pages_to_parse),
        )

    # Phase E: Populate ContentASTCache with ASTs from freshly parsed pages.
    # These will be persisted to disk in the build __init__.py after this phase.
    _ast_cache_stored = 0
    for page in pages_to_parse:
        page_ast = getattr(page, "_ast_cache", None)
        if page_ast is not None:
            raw = getattr(page, "_raw_content", None) or getattr(page, "content", None)
            if isinstance(raw, str) and raw:
                body_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
                ContentASTCache.put(page.source_path, body_hash, raw, page_ast)
                _ast_cache_stored += 1

    if _ast_cache_stored > 0:
        logger.info("ast_cache_stored_after_parsing", stored=_ast_cache_stored)

    parsing_duration_ms = (time.time() - parsing_start) * 1000
    if hasattr(orchestrator.stats, "parsing_time_ms"):
        orchestrator.stats.parsing_time_ms = parsing_duration_ms

    # Track cache statistics (include AST cache loads)
    if hasattr(orchestrator.stats, "parsing_cache_hits"):
        orchestrator.stats.parsing_cache_hits = cache_hits + _ast_cache_loaded

    return len(pages_to_parse)
