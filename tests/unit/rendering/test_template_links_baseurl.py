from pathlib import Path

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine


def test_baseurl_meta_and_nav_links(tmp_path: Path):
    # Arrange: minimal site with config
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    cfg = site_dir / "bengal.toml"
    cfg.write_text(
        """
[site]
title = "Test"
baseurl = "/bengal"

[build]
output_dir = "public"
        """,
        encoding="utf-8",
    )

    (site_dir / "content" / "index.md").write_text(
        """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
    )

    site = Site.from_config(site_dir)
    engine = TemplateEngine(site)

    html = engine.render("base.html", {"page": None})

    assert '<meta name="bengal:baseurl" content="/bengal">' in html
    # Logo link uses absolute_url
    assert 'href="/bengal/"' in html
