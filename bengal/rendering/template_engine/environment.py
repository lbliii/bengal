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

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from jinja2.bccache import FileSystemBytecodeCache
from jinja2.runtime import Context

from bengal.core.theme import get_theme_package
from bengal.rendering.template_functions import register_all
from bengal.utils.logger import get_logger
from bengal.utils.metadata import build_template_metadata

logger = get_logger(__name__)


def resolve_theme_chain(active_theme: str | None, site: Any) -> list[str]:
    """
    Resolve theme inheritance chain starting from the active theme.

    Order: child first → parent → ... (do not duplicate 'default').

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

    # Do not include 'default' twice; fallback is added separately
    return [t for t in chain if t != "default"]


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

    logger.debug(
        "template_dirs_configured",
        dir_count=len(template_dir_paths),
        dirs=[str(d) for d in template_dir_paths],
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
    elif auto_reload:
        logger.debug("template_bytecode_cache_disabled", reason="dev_server_auto_reload")

    # Create environment
    env_kwargs = {
        "loader": FileSystemLoader(template_dirs) if template_dirs else FileSystemLoader("."),
        "autoescape": select_autoescape(["html", "xml"]),
        "trim_blocks": True,
        "lstrip_blocks": True,
        "bytecode_cache": bytecode_cache,
        "auto_reload": auto_reload,
        # Enable 'do' extension for statement execution in templates (e.g., {% do list.append(x) %})
        # Enable 'loopcontrols' extension for {% break %} and {% continue %} in loops
        "extensions": ["jinja2.ext.do", "jinja2.ext.loopcontrols"],
    }

    if site.config.get("strict_mode", False):
        env_kwargs["undefined"] = StrictUndefined

    env = Environment(**env_kwargs)

    # Add custom filters
    from bengal.rendering.template_engine.url_helpers import filter_dateformat

    env.filters["dateformat"] = filter_dateformat

    # Add global variables
    env.globals["site"] = site
    env.globals["config"] = site.config
    # Add theme object for template access (alias for site.theme_config)
    env.globals["theme"] = site.theme_config

    # Add versioning context
    # Templates can access: versions (list), versioning_enabled (bool)
    # Per-page: current_version is set in page context, not here
    env.globals["versioning_enabled"] = site.versioning_enabled
    env.globals["versions"] = site.versions

    try:
        env.globals["bengal"] = build_template_metadata(site)
    except Exception as e:
        logger.debug(
            "template_metadata_build_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="using_fallback_metadata",
        )
        env.globals["bengal"] = {"engine": {"name": "Bengal SSG", "version": "unknown"}}

    # Add global functions
    env.globals["url_for"] = template_engine._url_for
    env.globals["get_menu"] = template_engine._get_menu
    env.globals["get_menu_lang"] = template_engine._get_menu_lang
    # Add Python's getattr for safe attribute access in templates
    # Usage: getattr(element, 'children', []) to safely get children with default
    env.globals["getattr"] = getattr

    # Make asset_url context-aware for file:// protocol support
    from jinja2 import pass_context

    @pass_context
    def asset_url_with_context(ctx: Context, asset_path: str) -> str:
        page = ctx.get("page") if hasattr(ctx, "get") else None
        result = template_engine._asset_url(asset_path, page_context=page)
        return str(result) if result else ""

    env.globals["asset_url"] = asset_url_with_context

    # Register all template functions
    register_all(env, site)

    # Best-effort cache of template search paths for non-dev builds.
    if not auto_reload:
        site._bengal_template_dirs_cache = {
            "key": cache_key,
            "template_dirs": list(template_dirs),
        }

    return env, template_dir_paths
