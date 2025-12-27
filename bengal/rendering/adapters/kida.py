"""
Kida-specific adapter for template functions.

Provides context-aware function factories for Kida's render-time injection.

Since Kida doesn't have @pass_context, we use a two-layer approach:
1. Static functions registered at environment setup (for simple cases)
2. Context-aware factory called at render time (for page-dependent functions)

Usage in KidaTemplateEngine:
    def render_template(self, name, context):
        page = context.get("page")
        inject_page_context(self._env, page)
        return template.render(context)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.site import Site


def register_context_functions(env: Any, site: Site) -> None:
    """Register context-dependent template functions for Kida.

    Strategy: Context-aware function factory

    Static functions are registered immediately. Page-dependent functions
    are created via a factory that's called at render time with the page.

    Args:
        env: Kida Environment instance
        site: Site instance
    """
    # Import pure function implementations
    from bengal.rendering.template_functions.i18n import (
        _current_lang,
        _languages,
        _make_t,
    )

    # Create base translator (closure over site)
    base_translate = _make_t(site)

    # Static functions (don't need page context or have sensible defaults)
    def languages() -> list[dict[str, Any]]:
        """Get configured languages list."""
        return _languages(site)

    # Context-aware factory - called at render time with page
    def make_page_aware_functions(page: Any = None) -> dict[str, Any]:
        """Create functions that have access to the current page.

        Called by KidaTemplateEngine.render_template() before rendering.

        Args:
            page: Current page being rendered

        Returns:
            Dict of function name -> function to merge into globals
        """

        # Create page-aware versions of context-dependent functions
        def t(
            key: str,
            params: dict[str, Any] | None = None,
            lang: str | None = None,
            default: str | None = None,
        ) -> str:
            """Translate a key using page context for language detection."""
            use_lang = lang or getattr(page, "lang", None)
            return base_translate(key, params=params, lang=use_lang, default=default)

        def current_lang() -> str | None:
            """Get current language from page or site default."""
            return _current_lang(site, page)

        def tag_url(tag: str) -> str:
            """Generate tag URL with locale-aware prefix."""
            return _tag_url_with_page(tag, site, page)

        def asset_url(path: str) -> str:
            """Generate asset URL with fingerprint resolution."""
            from bengal.rendering.assets import resolve_asset_url

            return resolve_asset_url(path, site, page)

        return {
            "t": t,
            "current_lang": current_lang,
            "tag_url": tag_url,
            "asset_url": asset_url,
        }

    # Register static functions
    env.globals.update(
        {
            "languages": languages,
        }
    )

    # Store factory for render-time injection
    env._page_aware_factory = make_page_aware_functions

    # Also register initial versions with no page context
    # (these will be overwritten at render time with page-aware versions)
    env.globals.update(make_page_aware_functions(None))


def inject_page_context(env: Any, page: Any = None) -> None:
    """Inject page-aware functions into environment globals before rendering.

    Called by KidaTemplateEngine.render_template():

        def render_template(self, name, context):
            page = context.get("page")
            inject_page_context(self._env, page)
            return template.render(context)

    Args:
        env: Kida Environment instance
        page: Current page being rendered
    """
    if hasattr(env, "_page_aware_factory"):
        page_functions = env._page_aware_factory(page)
        env.globals.update(page_functions)


def _tag_url_with_page(tag: str, site: Site, page: Any = None) -> str:
    """Generate tag URL with locale-aware prefix.

    Pure function implementation - no engine dependencies.

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
    cache_attr = "_kida_asset_manifest_cache"
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
