"""Page-like visibility helpers independent of the legacy Page package."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def normalize_visibility(
    metadata: Mapping[str, Any],
    content_signal_defaults: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge page visibility frontmatter with Bengal defaults."""
    if metadata.get("hidden", False):
        return {
            "menu": False,
            "listings": False,
            "sitemap": False,
            "robots": "noindex, nofollow",
            "render": "always",
            "search": False,
            "rss": False,
            "ai_train": False,
            "ai_input": False,
        }

    vis = metadata.get("visibility", {})
    if not isinstance(vis, Mapping):
        vis = {}

    return {
        "menu": vis.get("menu", True),
        "listings": vis.get("listings", True),
        "sitemap": vis.get("sitemap", True),
        "robots": vis.get("robots", "index, follow"),
        "render": vis.get("render", "always"),
        "search": vis.get("search", content_signal_defaults.get("search", True)),
        "rss": vis.get("rss", True),
        "ai_train": vis.get("ai_train", content_signal_defaults.get("ai_train", False)),
        "ai_input": vis.get("ai_input", content_signal_defaults.get("ai_input", True)),
    }


def get_content_signal_defaults(page: Any) -> dict[str, Any]:
    """Return site-level content signal defaults for a page-like object."""
    site = getattr(page, "_site", None)
    if site is None:
        return {}
    config = getattr(site, "config", None)
    if config is None:
        return {}
    try:
        content_signals = config.get("content_signals", {})
    except Exception:
        return {}
    return content_signals if isinstance(content_signals, dict) else {}


def get_page_visibility(page: Any) -> dict[str, Any]:
    """Return normalized visibility settings for a page-like object."""
    metadata = getattr(page, "metadata", {})
    if not isinstance(metadata, Mapping):
        metadata = {}
    return normalize_visibility(metadata, get_content_signal_defaults(page))


def is_page_in_listings(page: Any) -> bool:
    """Return whether a page-like object should appear in listings."""
    return bool(get_page_visibility(page)["listings"] and not _is_page_draft(page))


def is_page_in_sitemap(page: Any) -> bool:
    """Return whether a page-like object should appear in sitemap.xml."""
    return bool(get_page_visibility(page)["sitemap"] and not _is_page_draft(page))


def is_page_in_search(page: Any) -> bool:
    """Return whether a page-like object should appear in the search index."""
    return bool(get_page_visibility(page)["search"] and not _is_page_draft(page))


def is_page_in_rss(page: Any) -> bool:
    """Return whether a page-like object should appear in RSS/Atom feeds."""
    return bool(get_page_visibility(page)["rss"] and not _is_page_draft(page))


def is_page_in_ai_train(page: Any) -> bool:
    """Return whether a page-like object permits AI training use."""
    return bool(get_page_visibility(page)["ai_train"] and not _is_page_draft(page))


def is_page_in_ai_input(page: Any) -> bool:
    """Return whether a page-like object permits AI input/RAG use."""
    return bool(get_page_visibility(page)["ai_input"] and not _is_page_draft(page))


def get_robots_meta(page: Any) -> str:
    """Return the robots meta directive for a page-like object."""
    return str(get_page_visibility(page)["robots"])


def should_render_visibility(visibility: Mapping[str, Any], is_production: bool) -> bool:
    """Return whether a visibility object permits rendering in the environment."""
    render = visibility.get("render", "always")
    if render == "never":
        return False
    return not (render == "local" and is_production)


def should_render_page(page: Any) -> bool:
    """Return whether a page-like object is not marked render: never."""
    return bool(get_page_visibility(page)["render"] != "never")


def should_render_page_in_environment(page: Any, is_production: bool = False) -> bool:
    """Return whether a page-like object should render in the given environment."""
    return should_render_visibility(get_page_visibility(page), is_production)


def _is_page_draft(page: Any) -> bool:
    metadata = getattr(page, "metadata", {})
    if isinstance(metadata, Mapping):
        return bool(metadata.get("draft", False))
    return False
