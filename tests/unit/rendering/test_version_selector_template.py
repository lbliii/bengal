"""Tests for the default theme version selector partial."""

from __future__ import annotations

from bengal.core.site import Site
from bengal.rendering.engines import create_engine


def test_version_selector_partial_tolerates_missing_page(tmp_path) -> None:
    (tmp_path / "content").mkdir()
    (tmp_path / "bengal.toml").write_text(
        """
[site]
title = "Test Site"
baseurl = "/"
""",
        encoding="utf-8",
    )
    site = Site.from_config(tmp_path)
    engine = create_engine(site)

    rendered = engine.render_template(
        "partials/version-selector.html",
        {
            "page": None,
            "versioning_enabled": True,
            "versions": [
                {"id": "main", "label": "Latest", "latest": True, "url_prefix": ""},
                {"id": "1.0", "label": "1.0", "latest": False, "url_prefix": "/1.0"},
            ],
            "current_version": None,
            "is_latest_version": True,
        },
    )

    assert rendered.strip() == ""
