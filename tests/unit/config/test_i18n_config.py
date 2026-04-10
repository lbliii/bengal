"""Tests for i18n configuration behavior.

Validates that i18n config options (strategy, languages, fallback_to_default,
direction config overrides) behave correctly at the config/template layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.site import Site
from bengal.rendering.template_functions.i18n import (
    _current_lang,
    _direction,
    _languages,
    _make_t,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write_i18n(tmp_path: Path, lang: str, content: str) -> None:
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir(parents=True, exist_ok=True)
    (i18n_dir / f"{lang}.yaml").write_text(content, encoding="utf-8")


class TestI18nStrategyBehavior:
    """Test that different i18n strategy values produce correct behavior."""

    def test_no_strategy_means_disabled(self, tmp_path: Path) -> None:
        """No i18n config → current_lang returns default 'en'."""
        site = Site(root_path=tmp_path, config={})
        assert _current_lang(site) == "en"

    def test_strategy_none_means_disabled(self, tmp_path: Path) -> None:
        """strategy=None → i18n effectively disabled, default lang returned."""
        site = Site(root_path=tmp_path, config={"i18n": {"strategy": None}})
        assert _current_lang(site) == "en"

    def test_strategy_prefix_enabled(self, tmp_path: Path) -> None:
        """strategy='prefix' with languages → languages list populated."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [{"code": "en"}, {"code": "fr"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        langs = _languages(site)
        codes = [lang["code"] for lang in langs]
        assert "en" in codes
        assert "fr" in codes

    def test_unknown_strategy_does_not_crash(self, tmp_path: Path) -> None:
        """Unknown strategy value should not crash — code doesn't validate it."""
        config = {
            "i18n": {
                "strategy": "banana",
                "default_language": "en",
                "languages": [{"code": "en"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        # Should not raise
        assert _current_lang(site) == "en"


class TestLanguagesConfig:
    """Test languages list normalization and edge cases."""

    def test_empty_languages_returns_default(self, tmp_path: Path) -> None:
        """Empty languages list → default language auto-included."""
        config = {"i18n": {"strategy": "prefix", "default_language": "en", "languages": []}}
        site = Site(root_path=tmp_path, config=config)
        langs = _languages(site)
        assert len(langs) >= 1
        assert any(lang["code"] == "en" for lang in langs)

    def test_string_languages_normalized(self, tmp_path: Path) -> None:
        """String-form languages get normalized to LanguageInfo dicts."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": ["en", "fr", "de"],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        langs = _languages(site)
        codes = [lang["code"] for lang in langs]
        assert "en" in codes
        assert "fr" in codes
        assert "de" in codes
        # Each should have name and hreflang
        for lang in langs:
            assert "name" in lang
            assert "hreflang" in lang

    def test_duplicate_languages_deduplicated(self, tmp_path: Path) -> None:
        """Duplicate language codes should be deduplicated."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [{"code": "en"}, {"code": "en"}, {"code": "fr"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        langs = _languages(site)
        codes = [lang["code"] for lang in langs]
        assert codes.count("en") == 1

    def test_default_language_auto_included(self, tmp_path: Path) -> None:
        """Default language is included even when not in languages list."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [{"code": "fr"}, {"code": "de"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        langs = _languages(site)
        codes = [lang["code"] for lang in langs]
        assert "en" in codes

    def test_languages_sorted_by_weight(self, tmp_path: Path) -> None:
        """Languages should be sorted by weight then code."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [
                    {"code": "fr", "weight": 2},
                    {"code": "en", "weight": 1},
                    {"code": "de", "weight": 3},
                ],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        langs = _languages(site)
        codes = [lang["code"] for lang in langs]
        assert codes.index("en") < codes.index("fr") < codes.index("de")


class TestFallbackToDefault:
    """Test fallback_to_default translation behavior."""

    def test_fallback_enabled_uses_default_lang(self, tmp_path: Path) -> None:
        """With fallback_to_default=True, missing key in fr falls back to en."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "fallback_to_default": True,
                "languages": [{"code": "en"}, {"code": "fr"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        _write_i18n(tmp_path, "en", 'greeting: "Hello"')
        _write_i18n(tmp_path, "fr", 'other_key: "Autre"')

        t = _make_t(site)
        # French doesn't have 'greeting', should fallback to English
        result = t("greeting", lang="fr")
        assert result == "Hello"

    def test_fallback_disabled_returns_key(self, tmp_path: Path) -> None:
        """With fallback_to_default=False, missing key returns the key itself."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "fallback_to_default": False,
                "languages": [{"code": "en"}, {"code": "fr"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        _write_i18n(tmp_path, "en", 'greeting: "Hello"')
        _write_i18n(tmp_path, "fr", 'other_key: "Autre"')

        t = _make_t(site)
        # French doesn't have 'greeting', fallback disabled → returns key
        result = t("greeting", lang="fr")
        assert result == "greeting"

    def test_fallback_default_is_true(self, tmp_path: Path) -> None:
        """fallback_to_default defaults to True when not specified."""
        config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [{"code": "en"}, {"code": "fr"}],
            }
        }
        site = Site(root_path=tmp_path, config=config)
        _write_i18n(tmp_path, "en", 'greeting: "Hello"')

        t = _make_t(site)
        result = t("greeting", lang="fr")
        assert result == "Hello"


class TestDirectionConfigOverrides:
    """Test RTL direction config overrides at the function layer."""

    def test_rtl_true_forces_rtl(self, tmp_path: Path) -> None:
        """rtl=True on a language forces RTL even for non-RTL language code."""
        config = {
            "i18n": {
                "languages": [{"code": "en"}, {"code": "custom", "rtl": True}],
            }
        }
        site = Site(root_path=tmp_path, config=config)

        class P:
            lang = "custom"

        assert _direction(site, P()) == "rtl"

    def test_rtl_false_forces_ltr(self, tmp_path: Path) -> None:
        """rtl=False on Arabic forces LTR despite being in RTL locales."""
        config = {
            "i18n": {
                "languages": [{"code": "en"}, {"code": "ar", "rtl": False}],
            }
        }
        site = Site(root_path=tmp_path, config=config)

        class P:
            lang = "ar"

        assert _direction(site, P()) == "ltr"

    def test_all_builtin_rtl_locales(self, tmp_path: Path) -> None:
        """All 9 built-in RTL locales should return 'rtl'."""
        rtl_codes = ["ar", "he", "fa", "ur", "yi", "dv", "ku", "ps", "sd"]
        for code in rtl_codes:
            config = {"i18n": {"languages": [{"code": code}]}}
            site = Site(root_path=tmp_path, config=config)

            class P:
                lang = code

            assert _direction(site, P()) == "rtl", f"{code} should be RTL"

    def test_non_rtl_locale_returns_ltr(self, tmp_path: Path) -> None:
        """Non-RTL language codes return 'ltr'."""
        for code in ["en", "fr", "de", "ja", "zh", "ko"]:
            config = {"i18n": {"languages": [{"code": code}]}}
            site = Site(root_path=tmp_path, config=config)

            class P:
                lang = code

            assert _direction(site, P()) == "ltr", f"{code} should be LTR"
