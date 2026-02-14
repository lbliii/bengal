"""Integration tests for i18n (internationalization) features.

Tests the existing i18n template functions:
- t() for UI translations
- alternate_links() for hreflang generation
- languages() for configured language list
- current_lang() for language detection
- locale_date() for date localization

Phase 2 of RFC: User Scenario Coverage - Extended Validation
"""

from __future__ import annotations

import pytest


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nTranslations:
    """Test i18n translation functionality."""

    def test_translation_files_loaded(self, site) -> None:
        """Translation files should be loadable from i18n/ directory."""
        i18n_dir = site.root_path / "i18n"

        # Verify translation files exist
        assert (i18n_dir / "en.yaml").exists(), "English translations should exist"
        assert (i18n_dir / "fr.yaml").exists(), "French translations should exist"

    def test_i18n_config_present(self, site) -> None:
        """i18n configuration should be loaded from bengal.toml."""
        i18n_config = site.config.get("i18n", {})

        assert i18n_config.get("default_language") == "en", "Default language should be 'en'"

        languages = i18n_config.get("languages", [])
        lang_codes = [lang.get("code") if isinstance(lang, dict) else lang for lang in languages]

        assert "en" in lang_codes, "English should be configured"
        assert "fr" in lang_codes, "French should be configured"

    def test_content_directories_exist(self, site) -> None:
        """Language-specific content directories should exist."""
        content_dir = site.root_path / "content"

        assert (content_dir / "en" / "_index.md").exists(), "English home page should exist"
        assert (content_dir / "fr" / "_index.md").exists(), "French home page should exist"

    def test_pages_have_lang_attribute(self, site) -> None:
        """Pages should have language attribute set."""
        pages_with_lang = [page for page in site.pages if hasattr(page, "lang") and page.lang]

        assert len(pages_with_lang) >= 2, "At least 2 pages should have lang attribute set"

    def test_translation_keys_present(self, site) -> None:
        """Pages should have translation_key for linking translations."""
        pages_with_key = [
            page for page in site.pages if hasattr(page, "translation_key") and page.translation_key
        ]

        assert len(pages_with_key) >= 2, "At least 2 pages should have translation_key for linking"


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nTemplateFunctions:
    """Test i18n template functions integration."""

    def test_languages_function_returns_configured(self, site) -> None:
        """languages() should return configured language list."""
        from bengal.rendering.template_functions.i18n import _languages

        langs = _languages(site)

        # Should return list of language info dicts
        assert isinstance(langs, list), "languages() should return a list"
        assert len(langs) >= 2, "Should have at least 2 languages configured"

        # Extract codes
        codes = [lang.get("code") for lang in langs]
        assert "en" in codes, "English should be in languages list"
        assert "fr" in codes, "French should be in languages list"

    def test_t_function_translates(self, site) -> None:
        """t() should translate UI strings."""
        from bengal.rendering.template_functions.i18n import _make_t

        translate = _make_t(site)

        # Test English translation
        en_home = translate("ui.home", lang="en")
        assert en_home == "Home", f"Expected 'Home', got '{en_home}'"

        # Test French translation
        fr_home = translate("ui.home", lang="fr")
        assert fr_home == "Accueil", f"Expected 'Accueil', got '{fr_home}'"

    def test_t_function_fallback(self, site) -> None:
        """t() should fallback to default language if key missing."""
        from bengal.rendering.template_functions.i18n import _make_t

        translate = _make_t(site)

        # Request a key that might only exist in one language
        # or fall back to key if not found at all
        result = translate("nonexistent.key", lang="fr")

        # Should return the key itself as fallback
        assert result == "nonexistent.key", f"Missing key should return key itself, got '{result}'"

    def test_current_lang_function(self, site) -> None:
        """current_lang() should detect language from config."""
        from bengal.rendering.template_functions.i18n import _current_lang

        lang = _current_lang(site)

        # Should return default language when no page context
        assert lang == "en", f"Expected 'en' as default, got '{lang}'"


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nBuild:
    """Test i18n build output."""

    def test_builds_successfully(self, site, build_site) -> None:
        """i18n site should build without errors."""
        build_site()

        output = site.output_dir
        assert output.exists(), "Output directory should exist"

    def test_generates_language_directories(self, site, build_site) -> None:
        """Build should generate language-specific directories."""
        build_site()

        output = site.output_dir

        # Check for language directories in output
        en_exists = (output / "en" / "index.html").exists()
        fr_exists = (output / "fr" / "index.html").exists()

        assert en_exists or fr_exists, "At least one language directory should exist in output"

    def test_pages_contain_translated_content(self, site, build_site) -> None:
        """Built pages should contain language-specific content."""
        build_site()

        output = site.output_dir

        # Check English content
        en_paths = [
            output / "en" / "index.html",
            output / "en" / "about" / "index.html",
        ]

        for path in en_paths:
            if path.exists():
                html = path.read_text()
                # Should contain English text
                assert "Welcome" in html or "About" in html or "english" in html.lower(), (
                    f"English page {path} should contain English content"
                )
                break

        # Check French content
        fr_paths = [
            output / "fr" / "index.html",
            output / "fr" / "about" / "index.html",
        ]

        for path in fr_paths:
            if path.exists():
                html = path.read_text()
                # Should contain French text
                assert (
                    "Bienvenue" in html or "propos" in html.lower() or "français" in html.lower()
                ), f"French page {path} should contain French content"
                break


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nAlternateLinks:
    """Test alternate links (hreflang) generation."""

    def test_pages_linked_by_translation_key(self, site) -> None:
        """Pages with same translation_key should be linked."""
        # Group pages by translation_key
        by_key: dict[str, list] = {}
        for page in site.pages:
            key = getattr(page, "translation_key", None)
            if key:
                by_key.setdefault(key, []).append(page)

        # Should have at least one key with multiple translations
        multi_lang_keys = [k for k, pages in by_key.items() if len(pages) > 1]

        assert len(multi_lang_keys) >= 1, (
            "At least one page should have translations in multiple languages"
        )

    def test_alternate_links_function(self, site) -> None:
        """alternate_links() should generate hreflang tags."""
        from bengal.rendering.template_functions.i18n import _alternate_links

        # Find a page with translation_key
        test_page = None
        for page in site.pages:
            if getattr(page, "translation_key", None):
                test_page = page
                break

        if test_page is None:
            pytest.skip("No page with translation_key found")

        alternates = _alternate_links(site, test_page)

        # If translations exist, should have alternates
        if alternates:
            # Check structure
            for alt in alternates:
                assert "hreflang" in alt, "Alternate should have hreflang"
                assert "href" in alt, "Alternate should have href"


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nDateLocalization:
    """Test date localization functionality."""

    def test_locale_date_function(self) -> None:
        """locale_date() should format dates by locale."""
        from datetime import datetime

        from bengal.rendering.template_functions.i18n import _locale_date

        test_date = datetime(2025, 1, 15)

        # Test date formatting
        result = _locale_date(test_date, format="medium", lang="en")

        # Should return a formatted date string
        assert result, "locale_date should return a formatted string"
        assert "2025" in result or "15" in result, f"Date should contain year or day: {result}"

    def test_locale_date_handles_none(self) -> None:
        """locale_date() should handle None gracefully."""
        from bengal.rendering.template_functions.i18n import _locale_date

        result = _locale_date(None)

        # Should return empty string for None
        assert result == "", f"Expected empty string for None, got '{result}'"


@pytest.mark.bengal(testroot="test-i18n-content")
class TestLanguageSwitcher:
    """Test language switcher partial rendering."""

    def test_language_switcher_partial_exists(self) -> None:
        """Language switcher partial should exist in theme."""
        from pathlib import Path

        themes_dir = Path(__file__).parent.parent.parent / "bengal" / "themes" / "default"
        partial_path = themes_dir / "templates" / "partials" / "language-switcher.html"

        assert partial_path.exists(), f"Language switcher partial should exist at {partial_path}"

    def test_language_switcher_css_exists(self) -> None:
        """Language switcher CSS should exist in theme."""
        from pathlib import Path

        themes_dir = Path(__file__).parent.parent.parent / "bengal" / "themes" / "default"
        css_path = themes_dir / "assets" / "css" / "components" / "language-switcher.css"

        assert css_path.exists(), f"Language switcher CSS should exist at {css_path}"

    def test_language_switcher_partial_content(self) -> None:
        """Language switcher partial should contain expected elements."""
        from pathlib import Path

        themes_dir = Path(__file__).parent.parent.parent / "bengal" / "themes" / "default"
        partial_path = themes_dir / "templates" / "partials" / "language-switcher.html"

        content = partial_path.read_text()

        # Check for key elements
        assert "language-switcher" in content, "Should have language-switcher class"
        assert "languages()" in content, "Should use languages() function"
        assert "alternate_links" in content, "Should use alternate_links() function"
        assert "current_lang" in content, "Should use current_lang() function"
        assert "aria-" in content, "Should have accessibility attributes"
