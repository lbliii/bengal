"""Tests for design token manifest generation (#545)."""

from __future__ import annotations

import json

from bengal.themes.generate import generate_design_tokens_manifest, write_design_tokens_manifest


def test_generate_design_tokens_manifest_has_named_consumer() -> None:
    manifest = generate_design_tokens_manifest()
    assert manifest["consumer"] == "action-bar-copy-theme-tokens"
    assert "snow-lynx" in manifest["palettes"]
    assert "palettes" in manifest
    assert manifest["default_palette"]["primary"]


def test_write_design_tokens_manifest_roundtrip(tmp_path) -> None:
    path = write_design_tokens_manifest(tmp_path / "design-tokens.json")
    data = json.loads(path.read_text())
    assert data["name"] == "bengal-default-theme"
    assert len(data["palettes"]) >= 5
