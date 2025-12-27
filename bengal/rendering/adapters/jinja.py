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
    """Generate asset URL with fingerprint resolution.

    Pure function implementation for asset URL generation.
    Resolves fingerprinted asset paths from the asset manifest.

    Args:
        asset_path: Path to asset (e.g., 'css/style.css')
        site: Site instance
        page: Optional page context (for file:// protocol support)

    Returns:
        Resolved asset URL, fingerprinted if manifest entry exists
    """
    from bengal.rendering.template_engine.url_helpers import with_baseurl

    if not asset_path:
        return with_baseurl("/assets/", site)

    # Normalize path
    clean_path = asset_path.replace("\\", "/").strip().lstrip("/")

    baseurl_value = (site.config.get("baseurl", "") or "").rstrip("/")

    # Handle file:// protocol - generate relative URLs
    if baseurl_value.startswith("file://"):
        return _asset_url_file_protocol(clean_path, site, page)

    # In dev server mode, prefer stable URLs without fingerprints
    if getattr(site, "dev_mode", False):
        return with_baseurl(f"/assets/{clean_path}", site)

    # Look up fingerprinted path from manifest
    fingerprinted_path = _resolve_fingerprinted_asset(clean_path, site)
    if fingerprinted_path:
        return with_baseurl(f"/{fingerprinted_path}", site)

    # Fallback: return direct asset path
    return with_baseurl(f"/assets/{clean_path}", site)


def _resolve_fingerprinted_asset(logical_path: str, site: Site) -> str | None:
    """Resolve a logical asset path to its fingerprinted output path.

    Uses the asset manifest cached on the site for efficient lookups.

    Args:
        logical_path: Logical asset path (e.g., 'css/style.css')
        site: Site instance

    Returns:
        Fingerprinted output path (e.g., 'assets/css/style.abc123.css') or None
    """
    from bengal.assets.manifest import AssetManifest

    # Use cached manifest if available
    cache_attr = "_jinja_asset_manifest_cache"
    manifest_cache = getattr(site, cache_attr, None)

    if manifest_cache is None:
        # Load manifest from output directory
        manifest_path = site.output_dir / "asset-manifest.json"
        manifest = AssetManifest.load(manifest_path)
        if manifest is None:
            # No manifest available - cache empty dict to avoid repeated loads
            setattr(site, cache_attr, {})
            return None
        # Cache the entries dict for fast lookups
        manifest_cache = dict(manifest.entries)
        setattr(site, cache_attr, manifest_cache)

    entry = manifest_cache.get(logical_path)
    if entry:
        return entry.output_path
    return None


def _asset_url_file_protocol(asset_path: str, site: Site, page: Any = None) -> str:
    """Generate asset URL for file:// protocol using relative paths.

    Args:
        asset_path: Validated asset path
        site: Site instance
        page: Page context for computing relative path

    Returns:
        Relative asset URL
    """
    from pathlib import Path

    asset_url_path = f"assets/{asset_path}"

    # Try to compute relative path from page
    if page and hasattr(page, "output_path") and page.output_path:
        try:
            page_rel_to_root = page.output_path.relative_to(site.output_dir)
            depth = (
                len(page_rel_to_root.parent.parts) if page_rel_to_root.parent != Path(".") else 0
            )
            if depth > 0:
                relative_prefix = "/".join([".."] * depth)
                return f"{relative_prefix}/{asset_url_path}"
            else:
                return f"./{asset_url_path}"
        except (ValueError, AttributeError):
            pass

    # Fallback: assume root-level
    return f"./{asset_url_path}"
