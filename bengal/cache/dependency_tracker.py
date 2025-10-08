"""
Dependency Tracker - Tracks dependencies during the build process.
"""

from pathlib import Path
from typing import Set, Optional
import threading
from bengal.cache.build_cache import BuildCache
from bengal.utils.logger import get_logger


class DependencyTracker:
    """
    Tracks dependencies between pages and their templates, partials, and config files.
    
    This is used during the build process to populate the BuildCache with dependency
    information, which is then used for incremental builds.
    
    Thread-safe: Uses thread-local storage to track current page per thread.
    """
    
    def __init__(self, cache: BuildCache):
        """
        Initialize the dependency tracker.
        
        Args:
            cache: BuildCache instance to store dependencies in
        """
        self.cache = cache
        self.logger = get_logger(__name__)
        # Use thread-local storage for current page to support parallel processing
        self.current_page = threading.local()
    
    def start_page(self, page_path: Path) -> None:
        """
        Mark the start of processing a page (thread-safe).
        
        Args:
            page_path: Path to the page being processed
        """
        self.current_page.value = page_path
        # Update the page's own hash
        self.cache.update_file(page_path)
    
    def track_template(self, template_path: Path) -> None:
        """
        Record that the current page depends on a template (thread-safe).
        
        Args:
            template_path: Path to the template file
        """
        if not hasattr(self.current_page, 'value'):
            return
        
        self.cache.add_dependency(self.current_page.value, template_path)
        self.cache.update_file(template_path)
    
    def track_partial(self, partial_path: Path) -> None:
        """
        Record that the current page depends on a partial/include (thread-safe).
        
        Args:
            partial_path: Path to the partial file
        """
        if not hasattr(self.current_page, 'value'):
            return
        
        self.cache.add_dependency(self.current_page.value, partial_path)
        self.cache.update_file(partial_path)
    
    def track_config(self, config_path: Path) -> None:
        """
        Record that the current page depends on the config file (thread-safe).
        All pages depend on config, so this marks it as a global dependency.
        
        Args:
            config_path: Path to the config file
        """
        if not hasattr(self.current_page, 'value'):
            return
        
        self.cache.add_dependency(self.current_page.value, config_path)
        self.cache.update_file(config_path)
    
    def track_asset(self, asset_path: Path) -> None:
        """
        Record an asset file (for cache invalidation).
        
        Args:
            asset_path: Path to the asset file
        """
        self.cache.update_file(asset_path)
    
    def track_taxonomy(self, page_path: Path, tags: Set[str]) -> None:
        """
        Record taxonomy (tags/categories) dependencies.
        
        When a page's tags change, tag pages need to be regenerated.
        
        Args:
            page_path: Path to the page
            tags: Set of tags/categories for this page
        """
        for tag in tags:
            # Normalize tag
            tag_key = f"tag:{tag.lower().replace(' ', '-')}"
            self.cache.add_taxonomy_dependency(tag_key, page_path)
    
    def end_page(self) -> None:
        """Mark the end of processing a page (thread-safe)."""
        if hasattr(self.current_page, 'value'):
            del self.current_page.value
    
    def get_changed_files(self, root_path: Path) -> Set[Path]:
        """
        Get all files that have changed since the last build.
        
        Args:
            root_path: Root path of the site
            
        Returns:
            Set of paths that have changed
        """
        changed = set()
        
        # Check all tracked files
        for file_path_str in self.cache.file_hashes.keys():
            file_path = Path(file_path_str)
            if file_path.exists() and self.cache.is_changed(file_path):
                changed.add(file_path)
        
        if changed:
            self.logger.info("changed_files_detected",
                           changed_count=len(changed),
                           total_tracked=len(self.cache.file_hashes),
                           change_ratio=f"{len(changed)/len(self.cache.file_hashes)*100:.1f}%")
        
        return changed
    
    def find_new_files(self, current_files: Set[Path]) -> Set[Path]:
        """
        Find files that are new (not in cache).
        
        Args:
            current_files: Set of current file paths
            
        Returns:
            Set of new file paths
        """
        tracked_files = {Path(f) for f in self.cache.file_hashes.keys()}
        new_files = current_files - tracked_files
        
        if new_files:
            self.logger.info("new_files_detected",
                           new_count=len(new_files),
                           total_current=len(current_files))
        
        return new_files
    
    def find_deleted_files(self, current_files: Set[Path]) -> Set[Path]:
        """
        Find files that were deleted (in cache but not on disk).
        
        Args:
            current_files: Set of current file paths
            
        Returns:
            Set of deleted file paths
        """
        tracked_files = {Path(f) for f in self.cache.file_hashes.keys()}
        deleted_files = tracked_files - current_files
        
        if deleted_files:
            self.logger.info("deleted_files_detected",
                           deleted_count=len(deleted_files),
                           total_tracked=len(tracked_files))
        
        return deleted_files

