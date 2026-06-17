"""Tests for git-derived last-modified helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from bengal.core.page.lastmod import resolve_page_lastmod, resolve_page_lastmod_iso


def test_resolve_page_lastmod_prefers_frontmatter() -> None:
    page = Mock()
    page.metadata = {"lastmod": "2024-05-01T12:00:00"}
    page.source_path = Path("/tmp/content/page.md")

    result = resolve_page_lastmod(page)

    assert result == datetime.fromisoformat("2024-05-01T12:00:00")


def test_resolve_page_lastmod_uses_git_dates_when_frontmatter_missing() -> None:
    page = Mock()
    page.metadata = {}
    source_path = Path("/repo/content/page.md").resolve()
    page.source_path = source_path

    git_dates = {source_path: datetime(2024, 6, 2, 9, 30, 0)}
    result = resolve_page_lastmod(page, git_dates=git_dates)

    assert result == git_dates[source_path]


def test_resolve_page_lastmod_iso_preserves_frontmatter_string() -> None:
    page = Mock()
    page.metadata = {"lastmod": "2025-06-15"}
    page.source_path = Path("/tmp/content/page.md")

    assert resolve_page_lastmod_iso(page) == "2025-06-15"


def test_resolve_page_lastmod_ignores_magicmock_git_dates() -> None:
    page = Mock()
    page.metadata = {}
    page.source_path = Path("/nonexistent/path/page.md")

    assert resolve_page_lastmod(page, git_dates=Mock()) is None
    assert resolve_page_lastmod_iso(page, git_dates=Mock()) is None
