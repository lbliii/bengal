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
        ("content/**", "content"),
        ("config/**", "config directory"),
    ]


def test_get_input_globs_includes_existing_build_input_dirs(tmp_path: Path) -> None:
    (tmp_path / "custom_templates").mkdir()
    (tmp_path / "public_files").mkdir()
    (tmp_path / "theme_assets").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "i18n").mkdir()
    (tmp_path / "themes").mkdir()
    site = StubSite(
        root_path=tmp_path,
        config={
            "build": {"templates_dir": "custom_templates", "assets_dir": "theme_assets"},
            "static": {"enabled": True, "dir": "public_files"},
        },
    )

    patterns = [pattern for pattern, _source in get_input_globs(site)]

    assert "custom_templates/**" in patterns
    assert "public_files/**" in patterns
    assert "theme_assets/**" in patterns
    assert "data/**" in patterns
    assert "i18n/**" in patterns
    assert "themes/**" in patterns


def test_get_input_globs_includes_configured_dynamic_inputs(tmp_path: Path) -> None:
    external_src = tmp_path.parent / "external-src"
    external_src.mkdir()
    external_spec = tmp_path.parent / "openapi.yaml"
    external_spec.write_text("openapi: 3.1.0\n")

    site = StubSite(
        root_path=tmp_path,
        config={
            "build": {"content_dir": "docs"},
            "autodoc": {
                "python": {"enabled": True, "source_dirs": [str(external_src)]},
                "cli": {"enabled": True, "app_module": "myapp.cli:main"},
                "openapi": {"enabled": True, "spec_file": str(external_spec)},
            },
            "external_refs": {
                "indexes": [
                    {"url": "data/local-index.json"},
                    {"url": "../../../other/public/xref.json"},
                    {"url": "https://example.com/remote-index.json"},
                ]
            },
            "theme": {"path": "../themes/custom"},
        },
    )

    patterns = [pattern for pattern, _source in get_input_globs(site)]

    assert "docs/**" in patterns
    assert f"{external_src.as_posix()}/**/*.py" in patterns
    assert "../myapp/**/*.py" in patterns
    assert external_spec.as_posix() in patterns
    assert "data/local-index.json" in patterns
    assert (tmp_path / "../../../other/public/xref.json").resolve().as_posix() in patterns
    assert "https://example.com/remote-index.json" not in patterns
    assert "../themes/custom/**" in patterns


def test_get_input_globs_includes_single_file_configs(tmp_path: Path) -> None:
    (tmp_path / "bengal.toml").write_text("[site]\ntitle = 'Test'\n")
    custom_config = tmp_path.parent / "custom.toml"
    custom_config.write_text("[site]\ntitle = 'Custom'\n")
    site = StubSite(root_path=tmp_path, config={})

    patterns = [pattern for pattern, _source in get_input_globs(site, config_path=custom_config)]

    assert "bengal.toml" in patterns
    assert custom_config.as_posix() in patterns
