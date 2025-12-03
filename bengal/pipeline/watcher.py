"""
File watcher for pipeline-based incremental rebuilds.

This module provides file watching infrastructure for the reactive pipeline,
enabling automatic incremental rebuilds when files change.

Key Components:
    - FileWatcher: Watches directories for changes with debouncing
    - WatchEvent: Represents a single file change event
    - PipelineRebuildHandler: Triggers pipeline rebuilds on changes

Usage:
    >>> from bengal.pipeline.watcher import FileWatcher
    >>> watcher = FileWatcher(content_dir, debounce_ms=300)
    >>> watcher.on_change(lambda events: rebuild(events))
    >>> watcher.start()

Integration:
    This module integrates with the reactive pipeline system to enable
    watch mode builds. When files change, only affected items are
    reprocessed through the pipeline.

Related:
    - bengal/server/build_handler.py - Existing dev server handler
    - bengal/pipeline/build.py - Pipeline factories
    - bengal/pipeline/cache.py - Cache invalidation on changes
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


class ChangeType(Enum):
    """Type of file change event."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class WatchEvent:
    """
    A single file change event.

    Attributes:
        path: Path to the changed file
        change_type: Type of change (created, modified, deleted, moved)
        timestamp: When the change occurred
        old_path: Previous path for moved files (None otherwise)
    """

    path: Path
    change_type: ChangeType
    timestamp: float = field(default_factory=time.time)
    old_path: Path | None = None

    @property
    def is_content(self) -> bool:
        """True if this is a content file change."""
        return self.path.suffix in (".md", ".markdown")

    @property
    def is_template(self) -> bool:
        """True if this is a template file change."""
        return self.path.suffix in (".html", ".jinja", ".jinja2")

    @property
    def is_asset(self) -> bool:
        """True if this is an asset file change."""
        return self.path.suffix in (".css", ".js", ".png", ".jpg", ".svg", ".woff", ".woff2")

    @property
    def is_config(self) -> bool:
        """True if this is a config file change."""
        return self.path.name in ("bengal.toml", "config.toml", "config.yaml")


@dataclass
class WatchBatch:
    """
    A batch of file changes collected during debounce period.

    Attributes:
        events: List of change events
        started_at: When the batch started
        finalized_at: When the batch was finalized (debounce expired)
    """

    events: list[WatchEvent] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finalized_at: float | None = None

    def add(self, event: WatchEvent) -> None:
        """Add an event to the batch."""
        self.events.append(event)

    @property
    def changed_paths(self) -> list[Path]:
        """Get unique paths of all changed files."""
        seen: set[Path] = set()
        paths: list[Path] = []
        for event in self.events:
            if event.path not in seen:
                seen.add(event.path)
                paths.append(event.path)
        return paths

    @property
    def has_content_changes(self) -> bool:
        """True if batch contains content file changes."""
        return any(e.is_content for e in self.events)

    @property
    def has_template_changes(self) -> bool:
        """True if batch contains template file changes."""
        return any(e.is_template for e in self.events)

    @property
    def has_config_changes(self) -> bool:
        """True if batch contains config file changes."""
        return any(e.is_config for e in self.events)

    @property
    def needs_full_rebuild(self) -> bool:
        """True if changes require full rebuild (config or templates)."""
        return self.has_config_changes or self.has_template_changes

    @property
    def content_paths(self) -> list[Path]:
        """Get paths of changed content files."""
        return [e.path for e in self.events if e.is_content]

    def finalize(self) -> None:
        """Mark batch as finalized."""
        self.finalized_at = time.time()


class FileWatcher:
    """
    Watches directories for file changes with debouncing.

    Collects file change events and batches them together, waiting for
    a debounce period before notifying handlers. This prevents rapid
    successive changes from triggering multiple rebuilds.

    Example:
        >>> watcher = FileWatcher(
        ...     watch_dirs=[content_dir, templates_dir],
        ...     debounce_ms=300,
        ... )
        >>> watcher.on_change(lambda batch: print(f"Changed: {batch.changed_paths}"))
        >>> watcher.start()

    Ignored Patterns:
        - Hidden files (.gitignore, .DS_Store)
        - Temp files (.tmp, .swp, ~)
        - Python cache (__pycache__, .pyc)
        - Output directory (public/)
        - Cache files (.bengal/)
    """

    IGNORED_PATTERNS = {
        ".git",
        ".gitignore",
        ".DS_Store",
        "__pycache__",
        ".pyc",
        ".pyo",
        ".tmp",
        ".swp",
        ".swo",
        "~",
        ".bengal",
        "public",
        "node_modules",
    }

    def __init__(
        self,
        watch_dirs: list[Path] | None = None,
        *,
        debounce_ms: int = 300,
        recursive: bool = True,
    ) -> None:
        """
        Initialize file watcher.

        Args:
            watch_dirs: Directories to watch (default: current directory)
            debounce_ms: Debounce delay in milliseconds
            recursive: Watch subdirectories recursively
        """
        self._watch_dirs = watch_dirs or [Path.cwd()]
        self._debounce_ms = debounce_ms
        self._recursive = recursive

        self._handlers: list[Callable[[WatchBatch], None]] = []
        self._current_batch: WatchBatch | None = None
        self._debounce_timer: threading.Timer | None = None
        self._lock = threading.Lock()

        self._observer: Any = None
        self._running = False

    def on_change(self, handler: Callable[[WatchBatch], None]) -> None:
        """
        Register a handler to be called when files change.

        The handler receives a WatchBatch containing all changes
        that occurred during the debounce period.

        Args:
            handler: Function to call with WatchBatch
        """
        self._handlers.append(handler)

    def start(self) -> None:
        """
        Start watching for file changes.

        Uses watchdog library for efficient file system monitoring.
        """
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logger.error(
                "watchdog_not_installed",
                hint="Install with: pip install watchdog",
            )
            raise ImportError("watchdog is required for file watching") from None

        class Handler(FileSystemEventHandler):
            def __init__(self, watcher: FileWatcher) -> None:
                self._watcher = watcher

            def on_any_event(self, event) -> None:
                if event.is_directory:
                    return
                self._watcher._handle_event(event)

        self._observer = Observer()
        handler = Handler(self)

        for watch_dir in self._watch_dirs:
            if watch_dir.exists():
                self._observer.schedule(handler, str(watch_dir), recursive=self._recursive)
                logger.debug("watching_directory", path=str(watch_dir))

        self._observer.start()
        self._running = True
        logger.info("file_watcher_started", directories=len(self._watch_dirs))

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None

        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None

        self._running = False
        logger.info("file_watcher_stopped")

    def _handle_event(self, event) -> None:
        """Handle a raw watchdog event."""
        path = Path(event.src_path)

        # Check if should ignore
        if self._should_ignore(path):
            return

        # Map watchdog event type to ChangeType
        change_type = self._map_event_type(event)
        if change_type is None:
            return

        # Create WatchEvent
        old_path = None
        if hasattr(event, "dest_path") and event.dest_path:
            old_path = path
            path = Path(event.dest_path)

        watch_event = WatchEvent(
            path=path,
            change_type=change_type,
            old_path=old_path,
        )

        self._add_event(watch_event)

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        # Check each part of the path
        for part in path.parts:
            if part in self.IGNORED_PATTERNS:
                return True
            if part.startswith(".") and part not in (".", ".."):
                return True
            if part.endswith("~"):
                return True

        # Check file extension/suffix patterns
        name = path.name
        if name.endswith(".tmp"):
            return True
        if name.endswith(".swp") or name.endswith(".swo"):
            return True
        return bool(name.endswith("~"))

    def _map_event_type(self, event) -> ChangeType | None:
        """Map watchdog event type to ChangeType."""
        event_type = event.event_type
        if event_type == "created":
            return ChangeType.CREATED
        if event_type == "modified":
            return ChangeType.MODIFIED
        if event_type == "deleted":
            return ChangeType.DELETED
        if event_type == "moved":
            return ChangeType.MOVED
        return None

    def _add_event(self, event: WatchEvent) -> None:
        """Add event to current batch with debouncing."""
        with self._lock:
            # Cancel existing timer
            if self._debounce_timer:
                self._debounce_timer.cancel()

            # Create or add to batch
            if self._current_batch is None:
                self._current_batch = WatchBatch()

            self._current_batch.add(event)

            # Start debounce timer
            self._debounce_timer = threading.Timer(
                self._debounce_ms / 1000.0,
                self._flush_batch,
            )
            self._debounce_timer.start()

    def _flush_batch(self) -> None:
        """Finalize and dispatch current batch."""
        with self._lock:
            if self._current_batch is None:
                return

            batch = self._current_batch
            batch.finalize()
            self._current_batch = None
            self._debounce_timer = None

        # Log batch summary
        logger.debug(
            "watch_batch_ready",
            files_changed=len(batch.events),
            content_changes=batch.has_content_changes,
            template_changes=batch.has_template_changes,
            config_changes=batch.has_config_changes,
        )

        # Notify handlers
        for handler in self._handlers:
            try:
                handler(batch)
            except Exception as e:
                logger.error("watch_handler_error", error=str(e))


class PipelineWatcher:
    """
    Watches files and triggers pipeline-based incremental rebuilds.

    Combines FileWatcher with the reactive pipeline to automatically
    rebuild only affected content when files change.

    Example:
        >>> from bengal.pipeline.watcher import PipelineWatcher
        >>> watcher = PipelineWatcher(site)
        >>> watcher.start()  # Blocks until stopped

    Integration with DevServer:
        The PipelineWatcher can be used instead of BuildHandler for
        pipeline-based watch mode builds.
    """

    def __init__(
        self,
        site: Any,
        *,
        debounce_ms: int = 300,
        use_cache: bool = True,
    ) -> None:
        """
        Initialize pipeline watcher.

        Args:
            site: Bengal Site instance
            debounce_ms: Debounce delay in milliseconds
            use_cache: Enable disk caching for pipeline
        """
        self.site = site
        self._debounce_ms = debounce_ms
        self._use_cache = use_cache

        # Determine watch directories
        root = site.root_path
        watch_dirs = [
            root / "content",
            root / "templates",
            root / "assets",
            root / "data",
            root / "themes",
        ]
        # Add config file's parent
        watch_dirs.append(root)

        self._watcher = FileWatcher(
            watch_dirs=[d for d in watch_dirs if d.exists()],
            debounce_ms=debounce_ms,
        )
        self._watcher.on_change(self._handle_changes)

        # Initialize cache if enabled
        self._cache = None
        if use_cache:
            from bengal.pipeline.cache import StreamCache

            cache_dir = root / ".bengal" / "pipeline"
            self._cache = StreamCache(cache_dir)

    def start(self) -> None:
        """Start watching and rebuilding."""
        logger.info("pipeline_watcher_starting")
        self._watcher.start()

    def stop(self) -> None:
        """Stop watching."""
        self._watcher.stop()
        if self._cache:
            self._cache.save()
        logger.info("pipeline_watcher_stopped")

    def _handle_changes(self, batch: WatchBatch) -> None:
        """Handle a batch of file changes."""
        from bengal.pipeline.build import create_build_pipeline, create_incremental_pipeline

        logger.info(
            "rebuild_triggered",
            changed_files=len(batch.changed_paths),
            full_rebuild=batch.needs_full_rebuild,
        )

        start_time = time.time()

        try:
            if batch.needs_full_rebuild:
                # Config or template change - full rebuild
                pipeline = create_build_pipeline(self.site)
                logger.info("full_rebuild_starting", reason="config_or_template_change")
            else:
                # Content-only change - incremental
                pipeline = create_incremental_pipeline(
                    self.site,
                    batch.content_paths,
                )
                logger.info("incremental_rebuild_starting", files=len(batch.content_paths))

            result = pipeline.run()
            elapsed = time.time() - start_time

            if result.success:
                logger.info(
                    "rebuild_complete",
                    pages=result.items_processed,
                    elapsed_seconds=round(elapsed, 2),
                )
            else:
                logger.warning(
                    "rebuild_completed_with_errors",
                    pages=result.items_processed,
                    errors=len(result.errors),
                    elapsed_seconds=round(elapsed, 2),
                )

            # Save cache after rebuild
            if self._cache:
                self._cache.save()

        except Exception as e:
            logger.error("rebuild_failed", error=str(e))
