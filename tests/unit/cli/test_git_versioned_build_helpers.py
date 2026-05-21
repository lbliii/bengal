"""Tests for Git versioned build helper behavior."""

from __future__ import annotations

from bengal.cli.milo_commands.build import _merge_staged_version_output


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
