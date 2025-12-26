"""
Generic adapter for unknown template engines.

Provides a fallback for engines that don't have specific adapters.
Functions are registered with sensible defaults (no page context).

For full context support, engine authors should create a custom adapter
following the pattern in jinja.py or kida.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.site import Site


def register_context_functions(env: Any, site: Site) -> None:
    """Register context-dependent template functions for unknown engines.

    These functions use site defaults since we can't access page context.
    For full context support, create a custom adapter for your engine.

    Args:
        env: Template environment instance
        site: Site instance
    """
    # Import pure function implementations
    from bengal.rendering.template_engine.url_helpers import with_baseurl
    from bengal.rendering.template_functions.i18n import (
        _current_lang,
        _languages,
        _make_t,
    )
    from bengal.rendering.template_functions.taxonomies import tag_url as base_tag_url

    # Create base translator (closure over site)
    base_translate = _make_t(site)

    def t(
        key: str,
        params: dict[str, Any] | None = None,
        lang: str | None = None,
        default: str | None = None,
    ) -> str:
        """Translate a key using site default language.

        Note: This generic adapter cannot access page context.
        For page-aware translations, create a custom adapter.

        Args:
            key: Translation key
            params: Interpolation parameters
            lang: Override language (falls back to site default)
            default: Default value if key not found
        """
        return base_translate(key, params=params, lang=lang, default=default)

    def current_lang() -> str | None:
        """Get current language from site default.

        Note: This generic adapter cannot access page context.
        """
        return _current_lang(site, None)

    def languages() -> list[dict[str, Any]]:
        """Get configured languages list."""
        return _languages(site)

    def tag_url(tag: str) -> str:
        """Generate tag URL without locale-aware prefix.

        Note: This generic adapter cannot access page context for i18n prefix.
        """
        relative_url = base_tag_url(tag)

        # Apply base URL prefix if configured
        baseurl = site.baseurl or ""
        if baseurl:
            baseurl = baseurl.rstrip("/")
            if not baseurl:
                return relative_url
            if not relative_url.startswith("/"):
                relative_url = "/" + relative_url
            if baseurl.startswith(("http://", "https://", "file://")):
                return f"{baseurl}{relative_url}"
            else:
                base_path = "/" + baseurl.lstrip("/")
                return f"{base_path}{relative_url}"

        return relative_url

    def asset_url(path: str) -> str:
        """Generate asset URL."""
        if not path:
            return with_baseurl("/assets/", site)

        clean_path = path.replace("\\", "/").strip().lstrip("/")
        return with_baseurl(f"/assets/{clean_path}", site)

    # Register functions - check if env has globals attribute
    if hasattr(env, "globals"):
        env.globals.update(
            {
                "t": t,
                "current_lang": current_lang,
                "languages": languages,
                "tag_url": tag_url,
                "asset_url": asset_url,
            }
        )
