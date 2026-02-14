"""Tests for asset manifest ContextVar pattern.

RFC: rfc-global-build-state-dependencies.md (Phase 2)

Thread Safety (Free-Threading / PEP 703):
    These tests verify that the ContextVar pattern provides proper
    thread isolation for asset manifest access during parallel rendering.
"""

from __future__ import annotations

import threading
import time

import pytest

from bengal.rendering.assets import (
    AssetManifestContext,
    asset_manifest_context,
    get_asset_manifest,
    reset_asset_manifest,
    set_asset_manifest,
)


class TestAssetManifestContext:
    """Tests for AssetManifestContext dataclass."""

    def test_is_frozen(self):
        """AssetManifestContext should be immutable (frozen dataclass)."""
        ctx = AssetManifestContext(entries={"css/style.css": "css/style.abc.css"})
        with pytest.raises(AttributeError):
            ctx.entries = {}  # type: ignore[misc]

    def test_entries_lookup(self):
        """Entries dict should allow fast lookup by logical path."""
        ctx = AssetManifestContext(
            entries={
                "css/style.css": "assets/css/style.abc123.css",
                "js/main.js": "assets/js/main.def456.js",
            },
            mtime=1234567890.0,
        )
        assert ctx.entries.get("css/style.css") == "assets/css/style.abc123.css"
        assert ctx.entries.get("js/main.js") == "assets/js/main.def456.js"
        assert ctx.entries.get("nonexistent.css") is None
        assert ctx.mtime == 1234567890.0

    def test_default_mtime_is_none(self):
        """Mtime should default to None when not provided."""
        ctx = AssetManifestContext(entries={})
        assert ctx.mtime is None


class TestContextVarFunctions:
    """Tests for ContextVar helper functions."""

    def test_get_returns_none_by_default(self):
        """get_asset_manifest() should return None when no context is set."""
        reset_asset_manifest()  # Ensure clean state
        assert get_asset_manifest() is None

    def test_set_and_get(self):
        """set_asset_manifest() should allow retrieval via get_asset_manifest()."""
        ctx = AssetManifestContext(entries={"test.css": "test.abc.css"})
        token = set_asset_manifest(ctx)
        try:
            retrieved = get_asset_manifest()
            assert retrieved is ctx
            assert retrieved.entries.get("test.css") == "test.abc.css"
        finally:
            reset_asset_manifest(token)

    def test_reset_restores_previous_value(self):
        """reset_asset_manifest(token) should restore the previous value."""
        ctx1 = AssetManifestContext(entries={"v1": "v1.css"})
        ctx2 = AssetManifestContext(entries={"v2": "v2.css"})

        token1 = set_asset_manifest(ctx1)
        try:
            assert get_asset_manifest() is ctx1

            token2 = set_asset_manifest(ctx2)
            assert get_asset_manifest() is ctx2

            reset_asset_manifest(token2)
            assert get_asset_manifest() is ctx1
        finally:
            reset_asset_manifest(token1)

    def test_reset_without_token_clears_to_none(self):
        """reset_asset_manifest() without token should reset to None."""
        ctx = AssetManifestContext(entries={"test": "test"})
        set_asset_manifest(ctx)
        assert get_asset_manifest() is not None

        reset_asset_manifest()
        assert get_asset_manifest() is None


class TestAssetManifestContextManager:
    """Tests for asset_manifest_context() context manager."""

    def test_context_manager_sets_and_resets(self):
        """Context manager should set context and reset on exit."""
        reset_asset_manifest()  # Ensure clean state
        ctx = AssetManifestContext(entries={"test.css": "test.abc.css"})

        assert get_asset_manifest() is None

        with asset_manifest_context(ctx):
            assert get_asset_manifest() is ctx

        assert get_asset_manifest() is None

    def test_context_manager_yields_context(self):
        """Context manager should yield the context it was given."""
        ctx = AssetManifestContext(entries={"x": "y"})

        with asset_manifest_context(ctx) as yielded:
            assert yielded is ctx

    def test_context_manager_supports_nesting(self):
        """Nested context managers should properly restore state."""
        reset_asset_manifest()
        outer = AssetManifestContext(entries={"outer": "outer.css"})
        inner = AssetManifestContext(entries={"inner": "inner.css"})

        with asset_manifest_context(outer):
            assert get_asset_manifest() is outer

            with asset_manifest_context(inner):
                assert get_asset_manifest() is inner

            assert get_asset_manifest() is outer

        assert get_asset_manifest() is None

    def test_context_manager_resets_on_exception(self):
        """Context manager should reset even when exception is raised."""
        reset_asset_manifest()
        ctx = AssetManifestContext(entries={"test": "test"})

        with asset_manifest_context(ctx):
            assert get_asset_manifest() is ctx
            with pytest.raises(ValueError, match="Test exception"):
                raise ValueError("Test exception")

        assert get_asset_manifest() is None


class TestThreadIsolation:
    """Tests for thread isolation of asset manifest ContextVar.

    RFC: rfc-global-build-state-dependencies.md (Phase 2)

    These tests verify that ContextVar provides proper thread isolation,
    which is essential for free-threaded Python (PEP 703) support.
    """

    def test_thread_isolation_basic(self):
        """Each thread should have independent asset manifest context."""
        results: dict[int, str | None] = {}
        errors: list[str] = []

        def worker(thread_id: int, entries: dict[str, str]):
            try:
                ctx = AssetManifestContext(entries=entries, mtime=None)
                with asset_manifest_context(ctx):
                    # Simulate some work
                    time.sleep(0.01)
                    # Each thread should see its own entries
                    manifest = get_asset_manifest()
                    if manifest:
                        results[thread_id] = manifest.entries.get("test.css")
                    else:
                        results[thread_id] = None
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [
            threading.Thread(target=worker, args=(1, {"test.css": "test.abc.css"})),
            threading.Thread(target=worker, args=(2, {"test.css": "test.xyz.css"})),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Check for errors
        assert not errors, f"Errors occurred: {errors}"

        # Each thread should have seen its own value
        assert results[1] == "test.abc.css"
        assert results[2] == "test.xyz.css"

    def test_thread_isolation_with_many_threads(self):
        """Thread isolation should work with many concurrent threads."""
        num_threads = 10
        results: dict[int, str | None] = {}
        errors: list[str] = []

        def worker(thread_id: int):
            try:
                # Each thread gets a unique fingerprint
                fingerprint = f"style.{thread_id:03d}.css"
                ctx = AssetManifestContext(
                    entries={"css/style.css": f"assets/css/{fingerprint}"},
                    mtime=float(thread_id),
                )
                with asset_manifest_context(ctx):
                    # Simulate varying work duration
                    time.sleep(0.005 * (thread_id % 3 + 1))
                    manifest = get_asset_manifest()
                    if manifest:
                        results[thread_id] = manifest.entries.get("css/style.css")
                    else:
                        results[thread_id] = None
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Check for errors
        assert not errors, f"Errors occurred: {errors}"

        # Each thread should have seen its own unique value
        for i in range(num_threads):
            expected = f"assets/css/style.{i:03d}.css"
            assert results[i] == expected, f"Thread {i} saw {results[i]}, expected {expected}"

    def test_main_thread_not_affected_by_worker_threads(self):
        """Worker thread context should not affect main thread context."""
        reset_asset_manifest()

        main_ctx = AssetManifestContext(entries={"main": "main.css"})
        set_asset_manifest(main_ctx)

        def worker():
            worker_ctx = AssetManifestContext(entries={"worker": "worker.css"})
            with asset_manifest_context(worker_ctx):
                time.sleep(0.02)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=10)

        # Main thread should still have its original context
        manifest = get_asset_manifest()
        assert manifest is not None
        assert manifest.entries.get("main") == "main.css"
        assert manifest.entries.get("worker") is None

        reset_asset_manifest()

    def test_no_context_leakage_between_sequential_threads(self):
        """Context should not leak when threads run sequentially."""
        reset_asset_manifest()

        results: list[str | None] = []

        def worker(fingerprint: str):
            ctx = AssetManifestContext(entries={"test": fingerprint})
            with asset_manifest_context(ctx):
                manifest = get_asset_manifest()
                results.append(manifest.entries.get("test") if manifest else None)

        # Run threads sequentially
        for fp in ["first", "second", "third"]:
            t = threading.Thread(target=worker, args=(fp,))
            t.start()
            t.join(timeout=10)

        # Each should have seen its own fingerprint
        assert results == ["first", "second", "third"]

        # Main thread should have no context
        assert get_asset_manifest() is None
