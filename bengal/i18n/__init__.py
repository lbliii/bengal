"""
Internationalization (i18n) package for Bengal.

Provides gettext-style PO/MO workflow:
- Catalog: Loaded translation catalog (gettext or PO)
- POLoader: Load .po files
- MOLoader: Load .mo files (compiled gettext)
- load_catalog: Load catalog for locale from i18n/{locale}/LC_MESSAGES/{domain}.po|.mo

Convention: i18n/{locale}/LC_MESSAGES/{domain}.po (source) and .mo (compiled).
"""

from __future__ import annotations

from bengal.i18n.catalog import (
    Catalog,
    MOLoader,
    POLoader,
    load_catalog,
)

__all__ = [
    "Catalog",
    "load_catalog",
    "MOLoader",
    "POLoader",
]
