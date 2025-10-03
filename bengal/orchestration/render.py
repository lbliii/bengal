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
        
        quiet = not self.site.config.get('verbose', False)
        
        if parallel and len(pages) > 1:
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

