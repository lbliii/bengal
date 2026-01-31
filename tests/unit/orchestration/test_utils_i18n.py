"""
Tests for orchestration/utils/i18n.py.

Tests I18nConfig, get_i18n_config, get_site_languages, is_i18n_enabled, and filter_pages_by_language.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.orchestration.utils.i18n import (
    I18nConfig,
    filter_pages_by_language,
    get_i18n_config,
    get_site_languages,
    is_i18n_enabled,
)


class TestI18nConfig:
    """Test I18nConfig dataclass."""

    def test_is_enabled_when_strategy_not_none(self) -> None:
        """is_enabled should be True when strategy is not 'none'."""
        config = I18nConfig(
            strategy="subdir",
            languages=("en", "es"),
            default_language="en",
            share_taxonomies=False,
        )
        assert config.is_enabled is True

    def test_is_enabled_when_strategy_none(self) -> None:
        """is_enabled should be False when strategy is 'none'."""
        config = I18nConfig(
            strategy="none",
            languages=("en",),
            default_language="en",
            share_taxonomies=False,
        )
        assert config.is_enabled is False

    def test_iteration(self) -> None:
        """Should be iterable over languages."""
        config = I18nConfig(
            strategy="subdir",
            languages=("en", "es", "fr"),
            default_language="en",
            share_taxonomies=False,
        )
        assert list(config) == ["en", "es", "fr"]

    def test_len(self) -> None:
        """Should return number of languages."""
        config = I18nConfig(
            strategy="subdir",
            languages=("en", "es"),
            default_language="en",
            share_taxonomies=False,
        )
        assert len(config) == 2

    def test_immutable(self) -> None:
        """Config should be immutable (frozen dataclass)."""
        config = I18nConfig(
            strategy="subdir",
            languages=("en",),
            default_language="en",
            share_taxonomies=False,
        )
        with pytest.raises(AttributeError):
            config.strategy = "domain"  # type: ignore


class TestGetI18nConfig:
    """Test get_i18n_config function."""

    def test_disabled_by_default(self) -> None:
        """Empty config should result in disabled i18n."""
        config = get_i18n_config({})
        assert config.is_enabled is False
        assert config.strategy == "none"
        assert config.default_language == "en"

    def test_none_strategy(self) -> None:
        """Explicit 'none' strategy should be disabled."""
        site_config = {"i18n": {"strategy": "none"}}
        config = get_i18n_config(site_config)
        assert config.is_enabled is False

    def test_subdir_strategy(self) -> None:
        """Subdir strategy should be enabled."""
        site_config = {
            "i18n": {
                "strategy": "subdir",
                "languages": [{"code": "en"}, {"code": "es"}],
                "default_language": "en",
            }
        }
        config = get_i18n_config(site_config)
        assert config.is_enabled is True
        assert config.strategy == "subdir"
        assert "en" in config.languages
        assert "es" in config.languages

    def test_languages_as_strings(self) -> None:
        """Languages can be specified as simple strings."""
        site_config = {
            "i18n": {
                "strategy": "subdir",
                "languages": ["en", "es", "fr"],
            }
        }
        config = get_i18n_config(site_config)
        assert set(config.languages) == {"en", "es", "fr"}

    def test_languages_as_dicts(self) -> None:
        """Languages can be specified as dicts with 'code' key."""
        site_config = {
            "i18n": {
                "strategy": "subdir",
                "languages": [
                    {"code": "en", "name": "English"},
                    {"code": "de", "name": "German"},
                ],
            }
        }
        config = get_i18n_config(site_config)
        assert "en" in config.languages
        assert "de" in config.languages

    def test_default_language_included(self) -> None:
        """Default language should be included even if not in languages list."""
        site_config = {
            "i18n": {
                "strategy": "subdir",
                "languages": ["en", "es"],
                "default_language": "fr",
            }
        }
        config = get_i18n_config(site_config)
        assert "fr" in config.languages

    def test_share_taxonomies(self) -> None:
        """share_taxonomies flag should be extracted."""
        site_config = {
            "i18n": {
                "strategy": "subdir",
                "languages": ["en"],
                "share_taxonomies": True,
            }
        }
        config = get_i18n_config(site_config)
        assert config.share_taxonomies is True

    def test_languages_deduplicated_and_sorted(self) -> None:
        """Languages should be deduplicated and sorted."""
        site_config = {
            "i18n": {
                "strategy": "subdir",
                "languages": ["es", "en", "en", "fr", "es"],
            }
        }
        config = get_i18n_config(site_config)
        assert config.languages == ("en", "es", "fr")

    def test_handles_none_i18n(self) -> None:
        """Handles None i18n config gracefully."""
        site_config = {"i18n": None}
        config = get_i18n_config(site_config)
        assert config.is_enabled is False


class TestGetSiteLanguages:
    """Test get_site_languages function."""

    def test_returns_language_list(self) -> None:
        """Should return list of languages."""
        site_config = {
            "i18n": {
                "strategy": "subdir",
                "languages": ["en", "es"],
            }
        }
        languages = get_site_languages(site_config)
        assert isinstance(languages, list)
        assert "en" in languages
        assert "es" in languages

    def test_empty_config(self) -> None:
        """Empty config should return default language."""
        languages = get_site_languages({})
        assert "en" in languages


class TestIsI18nEnabled:
    """Test is_i18n_enabled function."""

    def test_enabled(self) -> None:
        """Should return True when strategy is not 'none'."""
        assert is_i18n_enabled({"i18n": {"strategy": "subdir"}}) is True

    def test_disabled(self) -> None:
        """Should return False when strategy is 'none'."""
        assert is_i18n_enabled({"i18n": {"strategy": "none"}}) is False

    def test_missing_config(self) -> None:
        """Should return False when i18n config is missing."""
        assert is_i18n_enabled({}) is False


class TestFilterPagesByLanguage:
    """Test filter_pages_by_language function."""

    def test_filters_by_lang_attribute(self) -> None:
        """Should filter pages by their lang attribute."""
        en_page = MagicMock()
        en_page.lang = "en"
        es_page = MagicMock()
        es_page.lang = "es"

        pages = [en_page, es_page]
        filtered = filter_pages_by_language(pages, "en", "en", False, "subdir")

        assert len(filtered) == 1
        assert filtered[0].lang == "en"

    def test_no_filtering_when_disabled(self) -> None:
        """Should not filter when strategy is 'none'."""
        en_page = MagicMock()
        en_page.lang = "en"
        es_page = MagicMock()
        es_page.lang = "es"

        pages = [en_page, es_page]
        filtered = filter_pages_by_language(pages, "en", "en", False, "none")

        assert len(filtered) == 2

    def test_no_filtering_when_share_taxonomies(self) -> None:
        """Should not filter when share_taxonomies is True."""
        en_page = MagicMock()
        en_page.lang = "en"
        es_page = MagicMock()
        es_page.lang = "es"

        pages = [en_page, es_page]
        filtered = filter_pages_by_language(pages, "en", "en", True, "subdir")

        assert len(filtered) == 2

    def test_uses_default_lang_when_missing(self) -> None:
        """Pages without lang attribute should use default language."""
        page_no_lang = MagicMock(spec=["title"])  # No lang attribute
        page_with_lang = MagicMock()
        page_with_lang.lang = "es"

        pages = [page_no_lang, page_with_lang]
        filtered = filter_pages_by_language(pages, "en", "en", False, "subdir")

        # page_no_lang should match default lang "en"
        assert len(filtered) == 1
