"""Tests for ContextVarManager generic class.

RFC: rfc-free-threading-patterns.md

Thread Safety (Free-Threading / PEP 703):
    These tests verify that ContextVarManager provides proper
    thread isolation and supports nesting via tokens.
"""

from __future__ import annotations

import threading
import time

import pytest

from bengal.rendering.utils.contextvar import ContextVarManager


class TestContextVarManagerBasics:
    """Basic functionality tests for ContextVarManager."""

    def test_default_is_none(self):
        """Get should return None when nothing is set."""
        manager: ContextVarManager[str] = ContextVarManager("test_default")
        assert manager.get() is None

    def test_set_and_get(self):
        """Set should allow retrieval via get."""
        manager: ContextVarManager[str] = ContextVarManager("test_set_get")
        token = manager.set("hello")
        try:
            assert manager.get() == "hello"
        finally:
            manager.reset(token)

    def test_reset_with_token_restores_previous(self):
        """Reset with token should restore previous value."""
        manager: ContextVarManager[str] = ContextVarManager("test_reset_token")

        token1 = manager.set("first")
        assert manager.get() == "first"

        token2 = manager.set("second")
        assert manager.get() == "second"

        manager.reset(token2)
        assert manager.get() == "first"

        manager.reset(token1)
        assert manager.get() is None

    def test_reset_without_token_clears_to_none(self):
        """Reset without token should set to None."""
        manager: ContextVarManager[str] = ContextVarManager("test_reset_none")
        manager.set("value")
        assert manager.get() == "value"

        manager.reset()
        assert manager.get() is None

    def test_name_property(self):
        """Name property should return the ContextVar name."""
        manager: ContextVarManager[int] = ContextVarManager("my_context")
        assert manager.name == "my_context"

    def test_repr(self):
        """Repr should include the name."""
        manager: ContextVarManager[str] = ContextVarManager("test_repr")
        assert "test_repr" in repr(manager)


class TestContextVarManagerContextManager:
    """Tests for context manager usage."""

    def test_context_manager_sets_and_resets(self):
        """Context manager should set value and reset on exit."""
        manager: ContextVarManager[str] = ContextVarManager("test_cm_basic")
        manager.reset()  # Ensure clean state

        assert manager.get() is None

        with manager("hello"):
            assert manager.get() == "hello"

        assert manager.get() is None

    def test_context_manager_yields_value(self):
        """Context manager should yield the value it was given."""
        manager: ContextVarManager[str] = ContextVarManager("test_cm_yield")

        with manager("world") as value:
            assert value == "world"

    def test_context_manager_nesting(self):
        """Nested context managers should properly restore state."""
        manager: ContextVarManager[str] = ContextVarManager("test_cm_nesting")
        manager.reset()

        with manager("outer"):
            assert manager.get() == "outer"

            with manager("inner"):
                assert manager.get() == "inner"

            assert manager.get() == "outer"

        assert manager.get() is None

    def test_context_manager_resets_on_exception(self):
        """Context manager should reset even when exception is raised."""
        manager: ContextVarManager[str] = ContextVarManager("test_cm_exception")
        manager.reset()

        with pytest.raises(ValueError), manager("value"):
            assert manager.get() == "value"
            raise ValueError("Test exception")

        assert manager.get() is None

    def test_deeply_nested_context_managers(self):
        """Deeply nested context managers should work correctly."""
        manager: ContextVarManager[int] = ContextVarManager("test_deep_nesting")
        manager.reset()

        with manager(1):
            with manager(2):
                with manager(3):
                    with manager(4):
                        assert manager.get() == 4
                    assert manager.get() == 3
                assert manager.get() == 2
            assert manager.get() == 1
        assert manager.get() is None


class TestContextVarManagerThreadIsolation:
    """Tests for thread isolation.

    RFC: rfc-free-threading-patterns.md

    These tests verify that each thread gets its own independent context,
    which is essential for free-threaded Python (PEP 703) support.
    """

    def test_thread_isolation_basic(self):
        """Each thread should have independent context."""
        manager: ContextVarManager[str] = ContextVarManager("test_thread_basic")
        results: dict[int, str | None] = {}
        errors: list[str] = []

        def worker(thread_id: int, value: str):
            try:
                with manager(value):
                    time.sleep(0.01)  # Simulate work
                    results[thread_id] = manager.get()
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [
            threading.Thread(target=worker, args=(1, "thread1")),
            threading.Thread(target=worker, args=(2, "thread2")),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors occurred: {errors}"
        assert results[1] == "thread1"
        assert results[2] == "thread2"

    def test_thread_isolation_many_threads(self):
        """Thread isolation should work with many concurrent threads."""
        manager: ContextVarManager[int] = ContextVarManager("test_many_threads")
        num_threads = 20
        results: dict[int, int | None] = {}
        errors: list[str] = []

        def worker(thread_id: int):
            try:
                with manager(thread_id * 10):
                    time.sleep(0.005 * (thread_id % 5 + 1))
                    results[thread_id] = manager.get()
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors occurred: {errors}"

        for i in range(num_threads):
            assert results[i] == i * 10, f"Thread {i} saw {results[i]}, expected {i * 10}"

    def test_main_thread_not_affected_by_workers(self):
        """Worker thread context should not affect main thread."""
        manager: ContextVarManager[str] = ContextVarManager("test_main_thread")
        manager.reset()

        token = manager.set("main")

        def worker():
            with manager("worker"):
                time.sleep(0.02)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=10)

        # Main thread should still have its original value
        assert manager.get() == "main"
        manager.reset(token)


class TestContextVarManagerTypes:
    """Tests for different value types."""

    def test_with_dataclass(self):
        """Should work with dataclass values."""
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Config:
            name: str
            value: int

        manager: ContextVarManager[Config] = ContextVarManager("test_dataclass")

        config = Config(name="test", value=42)
        with manager(config) as c:
            assert c.name == "test"
            assert c.value == 42
            assert manager.get() is config

    def test_with_list(self):
        """Should work with list values."""
        manager: ContextVarManager[list[int]] = ContextVarManager("test_list")

        with manager([1, 2, 3]) as values:
            assert values == [1, 2, 3]

    def test_with_dict(self):
        """Should work with dict values."""
        manager: ContextVarManager[dict[str, int]] = ContextVarManager("test_dict")

        with manager({"a": 1, "b": 2}) as d:
            assert d["a"] == 1
            assert d["b"] == 2
