"""
Rendering orchestration for Bengal SSG.

Handles page rendering in both sequential and parallel modes.
"""

import concurrent.futures
import threading
from typing import TYPE_CHECKING, List, Optional, Any

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page
    from bengal.cache import DependencyTracker
    from bengal.utils.build_stats import BuildStats

# Thread-local storage for pipelines (reuse per thread, not per page!)
_thread_local = threading.local()


class RenderOrchestrator:
    """
    Handles page rendering.
    
    Responsibilities:
        - Sequential page rendering
        - Parallel page rendering with thread-local pipelines
        - Pipeline creation and management
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize render orchestrator.
        
        Args:
            site: Site instance containing pages and configuration
        """
        self.site = site
    
    def process(self, pages: List['Page'], parallel: bool = True, 
                tracker: Optional['DependencyTracker'] = None,
                stats: Optional['BuildStats'] = None) -> None:
        """
        Render pages (parallel or sequential).
        
        Args:
            pages: List of pages to render
            parallel: Whether to use parallel rendering
            tracker: Dependency tracker for incremental builds
            stats: Build statistics tracker
        """
        from bengal.rendering.pipeline import RenderingPipeline
        
        # PRE-PROCESS: Set output paths for pages being rendered
        # Note: This only sets paths for pages we're actually rendering.
        # Other pages should already have paths from previous builds or will get them when needed.
        self._set_output_paths_for_pages(pages)
        
        quiet = not self.site.config.get('verbose', False)
        
        # Use parallel rendering only for 5+ pages (avoid thread overhead for small batches)
        PARALLEL_THRESHOLD = 5
        if parallel and len(pages) >= PARALLEL_THRESHOLD:
            self._render_parallel(pages, tracker, quiet, stats)
        else:
            self._render_sequential(pages, tracker, quiet, stats)
    
    def _render_sequential(self, pages: List['Page'], 
                          tracker: Optional['DependencyTracker'],
                          quiet: bool,
                          stats: Optional['BuildStats']) -> None:
        """
        Build pages sequentially.
        
        Args:
            pages: Pages to render
            tracker: Dependency tracker
            quiet: Whether to suppress verbose output
            stats: Build statistics tracker
        """
        from bengal.rendering.pipeline import RenderingPipeline
        
        pipeline = RenderingPipeline(self.site, tracker, quiet=quiet, build_stats=stats)
        for page in pages:
            pipeline.process_page(page)
    
    def _render_parallel(self, pages: List['Page'],
                        tracker: Optional['DependencyTracker'],
                        quiet: bool,
                        stats: Optional['BuildStats']) -> None:
        """
        Build pages in parallel for better performance.
        
        Uses thread-local pipelines to avoid expensive Jinja2 environment
        re-initialization (one pipeline per thread, not per page).
        
        Args:
            pages: Pages to render
            tracker: Dependency tracker
            quiet: Whether to suppress verbose output
            stats: Build statistics tracker
        """
        from bengal.rendering.pipeline import RenderingPipeline
        
        max_workers = self.site.config.get("max_workers", 4)
        
        def process_page_with_pipeline(page):
            """Process a page with a thread-local pipeline instance (thread-safe)."""
            # Reuse pipeline for this thread (one per thread, NOT one per page!)
            # This avoids expensive Jinja2 environment re-initialization
            if not hasattr(_thread_local, 'pipeline'):
                _thread_local.pipeline = RenderingPipeline(
                    self.site, tracker, quiet=quiet, build_stats=stats
                )
            _thread_local.pipeline.process_page(page)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_page_with_pipeline, page) 
                for page in pages
            ]
            
            # Wait for all to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing page: {e}")
    
    def _set_output_paths_for_pages(self, pages: List['Page']) -> None:
        """
        Pre-set output paths for specific pages before rendering.
        
        Only processes pages that are being rendered, not all pages in the site.
        This is an optimization for incremental builds where we only render a subset.
        """
        from pathlib import Path
        
        content_dir = self.site.root_path / "content"
        
        for page in pages:
            # Skip if already set (e.g., generated pages)
            if page.output_path:
                continue
            
            # Determine output path using same logic as pipeline
            try:
                rel_path = page.source_path.relative_to(content_dir)
            except ValueError:
                # If not under content_dir, use just the filename
                rel_path = Path(page.source_path.name)
            
            # Change extension to .html
            output_rel_path = rel_path.with_suffix('.html')
            
            # Handle index pages specially (index.md and _index.md → index.html)
            # Others can optionally use pretty URLs (about.md → about/index.html)
            if self.site.config.get("pretty_urls", True) and output_rel_path.stem not in ("index", "_index"):
                output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
            elif output_rel_path.stem == "_index":
                # _index.md should become index.html in the same directory
                output_rel_path = output_rel_path.parent / "index.html"
            
            page.output_path = self.site.output_dir / output_rel_path

