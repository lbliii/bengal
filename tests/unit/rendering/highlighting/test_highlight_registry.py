"""
Tests for the highlighting backend registry.

Validates the registry functions: register_backend, get_highlighter,
list_backends, and highlight.
"""

from __future__ import annotations

import inspect
import threading

import pytest

from bengal.errors import BengalConfigError
from bengal.rendering.highlighting import (
    _HIGHLIGHT_BACKENDS,
    _HIGHLIGHT_BACKENDS_LOCK,
    get_highlighter,
    highlight,
    list_backends,
    register_backend,
)
from bengal.rendering.highlighting.rosettes import RosettesBackend


class TestRegistryFunctions:
    """Test the registry public API."""

    def test_rosettes_backend_registered_by_default(self) -> None:
        """Rosettes backend should be registered automatically."""
        backends = list_backends()
        assert "rosettes" in backends

    def test_get_highlighter_default_is_rosettes(self) -> None:
        """Default highlighter should be Rosettes."""
        backend = get_highlighter()
        assert backend.name == "rosettes"
        assert isinstance(backend, RosettesBackend)

    def test_get_highlighter_by_name(self) -> None:
        """Should get backend by explicit name."""
        backend = get_highlighter("rosettes")
        assert backend.name == "rosettes"

    def test_get_highlighter_case_insensitive(self) -> None:
        """Backend names should be case-insensitive."""
        backend1 = get_highlighter("rosettes")
        backend2 = get_highlighter("ROSETTES")
        backend3 = get_highlighter("Rosettes")

        assert backend1.name == backend2.name == backend3.name

    def test_get_highlighter_unknown_raises_error(self) -> None:
        """Unknown backend name should raise BengalConfigError."""
        with pytest.raises(BengalConfigError) as exc_info:
            get_highlighter("unknown-backend")

        assert "Unknown highlighting backend" in str(exc_info.value)
        assert "unknown-backend" in str(exc_info.value)

    def test_list_backends_returns_sorted_list(self) -> None:
        """list_backends() should return sorted list of names."""
        backends = list_backends()
        assert isinstance(backends, list)
        assert backends == sorted(backends)

    def test_highlight_function_uses_default_backend(self) -> None:
        """highlight() convenience function should work."""
        result = highlight("print('hello')", "python")

        assert isinstance(result, str)
        assert "hello" in result
        # Should have highlighting classes
        assert "rosettes" in result.lower()

    def test_highlight_with_explicit_backend(self) -> None:
        """highlight() should accept backend parameter."""
        result = highlight("print('hello')", "python", backend="rosettes")

        assert isinstance(result, str)
        assert "hello" in result


class TestRegisterBackend:
    """Test custom backend registration."""

    def test_register_custom_backend(self) -> None:
        """Should be able to register a custom backend."""

        class CustomBackend:
            @property
            def name(self) -> str:
                return "custom"

            def highlight(
                self,
                code: str,
                language: str,
                hl_lines: list[int] | None = None,
                show_linenos: bool = False,
            ) -> str:
                return f"<custom>{code}</custom>"

            def supports_language(self, language: str) -> bool:
                return True

        # Register the custom backend
        register_backend("custom", CustomBackend)

        # Should now be in the list
        assert "custom" in list_backends()

        # Should be retrievable
        backend = get_highlighter("custom")
        assert backend.name == "custom"

        # Should work via highlight()
        result = highlight("test", "python", backend="custom")
        assert "<custom>" in result

    def test_register_backend_requires_class(self) -> None:
        """register_backend() should require a class, not instance."""

        class ValidBackend:
            @property
            def name(self) -> str:
                return "valid"

            def highlight(self, code: str, language: str, **kwargs) -> str:
                return code

            def supports_language(self, language: str) -> bool:
                return True

        # Should work with class
        register_backend("valid", ValidBackend)

        # Should fail with instance
        with pytest.raises(TypeError):
            register_backend("invalid", ValidBackend())  # type: ignore


class TestAutoMode:
    """Test the 'auto' backend selection mode."""

    def test_auto_mode_uses_rosettes(self) -> None:
        """'auto' mode should use rosettes as the default backend."""
        backend = get_highlighter("auto")

        # Rosettes is the only built-in backend
        assert backend.name == "rosettes"

    def test_auto_mode_produces_valid_output(self) -> None:
        """'auto' mode should produce valid highlighted output."""
        result = highlight("print('hello')", "python", backend="auto")

        assert isinstance(result, str)
        assert "hello" in result
        assert "<" in result  # Should have HTML tags


class _LockProbeBackend:
    """Minimal backend used to exercise registry locking."""

    @property
    def name(self) -> str:
        return "lock-probe"

    def highlight(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        return code

    def supports_language(self, language: str) -> bool:
        return True


def _unregister_backends(names: list[str]) -> None:
    with _HIGHLIGHT_BACKENDS_LOCK:
        for name in names:
            _HIGHLIGHT_BACKENDS.pop(name, None)


class TestRegistryLock:
    """Module-level registry dict is locked on every read and write."""

    def test_registry_lock_is_threading_lock(self) -> None:
        assert type(_HIGHLIGHT_BACKENDS_LOCK) is type(threading.Lock())

    def test_public_signatures_unchanged(self) -> None:
        register_params = inspect.signature(register_backend).parameters
        assert list(register_params) == ["name", "backend_class"]

        get_params = inspect.signature(get_highlighter).parameters
        assert list(get_params) == ["name"]
        assert get_params["name"].default is None

        list_params = inspect.signature(list_backends).parameters
        assert list(list_params) == []
        assert inspect.signature(list_backends).return_annotation in {list[str], "list[str]"}

    def test_list_backends_returns_snapshot(self) -> None:
        backends = list_backends()
        backends.append("mutated-snapshot")
        assert "mutated-snapshot" not in list_backends()

    @pytest.mark.parallel_unsafe
    def test_concurrent_register_list_and_get(self) -> None:
        names = [f"lock-probe-{i}" for i in range(16)]
        errors: list[BaseException] = []

        def _register(name: str) -> None:
            try:
                register_backend(name, _LockProbeBackend)
            except Exception as exc:
                errors.append(exc)

        def _list_loop() -> None:
            try:
                for _ in range(40):
                    listed = list_backends()
                    assert isinstance(listed, list)
                    assert listed == sorted(listed)
            except Exception as exc:
                errors.append(exc)

        def _get_rosettes() -> None:
            try:
                for _ in range(20):
                    backend = get_highlighter("rosettes")
                    assert backend.name == "rosettes"
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_register, args=(name,)) for name in names]
        threads.extend(threading.Thread(target=_list_loop) for _ in range(4))
        threads.extend(threading.Thread(target=_get_rosettes) for _ in range(4))

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        try:
            assert errors == []
            listed = list_backends()
            for name in names:
                assert name in listed
            backend = get_highlighter(names[0])
            assert backend.name == "lock-probe"
        finally:
            _unregister_backends(names)
