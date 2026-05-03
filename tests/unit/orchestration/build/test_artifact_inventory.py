"""Tests for build artifact inventory population."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from bengal.core.output import BuildOutputCollector
from bengal.orchestration.build.artifact_inventory import populate_artifact_inventory

if TYPE_CHECKING:
    from pathlib import Path


def test_artifact_inventory_records_existing_outputs_only(tmp_path: Path) -> None:
    output_dir = tmp_path / "public"
    output_dir.mkdir()
    (output_dir / "docs").mkdir()
    (output_dir / "docs" / "index.html").write_text("docs", encoding="utf-8")
    (output_dir / "docs" / "index.txt").write_text("docs txt", encoding="utf-8")
    (output_dir / "llms.txt").write_text("llms", encoding="utf-8")
    (output_dir / "sitemap.xml").write_text("<xml />", encoding="utf-8")

    page = SimpleNamespace(output_path=output_dir / "docs" / "index.html")
    site = SimpleNamespace(
        output_dir=output_dir,
        pages=[page],
        config={
            "output_formats": {
                "enabled": True,
                "per_page": ["json", "llm_txt"],
                "site_wide": ["index_json", "llms_txt"],
            },
            "generate_rss": False,
        },
    )
    collector = BuildOutputCollector(output_dir=output_dir)
    build_context = SimpleNamespace(artifact_collector=collector, output_collector=None)

    populate_artifact_inventory(site, build_context)

    paths = set(collector.get_relative_paths())
    assert "docs/index.html" in paths
    assert "docs/index.txt" in paths
    assert "llms.txt" in paths
    assert "sitemap.xml" in paths
    assert "docs/index.json" not in paths
    assert "index.json" not in paths
