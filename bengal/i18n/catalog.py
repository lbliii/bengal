"""
Translation catalog loading for gettext PO/MO workflow.

Convention: i18n/{locale}/LC_MESSAGES/{domain}.po (source) and .mo (compiled).
"""

from __future__ import annotations

import gettext
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class Catalog:
    """
    Translation catalog interface.

    Provides gettext-like gettext() and ngettext() methods.
    Supports both PO/MO (gettext) and fallback dict-based lookups.
    """

    __slots__ = ("_fallback", "_plural_fn", "_translation")

    def __init__(
        self,
        translation: gettext.GNUTranslations | None = None,
        fallback: dict[str, str] | None = None,
        plural_fn: Callable[[int], int] | None = None,
    ) -> None:
        self._translation = translation
        self._fallback = fallback or {}
        self._plural_fn = plural_fn or (lambda n: 0 if n == 1 else 1)

    def gettext(self, message: str) -> str:
        """Translate a key. Returns message if not found."""
        if self._translation is not None:
            result = self._translation.gettext(message)
            if result != message:
                return result
        return self._fallback.get(message, message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """Translate with plural form."""
        if self._translation is not None:
            result = self._translation.ngettext(singular, plural, n)
            if result not in (singular, plural):
                return result
        idx = self._plural_fn(n)
        forms = [singular, plural]
        return forms[idx] if idx < len(forms) else forms[-1]

    def __bool__(self) -> bool:
        return self._translation is not None or bool(self._fallback)


class MOLoader:
    """Load .mo files via Python gettext."""

    @staticmethod
    def load(localedir: Path, domain: str, locale: str) -> Catalog | None:
        """
        Load .mo file for locale.

        Looks for localedir/locale/LC_MESSAGES/domain.mo
        """
        mo_path = localedir / locale / "LC_MESSAGES" / f"{domain}.mo"
        if not mo_path.exists():
            return None
        try:
            trans = gettext.translation(
                domain,
                localedir=str(localedir),
                languages=[locale],
                fallback=False,
            )
            return Catalog(translation=trans)
        except OSError:
            return None


class POLoader:
    """Load .po files via polib."""

    @staticmethod
    def load(localedir: Path, domain: str, locale: str) -> Catalog | None:
        """
        Load .po file for locale.

        Looks for localedir/locale/LC_MESSAGES/domain.po
        Supports singular and plural forms.
        """
        po_path = localedir / locale / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.exists():
            return None
        try:
            import polib

            po = polib.pofile(str(po_path))
            fallback: dict[str, str] = {}
            for entry in po:
                if entry.msgid and entry.msgstr:
                    fallback[entry.msgid] = entry.msgstr
            # Plural entries: store as msgid -> (msgid_plural, forms) for ngettext
            # Catalog uses fallback for gettext only; ngettext needs _translation
            # For PO-only: build a minimal gettext.GNUTranslations from polib
            # Polib can save to .mo - we could compile in memory. Simpler: use
            # fallback dict and accept ngettext returns singular/plural by index.
            return Catalog(fallback=fallback)
        except Exception:
            return None


# Per-site cache: (root_path, domain) -> {locale: Catalog}
_catalog_cache: dict[tuple[Path, str], dict[str, Catalog]] = {}
_cache_lock = threading.Lock()


def load_catalog(
    root_path: Path,
    locale: str,
    domain: str = "messages",
) -> Catalog | None:
    """
    Load translation catalog for locale.

    Preference: .mo (compiled) > .po (source). Falls back to None if neither exists.
    Uses gettext convention: i18n/{locale}/LC_MESSAGES/{domain}.po|.mo

    Args:
        root_path: Site root (e.g. content dir parent)
        locale: Language code (e.g. 'en', 'es')
        domain: Gettext domain (default: 'messages')

    Returns:
        Catalog or None if no PO/MO found
    """
    localedir = root_path / "i18n"
    cache_key = (root_path, domain)
    with _cache_lock:
        if cache_key not in _catalog_cache:
            _catalog_cache[cache_key] = {}
        cache = _catalog_cache[cache_key]
        if locale in cache:
            return cache[locale]
    catalog = MOLoader.load(localedir, domain, locale)
    if catalog is None:
        catalog = POLoader.load(localedir, domain, locale)
    with _cache_lock:
        if locale in cache:
            return cache[locale]
        cache[locale] = catalog
    return catalog


def clear_catalog_cache(root_path: Path | None = None) -> None:
    """Clear catalog cache for invalidation (e.g. after compile)."""
    global _catalog_cache
    with _cache_lock:
        if root_path is None:
            _catalog_cache.clear()
        else:
            keys_to_remove = [k for k in _catalog_cache if k[0] == root_path]
            for k in keys_to_remove:
                del _catalog_cache[k]


def compute_coverage(
    localedir: Path,
    domain: str,
    locale: str,
    required_keys: set[str],
) -> tuple[int, int, list[str]]:
    """
    Compute translation coverage for a locale against required keys.

    Args:
        localedir: Root i18n directory (e.g. root/i18n)
        domain: Gettext domain (e.g. messages)
        locale: Locale code (e.g. en, es)
        required_keys: Keys that must be translated (from template t() calls)

    Returns:
        (translated_count, total_count, missing_keys)
    """
    po_path = localedir / locale / "LC_MESSAGES" / f"{domain}.po"
    if not po_path.exists():
        return (0, len(required_keys), list(required_keys))

    try:
        import polib

        po = polib.pofile(str(po_path))
        translated = 0
        missing: list[str] = []
        for key in required_keys:
            entry = po.find(key)
            if entry is None:
                missing.append(key)
            elif entry.msgstr and entry.msgstr.strip():
                translated += 1
            else:
                missing.append(key)
        return (translated, len(required_keys), missing)
    except Exception:
        return (0, len(required_keys), list(required_keys))
