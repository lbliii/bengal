"""
Tests for incremental behavior of Directives validator analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.health.scope import ValidationScope, with_validation_scope
from bengal.health.validators.directives.analysis import DirectiveAnalyzer

if TYPE_CHECKING:
    from pathlib import Path


def test_directive_analyzer_uses_shared_validation_scope(tmp_path: Path) -> None:
    """
    Directive analysis scopes through ValidationScope instead of private changed-page skips.

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

    ctx = with_validation_scope(
        None,
        ValidationScope(incremental=True, files_to_validate=frozenset({a})),
    )

    # Act
    data = DirectiveAnalyzer().analyze(site, build_context=ctx)

    # Assert: only the scoped file is processed.
    stats = data.get("_stats") or {}
    assert stats.get("pages_processed") == 1
    skipped = (stats.get("pages_skipped") or {}).get("unscoped")
    assert skipped == 1
