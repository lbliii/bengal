"""
Template engine using Jinja2.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import toml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from jinja2.bccache import FileSystemBytecodeCache

from bengal.rendering.template_functions import register_all
from bengal.utils.logger import get_logger, truncate_error
from bengal.utils.metadata import build_template_metadata
from bengal.utils.theme_registry import get_theme_package

logger = get_logger(__name__)


class TemplateEngine:
    """
    Template engine for rendering pages with Jinja2 templates.
    """

    def __init__(self, site: Any) -> None:
        """
        Initialize the template engine.

        Args:
            site: Site instance
        """
        logger.debug(
            "initializing_template_engine", theme=site.theme, root_path=str(site.root_path)
        )

        self.site = site
        self.template_dirs = []  # Initialize before _create_environment populates it
        self.env = self._create_environment()  # This will populate self.template_dirs
        self._dependency_tracker = (
            None  # Set by RenderingPipeline for incremental builds (private attr)
        )

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
            # Site-level theme directory
            site_theme_templates = self.site.root_path / "themes" / theme_name / "templates"
            if site_theme_templates.exists():
                template_dirs.append(str(site_theme_templates))
                continue

            # Installed theme directory (via entry point)
            try:
                pkg = get_theme_package(theme_name)
                if pkg:
                    resolved = pkg.resolve_resource_path("templates")
                    if resolved and resolved.exists():
                        template_dirs.append(str(resolved))
                        continue
            except Exception:
                pass

            # Bundled theme directory
            bundled_theme_templates = (
                Path(__file__).parent.parent / "themes" / theme_name / "templates"
            )
            if bundled_theme_templates.exists():
                template_dirs.append(str(bundled_theme_templates))

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
        env_kwargs = {
            "loader": FileSystemLoader(template_dirs) if template_dirs else FileSystemLoader("."),
            "autoescape": select_autoescape(["html", "xml"]),
            "trim_blocks": True,
            "lstrip_blocks": True,
            "bytecode_cache": bytecode_cache,
            "auto_reload": False,  # Disable auto-reload for performance
        }

        # Only set undefined if strict_mode is enabled
        if self.site.config.get("strict_mode", False):
            env_kwargs["undefined"] = StrictUndefined

        env = Environment(**env_kwargs)

        # Add custom filters and functions (core template helpers)
        env.filters["dateformat"] = self._filter_dateformat

        # Add global variables (available in all templates and macros)
        env.globals["site"] = self.site
        env.globals["config"] = self.site.config
        # Curated build/runtime metadata for templates/JS (privacy-aware)
        try:
            env.globals["bengal"] = build_template_metadata(self.site)
        except Exception:
            env.globals["bengal"] = {"engine": {"name": "Bengal SSG", "version": "unknown"}}

        # Add global functions (core template helpers)
        env.globals["url_for"] = self._url_for
        env.globals["asset_url"] = self._asset_url
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
            except Exception:
                pass

        # Installed theme manifest
        try:
            pkg = get_theme_package(theme_name)
            if pkg:
                manifest_path = pkg.resolve_resource_path("theme.toml")
                if manifest_path and manifest_path.exists():
                    data = toml.load(str(manifest_path))
                    return data.get("extends")
        except Exception:
            pass

        # Bundled theme manifest
        bundled_manifest = Path(__file__).parent.parent / "themes" / theme_name / "theme.toml"
        if bundled_manifest.exists():
            try:
                data = toml.load(str(bundled_manifest))
                return data.get("extends")
            except Exception:
                pass

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

        try:
            template = self.env.get_template(template_name)
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
        Generate URL for a page.

        Args:
            page: Page object

        Returns:
            URL path (clean, without index.html)
        """
        # Use the page's url property if available (clean URLs)
        try:
            if hasattr(page, "url"):
                return page.url
        except Exception:
            pass

        # Support dict-like contexts (component preview/demo data)
        try:
            if isinstance(page, Mapping):
                if "url" in page:
                    return str(page["url"])
                if "slug" in page:
                    return f"/{page['slug']}/"
        except Exception:
            pass

        # Fallback to slug-based URL for objects
        try:
            return f"/{page.slug}/"
        except Exception:
            return "/"

    def _asset_url(self, asset_path: str) -> str:
        """
        Generate URL for an asset.

        Args:
            asset_path: Path to asset file

        Returns:
            Asset URL
        """
        # Attempt to resolve a fingerprinted file in output_dir/assets
        try:
            base = self.site.output_dir / "assets"
            # If input includes a directory (e.g., css/style.css), split it
            p = Path(asset_path)
            subdir = base / p.parent
            stem = p.stem
            suffix = p.suffix
            if subdir.exists():
                # Find first matching file with stem.hash.suffix
                for cand in subdir.glob(f"{stem}.*{suffix}"):
                    # Ensure pattern looks like fingerprint (dot + 8 hex)
                    parts = cand.name.split(".")
                    if len(parts) >= 3 and len(parts[-2]) >= 6:
                        rel = cand.relative_to(self.site.output_dir)
                        return f"/{rel.as_posix()}"
        except Exception:
            pass
        return f"/assets/{asset_path}"

    def _get_menu(self, menu_name: str = "main") -> list:
        """
        Get menu items as dicts for template access.

        Args:
            menu_name: Name of the menu to get (e.g., 'main', 'footer')

        Returns:
            List of menu item dicts
        """
        # If i18n enabled and current_language set, prefer localized menu
        i18n = self.site.config.get("i18n", {}) or {}
        lang = getattr(self.site, "current_language", None)
        if lang and i18n.get("strategy") != "none":
            localized = self.site.menu_localized.get(menu_name, {}).get(lang)
            if localized is not None:
                return [item.to_dict() for item in localized]
        menu = self.site.menu.get(menu_name, [])
        return [item.to_dict() for item in menu]

    def _get_menu_lang(self, menu_name: str = "main", lang: str = "") -> list:
        """
        Get menu items for a specific language.
        """
        if not lang:
            return self._get_menu(menu_name)
        localized = self.site.menu_localized.get(menu_name, {}).get(lang)
        if localized is None:
            # Fallback to default
            return self._get_menu(menu_name)
        return [item.to_dict() for item in localized]

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

        logger.debug(
            "template_not_found",
            template=template_name,
            searched_dirs=[str(d) for d in self.template_dirs],
        )
        return None
