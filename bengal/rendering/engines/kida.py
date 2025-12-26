"""Kida template engine integration for Bengal.

Implements TemplateEngineProtocol for Kida, making it available
as a BYOR (Bring Your Own Renderer) option.

Configuration:
    template_engine: kida

Features:
    - 2-5x faster than Jinja2 for typical templates
    - Free-threading safe (Python 3.14t)
    - Native async support
    - Pythonic scoping with let/set/export
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.errors import BengalRenderingError
from bengal.rendering.engines.errors import TemplateError, TemplateNotFoundError
from bengal.rendering.engines.protocol import TemplateEngineProtocol
from bengal.rendering.kida import Environment
from bengal.rendering.kida.environment import (
    FileSystemLoader,
)
from bengal.rendering.kida.environment import (
    TemplateNotFoundError as KidaTemplateNotFoundError,
)
from bengal.rendering.kida.environment import (
    TemplateSyntaxError as KidaTemplateSyntaxError,
)

if TYPE_CHECKING:
    from bengal.core import Site


class KidaTemplateEngine:
    """Bengal integration for Kida template engine.

    Implements TemplateEngineProtocol for seamless integration
    with Bengal's rendering pipeline.

    Example:
        # In bengal.yaml:
        site:
          template_engine: kida
    """

    __slots__ = ("site", "template_dirs", "_env", "_dependency_tracker", "_menu_dict_cache")

    def __init__(self, site: Site, *, profile: bool = False):
        """Initialize Kida engine for site.

        Args:
            site: Bengal Site instance
            profile: Enable template profiling (not yet implemented)
        """
        self.site = site
        self.template_dirs = self._build_template_dirs()

        # Dependency tracking (set by RenderingPipeline)
        self._dependency_tracker = None

        # Create Kida environment
        self._env = Environment(
            loader=FileSystemLoader(self.template_dirs),
            autoescape=self._select_autoescape,
            auto_reload=site.config.get("development", {}).get("auto_reload", True),
        )

        # Register Bengal-specific globals and filters
        # Uses register_all() which works because Kida has same interface as Jinja2
        self._register_bengal_template_functions()

    def _build_template_dirs(self) -> list[Path]:
        """Build ordered list of template search directories.

        Uses same resolution logic as Jinja engine:
        1. Site-level custom templates (highest priority)
        2. Theme chain (child themes first, then parent themes)
        """
        from bengal.core.theme.registry import get_theme_package
        from bengal.rendering.template_engine.environment import resolve_theme_chain

        dirs: list[Path] = []

        # Site-level custom templates (highest priority)
        custom_templates = self.site.root_path / "templates"
        if custom_templates.exists():
            dirs.append(custom_templates)

        # Resolve theme chain (handles theme inheritance)
        theme_chain = resolve_theme_chain(self.site.theme, self.site)

        for theme_name in theme_chain:
            # Site-level theme directory
            site_theme_templates = self.site.root_path / "themes" / theme_name / "templates"
            if site_theme_templates.exists():
                dirs.append(site_theme_templates)
                continue

            # Installed theme directory (via entry point)
            try:
                pkg = get_theme_package(theme_name)
                if pkg:
                    resolved = pkg.resolve_resource_path("templates")
                    if resolved and resolved.exists():
                        dirs.append(resolved)
                        continue
            except Exception:
                pass

            # Bundled theme directory
            bundled_theme_templates = (
                Path(__file__).parent.parent.parent / "themes" / theme_name / "templates"
            )
            if bundled_theme_templates.exists():
                dirs.append(bundled_theme_templates)

        # Ensure default theme exists as ultimate fallback
        # (resolve_theme_chain filters out 'default' to avoid duplicates)
        default_templates = Path(__file__).parent.parent.parent / "themes" / "default" / "templates"
        if default_templates not in dirs and default_templates.exists():
            dirs.append(default_templates)

        return dirs

    def _select_autoescape(self, name: str | None) -> bool:
        """Determine autoescape based on file extension."""
        if name is None:
            return True
        return name.endswith((".html", ".htm", ".xml"))

    def _register_bengal_template_functions(self) -> None:
        """Register Bengal-specific template functions.

        Strategy:
        1. Use register_all() which adds ~100 filters and globals
           (Works because Kida has same .filters/.globals interface as Jinja2)
        2. Override the 3 functions that use @pass_context decorator
        3. Add menu/asset functions from TemplateEngine mixins

        This avoids duplicating the filter registration logic that register_all()
        already handles correctly.
        """
        self._env.globals["site"] = self.site
        self._env.globals["config"] = self.site.config

        # === Step 1: Register all template functions (same as Jinja engine) ===
        # This provides: get_page, navigation, icons, seo, dates, strings, etc.
        try:
            from bengal.rendering.template_functions import register_all

            register_all(self._env, self.site)
        except ImportError:
            pass

        # === Step 2: Override @pass_context functions ===
        # Kida doesn't support Jinja2's @pass_context decorator, so we provide
        # context-free versions of the 3 functions that use it.
        try:
            from bengal.rendering.template_functions.i18n import _current_lang, _make_t

            base_translate = _make_t(self.site)

            def t_no_ctx(
                key: str,
                params: dict | None = None,
                lang: str | None = None,
                default: str | None = None,
            ) -> str:
                return base_translate(key, params=params, lang=lang, default=default)

            self._env.globals["t"] = t_no_ctx
            self._env.globals["current_lang"] = lambda: _current_lang(self.site, None)

            from bengal.rendering.template_functions.taxonomies import tag_url

            self._env.globals["tag_url"] = lambda tag: tag_url(tag, self.site)
        except ImportError:
            pass

        # === Step 3: Add functions from TemplateEngine mixins ===
        # These are added by Jinja's environment.py but not by register_all()
        try:
            from bengal.rendering.template_engine.url_helpers import (
                filter_dateformat,
                with_baseurl,
            )

            # asset_url (simplified - no manifest lookup)
            def simple_asset_url(path: str) -> str:
                if not path:
                    return "/assets/"
                clean_path = path.replace("\\", "/").strip().lstrip("/")
                return with_baseurl(f"/assets/{clean_path}", self.site)

            self._env.globals["asset_url"] = simple_asset_url

            # dateformat filter (from url_helpers, not dates module)
            self._env.filters["dateformat"] = filter_dateformat
            self._env.filters["date"] = filter_dateformat

            # breadcrumbs
            from bengal.rendering.template_functions.navigation import breadcrumbs

            self._env.globals["breadcrumbs"] = lambda page: breadcrumbs.get_breadcrumbs(
                page, self.site
            )
        except ImportError:
            pass

        # === Step 4: Menu functions (from MenuHelpersMixin) ===
        try:
            self._menu_dict_cache: dict[str, list[dict]] = {}
            self._env.globals["get_menu"] = self._get_menu
            self._env.globals["get_menu_lang"] = self._get_menu_lang
            self._env.globals["url_for"] = self._url_for
            self._env.globals["getattr"] = getattr
            self._env.globals["theme"] = self.site.theme_config
        except Exception:
            pass

    def _get_menu(self, menu_name: str = "main") -> list[dict]:
        """Get menu items as dicts (cached)."""
        i18n = self.site.config.get("i18n", {}) or {}
        lang = getattr(self.site, "current_language", None)
        if lang and i18n.get("strategy") != "none":
            localized = self.site.menu_localized.get(menu_name, {}).get(lang)
            if localized is not None:
                cache_key = f"{menu_name}:{lang}"
                if cache_key not in self._menu_dict_cache:
                    self._menu_dict_cache[cache_key] = [item.to_dict() for item in localized]
                return self._menu_dict_cache[cache_key]

        if menu_name not in self._menu_dict_cache:
            menu = self.site.menu.get(menu_name, [])
            self._menu_dict_cache[menu_name] = [item.to_dict() for item in menu]
        return self._menu_dict_cache[menu_name]

    def _get_menu_lang(self, menu_name: str = "main", lang: str = "") -> list[dict]:
        """Get menu items for a specific language (cached)."""
        if not lang:
            return self._get_menu(menu_name)

        cache_key = f"{menu_name}:{lang}"
        if cache_key in self._menu_dict_cache:
            return self._menu_dict_cache[cache_key]

        localized = self.site.menu_localized.get(menu_name, {}).get(lang)
        if localized is None:
            return self._get_menu(menu_name)

        self._menu_dict_cache[cache_key] = [item.to_dict() for item in localized]
        return self._menu_dict_cache[cache_key]

    def _url_for(self, page: Any) -> str:
        """Generate URL for a page."""
        if hasattr(page, "_path") and page._path:
            from bengal.rendering.template_engine.url_helpers import with_baseurl

            return with_baseurl(page._path, self.site.config.get("baseurl", ""))
        return getattr(page, "href", str(page)) if page else ""

    def render_template(
        self,
        name: str,
        context: dict[str, Any],
    ) -> str:
        """Render a named template.

        Args:
            name: Template identifier (e.g., "blog/single.html")
            context: Variables available to the template

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateRenderError: If rendering fails
        """
        try:
            template = self._env.get_template(name)

            # Inject site and config
            ctx = {"site": self.site, "config": self.site.config}
            ctx.update(context)

            return template.render(ctx)

        except KidaTemplateNotFoundError as e:
            raise TemplateNotFoundError(name, self.template_dirs) from e
        except KidaTemplateSyntaxError as e:
            raise BengalRenderingError(
                message=f"Template syntax error in '{name}': {e}",
                original_error=e,
            ) from e
        except Exception as e:
            raise BengalRenderingError(
                message=f"Template render error in '{name}': {e}",
                original_error=e,
            ) from e

    def render_string(
        self,
        template: str,
        context: dict[str, Any],
    ) -> str:
        """Render a template string.

        Args:
            template: Template content as string
            context: Variables available to the template

        Returns:
            Rendered HTML string
        """
        try:
            tmpl = self._env.from_string(template)

            # Inject site and config
            ctx = {"site": self.site, "config": self.site.config}
            ctx.update(context)

            return tmpl.render(ctx)

        except Exception as e:
            raise BengalRenderingError(
                message=f"Template string render error: {e}",
                original_error=e,
            ) from e

    def template_exists(self, name: str) -> bool:
        """Check if a template exists.

        Args:
            name: Template identifier

        Returns:
            True if template can be loaded
        """
        try:
            self._env.get_template(name)
            return True
        except Exception:
            return False

    def get_template_path(self, name: str) -> Path | None:
        """Resolve template name to filesystem path.

        Args:
            name: Template identifier

        Returns:
            Absolute path to template, or None if not found
        """
        for base in self.template_dirs:
            path = base / name
            if path.is_file():
                return path
        return None

    def list_templates(self) -> list[str]:
        """List all available template names.

        Returns:
            Sorted list of template names
        """
        templates = set()

        for base in self.template_dirs:
            if base.is_dir():
                for path in base.rglob("*.html"):
                    templates.add(str(path.relative_to(base)))
                for path in base.rglob("*.xml"):
                    templates.add(str(path.relative_to(base)))

        return sorted(templates)

    def validate(
        self,
        patterns: list[str] | None = None,
    ) -> list[TemplateError]:
        """Validate templates for syntax errors.

        Args:
            patterns: Optional glob patterns to filter

        Returns:
            List of TemplateError for invalid templates
        """
        errors = []

        for name in self.list_templates():
            # Filter by patterns if provided
            if patterns:
                from fnmatch import fnmatch

                if not any(fnmatch(name, p) for p in patterns):
                    continue

            try:
                self._env.get_template(name)
            except Exception as e:
                errors.append(
                    TemplateError(
                        message=str(e),
                        template_name=name,
                        lineno=getattr(e, "lineno", None),
                    )
                )

        return errors

    # =========================================================================
    # COMPATIBILITY METHODS (for Bengal internals)
    # =========================================================================

    @property
    def env(self) -> Environment:
        """Access to underlying Kida environment.

        Used by autodoc and other internals that check template existence.
        """
        return self._env

    def _find_template_path(self, name: str) -> Path | None:
        """Alias for get_template_path (used by debug/explainer)."""
        return self.get_template_path(name)

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Alias for render_template (for compatibility)."""
        return self.render_template(template_name, context)

    def validate_templates(self, include_patterns: list[str] | None = None) -> list[TemplateError]:
        """Alias for validate (for compatibility)."""
        return self.validate(include_patterns)


# Verify protocol compliance
def _check_protocol() -> None:
    """Verify KidaTemplateEngine implements TemplateEngineProtocol."""
    import typing

    if typing.TYPE_CHECKING:
        _: TemplateEngineProtocol = KidaTemplateEngine(...)  # type: ignore
