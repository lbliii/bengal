"""Tests for Merkle advisory snapshot persistence/diffing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bengal.orchestration.build.merkle_graph import collect_merkle_advisory


@dataclass
class _Page:
    source_path: Path
    metadata: dict[str, str]
    type: str | None = None


@dataclass
class _TemplateEngine:
    manifests: dict[str, dict[str, object]]

    def get_template_manifest(self, name: str) -> dict[str, object] | None:
        return self.manifests.get(name)


@dataclass
class _Site:
    pages: list[_Page]
    template_engine: _TemplateEngine


def test_merkle_advisory_persists_and_detects_noop(tmp_path: Path) -> None:
    page_path = tmp_path / "content.md"
    page_path.write_text("hello")
    site = _Site(
        pages=[_Page(source_path=page_path, metadata={"template": "page.html"})],
        template_engine=_TemplateEngine(
            manifests={
                "page.html": {
                    "name": "page.html",
                    "extends": "base.html",
                    "block_names": ("content",),
                    "block_hashes": {"content": "abc123"},
                    "dependencies": frozenset({"page.title"}),
                }
            }
        ),
    )

    first = collect_merkle_advisory(site, tmp_path)
    assert len(first.dirty_content) == 1
    assert len(first.dirty_templates) == 1
    assert len(first.dirty_pages) == 1
    assert first.previous_root is None

    second = collect_merkle_advisory(site, tmp_path)
    assert second.previous_root is not None
    assert len(second.dirty_content) == 0
    assert len(second.dirty_templates) == 0
    assert len(second.dirty_pages) == 0


def test_merkle_advisory_detects_content_and_template_changes(tmp_path: Path) -> None:
    page_path = tmp_path / "doc.md"
    page_path.write_text("first")
    engine = _TemplateEngine(
        manifests={
            "doc.html": {
                "name": "doc.html",
                "extends": "base.html",
                "block_names": ("content",),
                "block_hashes": {"content": "111"},
                "dependencies": frozenset({"page.content"}),
            }
        }
    )
    site = _Site(
        pages=[_Page(source_path=page_path, metadata={"template": "doc.html"})],
        template_engine=engine,
    )
    collect_merkle_advisory(site, tmp_path)

    page_path.write_text("second")
    advisory_content = collect_merkle_advisory(site, tmp_path)
    assert str(page_path) in advisory_content.dirty_content
    assert str(page_path) in advisory_content.dirty_pages

    engine.manifests["doc.html"] = {
        "name": "doc.html",
        "extends": "base.html",
        "block_names": ("content",),
        "block_hashes": {"content": "222"},
        "dependencies": frozenset({"page.content"}),
    }
    advisory_template = collect_merkle_advisory(site, tmp_path)
    assert "doc.html" in advisory_template.dirty_templates
    assert str(page_path) in advisory_template.dirty_pages
