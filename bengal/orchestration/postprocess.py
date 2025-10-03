"""
Post-processing orchestration for Bengal SSG.

Handles post-build tasks like sitemap generation, RSS feeds, and link validation.
"""

import concurrent.futures
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, List, Tuple, Callable

if TYPE_CHECKING:
    from bengal.core.site import Site

# Thread-safe output lock for parallel processing
_print_lock = Lock()


class PostprocessOrchestrator:
    """
    Handles post-processing tasks.
    
    Responsibilities:
        - Sitemap generation
        - RSS feed generation
        - Link validation
        - Parallel/sequential execution of tasks
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize postprocess orchestrator.
        
        Args:
            site: Site instance with rendered pages and configuration
        """
        self.site = site
    
    def run(self, parallel: bool = True) -> None:
        """
        Perform post-processing tasks (sitemap, RSS, link validation, etc.).
        
        Args:
            parallel: Whether to run tasks in parallel
        """
        print("\n🔧 Post-processing:")
        
        # Collect enabled tasks
        tasks = []
        
        if self.site.config.get("generate_sitemap", True):
            tasks.append(('sitemap', self._generate_sitemap))
        
        if self.site.config.get("generate_rss", True):
            tasks.append(('rss', self._generate_rss))
        
        if self.site.config.get("validate_links", True):
            tasks.append(('link validation', self._validate_links))
        
        if not tasks:
            return
        
        # Run in parallel if enabled and multiple tasks
        # Threshold of 2 tasks (always parallel if multiple tasks since they're independent)
        if parallel and len(tasks) > 1:
            self._run_parallel(tasks)
        else:
            self._run_sequential(tasks)
    
    def _run_sequential(self, tasks: List[Tuple[str, Callable]]) -> None:
        """
        Run post-processing tasks sequentially.
        
        Args:
            tasks: List of (task_name, task_function) tuples
        """
        for task_name, task_fn in tasks:
            try:
                task_fn()
            except Exception as e:
                with _print_lock:
                    print(f"  ✗ {task_name}: {e}")
    
    def _run_parallel(self, tasks: List[Tuple[str, Callable]]) -> None:
        """
        Run post-processing tasks in parallel.
        
        Args:
            tasks: List of (task_name, task_function) tuples
        """
        errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(task_fn): name for name, task_fn in tasks}
            
            for future in concurrent.futures.as_completed(futures):
                task_name = futures[future]
                try:
                    future.result()
                except Exception as e:
                    errors.append((task_name, str(e)))
        
        # Report errors
        if errors:
            with _print_lock:
                print(f"  ⚠️  {len(errors)} post-processing task(s) failed:")
                for task_name, error in errors:
                    print(f"    • {task_name}: {error}")
    
    def _generate_sitemap(self) -> None:
        """Generate sitemap (extracted for parallel execution)."""
        from bengal.postprocess.sitemap import SitemapGenerator
        generator = SitemapGenerator(self.site)
        generator.generate()
    
    def _generate_rss(self) -> None:
        """Generate RSS feed (extracted for parallel execution)."""
        from bengal.postprocess.rss import RSSGenerator
        generator = RSSGenerator(self.site)
        generator.generate()
    
    def _validate_links(self) -> None:
        """Validate links (extracted for parallel execution)."""
        from bengal.rendering.link_validator import LinkValidator
        validator = LinkValidator()
        broken_links = validator.validate_site(self.site)
        if broken_links:
            with _print_lock:
                print(f"Warning: Found {len(broken_links)} broken links")

