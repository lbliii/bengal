"""Integration tests for card_excerpt and excerpt_for_card in template context."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("kida", reason="Template engine requires kida")

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine


def test_card_excerpt_filter_in_template(tmp_path: Path) -> None:
    """Verify card_excerpt filter works when rendered via template engine."""
    site = Site(root_path=tmp_path, config={"title": "Test"})
    engine = TemplateEngine(site)

    html = engine.render_string(
        "{{ excerpt | card_excerpt(5, title, desc) | safe }}",
        {"excerpt": "My Post. This is the actual content to show.", "title": "My Post", "desc": ""},
    )
    assert "This is the actual content" in html
    assert "My Post" not in html
    assert html.strip().endswith("...")


def test_excerpt_for_card_filter_in_template(tmp_path: Path) -> None:
    """Verify excerpt_for_card filter works when rendered via template engine."""
    site = Site(root_path=tmp_path, config={"title": "Test"})
    engine = TemplateEngine(site)

    html = engine.render_string(
        "{{ content | excerpt_for_card(title, desc) }}",
        {
            "content": "Title. Description. Real content here.",
            "title": "Title",
            "desc": "Description",
        },
    )
    assert html.strip() == "Real content here."


def test_excerpt_for_card_empty_result_changelog(tmp_path: Path) -> None:
    """Changelog: when summary is only version/name, result is empty."""
    site = Site(root_path=tmp_path, config={"title": "Test"})
    engine = TemplateEngine(site)

    html = engine.render_string(
        "{{ summary | excerpt_for_card(version, name) | excerpt(160) }}",
        {"summary": "0.1.8", "version": "0.1.8", "name": ""},
    )
    assert html.strip() == ""


def test_excerpt_for_card_html_headers_get_spacing(tmp_path: Path) -> None:
    """HTML with headers should have space between them when collapsed for card."""
    site = Site(root_path=tmp_path, config={"title": "Test"})
    engine = TemplateEngine(site)

    html_content = (
        "<p>Intro text.</p><h2>Key Features</h2><h3>Fast Builds</h3><p>Parallel processing.</p>"
    )
    result = engine.render_string(
        "{{ content | excerpt_for_card('') }}",
        {"content": html_content},
    )
    # Should have space between "Key Features" and "Fast Builds" (not "Key FeaturesFast Builds")
    assert "Key Features Fast Builds" in result


def test_card_excerpt_html_with_string_excerpt_words_dirty_config(tmp_path: Path) -> None:
    """Simulate excerpt_words as string from config - must not raise TypeError."""
    site = Site(root_path=tmp_path, config={"title": "Test"})
    engine = TemplateEngine(site)

    # excerpt_words as string (e.g. from YAML) - filter must coerce at entry
    html = engine.render_string(
        "{{ excerpt | card_excerpt_html(excerpt_words, title, desc) | safe }}",
        {
            "excerpt": "My Post. This is the actual content to show in the card.",
            "excerpt_words": "5",
            "title": "My Post",
            "desc": "",
        },
    )
    assert "This is the actual" in html
    assert "My Post" not in html
    assert html.strip().endswith("...")
