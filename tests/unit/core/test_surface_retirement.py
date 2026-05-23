"""Retirement guards for core compatibility surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.check_core_surface_usage import scan_core_surface_usage, scan_file

if TYPE_CHECKING:
    from pathlib import Path


def test_bengal_internal_code_avoids_retired_section_content_pages() -> None:
    assert scan_core_surface_usage() == ()


def test_core_surface_usage_scan_flags_new_internal_call(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.py"
    candidate.write_text(
        """
def render(section):
    return section.content_pages
""",
        encoding="utf-8",
    )

    usages = scan_file(candidate, root=tmp_path)

    assert len(usages) == 1
    assert usages[0].path == "candidate.py"
    assert usages[0].attr == "content_pages"
    assert "section_ergonomics.content_pages" in usages[0].suggestion
