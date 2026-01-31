"""
Internationalization (i18n) utilities for orchestrators.

Consolidates i18n configuration extraction logic used across TaxonomyOrchestrator
and MenuOrchestrator. Provides a consistent interface for accessing i18n settings.

Example:
    >>> config = get_i18n_config(site.config)
    >>> for lang in config.languages:
    ...     build_menu_for_language(lang)

    >>> # Or use helper functions directly
    >>> if is_i18n_enabled(site.config):
    ...     languages = get_site_languages(site.config)

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class I18nConfig:
    """
    Immutable i18n configuration extracted from site config.

    Attributes:
        strategy: i18n strategy ("none", "subdir", "domain", etc.)
        languages: List of language codes (e.g., ["en", "es", "fr"])
        default_language: Default/fallback language code
        share_taxonomies: Whether taxonomies are shared across languages
    """

    strategy: str
    languages: tuple[str, ...]
    default_language: str
    share_taxonomies: bool

    @property
    def is_enabled(self) -> bool:
        """Check if i18n is enabled (strategy is not 'none')."""
        return self.strategy != "none"

    def __iter__(self):
        """Iterate over languages."""
        return iter(self.languages)

    def __len__(self) -> int:
        """Number of configured languages."""
        return len(self.languages)


def get_i18n_config(site_config: dict[str, Any]) -> I18nConfig:
    """
    Extract i18n configuration from site config.

    Handles various config formats and provides sensible defaults.

    Args:
        site_config: Site configuration dictionary

    Returns:
        I18nConfig with all i18n settings

    Example:
        >>> config = get_i18n_config({"i18n": {"strategy": "subdir", "languages": ["en", "es"]}})
        >>> config.is_enabled
        True
        >>> config.languages
        ('en', 'es')
    """
    i18n = site_config.get("i18n", {}) or {}

    strategy = i18n.get("strategy") or "none"
    share_taxonomies = bool(i18n.get("share_taxonomies", False))
    default_lang = i18n.get("default_language", "en")

    # Extract language codes from various formats
    languages: list[str] = []
    if strategy != "none":
        langs_cfg = i18n.get("languages") or []
        for entry in langs_cfg:
            if isinstance(entry, dict) and "code" in entry:
                languages.append(entry["code"])
            elif isinstance(entry, str):
                languages.append(entry)

        # Ensure default language is included
        if default_lang not in languages:
            languages.append(default_lang)
    else:
        # When i18n disabled, just use default language
        languages = [default_lang]

    return I18nConfig(
        strategy=strategy,
        languages=tuple(sorted(set(languages))),
        default_language=default_lang,
        share_taxonomies=share_taxonomies,
    )


def get_site_languages(site_config: dict[str, Any]) -> list[str]:
    """
    Get list of language codes from site config.

    Convenience function for when you only need the language list.

    Args:
        site_config: Site configuration dictionary

    Returns:
        List of language codes (sorted, deduplicated)

    Example:
        >>> get_site_languages({"i18n": {"languages": ["en", "es"]}})
        ['en', 'es']
    """
    return list(get_i18n_config(site_config).languages)


def is_i18n_enabled(site_config: dict[str, Any]) -> bool:
    """
    Check if i18n is enabled in site config.

    Args:
        site_config: Site configuration dictionary

    Returns:
        True if i18n strategy is not "none"

    Example:
        >>> is_i18n_enabled({"i18n": {"strategy": "subdir"}})
        True
        >>> is_i18n_enabled({})
        False
    """
    i18n = site_config.get("i18n", {}) or {}
    strategy = i18n.get("strategy") or "none"
    return strategy != "none"


def filter_pages_by_language(
    pages: list[Any],
    lang: str,
    default_lang: str,
    share_taxonomies: bool = False,
    strategy: str = "none",
) -> list[Any]:
    """
    Filter pages by language.

    Args:
        pages: List of Page objects to filter
        lang: Target language code
        default_lang: Default language code
        share_taxonomies: If True, include pages from all languages
        strategy: i18n strategy ("none" disables filtering)

    Returns:
        Filtered list of pages for the specified language

    Example:
        >>> pages = filter_pages_by_language(all_pages, "es", "en")
    """
    # No filtering if i18n disabled or taxonomies are shared
    if strategy == "none" or share_taxonomies:
        return pages

    # Filter by page's lang attribute
    return [
        p for p in pages
        if getattr(p, "lang", default_lang) == lang
    ]
