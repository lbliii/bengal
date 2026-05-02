"""Tests for docs template DOM order."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[3]
TEMPLATE_DIR = ROOT / "bengal" / "themes" / "default" / "templates" / "doc"


def test_docs_single_places_main_content_before_sidebar() -> None:
    template = (TEMPLATE_DIR / "single.html").read_text(encoding="utf-8")

    assert template.index('<div class="docs-main">') < template.index('<aside class="docs-sidebar"')


def test_docs_list_places_main_content_before_sidebar() -> None:
    template = (TEMPLATE_DIR / "list.html").read_text(encoding="utf-8")

    assert template.index('<div class="docs-main">') < template.index('<aside class="docs-sidebar"')
