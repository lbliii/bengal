"""
Unit tests for the isolated render crossover gate (issue #350, saga S5).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from bengal.orchestration.render.isolated.gate import (
    DEFAULT_THRESHOLD,
    IsolationSettings,
    decide_isolation,
    resolve_isolation_settings,
)

if TYPE_CHECKING:
    import pytest

# --- resolve_isolation_settings --------------------------------------------


def test_resolve_defaults_to_off() -> None:
    s = resolve_isolation_settings({})
    assert s.mode == "off"
    assert s.threshold == DEFAULT_THRESHOLD
    assert s.workers is None


def test_resolve_from_dict_config() -> None:
    config = {
        "build": {
            "render_isolation": "fork",
            "render_isolation_threshold": 250,
            "render_isolation_workers": 6,
        }
    }
    s = resolve_isolation_settings(config)
    assert s == IsolationSettings(mode="fork", threshold=250, workers=6)


def test_resolve_from_typed_config() -> None:
    config = SimpleNamespace(
        build=SimpleNamespace(
            render_isolation="auto",
            render_isolation_threshold=300,
            render_isolation_workers=None,
        )
    )
    s = resolve_isolation_settings(config)
    assert s.mode == "auto"
    assert s.threshold == 300


def test_resolve_invalid_mode_falls_back_to_off() -> None:
    s = resolve_isolation_settings({"build": {"render_isolation": "bogus"}})
    assert s.mode == "off"


def test_env_overrides_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BENGAL_RENDER_ISOLATION", "fork")
    monkeypatch.setenv("BENGAL_RENDER_ISOLATION_THRESHOLD", "10")
    monkeypatch.setenv("BENGAL_RENDER_ISOLATION_WORKERS", "4")
    s = resolve_isolation_settings({"build": {"render_isolation": "off"}})
    assert s.mode == "fork"
    assert s.threshold == 10
    assert s.workers == 4


# --- decide_isolation ------------------------------------------------------

_ENABLED = {
    "page_count": 1000,
    "incremental": False,
    "parallel": True,
    "has_snapshot": True,
    "fork_available": True,
}


def _fork_settings(threshold: int = 400) -> IsolationSettings:
    return IsolationSettings(mode="fork", threshold=threshold)


def test_decision_enabled_for_large_cold_build() -> None:
    d = decide_isolation(_fork_settings(400), **_ENABLED)
    assert d.enabled
    assert d.mode == "fork"


def test_decision_off_when_mode_off() -> None:
    d = decide_isolation(IsolationSettings(mode="off"), **_ENABLED)
    assert not d.enabled
    assert "off" in d.reason


def test_decision_off_when_incremental() -> None:
    d = decide_isolation(_fork_settings(), **{**_ENABLED, "incremental": True})
    assert not d.enabled
    assert "incremental" in d.reason


def test_decision_off_when_sequential() -> None:
    d = decide_isolation(_fork_settings(), **{**_ENABLED, "parallel": False})
    assert not d.enabled


def test_decision_off_without_snapshot() -> None:
    d = decide_isolation(_fork_settings(), **{**_ENABLED, "has_snapshot": False})
    assert not d.enabled


def test_decision_off_below_threshold() -> None:
    d = decide_isolation(_fork_settings(500), **{**_ENABLED, "page_count": 100})
    assert not d.enabled
    assert "below crossover" in d.reason


def test_decision_off_when_fork_unavailable() -> None:
    d = decide_isolation(_fork_settings(), **{**_ENABLED, "fork_available": False})
    assert not d.enabled
    assert "fork" in d.reason


def test_decision_spawn_not_implemented() -> None:
    d = decide_isolation(IsolationSettings(mode="spawn", threshold=400), **_ENABLED)
    assert not d.enabled
    assert "spawn" in d.reason


def test_decision_carries_worker_override() -> None:
    d = decide_isolation(IsolationSettings(mode="fork", threshold=400, workers=3), **_ENABLED)
    assert d.enabled
    assert d.workers == 3
