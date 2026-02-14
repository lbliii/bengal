from __future__ import annotations

from pathlib import Path

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine


def _write_i18n(tmp_path: Path, lang: str, content: str) -> None:
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir(parents=True, exist_ok=True)
    (i18n_dir / f"{lang}.yaml").write_text(content, encoding="utf-8")


def test_t_and_current_lang_from_context(tmp_path: Path) -> None:
    # Arrange: site with i18n config
    config = {
        "i18n": {
            "strategy": "prefix",
            "content_structure": "dir",
            "default_language": "en",
            "languages": [{"code": "en"}, {"code": "fr"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    # i18n files
    _write_i18n(tmp_path, "en", 'greeting: "Hello {name}"')
    _write_i18n(tmp_path, "fr", 'greeting: "Bonjour {name}"')

    engine = TemplateEngine(site)

    # Fake page object with lang
    class P:
        lang = "fr"

    # Use render_string which properly injects page context for both Jinja and Kida
    html = engine.render_string(
        "{{ t('greeting', {'name': 'Alice'}) }}",
        {"page": P(), "site": site},
    )
    assert "Bonjour Alice" in html


def test_alternate_links(tmp_path: Path) -> None:
    # Build a minimal site with two translated pages
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}, {"code": "fr"}],
        },
        "title": "Site",
        "baseurl": "https://example.com",
    }
    site = Site(root_path=tmp_path, config=config)

    from bengal.core.page import Page

    en = Page(source_path=tmp_path / "content" / "en" / "a.md", _raw_content="x", _raw_metadata={})
    fr = Page(source_path=tmp_path / "content" / "fr" / "a.md", _raw_content="x", _raw_metadata={})
    en.lang = "en"
    fr.lang = "fr"
    en.translation_key = "docs/a"
    fr.translation_key = "docs/a"
    site.pages = [en, fr]

    # Output paths set with prefix
    from bengal.utils.paths.url_strategy import URLStrategy

    en.output_path = URLStrategy.compute_regular_page_output_path(en, site)
    fr.output_path = URLStrategy.compute_regular_page_output_path(fr, site)

    engine = TemplateEngine(site)
    tmpl = engine.env.from_string(
        "{% for l in alternate_links(page) %}{{ l.hreflang }}|{{ l.href }}\n{% endfor %}"
    )
    out = tmpl.render(page=en, site=site)
    assert "en|" in out
    assert "fr|" in out
