"""Tests for the pluggable template-engine registry lock."""

from __future__ import annotations

import inspect
import threading
from types import SimpleNamespace

import pytest

from bengal.errors import BengalConfigError
from bengal.rendering.engines import (
    _ENGINES,
    _ENGINES_LOCK,
    create_engine,
    register_engine,
)


class _LockProbeEngine:
    """Minimal engine used to exercise registry locking."""

    def __init__(self, site: object) -> None:
        self.site = site


def _unregister_engines(names: list[str]) -> None:
    with _ENGINES_LOCK:
        for name in names:
            _ENGINES.pop(name, None)


def _site_for_engine(name: str) -> SimpleNamespace:
    return SimpleNamespace(config={"template_engine": name})


class TestRegistryLock:
    """Module-level registry dict is locked on every read and write."""

    def test_registry_lock_is_threading_lock(self) -> None:
        assert type(_ENGINES_LOCK) is type(threading.Lock())

    def test_public_signatures_unchanged(self) -> None:
        register_params = inspect.signature(register_engine).parameters
        assert list(register_params) == ["name", "engine_class"]

        create_params = inspect.signature(create_engine).parameters
        assert list(create_params) == ["site", "profile"]
        assert create_params["profile"].kind is inspect.Parameter.KEYWORD_ONLY
        assert create_params["profile"].default is False

    def test_register_then_create_uses_registered_class(self) -> None:
        name = "lock-probe-create"
        try:
            register_engine(name, _LockProbeEngine)
            engine = create_engine(_site_for_engine(name))
            assert isinstance(engine, _LockProbeEngine)
        finally:
            _unregister_engines([name])

    def test_unknown_engine_lists_registered_names(self) -> None:
        name = "lock-probe-listed"
        try:
            register_engine(name, _LockProbeEngine)
            with pytest.raises(BengalConfigError) as exc_info:
                create_engine(_site_for_engine("no-such-engine"))
            message = str(exc_info.value)
            assert "no-such-engine" in message
            assert name in message
            assert "kida" in message
        finally:
            _unregister_engines([name])

    @pytest.mark.parallel_unsafe
    def test_concurrent_register_and_create(self) -> None:
        names = [f"lock-probe-{i}" for i in range(16)]
        errors: list[BaseException] = []

        def _register(name: str) -> None:
            try:
                register_engine(name, _LockProbeEngine)
            except Exception as exc:
                errors.append(exc)

        def _create_loop() -> None:
            try:
                for name in names:
                    try:
                        engine = create_engine(_site_for_engine(name))
                    except BengalConfigError:
                        continue
                    assert isinstance(engine, _LockProbeEngine)
            except Exception as exc:
                errors.append(exc)

        def _unknown_loop() -> None:
            try:
                for _ in range(20):
                    with pytest.raises(BengalConfigError):
                        create_engine(_site_for_engine("no-such-engine"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_register, args=(name,)) for name in names]
        threads.extend(threading.Thread(target=_create_loop) for _ in range(4))
        threads.extend(threading.Thread(target=_unknown_loop) for _ in range(4))

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        try:
            assert errors == []
            for name in names:
                engine = create_engine(_site_for_engine(name))
                assert isinstance(engine, _LockProbeEngine)
        finally:
            _unregister_engines(names)
