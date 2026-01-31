import os

from bengal.errors.traceback import (
    TracebackConfig,
    TracebackStyle,
    apply_file_traceback_to_env,
    map_debug_flag_to_traceback,
    set_effective_style_from_cli,
)


def _clear_env(keys: list[str]) -> None:
    for k in keys:
        os.environ.pop(k, None)


def test_default_style_is_compact(monkeypatch):
    _clear_env([
        "BENGAL_TRACEBACK",
        "CI",
        "TERM",
        "BENGAL_TRACEBACK_SHOW_LOCALS",
        "BENGAL_TRACEBACK_MAX_FRAMES",
        "BENGAL_TRACEBACK_SUPPRESS",
    ])
    cfg = TracebackConfig.from_environment()
    assert cfg.style == TracebackStyle.COMPACT
    assert cfg.show_locals is False
    assert cfg.max_frames == 10


def test_env_sets_full_style(monkeypatch):
    _clear_env(["BENGAL_TRACEBACK"])
    monkeypatch.setenv("BENGAL_TRACEBACK", "full")
    cfg = TracebackConfig.from_environment()
    assert cfg.style == TracebackStyle.FULL
    assert cfg.show_locals is True
    assert cfg.max_frames >= 20


def test_map_debug_maps_to_full_when_not_overridden(monkeypatch):
    _clear_env(["BENGAL_TRACEBACK"])
    map_debug_flag_to_traceback(True, None)
    assert os.environ.get("BENGAL_TRACEBACK") == "full"


def test_map_debug_does_not_override_explicit_traceback(monkeypatch):
    _clear_env(["BENGAL_TRACEBACK"])
    set_effective_style_from_cli("minimal")
    map_debug_flag_to_traceback(True, "minimal")
    assert os.environ.get("BENGAL_TRACEBACK") == "minimal"


def test_get_renderer_types(monkeypatch):
    _clear_env(["BENGAL_TRACEBACK"])
    # Full
    set_effective_style_from_cli("full")
    cfg = TracebackConfig.from_environment()
    from bengal.errors.traceback import FullTracebackRenderer

    assert isinstance(cfg.get_renderer(), FullTracebackRenderer)

    # Compact
    set_effective_style_from_cli("compact")
    cfg = TracebackConfig.from_environment()
    from bengal.errors.traceback import CompactTracebackRenderer

    assert isinstance(cfg.get_renderer(), CompactTracebackRenderer)

    # Minimal
    set_effective_style_from_cli("minimal")
    cfg = TracebackConfig.from_environment()
    from bengal.errors.traceback import MinimalTracebackRenderer

    assert isinstance(cfg.get_renderer(), MinimalTracebackRenderer)

    # Off
    set_effective_style_from_cli("off")
    cfg = TracebackConfig.from_environment()
    from bengal.errors.traceback import OffTracebackRenderer

    assert isinstance(cfg.get_renderer(), OffTracebackRenderer)


def test_apply_file_traceback_to_env_sets_env(monkeypatch):
    # Clear env
    _clear_env(
        [
            "BENGAL_TRACEBACK",
            "BENGAL_TRACEBACK_SHOW_LOCALS",
            "BENGAL_TRACEBACK_MAX_FRAMES",
            "BENGAL_TRACEBACK_SUPPRESS",
        ]
    )

    site_cfg = {
        "dev": {
            "traceback": {
                "style": "minimal",
                "show_locals": True,
                "max_frames": 7,
                "suppress": ["click", "jinja2"],
            }
        }
    }

    apply_file_traceback_to_env(site_cfg)

    assert os.getenv("BENGAL_TRACEBACK") == "minimal"
    assert os.getenv("BENGAL_TRACEBACK_SHOW_LOCALS") == "1"
    assert os.getenv("BENGAL_TRACEBACK_MAX_FRAMES") == "7"
    assert os.getenv("BENGAL_TRACEBACK_SUPPRESS") == "click,jinja2"
