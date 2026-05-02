"""Tests for CI cache input discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bengal.cache.ci import get_input_globs

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class StubSite:
    root_path: Path
    config: dict[str, Any]


def test_get_input_globs_includes_builtin_inputs(tmp_path: Path) -> None:
    site = StubSite(root_path=tmp_path, config={})

    assert get_input_globs(site)[:2] == [
        ("content/**", "built-in"),
        ("config/**", "built-in"),
    ]


def test_get_input_globs_includes_existing_site_asset_dirs(tmp_path: Path) -> None:
    (tmp_path / "templates").mkdir()
    (tmp_path / "static").mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "themes").mkdir()
    site = StubSite(root_path=tmp_path, config={})

    patterns = [pattern for pattern, _source in get_input_globs(site)]

    assert "templates/**" in patterns
    assert "static/**" in patterns
    assert "assets/**" in patterns
    assert "themes/**" in patterns


def test_get_input_globs_includes_configured_dynamic_inputs(tmp_path: Path) -> None:
    site = StubSite(
        root_path=tmp_path,
        config={
            "autodoc": {
                "python": {"enabled": True, "source_dirs": ["../src"]},
                "cli": {"enabled": True, "app_module": "myapp.cli:main"},
                "openapi": {"enabled": True, "spec_file": "api/openapi.yaml"},
            },
            "external_refs": {
                "indexes": [
                    {"url": "data/local-index.json"},
                    {"url": "https://example.com/remote-index.json"},
                ]
            },
            "theme": {"path": "../themes/custom"},
        },
    )

    patterns = [pattern for pattern, _source in get_input_globs(site)]

    assert "../src/**/*.py" in patterns
    assert "../myapp/**/*.py" in patterns
    assert "api/openapi.yaml" in patterns
    assert "data/local-index.json" in patterns
    assert "https://example.com/remote-index.json" not in patterns
    assert "../themes/custom/**" in patterns
