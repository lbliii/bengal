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
    from bengal.protocols import SiteLike


def register_context_functions(env: Any, site: SiteLike) -> None:
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
            from bengal.rendering.urls import resolve_tag_url

            return resolve_tag_url(tag, site, page)

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
