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

from kida import Environment
from kida.bytecode_cache import BytecodeCache
from kida.environment import (
    FileSystemLoader,
)
from kida.environment import (
    TemplateNotFoundError as KidaTemplateNotFoundError,
)
from kida.environment import (
    TemplateSyntaxError as KidaTemplateSyntaxError,
)

from bengal.errors import BengalRenderingError
from bengal.protocols import EngineCapability, TemplateEngineProtocol
from bengal.protocols.capabilities import has_clear_template_cache
from bengal.rendering.engines.errors import TemplateError, TemplateNotFoundError
from bengal.themes.utils import DEFAULT_THEME_PATH, THEMES_ROOT

if TYPE_CHECKING:
    from bengal.core import Site
    from bengal.rendering.template_profiler import TemplateProfiler


class KidaTemplateEngine:
    """Bengal integration for Kida template engine.

    Implements TemplateEngineProtocol for seamless integration
    with Bengal's rendering pipeline.

    Example:
        # In bengal.yaml:
        site:
          template_engine: kida

    """

    NAME = "kida"
    __slots__ = (
        "_env",
        "_menu_dict_cache",
        "_profile",
        "_profiler",
        "site",
        "template_dirs",
    )

    def __init__(self, site: Site, *, profile: bool = False):
        """Initialize Kida engine for site.

        Args:
            site: Bengal Site instance
            profile: Enable template profiling for performance analysis

        Configuration (bengal.yaml):
            kida:
              bytecode_cache: true  # (default) Cache compiled templates to disk
              bytecode_cache: false # Disable bytecode caching

        Note:
            Strict mode (raising UndefinedError for undefined variables) is
            always enabled in Kida and cannot be disabled. This helps catch
            typos and missing context variables at render time.

        Bytecode Cache:
            When enabled, compiled template bytecode is persisted to
            `.bengal/cache/kida/` for near-instant cold-start loading.
            Provides 90%+ improvement in template loading times.
        """
        from bengal.rendering.template_profiler import TemplateProfiler, get_profiler
        from bengal.utils.observability.logger import get_logger

        logger = get_logger(__name__)

        self.site = site
        self.template_dirs = self._build_template_dirs()

        # Legacy dependency tracking removed — EffectTracer handles this now

        # Template profiling support
        self._profile = profile
        self._profiler: TemplateProfiler | None = None
        if profile:
            self._profiler = get_profiler() or TemplateProfiler()
            logger.debug("kida_template_profiling_enabled")

        # Get Kida-specific configuration
        kida_config = site.config.get("kida", {}) or {}

        # Configure bytecode cache for near-instant cold starts
        # Uses .bengal/cache/kida/ under site root for persistent caching
        bytecode_cache: BytecodeCache | bool | None = None
        if kida_config.get("bytecode_cache", True):  # Enabled by default
            cache_dir = site.root_path / ".bengal" / "cache" / "kida"
            bytecode_cache = BytecodeCache(cache_dir)

        # Fragment cache configuration
        # Larger cache for static site generation (many partials rendered repeatedly)
        fragment_cache_size = kida_config.get("fragment_cache_size", 2000)
        fragment_ttl = kida_config.get("fragment_ttl", 3600.0)  # 1 hour for SSG

        # Create Kida environment
        # Note: strict mode (UndefinedError for undefined vars) is always enabled
        self._env = Environment(
            loader=FileSystemLoader(self.template_dirs),
            autoescape=self._select_autoescape,
            auto_reload=site.config.get("development", {}).get("auto_reload", True),
            bytecode_cache=bytecode_cache,
            # Preserve AST for block metadata/dependency analysis (site-wide block caching)
            preserve_ast=True,
            # Fragment caching for {% cache "key" %}...{% end %} blocks
            fragment_cache_size=fragment_cache_size,
            fragment_ttl=fragment_ttl,
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
            except (ImportError, AttributeError, OSError):
                pass

            # Bundled theme directory
            bundled_theme_templates = THEMES_ROOT / theme_name / "templates"
            if bundled_theme_templates.exists():
                dirs.append(bundled_theme_templates)

        # Ensure default theme exists as ultimate fallback
        # (resolve_theme_chain filters out 'default' to avoid duplicates)
        default_templates = DEFAULT_THEME_PATH / "templates"
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
        1. Apply shared engine globals via get_engine_globals()
        2. Use register_all() with engine_type="kida" for filters and non-context functions
        3. Add engine-specific globals (url_for, get_menu, breadcrumbs)

        This uses the centralized context layer for consistent globals across engines.
        """
        # === Step 0: Apply shared engine globals ===
        # Single source of truth: site, config, theme, menus, bengal, versions, etc.
        from bengal.rendering.context import get_engine_globals

        self._env.globals.update(get_engine_globals(self.site))

        # === Step 1: Register all template functions with Kida adapter ===
        # This handles both non-context functions (icons, dates, strings, etc.)
        # and context-dependent functions (t, current_lang, tag_url, asset_url)
        # via the adapter layer
        from bengal.rendering.template_functions import register_all

        register_all(self._env, self.site, engine_type="kida")

        # === Step 2: Add filters from TemplateEngine mixins ===
        # These are added by Jinja's environment.py but not by register_all()
        try:
            from bengal.rendering.template_engine.url_helpers import filter_dateformat

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

        # === Step 3: Engine-specific globals (menu functions) ===
        self._menu_dict_cache: dict[str, list[dict]] = {}
        self._env.globals["get_menu"] = self._get_menu
        self._env.globals["get_menu_lang"] = self._get_menu_lang
        self._env.globals["url_for"] = self._url_for

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

    def invalidate_menu_cache(self) -> None:
        """
        Invalidate the menu dict cache.

        Call this after menus are rebuilt to ensure fresh dicts are generated.
        This ensures active menu states are correct for each page render.
        """
        self._menu_dict_cache.clear()

    def _url_for(self, page: Any) -> str:
        """Generate URL for a page with base URL support."""
        # If page has _path, use it to apply baseurl (for MockPage and similar)
        # Otherwise, use href property which should already include baseurl
        if hasattr(page, "_path") and page._path:
            from bengal.rendering.utils.url import apply_baseurl

            return apply_baseurl(page._path, self.site)
        from bengal.rendering.template_engine.url_helpers import href_for

        return href_for(page, self.site)

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
        # Invalidate menu cache to ensure fresh active states for each page
        self.invalidate_menu_cache()

        # Record template dependency for EffectTracer (via ContextVar)
        from bengal.effects.render_integration import record_extra_dependency, record_template_include

        record_template_include(name)
        template_path = self.get_template_path(name)
        if template_path:
            record_extra_dependency(template_path)
        # Track all templates in the inheritance chain (extends/includes)
        self._track_referenced_templates(name)

        try:
            template = self._env.get_template(name)

            # Get page-aware functions (t, current_lang, etc.)
            # Instead of mutating env.globals (not thread-safe), we pass them in context
            ctx = {"site": self.site, "config": self.site.config}
            # Use items() explicitly to trigger LazyPageContext evaluation.
            # dict.update(other_dict) may bypass __getitem__ via CPython optimization,
            # but items() always calls LazyPageContext.items() which evaluates lazy values.
            ctx.update(context.items())

            page = context.get("page")
            if hasattr(self._env, "_page_aware_factory"):
                page_functions = self._env._page_aware_factory(page)
                ctx.update(page_functions)

            # Cached blocks are automatically used by Template.render()
            # Profile template rendering if enabled
            if self._profiler:
                self._profiler.start_template(name)
                try:
                    result = template.render(ctx)
                finally:
                    self._profiler.end_template(name)
                return result
            return template.render(ctx)

        except KidaTemplateNotFoundError as e:
            raise TemplateNotFoundError(name, self.template_dirs) from e
        except KidaTemplateSyntaxError as e:
            raise BengalRenderingError(
                message=f"Template syntax error in '{name}': {e}",
                original_error=e,
            ) from e
        except TypeError as e:
            # Enhanced error message for "NoneType is not callable"
            error_str = str(e).lower()
            if (
                "'nonetype' object is not callable" in error_str
                or "nonetype object is not callable" in error_str
            ):
                # Try to identify what was being called
                import traceback

                tb = traceback.extract_tb(e.__traceback__)
                context_info = []
                for frame in reversed(tb):
                    if frame.line:
                        context_info.append(f"  at {frame.filename}:{frame.lineno}: {frame.line}")
                        if len(context_info) >= 3:
                            break

                context_str = (
                    "\n".join(context_info) if context_info else "  (no context available)"
                )
                raise BengalRenderingError(
                    message=(
                        f"Template '{name}': A function or filter is None (not callable).\n"
                        f"Call stack:\n{context_str}\n"
                        f"Check that all filters and template functions are properly registered."
                    ),
                    original_error=e,
                ) from e
            raise BengalRenderingError(
                message=f"Template render error in '{name}': {e}",
                original_error=e,
            ) from e
        except Exception as e:  # noqa: BLE001 — catch-all for arbitrary template/filter errors
            raise BengalRenderingError(
                message=f"Template render error in '{name}': {e}",
                original_error=e,
            ) from e

    def render_string(
        self,
        template: str,
        context: dict[str, Any],
        *,
        strict: bool = True,
    ) -> str:
        """Render a template string.

        Args:
            template: Template content as string
            context: Variables available to the template
            strict: If False, return empty string for undefined variables instead of raising

        Returns:
            Rendered HTML string
        """
        from kida.environment.exceptions import UndefinedError

        # Invalidate menu cache to ensure fresh active states
        self.invalidate_menu_cache()

        try:
            tmpl = self._env.from_string(template)

            # Get page-aware functions (t, current_lang, etc.)
            # Instead of mutating env.globals (not thread-safe), we pass them in context
            ctx = {"site": self.site, "config": self.site.config}
            # Use items() explicitly to trigger LazyPageContext evaluation.
            # dict.update(other_dict) may bypass __getitem__ via CPython optimization,
            # but items() always calls LazyPageContext.items() which evaluates lazy values.
            ctx.update(context.items())

            page = context.get("page")
            if hasattr(self._env, "_page_aware_factory"):
                page_functions = self._env._page_aware_factory(page)
                ctx.update(page_functions)

            return tmpl.render(ctx)

        except UndefinedError as e:
            # When strict=False, return empty string for undefined variables
            # This allows preprocessing to handle documentation examples gracefully
            if not strict:
                return ""
            raise BengalRenderingError(
                message=f"Template string render error: {e}",
                original_error=e,
            ) from e
        except Exception as e:  # noqa: BLE001 — catch-all for arbitrary template/filter errors
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
        except (KidaTemplateNotFoundError, OSError):
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

    def _track_referenced_templates(self, template_name: str) -> None:
        """Track all referenced templates (extends/includes/imports) as dependencies.

        Recursively walks the template tree to find all templates that could
        affect the output. Tracks:
        - Parent templates ({% extends %})
        - Included templates ({% include %})
        - Imported templates ({% import %}, {% from ... import %})

        Args:
            template_name: Name of template to analyze
        """
        from bengal.effects.render_integration import record_extra_dependency, record_template_include

        seen: set[str] = {template_name}
        to_process: list[str] = [template_name]

        while to_process:
            current_name = to_process.pop()

            try:
                template = self._env.get_template(current_name)
                ast = getattr(template, "_optimized_ast", None)
                if ast is None:
                    continue

                # Find all referenced templates in the AST
                referenced = self._extract_referenced_templates(ast)

                for ref_name in referenced:
                    if ref_name in seen:
                        continue
                    seen.add(ref_name)

                    # Record as dependency via EffectTracer
                    record_template_include(ref_name)
                    ref_path = self.get_template_path(ref_name)
                    if ref_path:
                        record_extra_dependency(ref_path)

                    # Queue for recursive processing (catches nested includes)
                    to_process.append(ref_name)

            except (AttributeError, TypeError, KeyError, OSError):
                # Template analysis is optional - don't fail the build
                continue

    def _extract_referenced_templates(self, ast: Any) -> set[str]:
        """Extract all referenced template names from an AST.

        Walks the AST to find Extends, Include, Import, and FromImport nodes
        and extracts their template names (if static strings).

        Args:
            ast: Parsed template AST

        Returns:
            Set of template names referenced by this template
        """
        referenced: set[str] = set()
        nodes_to_visit: list[Any] = [ast]

        while nodes_to_visit:
            node = nodes_to_visit.pop()
            if node is None:
                continue

            node_type = type(node).__name__

            # Check for template-referencing nodes
            if node_type in ("Extends", "Include", "Import", "FromImport"):
                template_expr = getattr(node, "template", None)
                if template_expr and type(template_expr).__name__ == "Const":
                    value = getattr(template_expr, "value", None)
                    if isinstance(value, str):
                        referenced.add(value)

            # Recurse into child nodes
            for attr in ("body", "else_", "empty", "cases", "default"):
                child = getattr(node, attr, None)
                if child is not None:
                    if isinstance(child, (list, tuple)):
                        nodes_to_visit.extend(child)
                    else:
                        nodes_to_visit.append(child)

            # Handle extends on Template node
            if node_type == "Template":
                extends = getattr(node, "extends", None)
                if extends:
                    nodes_to_visit.append(extends)

        return referenced

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
                # Determine error type from exception class name
                exc_name = type(e).__name__.lower()
                if "syntax" in exc_name:
                    error_type = "syntax"
                elif "undefined" in exc_name:
                    error_type = "undefined"
                elif "runtime" in exc_name:
                    error_type = "runtime"
                elif "notfound" in exc_name:
                    error_type = "not_found"
                else:
                    error_type = "other"
                errors.append(
                    TemplateError(
                        template=name,
                        message=str(e),
                        line=getattr(e, "lineno", None),
                        error_type=error_type,
                    )
                )

        return errors

    # =========================================================================
    # ENGINE CAPABILITIES
    # =========================================================================

    @property
    def capabilities(self) -> EngineCapability:
        """
        Return Kida engine capabilities.

        Kida supports all advanced features:
        - Block caching for efficient re-rendering
        - Block-level change detection for incremental builds
        - Template introspection for dependency analysis
        - Pipeline operators (|>) for functional transformations
        - Pattern matching (match/case) in templates
        """
        return (
            EngineCapability.BLOCK_CACHING
            | EngineCapability.BLOCK_LEVEL_DETECTION
            | EngineCapability.INTROSPECTION
            | EngineCapability.PIPELINE_OPERATORS
            | EngineCapability.PATTERN_MATCHING
        )

    def has_capability(self, cap: EngineCapability) -> bool:
        """Check if Kida has a specific capability."""
        return cap in self.capabilities

    # =========================================================================
    # TEMPLATE INTROSPECTION
    # =========================================================================

    def get_template_introspection(self, name: str) -> dict[str, Any] | None:
        """Get introspection metadata for a template.

        Returns analysis of template structure including:
        - blocks: Block metadata (dependencies, purity, cache scope)
        - extends: Parent template name (if any)
        - all_dependencies: All context paths the template accesses

        Args:
            name: Template identifier (e.g., "page.html")

        Returns:
            Dict with template metadata, or None if:
            - Template not found
            - AST was not preserved (preserve_ast=False)

        Example:
            >>> info = engine.get_template_introspection("page.html")
            >>> if info:
            ...     for block_name, meta in info["blocks"].items():
            ...         if meta.cache_scope == "site":
            ...             print(f"Block {block_name} is site-cacheable")
        """
        try:
            template = self._env.get_template(name)
            meta = template.template_metadata()
            if meta is None:
                return None

            return {
                "name": meta.name,
                "extends": meta.extends,
                "blocks": meta.blocks,
                "all_dependencies": meta.all_dependencies(),
            }
        except Exception:
            return None

    def get_cacheable_blocks(self, name: str) -> dict[str, str]:
        """Get blocks that can be cached and their cache scope.

        Convenience method for build optimization. Returns only blocks
        with determined cache scope (excludes "unknown").

        Args:
            name: Template identifier

        Returns:
            Dict of block_name → cache_scope ("site" or "page")

        Example:
            >>> cacheable = engine.get_cacheable_blocks("base.html")
            >>> # {'nav': 'site', 'footer': 'site', 'content': 'page'}
        """
        info = self.get_template_introspection(name)
        if not info:
            return {}

        return {
            block_name: meta.cache_scope
            for block_name, meta in info["blocks"].items()
            if meta.cache_scope in ("site", "page") and meta.is_pure == "pure"
        }

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

    def get_template_profile(self) -> dict[str, Any] | None:
        """Get template profiling report.

        Returns:
            Dictionary with timing statistics, or None if profiling disabled.
        """
        if self._profiler:
            return self._profiler.get_report()
        return None

    def clear_template_cache(self, names: list[str] | None = None) -> None:
        """Clear template cache for external invalidation.

        Called by TemplateChangeDetector when template files change to force
        cache invalidation without waiting for hash checks.

        Args:
            names: Optional list of template names to clear.
                   If None, clears all cached templates.

        Example:
            >>> engine.clear_template_cache()  # Clear all
            >>> engine.clear_template_cache(["base.html", "page.html"])  # Specific
        """
        if has_clear_template_cache(self._env):
            self._env.clear_template_cache(names)

    def precompile_templates(self, template_names: list[str] | None = None) -> int:
        """Pre-compile templates to warm the cache.

        Compiles templates ahead of rendering to avoid compile-on-demand
        overhead during the render phase. This is especially beneficial
        when using bytecode caching (templates are compiled and cached to disk).

        Args:
            template_names: Optional list of template names to precompile.
                           If None, precompiles all templates in template_dirs.

        Returns:
            Number of templates compiled

        Example:
            >>> # Precompile all templates at build start
            >>> count = engine.precompile_templates()
            >>> print(f"Precompiled {count} templates")
        """
        templates = template_names or self.list_templates()
        compiled = 0

        for name in templates:
            try:
                self._env.get_template(name)
                compiled += 1
            except Exception:
                # Skip templates that fail to compile
                # (will be caught later during rendering)
                pass

        return compiled

    def cache_info(self) -> dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dict with template, fragment, and bytecode cache stats

        Example:
            >>> info = engine.cache_info()
            >>> print(f"Template hits: {info['template']['hits']}")
            >>> print(f"Fragment hits: {info['fragment']['hits']}")
        """
        if hasattr(self._env, "cache_info"):
            return self._env.cache_info()
        return {}

    def _resolve_theme_chain(self, active_theme: str | None) -> list[str]:
        """Resolve theme inheritance chain."""
        from bengal.rendering.template_engine.environment import resolve_theme_chain

        return resolve_theme_chain(active_theme, self.site)


# Verify protocol compliance
def _check_protocol() -> None:
    """Verify KidaTemplateEngine implements TemplateEngineProtocol."""
    import typing

    if typing.TYPE_CHECKING:
        _: TemplateEngineProtocol = KidaTemplateEngine(...)  # type: ignore
