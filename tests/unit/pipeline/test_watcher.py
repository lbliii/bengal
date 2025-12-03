"""
Unit tests for bengal.pipeline.watcher - file watching for watch mode.

Tests:
    - WatchEvent classification
    - WatchBatch aggregation
    - FileWatcher ignore patterns
    - Debouncing behavior
"""

from __future__ import annotations

import time
from pathlib import Path

from bengal.pipeline.watcher import (
    ChangeType,
    FileWatcher,
    WatchBatch,
    WatchEvent,
)


class TestWatchEvent:
    """Tests for WatchEvent dataclass."""

    def test_creation(self) -> None:
        """WatchEvent stores all fields."""
        event = WatchEvent(
            path=Path("content/post.md"),
            change_type=ChangeType.MODIFIED,
        )

        assert event.path == Path("content/post.md")
        assert event.change_type == ChangeType.MODIFIED
        assert event.timestamp > 0
        assert event.old_path is None

    def test_is_content(self) -> None:
        """is_content detects markdown files."""
        assert WatchEvent(Path("post.md"), ChangeType.MODIFIED).is_content
        assert WatchEvent(Path("docs/guide.markdown"), ChangeType.MODIFIED).is_content
        assert not WatchEvent(Path("style.css"), ChangeType.MODIFIED).is_content

    def test_is_template(self) -> None:
        """is_template detects template files."""
        assert WatchEvent(Path("base.html"), ChangeType.MODIFIED).is_template
        assert WatchEvent(Path("page.jinja2"), ChangeType.MODIFIED).is_template
        assert not WatchEvent(Path("post.md"), ChangeType.MODIFIED).is_template

    def test_is_asset(self) -> None:
        """is_asset detects asset files."""
        assert WatchEvent(Path("style.css"), ChangeType.MODIFIED).is_asset
        assert WatchEvent(Path("app.js"), ChangeType.MODIFIED).is_asset
        assert WatchEvent(Path("logo.png"), ChangeType.MODIFIED).is_asset
        assert not WatchEvent(Path("post.md"), ChangeType.MODIFIED).is_asset

    def test_is_config(self) -> None:
        """is_config detects config files."""
        assert WatchEvent(Path("bengal.toml"), ChangeType.MODIFIED).is_config
        assert WatchEvent(Path("config.yaml"), ChangeType.MODIFIED).is_config
        assert not WatchEvent(Path("post.md"), ChangeType.MODIFIED).is_config

    def test_moved_event(self) -> None:
        """Moved events track old path."""
        event = WatchEvent(
            path=Path("new/location.md"),
            change_type=ChangeType.MOVED,
            old_path=Path("old/location.md"),
        )

        assert event.old_path == Path("old/location.md")


class TestWatchBatch:
    """Tests for WatchBatch."""

    def test_empty_batch(self) -> None:
        """Empty batch has no events."""
        batch = WatchBatch()

        assert len(batch.events) == 0
        assert batch.changed_paths == []
        assert not batch.has_content_changes
        assert not batch.has_template_changes
        assert not batch.has_config_changes

    def test_add_events(self) -> None:
        """Events can be added to batch."""
        batch = WatchBatch()
        batch.add(WatchEvent(Path("a.md"), ChangeType.MODIFIED))
        batch.add(WatchEvent(Path("b.md"), ChangeType.CREATED))

        assert len(batch.events) == 2

    def test_changed_paths_unique(self) -> None:
        """changed_paths returns unique paths."""
        batch = WatchBatch()
        batch.add(WatchEvent(Path("a.md"), ChangeType.MODIFIED))
        batch.add(WatchEvent(Path("a.md"), ChangeType.MODIFIED))  # Duplicate
        batch.add(WatchEvent(Path("b.md"), ChangeType.MODIFIED))

        paths = batch.changed_paths
        assert len(paths) == 2
        assert Path("a.md") in paths
        assert Path("b.md") in paths

    def test_has_content_changes(self) -> None:
        """has_content_changes detects content files."""
        batch = WatchBatch()
        batch.add(WatchEvent(Path("style.css"), ChangeType.MODIFIED))

        assert not batch.has_content_changes

        batch.add(WatchEvent(Path("post.md"), ChangeType.MODIFIED))
        assert batch.has_content_changes

    def test_has_template_changes(self) -> None:
        """has_template_changes detects templates."""
        batch = WatchBatch()
        batch.add(WatchEvent(Path("post.md"), ChangeType.MODIFIED))

        assert not batch.has_template_changes

        batch.add(WatchEvent(Path("base.html"), ChangeType.MODIFIED))
        assert batch.has_template_changes

    def test_has_config_changes(self) -> None:
        """has_config_changes detects config files."""
        batch = WatchBatch()
        batch.add(WatchEvent(Path("post.md"), ChangeType.MODIFIED))

        assert not batch.has_config_changes

        batch.add(WatchEvent(Path("bengal.toml"), ChangeType.MODIFIED))
        assert batch.has_config_changes

    def test_needs_full_rebuild(self) -> None:
        """needs_full_rebuild for config/template changes."""
        # Content only - no full rebuild
        batch1 = WatchBatch()
        batch1.add(WatchEvent(Path("post.md"), ChangeType.MODIFIED))
        assert not batch1.needs_full_rebuild

        # Template change - full rebuild
        batch2 = WatchBatch()
        batch2.add(WatchEvent(Path("base.html"), ChangeType.MODIFIED))
        assert batch2.needs_full_rebuild

        # Config change - full rebuild
        batch3 = WatchBatch()
        batch3.add(WatchEvent(Path("bengal.toml"), ChangeType.MODIFIED))
        assert batch3.needs_full_rebuild

    def test_content_paths(self) -> None:
        """content_paths returns only content file paths."""
        batch = WatchBatch()
        batch.add(WatchEvent(Path("post.md"), ChangeType.MODIFIED))
        batch.add(WatchEvent(Path("style.css"), ChangeType.MODIFIED))
        batch.add(WatchEvent(Path("guide.md"), ChangeType.MODIFIED))

        content_paths = batch.content_paths
        assert len(content_paths) == 2
        assert Path("post.md") in content_paths
        assert Path("guide.md") in content_paths
        assert Path("style.css") not in content_paths

    def test_finalize(self) -> None:
        """finalize sets finalized_at timestamp."""
        batch = WatchBatch()
        assert batch.finalized_at is None

        batch.finalize()
        assert batch.finalized_at is not None
        assert batch.finalized_at > batch.started_at


class TestFileWatcher:
    """Tests for FileWatcher."""

    def test_ignore_hidden_files(self) -> None:
        """Hidden files are ignored."""
        watcher = FileWatcher()

        assert watcher._should_ignore(Path(".gitignore"))
        assert watcher._should_ignore(Path(".DS_Store"))
        assert watcher._should_ignore(Path("content/.hidden/file.md"))

    def test_ignore_temp_files(self) -> None:
        """Temp files are ignored."""
        watcher = FileWatcher()

        assert watcher._should_ignore(Path("file.tmp"))
        assert watcher._should_ignore(Path("file.swp"))
        assert watcher._should_ignore(Path("file~"))

    def test_ignore_python_cache(self) -> None:
        """Python cache is ignored."""
        watcher = FileWatcher()

        assert watcher._should_ignore(Path("__pycache__/module.pyc"))
        assert watcher._should_ignore(Path("bengal/__pycache__/core.pyc"))

    def test_ignore_bengal_cache(self) -> None:
        """Bengal cache directory is ignored."""
        watcher = FileWatcher()

        assert watcher._should_ignore(Path(".bengal/cache.json"))
        assert watcher._should_ignore(Path(".bengal/pipeline/streams.json"))

    def test_ignore_output_directory(self) -> None:
        """Output directory is ignored."""
        watcher = FileWatcher()

        assert watcher._should_ignore(Path("public/index.html"))
        assert watcher._should_ignore(Path("public/docs/guide.html"))

    def test_allow_content_files(self) -> None:
        """Content files are not ignored."""
        watcher = FileWatcher()

        assert not watcher._should_ignore(Path("content/post.md"))
        assert not watcher._should_ignore(Path("content/docs/guide.md"))
        assert not watcher._should_ignore(Path("templates/base.html"))

    def test_on_change_registers_handler(self) -> None:
        """on_change registers handler."""
        watcher = FileWatcher()
        handler_called = []

        watcher.on_change(lambda batch: handler_called.append(batch))

        assert len(watcher._handlers) == 1

    def test_multiple_handlers(self) -> None:
        """Multiple handlers can be registered."""
        watcher = FileWatcher()

        watcher.on_change(lambda b: None)
        watcher.on_change(lambda b: None)
        watcher.on_change(lambda b: None)

        assert len(watcher._handlers) == 3


class TestFileWatcherDebounce:
    """Tests for FileWatcher debouncing."""

    def test_debounce_batches_events(self) -> None:
        """Events within debounce period are batched."""
        watcher = FileWatcher(debounce_ms=100)
        batches_received: list[WatchBatch] = []
        watcher.on_change(lambda b: batches_received.append(b))

        # Simulate rapid events
        event1 = WatchEvent(Path("a.md"), ChangeType.MODIFIED)
        event2 = WatchEvent(Path("b.md"), ChangeType.MODIFIED)

        watcher._add_event(event1)
        watcher._add_event(event2)

        # Before debounce expires
        assert len(batches_received) == 0

        # Wait for debounce
        time.sleep(0.15)

        # Should receive one batch with both events
        assert len(batches_received) == 1
        assert len(batches_received[0].events) == 2

    def test_separate_batches_after_debounce(self) -> None:
        """Events after debounce create new batch."""
        watcher = FileWatcher(debounce_ms=50)
        batches_received: list[WatchBatch] = []
        watcher.on_change(lambda b: batches_received.append(b))

        # First event
        watcher._add_event(WatchEvent(Path("a.md"), ChangeType.MODIFIED))

        # Wait for debounce
        time.sleep(0.1)

        # Should have first batch
        assert len(batches_received) == 1

        # Second event (creates new batch)
        watcher._add_event(WatchEvent(Path("b.md"), ChangeType.MODIFIED))

        # Wait for second debounce
        time.sleep(0.1)

        # Should have two batches
        assert len(batches_received) == 2


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_values(self) -> None:
        """ChangeType has expected values."""
        assert ChangeType.CREATED.value == "created"
        assert ChangeType.MODIFIED.value == "modified"
        assert ChangeType.DELETED.value == "deleted"
        assert ChangeType.MOVED.value == "moved"
