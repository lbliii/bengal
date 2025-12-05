from __future__ import annotations


from datetime import datetime
from pathlib import Path

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine


def _make_site(config: dict | None = None) -> Site:
    cfg = config or {}
    return Site(root_path=Path("."), config=cfg)


def test_bengal_global_minimal_exposure():
    site = _make_site({"expose_metadata": "minimal"})
    engine = TemplateEngine(site)
    meta = engine.env.globals.get("bengal")
    assert isinstance(meta, dict)
    assert meta["engine"]["name"] == "Bengal SSG"
    # minimal should only expose engine
    assert set(meta.keys()) == {"engine"}


def test_bengal_global_standard_exposure_includes_theme_and_build_and_i18n():
    site = _make_site({"expose_metadata": "standard", "i18n": {"strategy": "none"}})
    site.build_time = datetime.now()
    engine = TemplateEngine(site)
    meta = engine.env.globals.get("bengal")
    assert "engine" in meta
    assert "theme" in meta
    assert "build" in meta
    assert "i18n" in meta


def test_bengal_global_extended_exposure_includes_rendering_info():
    site = _make_site({"expose_metadata": "extended", "markdown": {"parser": "mistune"}})
    engine = TemplateEngine(site)
    meta = engine.env.globals.get("bengal")
    assert "rendering" in meta
    assert meta["rendering"]["markdown"] in (
        "mistune",
        "markdown",
        "python-markdown",
        "python_markdown",
    )


def test_json_bootstrap_includes_bengal_when_enabled(tmp_path):
    # Arrange a minimal rendering scenario that uses base.html include
    site = Site(root_path=tmp_path, config={"expose_metadata_json": True})
    # Place a simple template that extends base and emits the head content
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "base.html").write_text(
        """
<!DOCTYPE html>
<html>
<head>
    {% include 'partials/meta-generator.html' %}
    {% if config.get('expose_metadata_json') %}
    <script id="bengal-bootstrap" type="application/json">{{ bengal | jsonify }}</script>
    <script>
        (function () {
            var el = document.getElementById('bengal-bootstrap');
            if (el) { window.__BENGAL__ = JSON.parse(el.textContent || '{}'); }
        })();
    </script>
    {% endif %}
</head>
<body></body>
</html>
""",
        encoding="utf-8",
    )
    # partials dir and file
    (templates_dir / "partials").mkdir(exist_ok=True)
    (templates_dir / "partials" / "meta-generator.html").write_text(
        '<meta name="generator" content="Bengal">', encoding="utf-8"
    )

    engine = TemplateEngine(site)
    html = engine.render("base.html", {})

    assert 'id="bengal-bootstrap"' in html
    assert 'type="application/json"' in html
