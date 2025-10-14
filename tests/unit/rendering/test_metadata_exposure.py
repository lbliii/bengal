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
