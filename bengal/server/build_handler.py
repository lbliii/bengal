"""
File system event handler for automatic site rebuilds.

Watches for file changes and triggers incremental rebuilds with debouncing.
"""

from pathlib import Path
from typing import Any, Optional, Set
import threading
import time
from datetime import datetime
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from bengal.utils.build_stats import display_build_stats, show_building_indicator, show_error
from bengal.utils.logger import get_logger
from bengal.server.live_reload import notify_clients_reload

logger = get_logger(__name__)


class BuildHandler(FileSystemEventHandler):
    """
    File system event handler that triggers site rebuild with debouncing.
    """
    
    # Debounce delay in seconds
    DEBOUNCE_DELAY = 0.2
    
    def __init__(self, site: Any) -> None:
        """
        Initialize the build handler.
        
        Args:
            site: Site instance
        """
        self.site = site
        self.building = False
        self.pending_changes: Set[str] = set()
        self.debounce_timer: Optional[threading.Timer] = None
        self.timer_lock = threading.Lock()
    
    def _clear_ephemeral_state(self) -> None:
        """
        Clear ephemeral state that shouldn't persist between builds.
        
        This is CRITICAL in dev server mode where the Site object persists
        across multiple builds. We must clear derived state to avoid stale
        object references.
        
        Persistence contract:
        - root_path, config, theme: Persist (static config)
        - output_dir, build_time: Persist (metadata)
        - pages, sections, assets: CLEAR (will be rediscovered)
        - taxonomies, menu, xref_index: CLEAR (derived from pages)
        
        This prevents the stale reference bug where taxonomies contain
        old Page objects from previous builds.
        """
        logger.debug("clearing_ephemeral_state", site_root=str(self.site.root_path))
        
        # Clear content (will be rediscovered)
        self.site.pages = []
        self.site.sections = []
        self.site.assets = []
        
        # Clear derived structures (contain object references)
        self.site.taxonomies = {}
        self.site.menu = {}
        self.site.menu_builders = {}
        
        # Clear indices (rebuilt from pages)
        if hasattr(self.site, 'xref_index'):
            self.site.xref_index = {}
        
        # Clear caches on pages (if any survived somehow)
        self.site.invalidate_regular_pages_cache()
    
    def _should_ignore_file(self, file_path: str) -> bool:
        """
        Check if file should be ignored (temp files, swap files, etc).
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file should be ignored
        """
        ignore_patterns = [
            '.swp', '.swo', '.swx',  # Vim swap files
            '.tmp', '~',              # Temp files
            '.pyc', '.pyo',           # Python cache
            '__pycache__',            # Python cache dir
            '.DS_Store',              # macOS
            '.git',                   # Git
            '.bengal-cache.json',     # Bengal cache
            '.bengal-build.log',      # Build log (would cause infinite rebuild loop!)
            'public/',                # Default output directory
        ]
        
        path = Path(file_path)
        name = path.name
        
        # Check if file matches any ignore pattern
        for pattern in ignore_patterns:
            if pattern in name or name.endswith(pattern):
                return True
        
        return False
    
    def _trigger_build(self) -> None:
        """Execute the actual build (called after debounce delay)."""
        with self.timer_lock:
            self.debounce_timer = None
            
            if self.building:
                logger.debug("build_skipped", reason="build_already_in_progress")
                return
            
            self.building = True
            
            # Get first changed file for display
            file_name = "multiple files"
            changed_files = list(self.pending_changes)
            file_count = len(changed_files)
            
            if self.pending_changes:
                first_file = next(iter(self.pending_changes))
                file_name = Path(first_file).name
                if file_count > 1:
                    file_name = f"{file_name} (+{file_count - 1} more)"
            
            logger.info("rebuild_triggered",
                       changed_file_count=file_count,
                       changed_files=changed_files[:10],  # Limit to first 10 for readability
                       trigger_file=str(changed_files[0]) if changed_files else None)
            
            self.pending_changes.clear()
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n  \033[90m{'─' * 78}\033[0m")
            print(f"  {timestamp} │ \033[33m📝 File changed:\033[0m {file_name}")
            print(f"  \033[90m{'─' * 78}\033[0m\n")
            show_building_indicator("Rebuilding")
            
            build_start = time.time()
            
            # CRITICAL: Clear ephemeral state before rebuild
            # This prevents stale object references (bug: taxonomy counts wrong)
            self._clear_ephemeral_state()
            
            try:
                # Use incremental + parallel for fast dev server rebuilds (5-10x faster)
                # Cache invalidation auto-detects config/template changes and falls back to full rebuild
                stats = self.site.build(parallel=True, incremental=True)
                build_duration = time.time() - build_start
                
                display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))
                print(f"\n  \033[90m{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH\033[0m")
                print(f"  \033[90m{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}\033[0m")
                
                logger.info("rebuild_complete",
                           duration_seconds=round(build_duration, 2),
                           pages_built=stats.total_pages,
                           incremental=stats.incremental,
                           parallel=stats.parallel)
                
                # Notify all SSE clients to reload
                notify_clients_reload()
            except Exception as e:
                build_duration = time.time() - build_start
                
                show_error(f"Build failed: {e}", show_art=False)
                print(f"\n  \033[90m{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH\033[0m")
                print(f"  \033[90m{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}\033[0m")
                
                logger.error("rebuild_failed",
                            duration_seconds=round(build_duration, 2),
                            error=str(e),
                            error_type=type(e).__name__,
                            changed_files=changed_files[:5])
            finally:
                self.building = False
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events with debouncing.
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
        
        # Skip files in output directory
        try:
            Path(event.src_path).relative_to(self.site.output_dir)
            logger.debug("file_change_ignored",
                        file=event.src_path,
                        reason="in_output_directory")
            return
        except ValueError:
            pass
        
        # Skip temp files and other files that should be ignored
        if self._should_ignore_file(event.src_path):
            logger.debug("file_change_ignored",
                        file=event.src_path,
                        reason="ignored_pattern")
            return
        
        # Add to pending changes
        is_new = event.src_path not in self.pending_changes
        self.pending_changes.add(event.src_path)
        
        logger.debug("file_change_detected",
                    file=event.src_path,
                    pending_count=len(self.pending_changes),
                    is_new_in_batch=is_new)
        
        # Cancel existing timer and start new one (debouncing)
        with self.timer_lock:
            if self.debounce_timer:
                self.debounce_timer.cancel()
                logger.debug("debounce_timer_reset",
                            delay_ms=self.DEBOUNCE_DELAY * 1000)
            
            self.debounce_timer = threading.Timer(self.DEBOUNCE_DELAY, self._trigger_build)
            self.debounce_timer.daemon = True
            self.debounce_timer.start()

