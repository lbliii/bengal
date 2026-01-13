"""
Tests for incremental behavior of Directives validator analysis.
"""

from __future__ import annotations

from pathlib import Path

from bengal.health.validators.directives.analysis import DirectiveAnalyzer
from bengal.utils.build_context import BuildContext


def test_directive_analyzer_skips_unchanged_pages_in_incremental_mode(tmp_path: Path) -> None:
    """
    When incremental mode is enabled and changed_page_paths is empty, directive analysis should
    skip all pages (no disk reads / parsing work).
        
    """
    # Arrange: create 2 content files and fake pages pointing at them
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text(":::{admonition} Note\nHello\n:::\n", encoding="utf-8")
    b.write_text("No directives here\n", encoding="utf-8")

    page_a = type("P", (), {})()
    page_a.source_path = a
    page_a.metadata = {}

    page_b = type("P", (), {})()
    page_b.source_path = b
    page_b.metadata = {}

    site = type("S", (), {})()
    site.pages = [page_a, page_b]

    ctx = BuildContext(incremental=True, changed_page_paths=set())

    # Act
    data = DirectiveAnalyzer().analyze(site, build_context=ctx)

    # Assert: nothing processed, everything skipped by no_changes
    stats = data.get("_stats") or {}
    assert stats.get("pages_processed") == 0
    skipped = (stats.get("pages_skipped") or {}).get("no_changes")
    assert skipped == 2
