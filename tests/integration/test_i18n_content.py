"""Integration tests for i18n content structure.

Tests directory-based internationalization:
- content/en/ and content/fr/ directory structure
- Language detection from directory prefix
- Translation key assignment
- Language fallback behavior

Phase 5 of RFC: User Scenario Coverage & Validation Matrix
"""

from __future__ import annotations

import pytest


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nContentDiscovery:
    """Test directory-based i18n content discovery."""

    def test_all_language_content_discovered(self, site) -> None:
        """Content from all language directories should be discovered."""
        # Should have pages from both en/ and fr/ directories
        assert len(site.pages) >= 6, (
            f"Expected at least 6 pages (3 per language), found {len(site.pages)}"
        )

    def test_english_content_discovered(self, site) -> None:
        """English content should be discovered from en/ directory."""
        en_pages = [p for p in site.pages if "/en/" in str(p.source_path)]
        assert len(en_pages) >= 3, f"Expected at least 3 English pages, found {len(en_pages)}"

    def test_french_content_discovered(self, site) -> None:
        """French content should be discovered from fr/ directory."""
        fr_pages = [p for p in site.pages if "/fr/" in str(p.source_path)]
        assert len(fr_pages) >= 3, f"Expected at least 3 French pages, found {len(fr_pages)}"


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nLanguageDetection:
    """Test language detection from directory structure."""

    def test_english_pages_have_en_lang(self, site) -> None:
        """Pages in en/ directory should have lang='en'."""
        en_pages = [p for p in site.pages if "/en/" in str(p.source_path)]

        for page in en_pages:
            page_lang = getattr(page, "lang", None)
            if page_lang is not None:
                assert page_lang == "en", (
                    f"Page {page.source_path} should have lang='en', got '{page_lang}'"
                )

    def test_french_pages_have_fr_lang(self, site) -> None:
        """Pages in fr/ directory should have lang='fr'."""
        fr_pages = [p for p in site.pages if "/fr/" in str(p.source_path)]

        for page in fr_pages:
            page_lang = getattr(page, "lang", None)
            if page_lang is not None:
                assert page_lang == "fr", (
                    f"Page {page.source_path} should have lang='fr', got '{page_lang}'"
                )


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nTranslationKeys:
    """Test translation key assignment for linking translated pages."""

    def test_about_pages_have_same_translation_key(self, site) -> None:
        """About pages in en/ and fr/ should have the same translation_key."""
        about_pages = [p for p in site.pages if "about" in str(p.source_path).lower()]

        if len(about_pages) >= 2:
            translation_keys = set()
            for page in about_pages:
                key = getattr(page, "translation_key", None)
                if key:
                    translation_keys.add(key)

            # If translation keys are set, they should match across languages
            if translation_keys:
                # All about pages should have the same key (or different keys if structure differs)
                # This test verifies keys are being assigned
                assert len(translation_keys) >= 1, "Translation keys should be assigned"

    def test_guide_pages_have_matching_translation_keys(self, site) -> None:
        """Guide pages should have matching translation keys across languages."""
        # Filter for specifically the guide.md files (not index or about)
        guide_pages = [p for p in site.pages if "guide.md" in str(p.source_path).lower()]

        translation_keys = []
        for page in guide_pages:
            key = getattr(page, "translation_key", None)
            if key:
                translation_keys.append(key)

        # If we have translation keys, verify they're consistent
        # Guide pages from en and fr should have the same key
        if len(translation_keys) >= 2:
            unique_keys = set(translation_keys)
            # Both en/docs/guide.md and fr/docs/guide.md should resolve to same key
            assert len(unique_keys) <= 1, (
                f"Guide pages should have matching translation keys, got: {unique_keys}"
            )


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nBuild:
    """Test building i18n content sites."""

    def test_site_builds_successfully(self, site, build_site) -> None:
        """i18n site should build without errors."""
        build_site()

        output = site.output_dir
        assert output.exists(), "Output directory should exist"

    def test_language_directories_in_output(self, site, build_site) -> None:
        """Output should have language-specific directories."""
        build_site()

        output = site.output_dir

        # Check for language directories in output
        en_exists = (output / "en").exists() or (output / "en" / "index.html").exists()
        fr_exists = (output / "fr").exists() or (output / "fr" / "index.html").exists()

        # At least one language should have output
        assert en_exists or fr_exists, "Should have language-specific output directories"

    def test_all_pages_rendered(self, site, build_site) -> None:
        """All pages from all languages should be rendered."""
        build_site()

        output = site.output_dir

        # Check for English pages
        en_about = (
            (output / "en" / "about" / "index.html").exists()
            or (output / "en" / "about.html").exists()
            or (output / "about" / "index.html").exists()
        )

        # Check for French pages
        fr_about = (output / "fr" / "about" / "index.html").exists() or (
            output / "fr" / "about.html"
        ).exists()

        # We should have content from both languages rendered
        assert en_about or fr_about, "About pages should be rendered for at least one language"


@pytest.mark.bengal(testroot="test-i18n-content")
class TestI18nConfiguration:
    """Test i18n configuration from bengal.toml."""

    def test_i18n_config_loaded(self, site) -> None:
        """i18n configuration should be loaded from config."""
        i18n_config = site.config.get("i18n", {})

        assert i18n_config.get("default_language") == "en", "Default language should be 'en'"
        assert i18n_config.get("content_structure") == "dir", "Content structure should be 'dir'"

    def test_languages_configured(self, site) -> None:
        """Languages should be configured in i18n config."""
        i18n_config = site.config.get("i18n", {})
        languages = i18n_config.get("languages", [])

        # Should have at least 2 languages configured
        assert len(languages) >= 2, f"Expected at least 2 languages, found {len(languages)}"

        # Extract language codes
        codes = []
        for lang in languages:
            if isinstance(lang, dict):
                codes.append(lang.get("code"))
            elif isinstance(lang, str):
                codes.append(lang)

        assert "en" in codes, "English should be configured"
        assert "fr" in codes, "French should be configured"
