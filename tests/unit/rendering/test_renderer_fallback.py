"""
Unit tests for renderer template-error fallback vs overlay vs strict raise.

Contract:
- Strict ``bengal build`` re-raises ``TemplateRenderError`` (no overlay HTML).
- Non-strict builds write the small fallback page, not the browser overlay.
- ``BENGAL_DEV_SERVER=1`` (``bengal serve``) writes overlay HTML even when
  serve has flipped ``build.strict_mode``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bengal.rendering.errors import TemplateRenderError
from bengal.rendering.renderer.fallback import (
    handle_render_error,
    render_fallback,
    resolve_strict_mode,
)


def _renderer(*, config: dict[str, object], stats_strict: bool = False) -> SimpleNamespace:
    site = SimpleNamespace(config=config, output_dir=Path("/tmp/bengal-fallback-test"))
    stats = SimpleNamespace(
        strict_mode=stats_strict,
        get_error_deduplicator=lambda: SimpleNamespace(should_display=lambda _err: True),
        add_template_error=Mock(),
    )
    engine = SimpleNamespace(
        env=SimpleNamespace(filters={}, globals={}),
        template_dirs=[],
        _find_template_path=lambda _name: None,
    )
    renderer = SimpleNamespace(
        site=site,
        build_stats=stats,
        template_engine=engine,
        _get_site_title=lambda: "Site",
    )
    renderer._render_fallback = lambda page, content: render_fallback(renderer, page, content)
    return renderer


def _page() -> SimpleNamespace:
    return SimpleNamespace(title="Test Page", source_path=Path("content/test.md"))


def _handle(renderer: SimpleNamespace) -> str:
    return handle_render_error(
        renderer,
        _page(),
        "<p>body</p>",
        "nonexistent.html",
        FileNotFoundError("nonexistent.html"),
    )


class TestResolveStrictMode:
    def test_build_stats_strict_from_build_options(self) -> None:
        renderer = _renderer(config={"build": {"strict_mode": False}}, stats_strict=True)
        assert resolve_strict_mode(renderer) is True

    def test_canonical_build_strict_mode(self) -> None:
        renderer = _renderer(config={"build": {"strict_mode": True}}, stats_strict=False)
        assert resolve_strict_mode(renderer) is True

    def test_legacy_top_level_strict_mode(self) -> None:
        renderer = _renderer(config={"strict_mode": True, "build": {"strict_mode": False}})
        assert resolve_strict_mode(renderer) is True

    def test_default_is_not_strict(self) -> None:
        renderer = _renderer(config={"build": {"strict_mode": False}})
        assert resolve_strict_mode(renderer) is False


class TestHandleRenderError:
    def test_strict_build_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BENGAL_DEV_SERVER", raising=False)
        renderer = _renderer(config={"build": {"strict_mode": True}})
        with pytest.raises(TemplateRenderError):
            _handle(renderer)

    def test_legacy_top_level_strict_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BENGAL_DEV_SERVER", raising=False)
        renderer = _renderer(config={"strict_mode": True})
        with pytest.raises(TemplateRenderError):
            _handle(renderer)

    def test_stats_strict_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BENGAL_DEV_SERVER", raising=False)
        renderer = _renderer(config={"build": {"strict_mode": False}}, stats_strict=True)
        with pytest.raises(TemplateRenderError):
            _handle(renderer)

    def test_non_strict_build_uses_small_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BENGAL_DEV_SERVER", raising=False)
        renderer = _renderer(config={"build": {"strict_mode": False}})
        html = _handle(renderer)
        assert "fallback mode" in html
        assert "Build Error" not in html
        assert len(html.encode()) < 2000

    def test_dev_server_uses_overlay_even_when_strict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BENGAL_DEV_SERVER", "1")
        renderer = _renderer(config={"build": {"strict_mode": True}})
        html = _handle(renderer)
        assert "Build Error" in html
        assert "fallback mode" not in html
