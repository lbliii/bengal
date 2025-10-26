"""
File system event handler for automatic site rebuilds.

Watches for file changes and triggers incremental rebuilds with debouncing.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from bengal.utils.build_stats import display_build_stats, show_building_indicator, show_error
from bengal.utils.cli_output import CLIOutput
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class BuildHandler(FileSystemEventHandler):
    """
    File system event handler that triggers site rebuild with debouncing.

    Watches for file changes and automatically rebuilds the site when changes
    are detected. Uses debouncing to batch multiple rapid changes into a single
    rebuild, preventing excessive rebuilds when multiple files are saved at once.

    Features:
    - Debounced rebuilds (0.3s delay to batch changes)
    - Incremental builds for speed (5-10x faster)
    - Parallel rendering
    - Stale object reference prevention (clears ephemeral state)
    - Build error recovery (errors don't crash server)
    - Automatic cache invalidation for config/template changes
    - Handles all file events: create, modify, delete, move/rename

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

    # Debounce delay in seconds (slightly higher to coalesce noisy editor events)
    DEBOUNCE_DELAY = 0.3

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
        path = Path(file_path)

        # Ignore common transient files by suffix
        suffix_ignores = {
            ".swp",
            ".swo",
            ".swx",  # Vim swap files
            ".tmp",
            ".pyc",
            ".pyo",
            ".orig",
            ".rej",
            "~",  # Editor backup files (Emacs, Vim)
            "~~",  # Alternate backup suffixes
        }

        # Ignore common transient files by exact filename
        name_ignores = {
            ".DS_Store",
            ".bengal-cache.json",
            ".bengal-build.log",
        }

        # Ignore when file lives under these directories anywhere in the path
        dir_ignores = {
            ".git",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".cache",
            "venv",
            ".venv",
            ".idea",
            ".vscode",
            "coverage",
            "htmlcov",
            "dist",
            "build",
            "public",
        }

        # Suffix ignores
        if any(str(path).endswith(suf) for suf in suffix_ignores):
            return True

        # Filename ignores
        if path.name in name_ignores:
            return True

        # Directory ignores (match any segment)
        return any(seg in dir_ignores for seg in path.parts)

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

            # Use CLIOutput for consistent formatting
            cli = CLIOutput()
            cli.file_change_notice(file_name=file_name, timestamp=timestamp)
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
                cli.server_url_inline(host=self.host, port=self.port)
                cli.request_log_header()

                logger.info(
                    "rebuild_complete",
                    duration_seconds=round(build_duration, 2),
                    pages_built=stats.total_pages,
                    incremental=stats.incremental,
                    parallel=stats.parallel,
                )

                # Output-diff–driven reload decision
                if getattr(stats, "skipped", False):
                    logger.info("reload_suppressed", reason="build_skipped")
                else:
                    from bengal.server.reload_controller import controller

                    decision = controller.decide_and_update(self.site.output_dir)

                    if decision.action == "none":
                        logger.info("reload_suppressed", reason=decision.reason)
                    else:
                        # Public API: send structured payload to clients
                        from bengal.server.live_reload import send_reload_payload

                        send_reload_payload(
                            decision.action, decision.reason, decision.changed_paths
                        )

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
                cli.blank()
                cli.request_log_header()

                logger.error(
                    "rebuild_failed",
                    duration_seconds=round(build_duration, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                    changed_files=changed_files[:5],
                )
            finally:
                self.building = False

    def _handle_file_event(self, event: FileSystemEvent, event_type: str) -> None:
        """
        Common handler for file system events with debouncing.

        Multiple rapid file changes are batched together and trigger a single
        rebuild after a short delay (DEBOUNCE_DELAY seconds).

        Files in the output directory and matching ignore patterns are skipped
        to prevent infinite rebuild loops.

        Args:
            event: File system event
            event_type: Type of event (created, modified, deleted, moved)

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
            event_type=event_type,
            pending_count=len(self.pending_changes),
            is_new_in_batch=is_new,
        )

        # Cancel existing timer and start new one (debouncing)
        with self.timer_lock:
            if self.debounce_timer:
                self.debounce_timer.cancel()
                logger.debug("debounce_timer_reset", delay_ms=self.DEBOUNCE_DELAY * 1000)

            # Allow override via config: dev.watch.debounce_ms or env BENGAL_DEBOUNCE_MS
            delay = self.DEBOUNCE_DELAY
            import os as _os

            from bengal.server.utils import get_dev_config, safe_int

            debounce_ms_env = _os.environ.get("BENGAL_DEBOUNCE_MS")
            debounce_ms_cfg = (
                get_dev_config(self.site.config, "watch", "debounce_ms")
                if hasattr(self.site, "config")
                else None
            )
            debounce_ms = safe_int(
                debounce_ms_env if debounce_ms_env is not None else debounce_ms_cfg, 0
            )
            if debounce_ms > 0:
                delay = debounce_ms / 1000.0

            self.debounce_timer = threading.Timer(delay, self._trigger_build)
            self.debounce_timer.daemon = True
            self.debounce_timer.start()

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Handle file creation events.

        Args:
            event: File system event
        """
        self._handle_file_event(event, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.

        Args:
            event: File system event
        """
        self._handle_file_event(event, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """
        Handle file deletion events.

        Args:
            event: File system event
        """
        self._handle_file_event(event, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        """
        Handle file move/rename events.

        Args:
            event: File system event with src_path and dest_path
        """
        # For moved files, we need to track both source and destination
        # The _handle_file_event will handle src_path, and we manually add dest_path
        self._handle_file_event(event, "moved")

        # Also add the destination path if it's not in the output directory
        if hasattr(event, "dest_path"):
            try:
                Path(event.dest_path).relative_to(self.site.output_dir)
                return
            except ValueError:
                pass

            if not self._should_ignore_file(event.dest_path):
                self.pending_changes.add(event.dest_path)
                logger.debug(
                    "file_move_destination_tracked",
                    dest_path=event.dest_path,
                    pending_count=len(self.pending_changes),
                )
