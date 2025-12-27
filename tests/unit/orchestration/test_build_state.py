"""
Unit tests for BuildState.

Tests the BuildState class which provides per-build mutable state
with thread-safe locks and render context management.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime

from bengal.orchestration.build_state import BuildState


class TestBuildStateBasics:
    """Test basic BuildState operations."""

    def test_default_values(self) -> None:
        """Default state has expected values."""
        state = BuildState()

        assert state.incremental is False
        assert state.dev_mode is False
        assert state.current_language is None
        assert state.current_version is None
        assert len(state.features_detected) == 0
        assert len(state.discovery_timing_ms) == 0

    def test_build_time_defaults_to_now(self) -> None:
        """Build time defaults to current time."""
        before = datetime.now()
        state = BuildState()
        after = datetime.now()

        assert before <= state.build_time <= after

    def test_custom_build_time(self) -> None:
        """Build time can be set explicitly."""
        custom_time = datetime(2024, 1, 15, 10, 30, 0)
        state = BuildState(build_time=custom_time)

        assert state.build_time == custom_time

    def test_repr_shows_mode(self) -> None:
        """Repr shows build mode."""
        full_state = BuildState(incremental=False)
        assert "full" in repr(full_state)

        incr_state = BuildState(incremental=True)
        assert "incremental" in repr(incr_state)

    def test_repr_shows_dev_mode(self) -> None:
        """Repr indicates dev mode."""
        dev_state = BuildState(dev_mode=True)
        assert "(dev)" in repr(dev_state)

        prod_state = BuildState(dev_mode=False)
        assert "(dev)" not in repr(prod_state)


class TestRenderContext:
    """Test render context management."""

    def test_set_render_context(self) -> None:
        """Render context can be set."""
        state = BuildState()
        state.set_render_context(language="en", version="v2")

        assert state.current_language == "en"
        assert state.current_version == "v2"

    def test_set_render_context_with_none(self) -> None:
        """Render context accepts None values."""
        state = BuildState()
        state.set_render_context(language="en", version=None)

        assert state.current_language == "en"
        assert state.current_version is None

    def test_clear_render_context(self) -> None:
        """Render context can be cleared."""
        state = BuildState()
        state.set_render_context(language="en", version="v2")
        state.clear_render_context()

        assert state.current_language is None
        assert state.current_version is None


class TestCacheManagement:
    """Test cache management."""

    def test_reset_caches_clears_all(self) -> None:
        """reset_caches clears all caches."""
        state = BuildState()

        # Populate caches
        state.template_cache["key"] = "value"
        state.asset_manifest_cache["asset"] = "manifest"
        state.theme_chain_cache = ["theme1", "theme2"]
        state.template_dirs_cache = {"dir": "path"}
        state.template_metadata_cache = {"meta": "data"}
        state.features_detected.add("mermaid")
        state.asset_manifest_fallbacks.add("fallback")

        state.reset_caches()

        assert len(state.template_cache) == 0
        assert len(state.asset_manifest_cache) == 0
        assert state.theme_chain_cache is None
        assert state.template_dirs_cache is None
        assert state.template_metadata_cache is None
        assert len(state.features_detected) == 0
        assert len(state.asset_manifest_fallbacks) == 0

    def test_caches_are_independent(self) -> None:
        """Each BuildState instance has independent caches."""
        state1 = BuildState()
        state2 = BuildState()

        state1.template_cache["key1"] = "value1"
        state2.template_cache["key2"] = "value2"

        assert "key1" in state1.template_cache
        assert "key2" not in state1.template_cache
        assert "key2" in state2.template_cache
        assert "key1" not in state2.template_cache


class TestThreadSafeLocks:
    """Test thread-safe lock management."""

    def test_get_lock_returns_lock(self) -> None:
        """get_lock returns a Lock instance."""
        state = BuildState()
        lock = state.get_lock("test")

        assert isinstance(lock, type(threading.Lock()))

    def test_same_name_returns_same_lock(self) -> None:
        """Same lock name returns same lock instance."""
        state = BuildState()
        lock1 = state.get_lock("asset_write")
        lock2 = state.get_lock("asset_write")

        assert lock1 is lock2

    def test_different_names_return_different_locks(self) -> None:
        """Different lock names return different lock instances."""
        state = BuildState()
        lock1 = state.get_lock("asset_write")
        lock2 = state.get_lock("template_compile")

        assert lock1 is not lock2

    def test_lock_provides_mutual_exclusion(self) -> None:
        """Locks provide mutual exclusion."""
        state = BuildState()
        shared_value = []
        errors = []

        def worker(worker_id: int) -> None:
            try:
                with state.get_lock("shared"):
                    # Simulate critical section
                    temp = len(shared_value)
                    time.sleep(0.01)  # Small delay to expose race conditions
                    shared_value.append(worker_id)
                    # Verify no interference
                    assert len(shared_value) == temp + 1
            except AssertionError as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Race conditions detected: {errors}"
        assert len(shared_value) == 10

    def test_locks_are_per_state_instance(self) -> None:
        """Each BuildState has independent locks."""
        state1 = BuildState()
        state2 = BuildState()

        lock1 = state1.get_lock("test")
        lock2 = state2.get_lock("test")

        assert lock1 is not lock2


class TestFeaturesDetected:
    """Test features_detected set."""

    def test_features_start_empty(self) -> None:
        """Features set starts empty."""
        state = BuildState()
        assert len(state.features_detected) == 0

    def test_can_add_features(self) -> None:
        """Features can be added."""
        state = BuildState()
        state.features_detected.add("mermaid")
        state.features_detected.add("data_tables")

        assert "mermaid" in state.features_detected
        assert "data_tables" in state.features_detected
        assert "unknown" not in state.features_detected

    def test_features_cleared_on_reset(self) -> None:
        """Features are cleared on reset_caches."""
        state = BuildState()
        state.features_detected.add("mermaid")

        state.reset_caches()

        assert len(state.features_detected) == 0


class TestAssetManifestState:
    """Test asset manifest state fields."""

    def test_asset_manifest_previous_starts_none(self) -> None:
        """Previous manifest starts as None."""
        state = BuildState()
        assert state.asset_manifest_previous is None

    def test_asset_manifest_fallbacks_starts_empty(self) -> None:
        """Fallbacks set starts empty."""
        state = BuildState()
        assert len(state.asset_manifest_fallbacks) == 0

    def test_asset_manifest_previous_can_be_set(self) -> None:
        """Previous manifest can be set."""
        state = BuildState()
        manifest = {"asset1": "hash1"}
        state.asset_manifest_previous = manifest

        assert state.asset_manifest_previous == manifest

    def test_fallbacks_cleared_on_reset(self) -> None:
        """Fallbacks are cleared on reset_caches."""
        state = BuildState()
        state.asset_manifest_fallbacks.add("fallback1")

        state.reset_caches()

        assert len(state.asset_manifest_fallbacks) == 0
