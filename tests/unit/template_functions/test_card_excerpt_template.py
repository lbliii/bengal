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
