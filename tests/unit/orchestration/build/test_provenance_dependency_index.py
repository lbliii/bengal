"""Tests for provenance dependency-index lookup integration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bengal.build.contracts import DependencyIndexEntry, DependencyReadIndex
from bengal.cache import BuildCache
from bengal.orchestration.build import provenance_filter


def test_expand_forced_changed_uses_dependency_index_for_data_file(
    tmp_path: Path, monkeypatch
) -> None:
    """Data-file changes can use the persisted dependency read index."""
    data_file = tmp_path / "data" / "team.yaml"
    data_file.parent.mkdir()
    data_file.write_text("team: docs\n")
    cache = BuildCache(site_root=tmp_path)
    site = SimpleNamespace(root_path=tmp_path)
    index = DependencyReadIndex(
        [
            DependencyIndexEntry(
                dependency_kind="data",
                dependency_key="data/team.yaml",
                page_keys=("content/about.md",),
                invalidation_reason="data_dependency_changed",
                producer="provenance",
            )
        ]
    )
    monkeypatch.setattr(provenance_filter, "iter_template_files", lambda _site: ())

    expanded, reasons = provenance_filter._expand_forced_changed(set(), cache, site, [], index)

    assert expanded == {Path("content/about.md")}
    assert reasons["content/about.md"] == ["data_file:team.yaml"]


def test_get_pages_for_data_file_falls_back_without_dependency_index(tmp_path: Path) -> None:
    """Missing dependency-index entries preserve the existing cache-graph fallback."""
    data_file = tmp_path / "data" / "team.yaml"
    content_file = tmp_path / "content" / "about.md"
    data_file.parent.mkdir()
    content_file.parent.mkdir()
    data_file.write_text("team: docs\n")
    content_file.write_text("# About\n")
    cache = BuildCache(site_root=tmp_path)
    cache.add_dependency(content_file, data_file)

    pages = provenance_filter._get_pages_for_data_file(cache, data_file, DependencyReadIndex())

    assert pages == {Path("content/about.md")}


def test_expand_forced_changed_uses_dependency_index_for_templates(
    tmp_path: Path, monkeypatch
) -> None:
    """Template changes can use the read index without broad full-rebuild fallback."""
    template_dir = tmp_path / "templates"
    template_file = template_dir / "page.html"
    template_dir.mkdir()
    template_file.write_text("{{ page.title }}\n")
    cache = BuildCache(site_root=tmp_path)
    site = SimpleNamespace(root_path=tmp_path)
    pages = [
        SimpleNamespace(source_path=Path("content/about.md")),
        SimpleNamespace(source_path=Path("content/other.md")),
    ]
    index = DependencyReadIndex(
        [
            DependencyIndexEntry(
                dependency_kind="template",
                dependency_key="page.html",
                page_keys=("content/about.md",),
                invalidation_reason="template_dependency_changed",
                producer="provenance",
            )
        ]
    )
    monkeypatch.setattr(provenance_filter, "iter_template_files", lambda _site: (template_file,))
    monkeypatch.setattr(provenance_filter, "resolve_template_dirs", lambda _site: [template_dir])

    expanded, reasons = provenance_filter._expand_forced_changed(set(), cache, site, pages, index)

    assert expanded == {Path("content/about.md")}
    assert reasons["content/about.md"] == ["template_changed:page.html"]
