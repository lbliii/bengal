"""Tests for Git versioned build helper behavior."""

from __future__ import annotations

import types

from bengal.cli.milo_commands.build import (
    _apply_inherited_capabilities,
    _merge_staged_version_output,
)


def _site_with_config(config) -> types.SimpleNamespace:
    return types.SimpleNamespace(config=config)


def test_inherited_capabilities_seed_a_worktree_with_none() -> None:
    """A tag cut before a capability existed gets it from the build environment."""
    site = _site_with_config({})

    _apply_inherited_capabilities(site, {"mermaid": True})

    assert site.config["capabilities"] == {"mermaid": True}


def test_inherited_capabilities_win_on_conflict_but_preserve_local_keys() -> None:
    """Build-environment activation overrides the tag; worktree-only keys survive."""
    site = _site_with_config({"capabilities": {"mermaid": False, "legacy": True}})

    _apply_inherited_capabilities(site, {"mermaid": True, "katex": True})

    assert site.config["capabilities"] == {
        "mermaid": True,  # parent (build env) wins over the tag's False
        "katex": True,  # parent adds a new capability
        "legacy": True,  # worktree-only key preserved
    }


def test_inherited_capabilities_noop_when_empty_or_missing() -> None:
    """No capabilities in the build environment leaves the worktree untouched."""
    site = _site_with_config({"capabilities": {"mermaid": True}})

    _apply_inherited_capabilities(site, None)
    _apply_inherited_capabilities(site, {})

    assert site.config["capabilities"] == {"mermaid": True}
    # And an absent inherited dict must not create the key on a bare site.
    bare = _site_with_config({})
    _apply_inherited_capabilities(bare, None)
    assert "capabilities" not in bare.config


def test_merge_staged_version_output_preserves_latest_assets(tmp_path) -> None:
    source_dir = tmp_path / "staged"
    root_output_dir = tmp_path / "public"

    (source_dir / "docs" / "v1").mkdir(parents=True)
    (source_dir / "docs" / "v1" / "index.html").write_text("v1", encoding="utf-8")
    (source_dir / "assets" / "css").mkdir(parents=True)
    (source_dir / "assets" / "css" / "style.css").write_text("legacy", encoding="utf-8")
    (source_dir / "assets" / "css" / "legacy.css").write_text("legacy only", encoding="utf-8")

    (root_output_dir / "assets" / "css").mkdir(parents=True)
    (root_output_dir / "assets" / "css" / "style.css").write_text("latest", encoding="utf-8")

    _merge_staged_version_output(
        source_dir=source_dir,
        root_output_dir=root_output_dir,
        sections=["docs"],
        version_id="v1",
    )

    assert (root_output_dir / "docs" / "v1" / "index.html").read_text(encoding="utf-8") == "v1"
    assert (root_output_dir / "assets" / "css" / "style.css").read_text(
        encoding="utf-8"
    ) == "latest"
    assert (root_output_dir / "assets" / "css" / "legacy.css").read_text(
        encoding="utf-8"
    ) == "legacy only"
