"""Tests for include inspector debug helper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.debug.include_inspector import inspect_page_includes

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class FakeSite:
    root_path: Path


def test_inspect_page_includes_resolves_snippet(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    snippet = content_dir / "_snippets" / "note.md"
    snippet.parent.mkdir(parents=True)
    snippet.write_text("Note.\n")

    page_path = content_dir / "docs" / "page.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(":::{include} _snippets/note.md\n:::\n")

    inspection = inspect_page_includes(FakeSite(root_path=tmp_path), "docs/page.md")
    assert len(inspection.references) == 1
    assert inspection.references[0].resolved_path == snippet.resolve()
    assert not inspection.missing_targets


def test_inspect_page_includes_reports_missing_target(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    page_path = content_dir / "page.md"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(":::{include} _snippets/missing.md\n:::\n")

    inspection = inspect_page_includes(FakeSite(root_path=tmp_path), "page.md")
    assert len(inspection.missing_targets) == 1
