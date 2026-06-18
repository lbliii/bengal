"""
Guard: unified theme primitives (#539, #540).

Prevents re-introducing deleted duplicate CSS files and ensures shortcodes,
manifest entries, and modern layout/scoping primitives stay in place.
"""

from __future__ import annotations

from pathlib import Path

THEME = Path(__file__).resolve().parents[3] / "bengal" / "themes" / "default"
CSS = THEME / "assets" / "css" / "components"
TEMPLATES = THEME / "templates"


def test_merged_stylesheets_deleted() -> None:
    for name in ("api-hub.css", "search-modal.css", "alerts.css"):
        assert not (CSS / name).exists(), f"{name} should be merged and deleted"


def test_manifest_no_deleted_stylesheets() -> None:
    from bengal.themes.default.css_manifest import (
        CSS_FEATURE_MAP,
        CSS_SHARED,
        CSS_TYPE_MAP,
    )

    all_paths: set[str] = set(CSS_SHARED)
    for files in CSS_TYPE_MAP.values():
        all_paths.update(files)
    for files in CSS_FEATURE_MAP.values():
        all_paths.update(files)

    for deleted in (
        "components/api-hub.css",
        "components/search-modal.css",
        "components/alerts.css",
    ):
        assert deleted not in all_paths


def test_shortcodes_route_to_admonition_partial() -> None:
    for name in ("warning.html", "tip.html", "danger.html"):
        text = (TEMPLATES / "shortcodes" / name).read_text(encoding="utf-8")
        assert "partials/admonition-shortcode.html" in text
        assert 'class="callout' not in text


def test_admonitions_have_no_callout_selectors() -> None:
    admonitions = (CSS / "admonitions.css").read_text(encoding="utf-8")
    assert ".callout" not in admonitions


def test_search_is_single_stylesheet() -> None:
    assert (CSS / "search.css").exists()
    search = (CSS / "search.css").read_text(encoding="utf-8")
    assert ".search-dialog" in search or ".search-modal" in search


def test_container_queries_on_layout_primitives() -> None:
    tracks = (CSS / "tracks.css").read_text(encoding="utf-8")
    hub = (CSS / "hub-cards.css").read_text(encoding="utf-8")
    cards = (CSS / "cards.css").read_text(encoding="utf-8")

    assert "container-name: tracks-layout" in tracks
    assert "@container tracks-layout" in tracks
    assert "container-name: hub-layout" in hub
    assert "@container hub-layout" in hub
    assert "container-name: card-grid" in cards
    assert "@container card-grid" in cards


def test_prose_links_use_scope() -> None:
    typography = (THEME / "assets" / "css" / "base" / "typography.css").read_text(encoding="utf-8")
    assert "@scope (.prose)" in typography
