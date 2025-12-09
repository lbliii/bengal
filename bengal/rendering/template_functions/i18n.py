"""
Internationalization (i18n) template helpers.

Provides:
- t(key, params={}, lang=None): translate UI strings from i18n/<lang>.(yaml|json|toml)
- current_lang(): current language code inferred from page/site
- languages(): configured languages list from config
- alternate_links(page): list of {hreflang, href} for page translations
- locale_date(date, format='medium'): localized date formatting (Babel if available)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from bengal.utils.file_io import load_data_file
from bengal.utils.logger import get_logger

try:
    from jinja2 import pass_context  # Jinja2 >=3
except Exception:  # pragma: no cover - fallback, tests ensure availability
    from collections.abc import Callable
    from typing import Any, TypeVar

    F = TypeVar("F", bound=Callable[..., Any])

    def pass_context(fn: F) -> F:
        return fn


if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)

# Track warned translation keys to avoid spamming logs (once per key per build)
_warned_translation_keys: set[str] = set()


class LanguageInfo(TypedDict, total=False):
    """
    TypedDict for language information returned by _languages().

    All fields except baseurl are required. baseurl is optional.
    """

    code: str  # Language code (e.g., 'en', 'fr')
    name: str  # Display name (e.g., 'English', 'Français')
    hreflang: str  # hreflang attribute value (usually same as code)
    baseurl: str  # Base URL for this language (optional)
    weight: int  # Sort weight (lower = earlier in list)


def _warn_missing_translation(key: str, lang: str) -> None:
    """
    Log a debug warning when a translation key is missing.

    Only warns once per key/lang combination per build to avoid log spam.

    Args:
        key: The missing translation key
        lang: The language that was checked
    """
    warn_key = f"{lang}:{key}"
    if warn_key not in _warned_translation_keys:
        _warned_translation_keys.add(warn_key)
        logger.debug(
            "translation_missing",
            key=key,
            lang=lang,
            fallback="key_returned",
            hint=f"Add translation for '{key}' in i18n/{lang}.yaml",
        )


def reset_translation_warnings() -> None:
    """
    Reset the set of warned translation keys.

    Useful for testing or when starting a new build.
    """
    _warned_translation_keys.clear()


_DEF_FORMATS = {
    "short": "yyyy-MM-dd",
    "medium": "LLL d, yyyy",
    "long": "LLLL d, yyyy",
}


def register(env: Environment, site: Site) -> None:
    """Register i18n helpers into Jinja2 environment.

    Globals:
      - t
      - current_lang
      - languages
      - alternate_links
      - locale_date
    """
    # Base translators (no context)
    base_translate = _make_t(site)

    @pass_context
    def t(ctx: Any, key: str, params: dict[str, Any] | None = None, lang: str | None = None) -> str:
        page = ctx.get("page") if hasattr(ctx, "get") else None
        use_lang = lang or getattr(page, "lang", None)
        return base_translate(key, params=params, lang=use_lang)

    @pass_context
    def current_lang(ctx: Any) -> str | None:
        page = ctx.get("page") if hasattr(ctx, "get") else None
        return _current_lang(site, page)

    def languages() -> list[LanguageInfo]:
        return _languages(site)

    def alternate_links(page: Any = None) -> list[dict[str, str]]:
        return _alternate_links(site, page)

    def locale_date(date: Any, format: str = "medium", lang: str | None = None) -> str:
        return _locale_date(date, format, lang)

    env.globals.update(
        {
            "t": t,
            "current_lang": current_lang,
            "languages": languages,
            "alternate_links": alternate_links,
            "locale_date": locale_date,
        }
    )


def _current_lang(site: Site, page: Any | None = None) -> str | None:
    i18n = site.config.get("i18n", {}) or {}
    default = i18n.get("default_language", "en")
    if page is not None and getattr(page, "lang", None):
        return page.lang
    return getattr(site, "current_language", None) or default


def _languages(site: Site) -> list[LanguageInfo]:
    """
    Get normalized list of configured languages.

    Returns:
        List of LanguageInfo dictionaries with code, name, hreflang, and optional baseurl/weight.
    """
    i18n = site.config.get("i18n", {}) or {}
    langs = i18n.get("languages") or []
    # Normalize to list of dicts with code and hreflang
    normalized: list[LanguageInfo] = []
    seen = set()
    for entry in langs:
        if isinstance(entry, dict):
            code = entry.get("code")
            if code and code not in seen:
                seen.add(code)
                lang_info: LanguageInfo = {
                    "code": code,
                    "name": entry.get("name", code),
                    "hreflang": entry.get("hreflang", code),
                    "weight": entry.get("weight", 0),
                }
                if baseurl := entry.get("baseurl"):
                    lang_info["baseurl"] = baseurl
                normalized.append(lang_info)
        elif isinstance(entry, str):
            if entry not in seen:
                seen.add(entry)
                normalized.append({"code": entry, "name": entry, "hreflang": entry, "weight": 0})
    # Ensure default exists
    default = i18n.get("default_language", "en")
    if default and default not in {lang["code"] for lang in normalized}:
        normalized.append({"code": default, "name": default, "hreflang": default, "weight": -1})
    normalized.sort(key=lambda x: (x.get("weight", 0), x["code"]))
    return normalized


def _make_t(site: Site) -> Callable[[str, dict[str, Any] | None, str | None], str]:
    cache: dict[str, dict[str, Any]] = {}
    i18n_dir = site.root_path / "i18n"

    def load_lang(lang: str) -> dict[str, Any]:
        if lang in cache:
            return cache[lang]
        # Look for preferred extensions in order
        for ext in (".yaml", ".yml", ".json", ".toml"):
            path = i18n_dir / f"{lang}{ext}"
            if path.exists():
                data = load_data_file(path, on_error="return_empty", caller="i18n") or {}
                cache[lang] = data
                return data
        cache[lang] = {}
        return {}

    def resolve_key(data: dict[str, Any], key: str) -> str | None:
        cur: Any = data
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur if isinstance(cur, str) else None

    def format_params(text: str, params: dict[str, Any]) -> str:
        try:
            return text.format(**params)
        except Exception as e:
            logger.debug(
                "i18n_format_params_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="returning_original_text",
            )
            return text

    def t(key: str, params: dict[str, Any] | None = None, lang: str | None = None) -> str:
        if not key:
            return ""
        i18n_cfg = site.config.get("i18n", {}) or {}
        default_lang = i18n_cfg.get("default_language", "en")
        use_lang = lang or default_lang
        # Primary language
        data = load_lang(use_lang)
        value = resolve_key(data, key)
        if value is None and i18n_cfg.get("fallback_to_default", True):
            # Fallback to default
            data_def = load_lang(default_lang)
            value = resolve_key(data_def, key)
        if value is None:
            # Log missing translation once per key per build
            _warn_missing_translation(key, use_lang)
            # Return key (debug-friendly) if missing
            value = key
        return format_params(value, params or {})

    return t


def _alternate_links(site: Site, page: Any | None) -> list[dict[str, str]]:
    if page is None:
        return []
    # Build alternates via translation_key
    i18n = site.config.get("i18n", {}) or {}
    if not getattr(page, "translation_key", None):
        return []
    # Collect pages by lang
    key = page.translation_key
    alternates: list[dict[str, str]] = []
    for p in site.pages:
        if getattr(p, "translation_key", None) == key and p.output_path:
            try:
                rel = p.output_path.relative_to(site.output_dir)
                href = "/" + str(rel).replace("index.html", "").replace("\\", "/").rstrip("/") + "/"
                lang = getattr(p, "lang", None) or i18n.get("default_language", "en")
                alternates.append({"hreflang": lang, "href": href})
            except Exception as e:
                logger.debug(
                    "i18n_alternate_link_failed",
                    page_path=str(p.output_path) if hasattr(p, "output_path") else None,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="skipping_alternate",
                )
                continue
    # Add x-default pointing to default language
    default_lang = i18n.get("default_language", "en")
    default = next((a for a in alternates if a["hreflang"] == default_lang), None)
    if default:
        alternates.append({"hreflang": "x-default", "href": default["href"]})
    return alternates


def _locale_date(date: Any, format: str = "medium", lang: str | None = None) -> str:
    if date is None:
        return ""
    # Try Babel for formatting
    try:
        from babel.dates import format_date

        pattern = _DEF_FORMATS.get(format, format)
        return format_date(date, format=pattern, locale=lang or "en")
    except Exception as e:
        # Fallback to simple strftime
        logger.debug(
            "i18n_babel_format_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="trying_strftime_fallback",
        )
        try:
            return date.strftime("%Y-%m-%d")
        except Exception as e2:
            logger.debug(
                "i18n_strftime_failed",
                error=str(e2),
                error_type=type(e2).__name__,
                action="returning_string_representation",
            )
            return str(date)
