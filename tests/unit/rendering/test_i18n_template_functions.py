from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine

if TYPE_CHECKING:
    from pathlib import Path


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


def test_direction_rtl_for_arabic(tmp_path: Path) -> None:
    """Arabic pages get dir='rtl' via direction()."""
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}, {"code": "ar"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class ArabicPage:
        lang = "ar"

    engine = TemplateEngine(site)
    html = engine.render_string(
        'dir="{{ direction() }}"',
        {"page": ArabicPage(), "site": site},
    )
    assert 'dir="rtl"' in html


def test_direction_ltr_for_english(tmp_path: Path) -> None:
    """English pages get dir='ltr' via direction()."""
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class EnglishPage:
        lang = "en"

    engine = TemplateEngine(site)
    html = engine.render_string(
        'dir="{{ direction() }}"',
        {"page": EnglishPage(), "site": site},
    )
    assert 'dir="ltr"' in html


def test_direction_config_override(tmp_path: Path) -> None:
    """Config rtl=true/false overrides default RTL detection."""
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [
                {"code": "en"},
                {"code": "ar", "rtl": False},
                {"code": "custom-rtl", "name": "Custom", "rtl": True},
            ],
        }
    }
    site = Site(root_path=tmp_path, config=config)
    engine = TemplateEngine(site)

    class ArPage:
        lang = "ar"

    class CustomPage:
        lang = "custom-rtl"

    ar_html = engine.render_string(
        'dir="{{ direction() }}"',
        {"page": ArPage(), "site": site},
    )
    assert 'dir="ltr"' in ar_html

    custom_html = engine.render_string(
        'dir="{{ direction() }}"',
        {"page": CustomPage(), "site": site},
    )
    assert 'dir="rtl"' in custom_html


def test_nt_singular(tmp_path: Path) -> None:
    """nt() returns singular form when n == 1."""
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class P:
        lang = "en"

    engine = TemplateEngine(site)
    html = engine.render_string(
        "{{ nt('1 item', '{n} items', 1) }}",
        {"page": P(), "site": site},
    )
    assert "1 item" in html


def test_nt_plural(tmp_path: Path) -> None:
    """nt() returns plural form when n != 1."""
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class P:
        lang = "en"

    engine = TemplateEngine(site)
    html = engine.render_string(
        "{{ nt('1 item', '{n} items', 5) }}",
        {"page": P(), "site": site},
    )
    assert "5 items" in html


def test_nt_zero(tmp_path: Path) -> None:
    """nt() returns plural form when n == 0."""
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class P:
        lang = "en"

    engine = TemplateEngine(site)
    html = engine.render_string(
        "{{ nt('1 item', '{n} items', 0) }}",
        {"page": P(), "site": site},
    )
    assert "0 items" in html


def test_nt_with_params(tmp_path: Path) -> None:
    """nt() interpolates params including {n}."""
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class P:
        lang = "en"

    engine = TemplateEngine(site)
    html = engine.render_string(
        "{{ nt('1 {thing}', '{n} {thing}s', 3, {'thing': 'cat'}) }}",
        {"page": P(), "site": site},
    )
    assert "3 cats" in html


def test_nt_respects_page_lang(tmp_path: Path) -> None:
    """nt() uses page.lang for language detection."""
    config = {
        "i18n": {
            "strategy": "prefix",
            "default_language": "en",
            "languages": [{"code": "en"}, {"code": "es"}],
        }
    }
    site = Site(root_path=tmp_path, config=config)

    class SpanishPage:
        lang = "es"

    # Without a catalog, nt() uses fallback. The key test is that it
    # doesn't error and correctly selects the plural form.
    engine = TemplateEngine(site)
    html = engine.render_string(
        "{{ nt('1 item', '{n} items', 2) }}",
        {"page": SpanishPage(), "site": site},
    )
    assert "2 items" in html


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
