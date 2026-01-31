"""Tests for patitas utility modules.

Tests the ContextVarManager and ThreadLocalPool base classes.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest

from bengal.parsing.backends.patitas.utils.contextvar import ContextVarManager
from bengal.parsing.backends.patitas.utils.pool import ThreadLocalPool


class TestContextVarManager:
    """Tests for the generic ContextVarManager utility."""

    def test_get_returns_default(self) -> None:
        """Get returns the default value when not set."""
        manager: ContextVarManager[str] = ContextVarManager("test", default="default")
        assert manager.get() == "default"

    def test_get_returns_none_without_default(self) -> None:
        """Get returns None when no default is set."""
        manager: ContextVarManager[str] = ContextVarManager("test")
        assert manager.get() is None

    def test_set_and_get(self) -> None:
        """Set changes the value, get retrieves it."""
        manager: ContextVarManager[str] = ContextVarManager("test", default="default")
        token = manager.set("new_value")
        assert manager.get() == "new_value"
        manager.reset(token)

    def test_reset_with_token(self) -> None:
        """Reset with token restores previous value."""
        manager: ContextVarManager[str] = ContextVarManager("test", default="default")
        token = manager.set("new_value")
        assert manager.get() == "new_value"
        manager.reset(token)
        assert manager.get() == "default"

    def test_reset_without_token(self) -> None:
        """Reset without token restores to default."""
        manager: ContextVarManager[str] = ContextVarManager("test", default="default")
        manager.set("new_value")
        assert manager.get() == "new_value"
        manager.reset()
        assert manager.get() == "default"

    def test_context_manager(self) -> None:
        """Context manager sets and restores value."""
        manager: ContextVarManager[str] = ContextVarManager("test", default="default")
        with manager.context("context_value") as val:
            assert val == "context_value"
            assert manager.get() == "context_value"
        assert manager.get() == "default"

    def test_nested_contexts(self) -> None:
        """Nested contexts restore properly."""
        manager: ContextVarManager[str] = ContextVarManager("test", default="default")
        with manager.context("outer") as outer:
            assert outer == "outer"
            with manager.context("inner") as inner:
                assert inner == "inner"
                assert manager.get() == "inner"
            assert manager.get() == "outer"
        assert manager.get() == "default"

    def test_get_or_raise(self) -> None:
        """get_or_raise raises when value is None."""
        manager: ContextVarManager[str] = ContextVarManager("test")
        with pytest.raises(ValueError, match="Test error"):
            manager.get_or_raise(ValueError, "Test error")

    def test_get_or_raise_returns_value(self) -> None:
        """get_or_raise returns value when set."""
        manager: ContextVarManager[str] = ContextVarManager("test")
        manager.set("value")
        result = manager.get_or_raise(ValueError, "Should not raise")
        assert result == "value"

    def test_name_property(self) -> None:
        """Name property returns the ContextVar name."""
        manager: ContextVarManager[str] = ContextVarManager("my_name", default="x")
        assert manager.name == "my_name"

    def test_thread_isolation(self) -> None:
        """Values are isolated between threads."""
        manager: ContextVarManager[str] = ContextVarManager("test", default="default")
        results: dict[str, str | None] = {}

        def set_in_thread(name: str, value: str) -> None:
            manager.set(value)
            results[name] = manager.get()

        thread1 = threading.Thread(target=set_in_thread, args=("t1", "value1"))
        thread2 = threading.Thread(target=set_in_thread, args=("t2", "value2"))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Each thread sees its own value
        assert results["t1"] == "value1"
        assert results["t2"] == "value2"
        # Main thread still sees default
        assert manager.get() == "default"


class SimplePool(ThreadLocalPool[list[Any]]):
    """Simple pool implementation for testing."""

    _env_var_name = ""  # No env var override

    @classmethod
    def _create(cls, initial: int = 0) -> list[Any]:
        return [initial]

    @classmethod
    def _reinit(cls, instance: list[Any], initial: int = 0) -> None:
        instance.clear()
        instance.append(initial)


class TestThreadLocalPool:
    """Tests for the generic ThreadLocalPool utility."""

    def setup_method(self) -> None:
        """Clear pool before each test."""
        SimplePool.clear()

    def test_acquire_creates_new(self) -> None:
        """Acquire creates new instance when pool is empty."""
        with SimplePool.acquire(42) as instance:
            assert instance == [42]

    def test_acquire_reuses_from_pool(self) -> None:
        """Acquire reuses instance from pool."""
        # First acquire creates new, then returns to pool
        with SimplePool.acquire(1) as instance1:
            id1 = id(instance1)

        # Second acquire reuses the same instance
        with SimplePool.acquire(2) as instance2:
            id2 = id(instance2)
            assert instance2 == [2]  # Reinit was called

        assert id1 == id2  # Same object reused

    def test_clear_empties_pool(self) -> None:
        """Clear removes all instances from pool."""
        with SimplePool.acquire(1):
            pass  # Returns to pool
        assert SimplePool.size() == 1

        SimplePool.clear()
        assert SimplePool.size() == 0

    def test_size_returns_pool_size(self) -> None:
        """Size returns current pool size."""
        assert SimplePool.size() == 0

        with SimplePool.acquire(1):
            pass  # Returns to pool
        assert SimplePool.size() == 1

        with SimplePool.acquire(2):
            pass  # Returns to pool
        assert SimplePool.size() == 1  # Only one slot used (reused then returned)

    def test_thread_isolation(self) -> None:
        """Each thread has its own pool."""
        results: dict[str, int] = {}

        def use_pool(name: str) -> None:
            # Each thread gets its own pool
            with SimplePool.acquire(1):
                pass
            results[name] = SimplePool.size()

        thread1 = threading.Thread(target=use_pool, args=("t1",))
        thread2 = threading.Thread(target=use_pool, args=("t2",))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Each thread has 1 item in its pool
        assert results["t1"] == 1
        assert results["t2"] == 1
        # Main thread pool is still empty
        assert SimplePool.size() == 0
