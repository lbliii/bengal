"""
Template engine using Jinja2 for page rendering.

Provides template rendering, template function registration, and optional
template profiling for performance analysis. Integrates with theme system
for template discovery and asset manifest for cache-busting.

Key Concepts:
    - Template inheritance: Child themes inherit parent templates
    - Bytecode caching: Compiled templates cached for faster subsequent renders
    - Template profiling: Optional timing data collection via --profile-templates
    - Strict mode: StrictUndefined enabled for better error detection

Related Modules:
    - bengal.rendering.template_profiler: Profiling implementation
    - bengal.rendering.template_functions: Template function registry
    - bengal.utils.theme_registry: Theme resolution and discovery

See Also:
    - bengal/rendering/template_profiler.py: Profiling implementation
    - plan/active/rfc-template-performance-optimization.md: Performance RFC
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

import toml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from jinja2.bccache import FileSystemBytecodeCache

from bengal.assets.manifest import AssetManifest, AssetManifestEntry
from bengal.rendering.template_functions import register_all
from bengal.rendering.template_profiler import (
    ProfiledTemplate,
    TemplateProfiler,
    get_profiler,
)
from bengal.utils.logger import get_logger, truncate_error
from bengal.utils.metadata import build_template_metadata
from bengal.utils.theme_registry import get_theme_package

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class TemplateEngine:
    """
    Template engine for rendering pages with Jinja2 templates.

    Provides Jinja2 template rendering with theme inheritance, template function
    registration, asset manifest access, and optional template profiling. Manages
    template discovery through theme chains and provides cache-busting via asset manifest.

    Creation:
        Direct instantiation: TemplateEngine(site, profile_templates=False)
            - Created by RenderingPipeline for template rendering
            - Requires Site instance with theme configuration
            - Optional profiling enabled via profile_templates flag

    Attributes:
        site: Site instance with theme and configuration
        template_dirs: List of template directories (populated during init)
        env: Jinja2 Environment instance
        _profile_templates: Whether template profiling is enabled
        _profiler: Optional TemplateProfiler for performance analysis
        _dependency_tracker: Optional DependencyTracker (set by RenderingPipeline)
        _asset_manifest_cache: Cached asset manifest entries

    Relationships:
        - Uses: Theme resolution for template directory discovery
        - Uses: Template functions for template function registration
        - Uses: AssetManifest for cache-busting asset URLs
        - Used by: RenderingPipeline for template rendering
        - Used by: Renderer for page rendering

    Notes:
        - Bytecode cache: When enabled via config, compiled templates are cached under
          `output/.bengal-cache/templates` using a stable filename pattern. Jinja2 invalidates
          entries when source templates change.
        - Strict mode and auto reload: `strict_mode` enables `StrictUndefined`; `dev_server`
          enables `auto_reload` for faster iteration.
        - Include/extends cycles: Cycle detection is delegated to Jinja2. Recursive includes or
          self-extends surface as `TemplateError` or `RecursionError` from Jinja2 during render.

    Thread Safety:
        Thread-safe. Each thread should have its own TemplateEngine instance.

    Examples:
        engine = TemplateEngine(site, profile_templates=True)
        html = engine.render_template("page.html", {"page": page})
    """

    def __init__(self, site: Any, profile_templates: bool = False) -> None:
        """
        Initialize the template engine.

        Args:
            site: Site instance
            profile_templates: Enable template profiling for performance analysis
        """
        logger.debug(
            "initializing_template_engine", theme=site.theme, root_path=str(site.root_path)
        )

        self.site = site
        self.template_dirs = []  # Initialize before _create_environment populates it

        # Template profiling support (for --profile-templates flag)
        self._profile_templates = profile_templates
        self._profiler: TemplateProfiler | None = None
        if profile_templates:
            self._profiler = get_profiler() or TemplateProfiler()
            logger.debug("template_profiling_enabled")

        self.env = self._create_environment()  # This will populate self.template_dirs
        self._dependency_tracker = (
            None  # Set by RenderingPipeline for incremental builds (private attr)
        )
        self._asset_manifest_path = self.site.output_dir / "asset-manifest.json"
        self._asset_manifest_mtime: float | None = None
        self._asset_manifest_cache: dict[str, AssetManifestEntry] = {}
        self._asset_manifest_fallbacks: set[str] = set()

        # Menu dict cache - avoids repeated to_dict() calls on every page render
        # Format: {"main": [dict, ...], "footer": [...]}
        # Invalidated when menus are rebuilt (see invalidate_menu_cache)
        self._menu_dict_cache: dict[str, list[dict]] = {}

    def _create_environment(self) -> Environment:
        """
        Create and configure Jinja2 environment.

        Returns:
            Configured Jinja2 environment
        """
        # Look for templates in multiple locations with theme inheritance
        template_dirs = []

        # Custom templates directory
        custom_templates = self.site.root_path / "templates"
        if custom_templates.exists():
            template_dirs.append(str(custom_templates))

        # Theme templates with inheritance (child first, then parents)
        for theme_name in self._resolve_theme_chain(self.site.theme):
            theme_found = False

            # Site-level theme directory
            site_theme_templates = self.site.root_path / "themes" / theme_name / "templates"
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
                    error_type=type(e).__name__,
                )

            # Bundled theme directory
            bundled_theme_templates = (
                Path(__file__).parent.parent / "themes" / theme_name / "templates"
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
                # Print visible warning to stderr for user awareness
                import sys

                print(
                    f"⚠️  Theme '{theme_name}' not found. Using default theme.",
                    file=sys.stderr,
                )
                print(
                    f"    Searched: {site_theme_templates}, {bundled_theme_templates}",
                    file=sys.stderr,
                )

        # Ensure default exists as ultimate fallback
        default_templates = Path(__file__).parent.parent / "themes" / "default" / "templates"
        if str(default_templates) not in template_dirs and default_templates.exists():
            template_dirs.append(str(default_templates))

        # Store for dependency tracking (convert back to Path objects)
        self.template_dirs = [Path(d) for d in template_dirs]

        logger.debug(
            "template_dirs_configured",
            dir_count=len(self.template_dirs),
            dirs=[str(d) for d in self.template_dirs],
        )

        # Setup bytecode cache for faster template compilation
        # This caches compiled templates between builds (10-15% speedup)
        bytecode_cache = None
        cache_templates = self.site.config.get("cache_templates", True)

        if cache_templates:
            # Create cache directory
            cache_dir = self.site.output_dir / ".bengal-cache" / "templates"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Enable bytecode cache
            # Jinja2 will automatically invalidate cache when templates change
            bytecode_cache = FileSystemBytecodeCache(
                directory=str(cache_dir), pattern="__bengal_template_%s.cache"
            )

            logger.debug("template_bytecode_cache_enabled", cache_dir=str(cache_dir))

        # Create environment
        # Use StrictUndefined in strict_mode to catch missing variables
        # Enable auto_reload in dev mode for hot-reloading templates
        auto_reload = self.site.config.get("dev_server", False)

        env_kwargs = {
            "loader": FileSystemLoader(template_dirs) if template_dirs else FileSystemLoader("."),
            "autoescape": select_autoescape(["html", "xml"]),
            "trim_blocks": True,
            "lstrip_blocks": True,
            "bytecode_cache": bytecode_cache,
            "auto_reload": auto_reload,  # Enable in dev mode for hot reload
        }

        # Only set undefined if strict_mode is enabled
        if self.site.config.get("strict_mode", False):
            env_kwargs["undefined"] = StrictUndefined

        env = Environment(**env_kwargs)

        # Add custom filters and functions (core template helpers)
        env.filters["dateformat"] = self._filter_dateformat

        # Add global variables (available in all templates and macros)
        # Pages and sections already have _site reference, no wrapping needed
        env.globals["site"] = self.site
        env.globals["config"] = self.site.config
        # Curated build/runtime metadata for templates/JS (privacy-aware)
        try:
            env.globals["bengal"] = build_template_metadata(self.site)
        except Exception:
            env.globals["bengal"] = {"engine": {"name": "Bengal SSG", "version": "unknown"}}

        # Add global functions (core template helpers)
        env.globals["url_for"] = self._url_for

        # Make asset_url context-aware for file:// protocol support
        from jinja2 import pass_context

        @pass_context
        def asset_url_with_context(ctx, asset_path: str) -> str:
            page = ctx.get("page") if hasattr(ctx, "get") else None
            return self._asset_url(asset_path, page_context=page)

        env.globals["asset_url"] = asset_url_with_context
        env.globals["get_menu"] = self._get_menu
        env.globals["get_menu_lang"] = self._get_menu_lang

        # Register all template functions (Phase 1: 30 functions)
        register_all(env, self.site)

        return env

    def _resolve_theme_chain(self, active_theme: str | None) -> list:
        """
        Resolve theme inheritance chain starting from the active theme.
        Order: child first → parent → ... (do not duplicate 'default').
        """
        chain = []
        visited = set()
        current = active_theme or "default"
        depth = 0
        MAX_DEPTH = 5

        while current and current not in visited and depth < MAX_DEPTH:
            visited.add(current)
            chain.append(current)
            extends = self._read_theme_extends(current)
            if not extends or extends == current:
                break
            current = extends
            depth += 1

        # Do not include 'default' twice; fallback is added separately
        return [t for t in chain if t != "default"]

    def _read_theme_extends(self, theme_name: str) -> str | None:
        """Read theme.toml for 'extends' from site, installed, or bundled theme path."""
        # Site theme manifest
        site_manifest = self.site.root_path / "themes" / theme_name / "theme.toml"
        if site_manifest.exists():
            try:
                data = toml.load(str(site_manifest))
                return data.get("extends")
            except Exception as e:
                logger.debug(
                    "theme_manifest_read_failed",
                    theme=theme_name,
                    path=str(site_manifest),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Installed theme manifest
        try:
            pkg = get_theme_package(theme_name)
            if pkg:
                manifest_path = pkg.resolve_resource_path("theme.toml")
                if manifest_path and manifest_path.exists():
                    try:
                        data = toml.load(str(manifest_path))
                        return data.get("extends")
                    except Exception as e:
                        logger.debug(
                            "theme_manifest_read_failed",
                            theme=theme_name,
                            path=str(manifest_path),
                            error=str(e),
                            error_type=type(e).__name__,
                        )
        except Exception as e:
            logger.debug(
                "theme_package_resolve_failed",
                theme=theme_name,
                error=str(e),
                error_type=type(e).__name__,
            )

        # Bundled theme manifest
        bundled_manifest = Path(__file__).parent.parent / "themes" / theme_name / "theme.toml"
        if bundled_manifest.exists():
            try:
                data = toml.load(str(bundled_manifest))
                return data.get("extends")
            except Exception as e:
                logger.debug(
                    "theme_manifest_read_failed",
                    theme=theme_name,
                    path=str(bundled_manifest),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        return None

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file
            context: Template context variables

        Returns:
            Rendered HTML
        """
        logger.debug(
            "rendering_template", template=template_name, context_keys=list(context.keys())
        )

        # Track template dependency
        if self._dependency_tracker:
            template_path = self._find_template_path(template_name)
            if template_path:
                self._dependency_tracker.track_template(template_path)
                logger.debug(
                    "tracked_template_dependency", template=template_name, path=str(template_path)
                )

        # Add site to context
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)

        # Pages and sections already have _site reference and can access baseurl
        # via permalink property. No wrapping needed.

        try:
            template = self.env.get_template(template_name)

            # Wrap with profiling if enabled
            if self._profiler:
                profiled_template = ProfiledTemplate(template, self._profiler)
                result = profiled_template.render(**context)
            else:
                result = template.render(**context)

            logger.debug("template_rendered", template=template_name, output_size=len(result))

            return result

        except Exception as e:
            # Log the error with context before re-raising
            logger.error(
                "template_render_failed",
                template=template_name,
                error_type=type(e).__name__,
                error=truncate_error(e, 500),
                context_keys=list(context.keys()),
            )
            raise

    def get_template_profile(self) -> dict[str, Any] | None:
        """
        Get template profiling report.

        Returns:
            Dictionary with template and function timing statistics,
            or None if profiling is not enabled.

        Example:
            report = engine.get_template_profile()
            if report:
                for name, stats in report['templates'].items():
                    print(f"{name}: {stats['count']} renders, {stats['total_ms']:.2f}ms")
        """
        if self._profiler:
            return self._profiler.get_report()
        return None

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        """
        Render a template string with the given context.

        Args:
            template_string: Template content as string
            context: Template context variables

        Returns:
            Rendered HTML
        """
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)

        template = self.env.from_string(template_string)
        return template.render(**context)

    def _filter_dateformat(self, date: Any, format: str = "%Y-%m-%d") -> str:
        """
        Format a date using strftime.

        Args:
            date: Date to format
            format: strftime format string

        Returns:
            Formatted date string
        """
        if date is None:
            return ""

        try:
            return date.strftime(format)
        except (AttributeError, ValueError):
            return str(date)

    def _url_for(self, page: Any) -> str:
        """
        Generate URL for a page with base URL support.

        Delegates to url_helpers.url_for for consistent URL generation.

        Args:
            page: Page object

        Returns:
            URL path (clean, without index.html) with base URL prefix if configured
        """
        from bengal.rendering.template_engine.url_helpers import url_for

        return url_for(page, self.site)

    def _with_baseurl(self, path: str) -> str:
        """
        Apply base URL prefix to a path.

        Delegates to url_helpers.with_baseurl for consistent URL handling.

        Args:
            path: Relative path starting with '/'

        Returns:
            Path with base URL prefix (absolute or path-only)
        """
        from bengal.rendering.template_engine.url_helpers import with_baseurl

        return with_baseurl(path, self.site)

    def _asset_url(self, asset_path: str, page_context: Any = None) -> str:
        """
        Generate URL for an asset.

        Args:
            asset_path: Path to asset file
            page_context: Optional page context for computing relative paths (for file:// support)

        Returns:
            Asset URL
        """

        # Normalize and validate the provided asset path to prevent traversal/absolute paths
        def _normalize_and_validate_asset_path(raw_path: str) -> str:
            # Convert Windows-style separators and trim whitespace
            candidate = (raw_path or "").replace("\\", "/").strip()
            # Remove any leading slash to keep it relative inside /assets
            while candidate.startswith("/"):
                candidate = candidate[1:]

            try:
                posix_path = PurePosixPath(candidate)
            except Exception:
                return ""

            # Reject absolute paths and traversal segments
            if posix_path.is_absolute() or any(part == ".." for part in posix_path.parts):
                return ""

            # Collapse any '.' segments by reconstructing the path
            sanitized = PurePosixPath(*[p for p in posix_path.parts if p not in ("", ".")])
            return sanitized.as_posix()

        safe_asset_path = _normalize_and_validate_asset_path(asset_path)
        if not safe_asset_path:
            logger.warning("asset_path_invalid", provided=str(asset_path))
            return "/assets/"

        # Check if baseurl is file:// - if so, generate relative URLs for file:// protocol
        baseurl_value = (self.site.config.get("baseurl", "") or "").rstrip("/")
        if baseurl_value.startswith("file://"):
            # Compute relative path from current page to assets directory
            asset_url_path = f"assets/{safe_asset_path}"

            # Try to compute relative path from page's output location
            if page_context and hasattr(page_context, "output_path") and page_context.output_path:
                try:
                    # Compute relative path from page to site root
                    page_rel_to_root = page_context.output_path.relative_to(self.site.output_dir)
                    # Count depth (number of parent directories)
                    depth = (
                        len(page_rel_to_root.parent.parts)
                        if page_rel_to_root.parent != Path(".")
                        else 0
                    )
                    # Generate relative path: ../ repeated depth times, then assets/...
                    if depth > 0:
                        relative_prefix = "/".join([".."] * depth)
                        return f"{relative_prefix}/{asset_url_path}"
                    else:
                        # Root level page
                        return f"./{asset_url_path}"
                except (ValueError, AttributeError):
                    # If page_context.output_path is not set or not relative to output_dir,
                    # fall back to using root-relative path
                    pass

            # Fallback: assume root-level (works for index.html and most pages)
            return f"./{asset_url_path}"

        # In dev server mode, prefer stable URLs without fingerprints for CSS/JS
        # Skip this for file:// protocol (handled separately above)
        if not baseurl_value.startswith("file://"):
            try:
                if self.site.config.get("dev_server", False):
                    return self._with_baseurl(f"/assets/{safe_asset_path}")
            except Exception:
                # If config access fails or URL generation fails, continue to manifest lookup
                logger.debug("Error generating dev server asset URL for %r", safe_asset_path)

        # Use manifest as single source of truth for asset resolution
        manifest_entry = self._get_manifest_entry(safe_asset_path)
        if manifest_entry:
            manifest_path = f"/{manifest_entry.output_path}"
            # For file:// protocol, convert manifest path to relative
            if baseurl_value.startswith("file://") and page_context:
                try:
                    if hasattr(page_context, "output_path") and page_context.output_path:
                        page_rel_to_root = page_context.output_path.relative_to(
                            self.site.output_dir
                        )
                        depth = (
                            len(page_rel_to_root.parent.parts)
                            if page_rel_to_root.parent != Path(".")
                            else 0
                        )
                        # Remove leading / from manifest path for relative URL
                        rel_manifest_path = manifest_entry.output_path.lstrip("/")
                        if depth > 0:
                            relative_prefix = "/".join([".."] * depth)
                            return f"{relative_prefix}/{rel_manifest_path}"
                        else:
                            return f"./{rel_manifest_path}"
                except (ValueError, AttributeError):
                    # If page_context.output_path is not set or not relative to output_dir,
                    # fall back to using baseurl with manifest path
                    pass
            return self._with_baseurl(manifest_path)

        # If manifest exists but entry is missing, warn and fall back to direct path
        if self._asset_manifest_path.exists():
            self._warn_manifest_fallback(safe_asset_path)

        # Fallback: check output directory for fingerprinted files
        # This handles cases where fingerprinted files exist but manifest is missing
        asset_path_obj = PurePosixPath(safe_asset_path)
        output_asset_dir = self.site.output_dir / "assets" / asset_path_obj.parent
        output_asset_name = asset_path_obj.name

        # For file:// protocol fallback, use relative path
        if baseurl_value.startswith("file://"):
            fallback_path = f"assets/{safe_asset_path}"
            if page_context and hasattr(page_context, "output_path") and page_context.output_path:
                try:
                    page_rel_to_root = page_context.output_path.relative_to(self.site.output_dir)
                    depth = (
                        len(page_rel_to_root.parent.parts)
                        if page_rel_to_root.parent != Path(".")
                        else 0
                    )
                    if depth > 0:
                        relative_prefix = "/".join([".."] * depth)
                        return f"{relative_prefix}/{fallback_path}"
                    else:
                        return f"./{fallback_path}"
                except (ValueError, AttributeError):
                    # Could not compute relative path for file:// fallback asset; fall back to root-relative
                    logger.debug(
                        "Failed to compute relative path for file:// fallback asset: %s",
                        safe_asset_path,
                    )
            return f"./{fallback_path}"

        if output_asset_dir.exists():
            # Look for fingerprinted version (e.g., style.12345678.css)
            if "." in output_asset_name:
                base_name, ext = output_asset_name.rsplit(".", 1)
                # Pattern: base.fingerprint.ext (e.g., style.12345678.css)
                pattern = f"{base_name}.*.{ext}"
            else:
                # No extension, just look for base.*
                pattern = f"{output_asset_name}.*"

            fingerprinted_files = list(output_asset_dir.glob(pattern))
            if fingerprinted_files:
                # Use the first fingerprinted file found
                fingerprinted_name = fingerprinted_files[0].name
                fingerprinted_path = asset_path_obj.parent / fingerprinted_name
                fingerprinted_url = f"/assets/{fingerprinted_path.as_posix()}"

                # Handle file:// protocol for fingerprinted files
                if baseurl_value.startswith("file://") and page_context:
                    try:
                        if hasattr(page_context, "output_path") and page_context.output_path:
                            page_rel_to_root = page_context.output_path.relative_to(
                                self.site.output_dir
                            )
                            depth = (
                                len(page_rel_to_root.parent.parts)
                                if page_rel_to_root.parent != Path(".")
                                else 0
                            )
                            rel_fingerprinted_path = fingerprinted_url.lstrip("/")
                            if depth > 0:
                                relative_prefix = "/".join([".."] * depth)
                                return f"{relative_prefix}/{rel_fingerprinted_path}"
                            else:
                                return f"./{rel_fingerprinted_path}"
                    except (ValueError, AttributeError):
                        # Could not compute relative path for fingerprinted asset; fall back to default URL
                        logger.debug(
                            "Failed to compute relative path for fingerprinted asset: %s",
                            safe_asset_path,
                        )

                return self._with_baseurl(fingerprinted_url)

        # Final fallback: return direct asset path (for dev or when manifest unavailable)
        fallback_url = f"/assets/{safe_asset_path}"

        # Handle file:// protocol for final fallback
        if baseurl_value.startswith("file://"):
            fallback_path = f"assets/{safe_asset_path}"
            if page_context and hasattr(page_context, "output_path") and page_context.output_path:
                try:
                    page_rel_to_root = page_context.output_path.relative_to(self.site.output_dir)
                    depth = (
                        len(page_rel_to_root.parent.parts)
                        if page_rel_to_root.parent != Path(".")
                        else 0
                    )
                    if depth > 0:
                        relative_prefix = "/".join([".."] * depth)
                        return f"{relative_prefix}/{fallback_path}"
                    else:
                        return f"./{fallback_path}"
                except (ValueError, AttributeError):
                    # Could not compute relative path for final fallback asset; fall back to root-relative
                    logger.debug(
                        "Failed to compute relative path for final fallback asset: %s",
                        safe_asset_path,
                    )
            return f"./{fallback_path}"

        return self._with_baseurl(fallback_url)

    def invalidate_menu_cache(self) -> None:
        """
        Invalidate the menu dict cache.

        Call this after menus are rebuilt to ensure fresh dicts are generated.
        """
        self._menu_dict_cache.clear()

    def _get_menu(self, menu_name: str = "main") -> list:
        """
        Get menu items as dicts for template access (cached).

        Args:
            menu_name: Name of the menu to get (e.g., 'main', 'footer')

        Returns:
            List of menu item dicts

        Performance:
            Menu dicts are cached to avoid repeated to_dict() calls on every
            page render. Cache is invalidated when menus are rebuilt.
        """
        # If i18n enabled and current_language set, prefer localized menu
        i18n = self.site.config.get("i18n", {}) or {}
        lang = getattr(self.site, "current_language", None)
        if lang and i18n.get("strategy") != "none":
            localized = self.site.menu_localized.get(menu_name, {}).get(lang)
            if localized is not None:
                cache_key = f"{menu_name}:{lang}"
                if cache_key not in self._menu_dict_cache:
                    self._menu_dict_cache[cache_key] = [
                        item.to_dict() for item in localized
                    ]
                return self._menu_dict_cache[cache_key]

        # Check cache for non-localized menu
        if menu_name not in self._menu_dict_cache:
            menu = self.site.menu.get(menu_name, [])
            self._menu_dict_cache[menu_name] = [item.to_dict() for item in menu]
        return self._menu_dict_cache[menu_name]

    def _get_menu_lang(self, menu_name: str = "main", lang: str = "") -> list:
        """
        Get menu items for a specific language (cached).
        """
        if not lang:
            return self._get_menu(menu_name)

        cache_key = f"{menu_name}:{lang}"
        if cache_key in self._menu_dict_cache:
            return self._menu_dict_cache[cache_key]

        localized = self.site.menu_localized.get(menu_name, {}).get(lang)
        if localized is None:
            # Fallback to default
            return self._get_menu(menu_name)

        self._menu_dict_cache[cache_key] = [item.to_dict() for item in localized]
        return self._menu_dict_cache[cache_key]

    def _find_template_path(self, template_name: str) -> Path | None:
        """
        Find the full path to a template file.

        Args:
            template_name: Name of the template

        Returns:
            Full path to template file, or None if not found
        """
        for template_dir in self.template_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                logger.debug(
                    "template_found",
                    template=template_name,
                    path=str(template_path),
                    dir=str(template_dir),
                )
                return template_path

    def _get_manifest_entry(self, logical_path: str) -> AssetManifestEntry | None:
        """
        Return manifest entry for logical path if the manifest is present.
        """
        cache = self._load_asset_manifest()
        return cache.get(PurePosixPath(logical_path).as_posix())

    def _load_asset_manifest(self) -> dict[str, AssetManifestEntry]:
        """
        Load and cache the asset manifest based on file mtime.
        """
        manifest_path = self._asset_manifest_path
        try:
            stat = manifest_path.stat()
        except FileNotFoundError:
            self._asset_manifest_mtime = None
            self._asset_manifest_cache = {}
            return self._asset_manifest_cache

        if self._asset_manifest_mtime == stat.st_mtime:
            return self._asset_manifest_cache

        manifest = AssetManifest.load(manifest_path)
        if manifest is None:
            self._asset_manifest_cache = {}
        else:
            self._asset_manifest_cache = dict(manifest.entries)
        self._asset_manifest_mtime = stat.st_mtime
        return self._asset_manifest_cache

    def _warn_manifest_fallback(self, logical_path: str) -> None:
        """
        Warn once per logical path when manifest lookup misses and fallback is used.
        """
        if logical_path in self._asset_manifest_fallbacks:
            return
        self._asset_manifest_fallbacks.add(logical_path)
        logger.warning(
            "asset_manifest_miss",
            logical_path=logical_path,
            manifest=str(self._asset_manifest_path),
        )

        logger.debug(
            "asset_manifest_fallback",
            logical_path=logical_path,
            manifest=str(self._asset_manifest_path),
        )
        return None
