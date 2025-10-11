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

from typing import TYPE_CHECKING, Any

from bengal.utils.file_io import load_data_file
from bengal.utils.logger import get_logger

try:
    from jinja2 import pass_context  # Jinja2 >=3
except Exception:  # pragma: no cover - fallback, tests ensure availability
    def pass_context(fn):
        return fn

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)


_DEF_FORMATS = {
    'short': 'yyyy-MM-dd',
    'medium': 'LLL d, yyyy',
    'long': 'LLLL d, yyyy',
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
    def t(ctx, key: str, params: dict[str, Any] | None = None, lang: str | None = None) -> str:
        page = ctx.get('page') if hasattr(ctx, 'get') else None
        use_lang = lang or getattr(page, 'lang', None)
        return base_translate(key, params=params, lang=use_lang)

    @pass_context
    def current_lang(ctx) -> str | None:
        page = ctx.get('page') if hasattr(ctx, 'get') else None
        return _current_lang(site, page)

    def languages() -> list[dict[str, Any]]:
        return _languages(site)

    def alternate_links(page=None) -> list[dict[str, str]]:
        return _alternate_links(site, page)

    def locale_date(date, format='medium', lang=None) -> str:
        return _locale_date(date, format, lang)

    env.globals.update({
        't': t,
        'current_lang': current_lang,
        'languages': languages,
        'alternate_links': alternate_links,
        'locale_date': locale_date,
    })


def _current_lang(site: Site, page: Any | None = None) -> str | None:
    i18n = site.config.get('i18n', {}) or {}
    default = i18n.get('default_language', 'en')
    if page is not None and getattr(page, 'lang', None):
        return page.lang
    return getattr(site, 'current_language', None) or default


def _languages(site: Site) -> list[dict[str, Any]]:
    i18n = site.config.get('i18n', {}) or {}
    langs = i18n.get('languages') or []
    # Normalize to list of dicts with code and hreflang
    normalized: list[dict[str, Any]] = []
    seen = set()
    for entry in langs:
        if isinstance(entry, dict):
            code = entry.get('code')
            if code and code not in seen:
                seen.add(code)
                normalized.append({
                    'code': code,
                    'name': entry.get('name', code),
                    'hreflang': entry.get('hreflang', code),
                    'baseurl': entry.get('baseurl'),
                    'weight': entry.get('weight', 0),
                })
        elif isinstance(entry, str):
            if entry not in seen:
                seen.add(entry)
                normalized.append({'code': entry, 'name': entry, 'hreflang': entry, 'weight': 0})
    # Ensure default exists
    default = i18n.get('default_language', 'en')
    if default and default not in {lang['code'] for lang in normalized}:
        normalized.append({'code': default, 'name': default, 'hreflang': default, 'weight': -1})
    normalized.sort(key=lambda x: (x.get('weight', 0), x['code']))
    return normalized


def _make_t(site: Site):
    cache: dict[str, dict[str, Any]] = {}
    i18n_dir = site.root_path / 'i18n'

    def load_lang(lang: str) -> dict[str, Any]:
        if lang in cache:
            return cache[lang]
        # Look for preferred extensions in order
        for ext in ('.yaml', '.yml', '.json', '.toml'):
            path = i18n_dir / f'{lang}{ext}'
            if path.exists():
                data = load_data_file(path, on_error='return_empty', caller='i18n') or {}
                cache[lang] = data
                return data
        cache[lang] = {}
        return {}

    def resolve_key(data: dict[str, Any], key: str) -> str | None:
        cur: Any = data
        for part in key.split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur if isinstance(cur, str) else None

    def format_params(text: str, params: dict[str, Any]) -> str:
        try:
            return text.format(**params)
        except Exception:
            return text

    def t(key: str, params: dict[str, Any] | None = None, lang: str | None = None) -> str:
        if not key:
            return ''
        i18n_cfg = site.config.get('i18n', {}) or {}
        default_lang = i18n_cfg.get('default_language', 'en')
        use_lang = (lang or default_lang)
        # Primary language
        data = load_lang(use_lang)
        value = resolve_key(data, key)
        if value is None and i18n_cfg.get('fallback_to_default', True):
            # Fallback to default
            data_def = load_lang(default_lang)
            value = resolve_key(data_def, key)
        if value is None:
            # Return key (debug-friendly) if missing
            value = key
        return format_params(value, params or {})

    return t


def _alternate_links(site: Site, page: Any | None) -> list[dict[str, str]]:
    if page is None:
        return []
    # Build alternates via translation_key
    i18n = site.config.get('i18n', {}) or {}
    if not getattr(page, 'translation_key', None):
        return []
    # Collect pages by lang
    key = page.translation_key
    alternates: list[dict[str, str]] = []
    for p in site.pages:
        if getattr(p, 'translation_key', None) == key and p.output_path:
            try:
                rel = p.output_path.relative_to(site.output_dir)
                href = '/' + str(rel).replace('index.html', '').replace('\\', '/').rstrip('/') + '/'
                lang = getattr(p, 'lang', None) or i18n.get('default_language', 'en')
                alternates.append({'hreflang': lang, 'href': href})
            except Exception:
                continue
    # Add x-default pointing to default language
    default_lang = i18n.get('default_language', 'en')
    default = next((a for a in alternates if a['hreflang'] == default_lang), None)
    if default:
        alternates.append({'hreflang': 'x-default', 'href': default['href']})
    return alternates


def _locale_date(date: Any, format: str = 'medium', lang: str | None = None) -> str:
    if date is None:
        return ''
    # Try Babel for formatting
    try:
        from babel.dates import format_date
        pattern = _DEF_FORMATS.get(format, format)
        return format_date(date, format=pattern, locale=lang or 'en')
    except Exception:
        # Fallback to simple strftime
        try:
            return date.strftime('%Y-%m-%d')
        except Exception:
            return str(date)
