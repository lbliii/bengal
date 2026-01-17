"""
Jinja2 environment creation and configuration for template engine.

Provides environment setup, theme resolution, and template directory discovery.

Related Modules:
- bengal.rendering.template_engine.core: Uses this for environment creation
- bengal.utils.theme_registry: Theme package resolution

"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PrefixLoader,
    StrictUndefined,
    select_autoescape,
)

# ChainableUndefined is not in jinja2 type stubs; use StrictUndefined as fallback
try:
    from jinja2 import ChainableUndefined
except ImportError:
    ChainableUndefined = StrictUndefined  # type: ignore[misc, assignment]
from jinja2.bccache import FileSystemBytecodeCache

from bengal.core.theme import get_theme_package
from bengal.errors import ErrorCode
from bengal.rendering.context import ParamsContext, get_engine_globals
from bengal.rendering.template_functions import register_all
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


def resolve_theme_chain(active_theme: str | None, site: Any) -> list[str]:
    """
    Resolve theme inheritance chain starting from the active theme.
    
    Order: child first → parent → ... (do not duplicate 'default').
    
    When active_theme is "default" (or None), returns ["default"] so that
    the bundled default theme assets are discovered. For child themes that
    extend "default", filters out "default" since it's added as a fallback
    separately in template loaders.
    
    Args:
        active_theme: Active theme name
        site: Site instance
    
    Returns:
        List of theme names in inheritance order
        
    """
    chain = []
    visited: set[str] = set()
    current = active_theme or "default"
    depth = 0
    MAX_DEPTH = 5

    while current and current not in visited and depth < MAX_DEPTH:
        visited.add(current)
        chain.append(current)
        extends = read_theme_extends(current, site)
        if not extends or extends == current:
            break
        current = extends
        depth += 1

    # When active_theme is "default" itself, keep it so assets are discovered.
    # For child themes extending default, filter out "default" since the caller
    # adds it as a fallback separately.
    if (active_theme or "default") == "default":
        return chain
    return [t for t in chain if t != "default"]


def _resolve_theme_templates_path(theme_name: str, site: Any) -> Path | None:
    """
    Resolve the templates directory path for a theme.
    
    Checks site themes, installed themes, and bundled themes in order.
    
    Args:
        theme_name: Theme name to look up
        site: Site instance
    
    Returns:
        Path to theme's templates directory, or None if not found
        
    """
    # Site-level theme directory
    site_theme_templates = site.root_path / "themes" / theme_name / "templates"
    if site_theme_templates.exists():
        return site_theme_templates

    # Installed theme directory (via entry point)
    try:
        pkg = get_theme_package(theme_name)
        if pkg:
            resolved = pkg.resolve_resource_path("templates")
            if resolved and resolved.exists():
                return resolved
    except Exception as e:
        logger.debug(
            "theme_resolution_installed_failed",
            theme=theme_name,
            error=str(e),
        )

    # Bundled theme directory
    bundled_theme_templates = (
        Path(__file__).parent.parent.parent / "themes" / theme_name / "templates"
    )
    if bundled_theme_templates.exists():
        return bundled_theme_templates

    return None


def read_theme_extends(theme_name: str, site: Any) -> str | None:
    """
    Read theme.toml for 'extends' from site, installed, or bundled theme path.
    
    Args:
        theme_name: Theme name to look up
        site: Site instance
    
    Returns:
        Parent theme name if extends is set, None otherwise
        
    """
    # Site theme manifest
    site_manifest = site.root_path / "themes" / theme_name / "theme.toml"
    if site_manifest.exists():
        try:
            with open(site_manifest, "rb") as f:
                data = tomllib.load(f)
            extends = data.get("extends")
            return str(extends) if extends else None
        except Exception as e:
            logger.debug(
                "theme_manifest_read_failed",
                theme=theme_name,
                path=str(site_manifest),
                error=str(e),
            )

    # Installed theme manifest
    try:
        pkg = get_theme_package(theme_name)
        if pkg:
            manifest_path = pkg.resolve_resource_path("theme.toml")
            if manifest_path and manifest_path.exists():
                try:
                    with open(manifest_path, "rb") as f:
                        data = tomllib.load(f)
                    extends = data.get("extends")
                    return str(extends) if extends else None
                except Exception as e:
                    logger.debug(
                        "theme_manifest_read_failed",
                        theme=theme_name,
                        path=str(manifest_path),
                        error=str(e),
                    )
    except Exception as e:
        logger.debug(
            "theme_package_resolve_failed",
            theme=theme_name,
            error=str(e),
        )

    # Bundled theme manifest
    bundled_manifest = Path(__file__).parent.parent.parent / "themes" / theme_name / "theme.toml"
    if bundled_manifest.exists():
        try:
            with open(bundled_manifest, "rb") as f:
                data = tomllib.load(f)
            extends = data.get("extends")
            return str(extends) if extends else None
        except Exception as e:
            logger.debug(
                "theme_manifest_read_failed",
                theme=theme_name,
                path=str(bundled_manifest),
                error=str(e),
            )

    return None


def create_jinja_environment(
    site: Any,
    template_engine: Any,
    profile_templates: bool = False,
) -> tuple[Environment, list[Path]]:
    """
    Create and configure Jinja2 environment.
    
    Args:
        site: Site instance
        template_engine: TemplateEngine instance (for function bindings)
        profile_templates: Whether template profiling is enabled
    
    Returns:
        Tuple of (Jinja2 Environment, list of template directories)
        
    """
    import sys

    # Dev server should always reflect filesystem changes (do not cache).
    auto_reload = site.dev_mode

    # Look for templates in multiple locations with theme inheritance.
    # Optimization: avoid repeating filesystem scanning N times when rendering in parallel
    # (each worker thread creates its own TemplateEngine + Jinja Environment).
    template_dirs: list[str] = []
    used_cache = False
    cache_key = (getattr(site, "theme", None), str(getattr(site, "root_path", "")))
    cached = site._bengal_template_dirs_cache
    if not auto_reload and isinstance(cached, dict) and cached.get("key") == cache_key:
        cached_dirs = cached.get("template_dirs")
        if isinstance(cached_dirs, list) and all(isinstance(d, str) for d in cached_dirs):
            template_dirs = list(cached_dirs)
            used_cache = True

    # Custom templates directory
    if not used_cache:
        custom_templates = site.root_path / "templates"
        if custom_templates.exists():
            template_dirs.append(str(custom_templates))

    # Theme templates with inheritance (child first, then parents)
    if not used_cache:
        theme_chain_cached = site._bengal_theme_chain_cache
        if (
            not auto_reload
            and isinstance(theme_chain_cached, dict)
            and theme_chain_cached.get("key") == cache_key
        ):
            theme_chain = theme_chain_cached.get("chain", [])
        else:
            theme_chain = resolve_theme_chain(site.theme, site)
            if not auto_reload:
                site._bengal_theme_chain_cache = {"key": cache_key, "chain": list(theme_chain)}

        for theme_name in theme_chain:
            theme_found = False

            # Site-level theme directory
            site_theme_templates = site.root_path / "themes" / theme_name / "templates"
            if site_theme_templates.exists():
                template_dirs.append(str(site_theme_templates))
                theme_found = True
                continue

            # Installed theme directory (via entry point)
            try:
                pkg = get_theme_package(theme_name)
                if pkg:
                    resolved = pkg.resolve_resource_path("templates")
                    if resolved and resolved.exists():
                        template_dirs.append(str(resolved))
                        theme_found = True
                        continue
            except Exception as e:
                logger.debug(
                    "theme_resolution_installed_failed",
                    theme=theme_name,
                    error=str(e),
                )

            # Bundled theme directory
            bundled_theme_templates = (
                Path(__file__).parent.parent.parent / "themes" / theme_name / "templates"
            )
            if bundled_theme_templates.exists():
                template_dirs.append(str(bundled_theme_templates))
                theme_found = True

            # Warn if theme not found in any location
            if not theme_found:
                logger.warning(
                    "theme_not_found",
                    theme=theme_name,
                    checked_site=str(site_theme_templates),
                    checked_bundled=str(bundled_theme_templates),
                    error_code=ErrorCode.C003.value,
                    suggestion="Check theme name spelling or install theme",
                    hint="Theme may be missing or incorrectly configured",
                )
                print(
                    f"⚠️  Theme '{theme_name}' not found. Using default theme.",
                    file=sys.stderr,
                )
                print(
                    f"    Searched: {site_theme_templates}, {bundled_theme_templates}",
                    file=sys.stderr,
                )

    # Ensure default exists as ultimate fallback
    default_templates = Path(__file__).parent.parent.parent / "themes" / "default" / "templates"
    if str(default_templates) not in template_dirs and default_templates.exists():
        template_dirs.append(str(default_templates))

    # Convert to Path objects for storage
    template_dir_paths = [Path(d) for d in template_dirs]

    # Build PrefixLoader mappings for cross-theme extends support.
    # This enables templates to explicitly reference parent themes:
    #   {% extends "default/base.html" %}
    # Without this, you can only use priority-based resolution.
    theme_prefix_loaders: dict[str, FileSystemLoader] = {}
    if not used_cache:
        # Include all themes in chain plus default
        all_themes = list(theme_chain) if "theme_chain" in dir() else []
        if "default" not in all_themes:
            all_themes.append("default")

        for theme_name in all_themes:
            theme_templates_path = _resolve_theme_templates_path(theme_name, site)
            if theme_templates_path:
                theme_prefix_loaders[theme_name] = FileSystemLoader(str(theme_templates_path))

    logger.debug(
        "template_dirs_configured",
        dir_count=len(template_dir_paths),
        dirs=[str(d) for d in template_dir_paths],
        prefix_loaders=list(theme_prefix_loaders.keys()),
    )

    # Setup bytecode cache for faster template compilation
    # DISABLED in dev mode: bytecode cache can cause stale templates when editing
    # bundled theme files, where mtime checks may be unreliable. The speed gain
    # is minimal in dev mode (templates are recompiled on each rebuild anyway).
    bytecode_cache = None
    cache_templates = site.config.get("cache_templates", True) and not auto_reload

    if cache_templates:
        # Migrate template cache from legacy location if exists
        if hasattr(site, "paths"):
            from bengal.cache.paths import migrate_template_cache

            migrate_template_cache(site.paths, site.output_dir)
            cache_dir = site.paths.templates_dir
        else:
            # Fallback for tests using DummySite or mocks without paths
            cache_dir = site.output_dir / ".bengal-cache" / "templates"

        cache_dir.mkdir(parents=True, exist_ok=True)
        bytecode_cache = FileSystemBytecodeCache(
            directory=str(cache_dir), pattern="__bengal_template_%s.cache"
        )
        logger.debug("template_bytecode_cache_enabled", cache_dir=str(cache_dir))

        # NOTE: Race condition mitigation
        # When multiple threads compile the same template simultaneously, Jinja2's
        # FileSystemBytecodeCache creates temporary .tmp files that may be cleaned up
        # before they're read, causing harmless FileNotFoundError warnings. To prevent
        # duplicate compilation work, we use per-template locks in JinjaTemplateEngine
        # to serialize compilation. Once one thread compiles and writes the bytecode cache,
        # other threads can load it quickly. This reduces wasted CPU from concurrent
        # compilation of the same template.
    elif auto_reload:
        logger.debug("template_bytecode_cache_disabled", reason="dev_server_auto_reload")

    # Create loader with cross-theme extends support.
    # ChoiceLoader tries loaders in order:
    #   1. FileSystemLoader: Standard priority-based resolution (project > theme > default)
    #   2. PrefixLoader: Explicit theme references like "default/base.html"
    #
    # This enables both patterns:
    #   {% extends "base.html" %}           -> Priority resolution (normal)
    #   {% extends "default/base.html" %}   -> Explicit parent theme (cross-theme extends)
    base_loader = FileSystemLoader(template_dirs) if template_dirs else FileSystemLoader(".")

    if theme_prefix_loaders:
        loader = ChoiceLoader([base_loader, PrefixLoader(theme_prefix_loaders)])
        logger.debug(
            "prefix_loader_enabled",
            themes=list(theme_prefix_loaders.keys()),
            usage_example='{% extends "default/base.html" %}',
        )
    else:
        loader = base_loader

    # Create environment with ChainableUndefined for safe dot-notation access
    # This allows templates to write {{ params.deeply.nested.missing }} without errors
    env = Environment(
        loader=loader,
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
        bytecode_cache=bytecode_cache,
        auto_reload=auto_reload,
        # Enable 'do' extension for statement execution in templates (e.g., {% do list.append(x) %})
        # Enable 'loopcontrols' extension for {% break %} and {% continue %} in loops
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
        # ChainableUndefined: allows chained attribute access on undefined values
        # e.g., {{ params.missing.nested.key }} returns Undefined instead of raising
        undefined=ChainableUndefined,
        # Finalize: convert None values to empty strings in output
        finalize=lambda x: "" if x is None else x,
    )

    # Add custom filters
    from bengal.rendering.template_engine.url_helpers import filter_dateformat

    env.filters["dateformat"] = filter_dateformat

    # safe_access filter: wraps raw dicts in ParamsContext for safe dot-notation access
    # Usage: {% set resume = site.data.resume | safe_access %}
    #        {{ resume.contact.email }}  # Safe, no .get() needed
    def filter_safe_access(value):
        """Wrap dict in ParamsContext for safe dot-notation access with '' defaults."""
        if isinstance(value, dict):
            return ParamsContext(value)
        return value

    env.filters["safe_access"] = filter_safe_access

    # === Shared engine globals ===
    # Single source of truth: site, config, theme, menus, bengal, versions, getattr, etc.
    # See bengal/rendering/context/__init__.py:get_engine_globals()
    env.globals.update(get_engine_globals(site))

    # === Engine-specific globals ===
    # These need access to the TemplateEngine instance
    env.globals["url_for"] = template_engine._url_for
    env.globals["get_menu"] = template_engine._get_menu
    env.globals["get_menu_lang"] = template_engine._get_menu_lang

    # Register all template functions (non-context-dependent)
    register_all(env, site)

    # Register context-dependent functions via adapter layer
    # This handles t(), current_lang(), tag_url(), asset_url() with @pass_context
    from bengal.rendering.adapters import register_context_functions

    register_context_functions(env, site, adapter_type="jinja")

    # Best-effort cache of template search paths for non-dev builds.
    if not auto_reload:
        site._bengal_template_dirs_cache = {
            "key": cache_key,
            "template_dirs": list(template_dirs),
        }

    return env, template_dir_paths
