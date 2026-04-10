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


class TestNtEdgeCases:
    """Edge cases for plural-aware translation via nt()."""

    def _make_site(self, tmp_path: Path, lang: str = "en") -> tuple:
        """Helper: create site + engine + page stub for nt() tests."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [{"code": "en"}, {"code": lang}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        engine = TemplateEngine(site)

        class P:
            pass

        P.lang = lang
        return site, engine, P()

    def test_nt_n_zero_uses_plural(self, tmp_path: Path) -> None:
        """n=0 should use plural form (English rules: 0 != 1)."""
        _, engine, page = self._make_site(tmp_path)
        html = engine.render_string(
            "{{ nt('1 item', '{n} items', 0) }}",
            {
                "page": page,
                "site": Site(
                    root_path=tmp_path,
                    config={"i18n": {"default_language": "en", "languages": [{"code": "en"}]}},
                ),
            },
        )
        assert "0 items" in html

    def test_nt_n_one_uses_singular(self, tmp_path: Path) -> None:
        """n=1 should use singular form."""
        site, engine, page = self._make_site(tmp_path)
        html = engine.render_string(
            "{{ nt('1 item', '{n} items', 1) }}",
            {"page": page, "site": site},
        )
        assert "1 item" in html
        assert "items" not in html

    def test_nt_n_two(self, tmp_path: Path) -> None:
        """n=2 should use plural form."""
        site, engine, page = self._make_site(tmp_path)
        html = engine.render_string(
            "{{ nt('1 item', '{n} items', 2) }}",
            {"page": page, "site": site},
        )
        assert "2 items" in html

    def test_nt_n_large(self, tmp_path: Path) -> None:
        """n=21 should use plural form (relevant for Slavic languages)."""
        site, engine, page = self._make_site(tmp_path)
        html = engine.render_string(
            "{{ nt('1 item', '{n} items', 21) }}",
            {"page": page, "site": site},
        )
        assert "21 items" in html

    def test_nt_negative_n(self, tmp_path: Path) -> None:
        """Negative n should use plural form (not 1)."""
        site, engine, page = self._make_site(tmp_path)
        html = engine.render_string(
            "{{ nt('1 item', '{n} items', -1) }}",
            {"page": page, "site": site},
        )
        assert "-1 items" in html

    def test_nt_no_params_no_placeholders(self, tmp_path: Path) -> None:
        """nt() with static strings (no {n}) works fine."""
        site, engine, page = self._make_site(tmp_path)
        html = engine.render_string(
            "{{ nt('one apple', 'several apples', 5) }}",
            {"page": page, "site": site},
        )
        assert "several apples" in html

    def test_nt_missing_catalog_falls_back(self, tmp_path: Path) -> None:
        """When no gettext catalog exists, nt() uses English-style fallback."""
        site, engine, page = self._make_site(tmp_path, lang="ja")
        html = engine.render_string(
            "{{ nt('1 item', '{n} items', 3) }}",
            {"page": page, "site": site},
        )
        assert "3 items" in html

    def test_nt_format_error_returns_raw(self, tmp_path: Path) -> None:
        """Bad format params don't crash — return unformatted string."""
        site, engine, page = self._make_site(tmp_path)
        html = engine.render_string(
            "{{ nt('1 item', '{n} {missing} items', 2) }}",
            {"page": page, "site": site},
        )
        # Should not crash; returns something (either formatted partially or raw)
        assert html is not None
        assert len(html.strip()) > 0


class TestCatalogNgettext:
    """Direct tests for Catalog.ngettext() plural form selection."""

    def test_default_plural_fn_singular(self) -> None:
        """Default plural function: n=1 → index 0 (singular)."""
        from bengal.i18n.catalog import Catalog

        cat = Catalog()
        assert cat.ngettext("apple", "apples", 1) == "apple"

    def test_default_plural_fn_plural(self) -> None:
        """Default plural function: n!=1 → index 1 (plural)."""
        from bengal.i18n.catalog import Catalog

        cat = Catalog()
        assert cat.ngettext("apple", "apples", 0) == "apples"
        assert cat.ngettext("apple", "apples", 2) == "apples"
        assert cat.ngettext("apple", "apples", 5) == "apples"

    def test_custom_plural_fn(self) -> None:
        """Custom plural function for 3-form language (e.g. Polish-style)."""
        from bengal.i18n.catalog import Catalog

        # Polish: n==1 → 0, n%10 in (2,3,4) and n%100 not in (12,13,14) → 1, else → 2
        # Simplified: just test that custom fn index is respected
        cat = Catalog(plural_fn=lambda n: 0 if n == 1 else 1)
        assert cat.ngettext("1 plik", "{n} pliki", 1) == "1 plik"
        assert cat.ngettext("1 plik", "{n} pliki", 5) == "{n} pliki"

    def test_plural_fn_out_of_range_falls_back(self) -> None:
        """If plural_fn returns index >= len(forms), use last form."""
        from bengal.i18n.catalog import Catalog

        # Return index 5 — way beyond the 2-element forms list
        cat = Catalog(plural_fn=lambda n: 5)
        result = cat.ngettext("apple", "apples", 3)
        assert result == "apples"  # Falls back to last form

    def test_ngettext_with_fallback_dict(self) -> None:
        """Catalog with fallback dict still uses plural_fn for ngettext."""
        from bengal.i18n.catalog import Catalog

        cat = Catalog(fallback={"hello": "hola"})
        # ngettext doesn't use fallback dict — uses forms + plural_fn
        assert cat.ngettext("1 thing", "{n} things", 1) == "1 thing"
        assert cat.ngettext("1 thing", "{n} things", 2) == "{n} things"


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
