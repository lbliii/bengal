"""Kida environment setup: loaders, template dirs, and Bengal function registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kida.environment import (
    ChoiceLoader,
    FileSystemLoader,
)
from kida.environment import (
    TemplateNotFoundError as KidaTemplateNotFoundError,
)

from bengal.errors.codes import ErrorCode
from bengal.rendering.engines.kida.provider_shim import _ProviderEnvShim

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def build_template_dirs(engine: Any) -> list[Path]:
    """Build ordered list of template search directories.

    Uses same resolution logic as Jinja engine:
    1. Site-level custom templates (highest priority)
    2. Theme chain (child themes first, then parent themes)
    """
    from bengal.rendering.template_engine.environment import resolve_template_dirs

    return resolve_template_dirs(engine.site)


def resolve_providers(engine: Any) -> tuple:
    """Resolve theme library providers from the theme chain."""
    from bengal.core.theme.providers import resolve_theme_providers
    from bengal.rendering.template_engine.environment import resolve_theme_chain

    theme_chain = resolve_theme_chain(engine.site.theme, engine.site)
    return resolve_theme_providers(engine.site.root_path, theme_chain)


def build_loader(engine: Any) -> FileSystemLoader | ChoiceLoader:
    """Build the template loader, incorporating provider loaders if present.

    When no providers declare loaders, returns a plain FileSystemLoader
    (zero overhead). When providers are present, returns a ChoiceLoader:
        1. FileSystemLoader(template_dirs)  — site + theme chain + default
        2. *provider.loader for each provider  — library templates
    """
    # Look up loader classes on the package so tests that patch
    # ``bengal.rendering.engines.kida.FileSystemLoader`` still apply.
    from bengal.rendering.engines.kida import ChoiceLoader as choice_loader
    from bengal.rendering.engines.kida import FileSystemLoader as fs_loader

    fs = fs_loader(engine.template_dirs)
    provider_loaders = [p.loader for p in engine._providers if p.loader is not None]
    if not provider_loaders:
        return fs
    return choice_loader([fs, *provider_loaders])


def register_bengal_template_functions(engine: Any) -> None:
    """Register Bengal-specific template functions.

    Strategy:
    1. Apply shared engine globals via get_engine_globals()
    2. Use register_all() with engine_type="kida" for filters and non-context functions
    3. Add engine-specific globals (url_for, get_menu, breadcrumbs)

    This uses the centralized context layer for consistent globals across engines.
    """
    # === Step 0: Apply shared engine globals ===
    # Single source of truth: site, config, theme, menus, bengal, versions, etc.
    from bengal.rendering.context import get_engine_globals

    engine._env.globals.update(get_engine_globals(engine.site))

    # === Step 1: Register all template functions with Kida adapter ===
    # This handles both non-context functions (icons, dates, strings, etc.)
    # and context-dependent functions (t, current_lang, tag_url, asset_url)
    # via the adapter layer
    # Pass active plugin registry for plugin-provided template extensions
    from bengal.plugins import get_active_registry
    from bengal.rendering.template_functions import register_all

    register_all(
        engine._env,
        engine.site,
        engine_type="kida",
        plugin_registry=get_active_registry(),
    )

    # === Step 2: Add filters from TemplateEngine mixins ===
    # These are added by Jinja's environment.py but not by register_all()
    try:
        from bengal.rendering.template_engine.url_helpers import filter_dateformat

        # dateformat filter (from url_helpers, not dates module)
        engine._env.filters["dateformat"] = filter_dateformat
        engine._env.filters["date"] = filter_dateformat

        # breadcrumbs
        from bengal.rendering.template_functions.navigation import breadcrumbs

        engine._env.globals["breadcrumbs"] = lambda page: breadcrumbs.get_breadcrumbs(page)
    except ImportError:
        pass

    # === Step 3: Engine-specific globals (menu functions) ===
    engine._menu_dict_cache: dict[str, list[dict]] = {}
    engine._env.globals["get_menu"] = engine._get_menu
    engine._env.globals["get_menu_lang"] = engine._get_menu_lang
    engine._env.globals["url_for"] = engine._url_for
    engine._env.globals["library_asset_tags"] = engine._library_asset_tags
    engine._env.globals["library_runtime"] = engine._library_runtime

    # === Step 4: Theme library provider filters/globals ===
    engine._register_provider_extensions()


def library_asset_tags(engine: Any):
    """Render tags for assets declared by active theme libraries."""
    from bengal.rendering.library_assets import render_library_asset_tags

    return render_library_asset_tags(engine._providers, engine.site)


def library_runtime(engine: Any) -> tuple[str, ...]:
    """Return runtime metadata declared by active theme libraries."""
    from bengal.rendering.library_assets import library_runtime_metadata

    return library_runtime_metadata(engine._providers)


def register_provider_extensions(engine: Any) -> None:
    """Register filters/globals from theme library providers.

    Captures Bengal's built-in names before registration so collisions
    can be detected. Provider names that collide with built-ins or
    other providers produce a BengalConfigError.
    """
    if not engine._providers:
        return

    from bengal.errors.exceptions import BengalConfigError

    builtin_filters = frozenset(engine._env.filters.keys())
    builtin_globals = frozenset(engine._env.globals.keys())
    filter_owners: dict[str, str] = {}  # filter name -> owning package
    global_owners: dict[str, str] = {}  # global name -> owning package

    for provider in engine._providers:
        if provider.register_env is None:
            continue

        shim = _ProviderEnvShim(
            engine._env,
            builtin_filters,
            builtin_globals,
            filter_owners,
            global_owners,
            provider.package,
        )
        try:
            provider.register_env(shim)
        except BengalConfigError:
            raise
        except Exception as e:
            from bengal.errors.context import ErrorDebugPayload

            msg = f"Theme library '{provider.package}': register_filters() failed: {e}"
            raise BengalConfigError(
                msg,
                code=ErrorCode.C003,
                suggestion=(
                    f"Fix '{provider.package}.register_filters(app)' or remove the "
                    "library from the theme's libraries list."
                ),
                debug_payload=ErrorDebugPayload(
                    processing_item=f"theme-library:{provider.package}",
                    processing_type="theme_library",
                    config_keys_accessed=["theme.libraries"],
                    relevant_config={
                        "library": provider.package,
                        "hook": "register_filters",
                    },
                    files_to_check=["themes/*/theme.toml", provider.package],
                    grep_patterns=[
                        f"libraries = .*{provider.package}",
                        "def register_filters",
                    ],
                ),
            ) from e


def create_directive_template_renderer(
    engine: Any,
) -> Callable[[str, dict[str, Any]], str | None]:
    """Create a callable that renders directive templates from the Kida Environment.

    Returns a function (name, context) -> str | None that:
    - Looks up directives/{name}.html in the template search path
    - Renders it with the given context dict
    - Returns None if no template is found (caller falls back to handler.render())

    The caller (_try_template_render) handles the two-step lookup:
    first directives/{node.name}.html, then directives/{token_type}.html.
    This function is called once per lookup attempt.

    Template search order follows the existing loader hierarchy:
    site templates → theme chain → default theme → provider libraries.
    Theme authors override by placing directives/{name}.html in their theme.
    """
    env = engine._env

    def render_directive_template(name: str, context: dict[str, Any]) -> str | None:
        template_name = f"directives/{name}.html"
        try:
            template = env.get_template(template_name)
        except KidaTemplateNotFoundError:
            return None
        return template.render(context)

    return render_directive_template


def resolve_theme_chain(engine: Any, active_theme: str | None) -> list[str]:
    """Resolve theme inheritance chain."""
    from bengal.rendering.template_engine.environment import resolve_theme_chain as resolve_chain

    return resolve_chain(active_theme, engine.site)
