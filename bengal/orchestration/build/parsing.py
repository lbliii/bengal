"""
Parsing phase for build pipeline.

Parses markdown content for all pages before snapshot creation.
Uses snapshot cache to skip re-parsing unchanged pages.

RFC: rfc-bengal-snapshot-engine (Snapshot Persistence section)
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.output import CLIOutput

logger = get_logger(__name__)


def phase_parse_content(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    pages_to_build: list[Page],
    parallel: bool = True,
    use_snapshot_cache: bool = True,
) -> int:
    """
    Parse markdown content for all pages before snapshot creation.
    
    Uses snapshot cache to skip re-parsing unchanged pages. This provides
    near-instant incremental builds by reusing pre-parsed HTML from the
    previous build.
    
    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        pages_to_build: List of pages to parse
        parallel: Whether to parse in parallel
        use_snapshot_cache: Whether to use snapshot cache for incremental parsing
        
    Returns:
        Number of pages that were parsed (vs cache hits)
        
    Side effects:
        - Populates page.parsed_ast with parsed HTML for all pages
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
                cli.info(f"  Parsing cache: {cache_hits}/{len(pages_to_build)} pages from cache ({cache_hits / len(pages_to_build) * 100:.1f}%)")
    
    # Parse pages that need parsing
    def parse_page(page: Page) -> None:
        """Parse a single page's markdown content."""
        # Create thread-local pipeline if needed
        if not hasattr(thread_local, "pipeline"):
            thread_local.pipeline = RenderingPipeline(
                orchestrator.site,
                dependency_tracker=None,  # No tracking during parsing phase
                quiet=True,
                build_stats=None,
                build_context=None,
            )
        
        # Parse content (stores in page.parsed_ast)
        thread_local.pipeline._parse_content(page)
    
    if pages_to_parse:
        if parallel and len(pages_to_parse) > 1:
            # Parallel parsing
            max_workers = min(len(pages_to_parse), 8)  # Reasonable limit
            with ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="Bengal-Parse",
            ) as executor:
                futures = {executor.submit(parse_page, page): page for page in pages_to_parse}
                
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
    
    parsing_duration_ms = (time.time() - parsing_start) * 1000
    if hasattr(orchestrator.stats, "parsing_time_ms"):
        orchestrator.stats.parsing_time_ms = parsing_duration_ms
    
    # Track cache statistics
    if hasattr(orchestrator.stats, "parsing_cache_hits"):
        orchestrator.stats.parsing_cache_hits = cache_hits
    
    return len(pages_to_parse)
