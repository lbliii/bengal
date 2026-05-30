"""Compatibility helpers for mutable page site context."""

from __future__ import annotations

from typing import Any, Protocol, cast


class _PageSiteContext(Protocol):
    _site: Any | None


def get_page_site(page: object) -> Any | None:
    """Return the legacy mutable page site reference, if present."""
    return getattr(page, "_site", None)


def set_page_site(page: object, site: Any | None) -> None:
    """Attach site context to a legacy mutable page object."""
    cast("_PageSiteContext", page)._site = site
