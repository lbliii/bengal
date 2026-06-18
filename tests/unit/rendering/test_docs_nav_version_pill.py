"""Tests for docs sidebar version switcher pill labeling."""

from __future__ import annotations

from unittest.mock import Mock

from bengal.core.site import Site
from bengal.rendering.context.lazy import make_lazy
from bengal.rendering.engines import create_engine


def _version_pill_template() -> str:
    """Minimal template mirroring docs-nav version pill resolution."""
    return """
{% let cur_version_id = page?.version %}
{% let vlabel = site.latest_version?.label ?? 'Latest' %}
{% let vstatus = 'current' %}
{% for v in versions %}
{% if cur_version_id is not none and cur_version_id == v.id %}
{% let vlabel = v.label %}
{% let vstatus = v.status or (v.deprecated and 'deprecated' or 'legacy') %}
{% end %}
{% end %}
<span class="docs-nav-vswitch__pill" data-status="{{ vstatus }}">{{ vlabel }}</span>
"""


def test_version_pill_uses_page_version_when_current_version_is_lazy(tmp_path) -> None:
    """Section-index pages must not read lazy current_version for the pill label."""
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

    page = Mock()
    page.version = "0.5.1"

    def _raise_if_evaluated() -> dict[str, str]:
        msg = "current_version should not be evaluated for pill label"
        raise AssertionError(msg)

    rendered = engine.render_string(
        _version_pill_template(),
        {
            "page": page,
            "versions": [
                {"id": "main", "label": "Latest", "latest": True, "status": "current"},
                {"id": "0.5.1", "label": "0.5.1", "latest": False, "status": "legacy"},
            ],
            "site": Mock(latest_version={"label": "Latest"}),
            "current_version": make_lazy(_raise_if_evaluated),
        },
    )

    assert 'class="docs-nav-vswitch__pill" data-status="legacy">0.5.1</span>' in rendered


def test_version_pill_falls_back_to_latest_label_without_page_version(tmp_path) -> None:
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

    rendered = engine.render_string(
        _version_pill_template(),
        {
            "page": Mock(version=None),
            "versions": [{"id": "main", "label": "Latest", "latest": True}],
            "site": Mock(latest_version={"label": "Latest"}),
            "current_version": None,
        },
    )

    assert ">Latest</span>" in rendered
