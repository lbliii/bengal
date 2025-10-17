"""
File system event handler for automatic site rebuilds.

Watches for file changes and triggers incremental rebuilds with debouncing.
"""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from bengal.server.live_reload import notify_clients_reload
from bengal.utils.build_stats import display_build_stats, show_building_indicator, show_error
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class BuildHandler(FileSystemEventHandler):
    """
    File system event handler that triggers site rebuild with debouncing.

    Watches for file changes and automatically rebuilds the site when changes
    are detected. Uses debouncing to batch multiple rapid changes into a single
    rebuild, preventing excessive rebuilds when multiple files are saved at once.

    Features:
    - Debounced rebuilds (0.2s delay to batch changes)
    - Incremental builds for speed (5-10x faster)
    - Parallel rendering
    - Stale object reference prevention (clears ephemeral state)
    - Build error recovery (errors don't crash server)
    - Automatic cache invalidation for config/template changes

    Ignored files:
    - Output directory (public/)
    - Build logs (.bengal-build.log)
    - Cache files (.bengal-cache.json)
    - Temp files (.tmp, ~, .swp, .swo)
    - System files (.DS_Store, .git)
    - Python cache (__pycache__, .pyc)

    Example:
        handler = BuildHandler(site, host="localhost", port=5173)
        observer = Observer()
        observer.schedule(handler, "content/", recursive=True)
        observer.start()
    """

    # Debounce delay in seconds
    DEBOUNCE_DELAY = 0.2

    def __init__(self, site: Any, host: str = "localhost", port: int = 5173) -> None:
        """
        Initialize the build handler.

        Args:
            site: Site instance
            host: Server host
            port: Server port
        """
        self.site = site
        self.host = host
        self.port = port
        self.building = False
        self.pending_changes: set[str] = set()
        self.debounce_timer: threading.Timer | None = None
        self.timer_lock = threading.Lock()

    def _clear_ephemeral_state(self) -> None:
        """Clear ephemeral state safely via Site API."""
        try:
            self.site.reset_ephemeral_state()
        except AttributeError:
            # Backward compatibility: inline clear for older Site versions
            logger.debug("clearing_ephemeral_state_legacy", site_root=str(self.site.root_path))
            self.site.pages = []
            self.site.sections = []
            self.site.assets = []
            self.site.taxonomies = {}
            self.site.menu = {}
            self.site.menu_builders = {}
            if hasattr(self.site, "xref_index"):
                self.site.xref_index = {}
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
            ".swp",
            ".swo",
            ".swx",  # Vim swap files
            ".tmp",
            "~",  # Temp files
            ".pyc",
            ".pyo",  # Python cache
            "__pycache__",  # Python cache dir
            ".DS_Store",  # macOS
            ".git",  # Git
            ".bengal-cache.json",  # Bengal cache
            ".bengal-build.log",  # Build log (would cause infinite rebuild loop!)
            "public/",  # Default output directory
        ]

        path = Path(file_path)
        name = path.name

        # Check if file matches any ignore pattern
        return any(pattern in name or name.endswith(pattern) for pattern in ignore_patterns)

    def _trigger_build(self) -> None:
        """
        Execute the actual build (called after debounce delay).

        This method:
        1. Clears ephemeral state to prevent stale object references
        2. Runs an incremental + parallel build for speed
        3. Displays build statistics
        4. Notifies connected SSE clients to reload

        Note:
            Build errors are caught and logged but don't crash the server.
            The server continues running even if a build fails.

        Raises:
            Exception: Build failures are logged but don't propagate
        """
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

            logger.info(
                "rebuild_triggered",
                changed_file_count=file_count,
                changed_files=changed_files[:10],  # Limit to first 10 for readability
                trigger_file=str(changed_files[0]) if changed_files else None,
            )

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
                # Use WRITER profile for clean, minimal output during file watching
                from bengal.utils.profile import BuildProfile

                # Ensure dev flags remain active on rebuilds
                try:
                    cfg = self.site.config
                    cfg["dev_server"] = True
                    cfg["fingerprint_assets"] = False
                    cfg.setdefault("minify_assets", False)
                except Exception:
                    pass

                stats = self.site.build(
                    parallel=True, incremental=True, profile=BuildProfile.WRITER
                )
                build_duration = time.time() - build_start

                display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))

                # Show server URL after rebuild for easy access
                print(
                    f"\n  \033[36m➜\033[0m  Local: \033[1mhttp://{self.host}:{self.port}/\033[0m\n"
                )

                print(f"  \033[90m{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH\033[0m")
                print(f"  \033[90m{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}\033[0m")

                logger.info(
                    "rebuild_complete",
                    duration_seconds=round(build_duration, 2),
                    pages_built=stats.total_pages,
                    incremental=stats.incremental,
                    parallel=stats.parallel,
                )

                # Notify SSE clients: CSS-only changes trigger CSS hot-reload
                try:
                    changed_lower = [str(p).lower() for p in changed_files]
                    only_css = len(changed_files) > 0 and all(
                        path.endswith(".css") for path in changed_lower
                    )
                except Exception:
                    only_css = False

                if only_css:
                    from bengal.server.live_reload import set_reload_action

                    set_reload_action("reload-css")
                else:
                    from bengal.server.live_reload import set_reload_action

                    set_reload_action("reload")

                notify_clients_reload()

                # Clear HTML cache after successful rebuild (files have changed)
                from bengal.server.request_handler import BengalRequestHandler

                with BengalRequestHandler._html_cache_lock:
                    cache_size = len(BengalRequestHandler._html_cache)
                    BengalRequestHandler._html_cache.clear()
                if cache_size > 0:
                    logger.debug("html_cache_cleared", entries_removed=cache_size)
            except Exception as e:
                build_duration = time.time() - build_start

                show_error(f"Build failed: {e}", show_art=False)
                print(f"\n  \033[90m{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH\033[0m")
                print(f"  \033[90m{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}\033[0m")

                logger.error(
                    "rebuild_failed",
                    duration_seconds=round(build_duration, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                    changed_files=changed_files[:5],
                )
            finally:
                self.building = False

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events with debouncing.

        Multiple rapid file changes are batched together and trigger a single
        rebuild after a short delay (DEBOUNCE_DELAY seconds).

        Files in the output directory and matching ignore patterns are skipped
        to prevent infinite rebuild loops.

        Args:
            event: File system event

        Note:
            This method implements debouncing by canceling the previous timer
            and starting a new one on each file change.
        """
        if event.is_directory:
            return

        # Skip files in output directory
        try:
            Path(event.src_path).relative_to(self.site.output_dir)
            logger.debug("file_change_ignored", file=event.src_path, reason="in_output_directory")
            return
        except ValueError:
            pass

        # Skip temp files and other files that should be ignored
        if self._should_ignore_file(event.src_path):
            logger.debug("file_change_ignored", file=event.src_path, reason="ignored_pattern")
            return

        # Add to pending changes
        is_new = event.src_path not in self.pending_changes
        self.pending_changes.add(event.src_path)

        logger.debug(
            "file_change_detected",
            file=event.src_path,
            pending_count=len(self.pending_changes),
            is_new_in_batch=is_new,
        )

        # Cancel existing timer and start new one (debouncing)
        with self.timer_lock:
            if self.debounce_timer:
                self.debounce_timer.cancel()
                logger.debug("debounce_timer_reset", delay_ms=self.DEBOUNCE_DELAY * 1000)

            self.debounce_timer = threading.Timer(self.DEBOUNCE_DELAY, self._trigger_build)
            self.debounce_timer.daemon = True
            self.debounce_timer.start()
