"""
Jinja2-specific adapter for template functions.

Wraps engine-agnostic template functions with Jinja2's @pass_context
decorator to extract page context automatically.

This adapter bridges pure Python functions to Jinja2's context mechanism:

    Pure function:
        def translate(site, key, lang=None, page=None) -> str

    Jinja2 adapter:
        @pass_context
        def t(ctx, key, lang=None):
            page = ctx.get("page")
            return translate(site, key, lang=lang, page=page)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jinja2 import pass_context

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register_context_functions(env: Environment, site: Site) -> None:
    """Register context-dependent template functions for Jinja2.

    These functions use @pass_context to extract page from the template context.

    Args:
        env: Jinja2 Environment instance
        site: Site instance
    """
    # Import pure function implementations
    from bengal.rendering.template_functions.i18n import (
        _current_lang,
        _make_t,
    )

    # Create base translator (closure over site)
    base_translate = _make_t(site)

    @pass_context
    def t(
        ctx: Any,
        key: str,
        params: dict[str, Any] | None = None,
        lang: str | None = None,
        default: str | None = None,
    ) -> str:
        """Translate a key using page context for language detection.

        Args:
            ctx: Jinja2 context (automatically passed by @pass_context)
            key: Translation key
            params: Interpolation parameters
            lang: Override language
            default: Default value if key not found
        """
        page = ctx.get("page") if hasattr(ctx, "get") else None
        use_lang = lang or getattr(page, "lang", None)
        return base_translate(key, params=params, lang=use_lang, default=default)

    @pass_context
    def current_lang(ctx: Any) -> str | None:
        """Get current language from page context or site default."""
        page = ctx.get("page") if hasattr(ctx, "get") else None
        return _current_lang(site, page)

    @pass_context
    def tag_url(ctx: Any, tag: str) -> str:
        """Generate tag URL with locale-aware prefix.

        Args:
            ctx: Jinja2 context
            tag: Tag name
        """
        page = ctx.get("page") if hasattr(ctx, "get") else None
        return _tag_url_with_page(tag, site, page)

    @pass_context
    def asset_url(ctx: Any, asset_path: str) -> str:
        """Generate asset URL with page context for relative URL support.

        Args:
            ctx: Jinja2 context
            asset_path: Path to asset (e.g., "css/style.css")
        """
        page = ctx.get("page") if hasattr(ctx, "get") else None
        return _asset_url_with_page(asset_path, site, page)

    # Register context-dependent functions
    env.globals.update(
        {
            "t": t,
            "current_lang": current_lang,
            "tag_url": tag_url,
            "asset_url": asset_url,
        }
    )


def _tag_url_with_page(tag: str, site: Site, page: Any = None) -> str:
    """Generate tag URL with locale-aware prefix.

    Pure function implementation - no Jinja2 dependencies.

    Args:
        tag: Tag name
        site: Site instance
        page: Optional page for language detection
    """
    from bengal.rendering.template_functions.taxonomies import tag_url as base_tag_url

    # Get locale-aware prefix
    i18n = site.config.get("i18n", {}) or {}
    strategy = i18n.get("strategy", "none")
    default_lang = i18n.get("default_language", "en")
    default_in_subdir = bool(i18n.get("default_in_subdir", False))
    lang = getattr(page, "lang", None)
    prefix = ""
    if strategy == "prefix" and lang and (default_in_subdir or lang != default_lang):
        prefix = f"/{lang}"

    # Generate tag URL and apply base URL
    relative_url = f"{prefix}{base_tag_url(tag)}"

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


def _asset_url_with_page(asset_path: str, site: Site, page: Any = None) -> str:
    """Generate asset URL with optional page context.

    Pure function implementation for asset URL generation.

    Args:
        asset_path: Path to asset
        site: Site instance
        page: Optional page context (for future file:// protocol support)
    """
    from bengal.rendering.template_engine.url_helpers import with_baseurl

    if not asset_path:
        return with_baseurl("/assets/", site)

    clean_path = asset_path.replace("\\", "/").strip().lstrip("/")
    return with_baseurl(f"/assets/{clean_path}", site)
