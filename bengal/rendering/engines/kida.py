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

from threading import Lock
from typing import TYPE_CHECKING, Any

from kida import Environment
from kida.bytecode_cache import BytecodeCache
from kida.environment import (
    ChoiceLoader,
    FileSystemLoader,
)
from kida.environment import (
    TemplateNotFoundError as KidaTemplateNotFoundError,
)
from kida.environment import (
    TemplateSyntaxError as KidaTemplateSyntaxError,
)

from bengal.errors import BengalRenderingError
from bengal.errors.codes import ErrorCode
from bengal.protocols import EngineCapability, TemplateEngineProtocol
from bengal.protocols.capabilities import has_clear_template_cache
from bengal.rendering.context.lazy import LazyPageContext
from bengal.rendering.engines.errors import TemplateError, TemplateNotFoundError
from bengal.themes.utils import DEFAULT_THEME_PATH, THEMES_ROOT

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from bengal.core import Site
    from bengal.rendering.template_profiler import TemplateProfiler

# Filters whose output depends only on their inputs (no site/page/I/O/time).
# Kida's partial evaluator can fold these at compile time when all arguments
# are constants from static_context.
_PURE_FILTERS: set[str] = {
    # strings.py
    "truncatewords",
    "truncatewords_html",
    "slugify",
    "markdownify",
    "strip_html",
    "plainify",
    "truncate_chars",
    "replace_regex",
    "pluralize",
    "reading_time",
    "word_count",
    "wordcount",
    "excerpt",
    "excerpt_for_card",
    "card_excerpt",
    "card_excerpt_html",
    "strip_whitespace",
    "get",
    "first_sentence",
    "filesize",
    "split",
    "base64_encode",
    "base64_decode",
    # advanced_strings.py
    "camelize",
    "underscore",
    "titleize",
    "wrap",
    "indent",
    "softwrap_ident",
    "last_segment",
    "regex_search",
    "regex_findall",
    "trim_prefix",
    "trim_suffix",
    "has_prefix",
    "has_suffix",
    "contains",
    "to_sentence",
    # math_functions.py
    "percentage",
    "times",
    "divided_by",
    "ceil",
    "floor",
    "round",
    "coerce_int",
    # collections.py
    "where",
    "where_not",
    "group_by",
    "sort_by",
    "limit",
    "offset",
    "uniq",
    "flatten",
    "first",
    "last",
    "reverse",
    "union",
    "intersect",
    "complement",
    "group_by_year",
    "group_by_month",
    "archive_years",
    # advanced_collections.py
    "chunk",
    # dates.py (deterministic subset — excludes time_ago/days_ago/months_ago)
    "date_iso",
    "date_rfc822",
    "month_name",
    "humanize_days",
    "date_add",
    "date_diff",
    # data.py
    "jsonify",
    "merge",
    "has_key",
    "get_nested",
    "keys",
    "values",
    "items",
    # content.py
    "safe_html",
    "html_escape",
    "html_unescape",
    "nl2br",
    "smartquotes",
    "emojify",
    "extract_content",
    "demote_headings",
    "prefix_heading_ids",
    "urlize",
    "highlight",
    # seo.py
    "meta_description",
    "meta_keywords",
    # pagination_helpers.py
    "paginate",
    # images.py
    "image_srcset",
    "image_alt",
    # urls.py (deterministic subset — excludes absolute_url/href)
    "url_encode",
    "url_decode",
    "url_parse",
    "url_param",
    "url_query",
    # debug.py
    "debug",
    "typeof",
    "inspect",
    # autodoc.py
    "get_params",
    "param_count",
    "return_type",
    "get_return_info",
    "get_element_stats",
    "children_by_type",
    "public_only",
    "private_only",
    "is_autodoc_page",
    "members",
    "commands",
    "options",
    "member_view",
    "option_view",
    "command_view",
    # openapi.py
    "highlight_path_params",
    "method_color_class",
    "status_code_class",
    "endpoints",
    "schemas",
    # changelog.py
    "releases",
    "release_view",
    # taxonomies.py (deterministic subset)
    "has_tag",
    "tag_accent_index",
    # blog.py (deterministic subset)
    "posts",
    "post_view",
    "featured_posts",
}


class _ProviderEnvShim:
    """Adapter that lets library register_filters() calls set env.filters/globals.

    Detects collisions with Bengal built-ins and other providers.
    Implements the minimal template_filter()/template_global() decorator API
    that libraries like chirp_ui expect (Flask-style registration).
    """

    __slots__ = (
        "_builtin_filters",
        "_builtin_globals",
        "_env",
        "_filter_owners",
        "_global_owners",
        "_package",
    )

    def __init__(
        self,
        env: Environment,
        builtin_filters: frozenset[str],
        builtin_globals: frozenset[str],
        filter_owners: dict[str, str],
        global_owners: dict[str, str],
        package: str,
    ) -> None:
        self._env = env
        self._builtin_filters = builtin_filters
        self._builtin_globals = builtin_globals
        self._filter_owners = filter_owners
        self._global_owners = global_owners
        self._package = package

    def _check_collision(self, name: str, kind: str) -> None:
        from bengal.errors.context import ErrorDebugPayload
        from bengal.errors.exceptions import BengalConfigError

        builtins = self._builtin_filters if kind == "filter" else self._builtin_globals
        if name in builtins:
            msg = (
                f"Theme library '{self._package}': {kind} '{name}' collides with a Bengal built-in"
            )
            raise BengalConfigError(
                msg,
                code=ErrorCode.C003,
                suggestion=(
                    f"Rename the {kind} in '{self._package}' or remove the library "
                    "from the theme's libraries list."
                ),
                debug_payload=ErrorDebugPayload(
                    processing_item=f"theme-library:{self._package}",
                    processing_type="theme_library",
                    config_keys_accessed=["theme.libraries"],
                    relevant_config={
                        "library": self._package,
                        "kind": kind,
                        "name": name,
                        "collision": "bengal_builtin",
                    },
                    files_to_check=["themes/*/theme.toml", self._package],
                    grep_patterns=[f"libraries = .*{self._package}", f"{kind}.*{name}"],
                ),
            )
        owners = self._filter_owners if kind == "filter" else self._global_owners
        if name in owners:
            msg = (
                f"Theme library '{self._package}': {kind} '{name}' "
                f"collides with library '{owners[name]}'"
            )
            raise BengalConfigError(
                msg,
                code=ErrorCode.C003,
                suggestion=(
                    f"Rename the {kind} in either '{self._package}' or '{owners[name]}', "
                    "or remove one library from the theme's libraries list."
                ),
                debug_payload=ErrorDebugPayload(
                    processing_item=f"theme-library:{self._package}",
                    processing_type="theme_library",
                    config_keys_accessed=["theme.libraries"],
                    relevant_config={
                        "library": self._package,
                        "existing_library": owners[name],
                        "kind": kind,
                        "name": name,
                        "collision": "provider",
                    },
                    files_to_check=["themes/*/theme.toml", self._package, owners[name]],
                    grep_patterns=[f"libraries = .*{self._package}", f"{kind}.*{name}"],
                ),
            )

    def template_filter(self, name: str | None = None):
        """Decorator-style filter registration (Flask-compatible)."""

        def decorator(fn):
            filter_name = name or fn.__name__
            self._check_collision(filter_name, "filter")
            self._env.filters[filter_name] = fn
            self._filter_owners[filter_name] = self._package
            return fn

        return decorator

    def template_global(self, name: str | None = None):
        """Decorator-style global registration (Flask-compatible)."""

        def decorator(fn):
            global_name = name or fn.__name__
            self._check_collision(global_name, "global")
            self._env.globals[global_name] = fn
            self._global_owners[global_name] = self._package
            return fn

        return decorator

    def add_template_filter(self, fn, name: str | None = None) -> None:
        """Direct filter registration (non-decorator style)."""
        filter_name = name or fn.__name__
        self._check_collision(filter_name, "filter")
        self._env.filters[filter_name] = fn
        self._filter_owners[filter_name] = self._package

    def add_template_global(self, fn, name: str | None = None) -> None:
        """Direct global registration (non-decorator style)."""
        global_name = name or fn.__name__
        self._check_collision(global_name, "global")
        self._env.globals[global_name] = fn
        self._global_owners[global_name] = self._package


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
        "_directive_template_renderer",
        "_env",
        "_menu_dict_cache",
        "_profile",
        "_profiler",
        "_providers",
        "_template_dependency_cache",
        "_template_dependency_cache_lock",
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
              fragment_cache_size: 2000  # {% cache %} block entries (default)
              fragment_ttl: 3600.0  # Fragment TTL seconds (default 1h for SSG)
              max_extends_depth: 50  # (optional) {% extends %} chain limit
              max_include_depth: 50  # (optional) {% include %}/{% embed %} limit
              template_aliases:  # (optional) @alias/ template include roots
                components: ui/components

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
        self._providers = self._resolve_providers()
        self._template_dependency_cache: dict[str, tuple[str, ...]] = {}
        self._template_dependency_cache_lock = Lock()

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

        # Resource limits (kida 0.2.4+)
        # Optional overrides for sites with deep theme/inheritance chains
        env_kwargs: dict[str, Any] = {}
        if "max_extends_depth" in kida_config:
            env_kwargs["max_extends_depth"] = kida_config["max_extends_depth"]
        if "max_include_depth" in kida_config:
            env_kwargs["max_include_depth"] = kida_config["max_include_depth"]
        if "template_aliases" in kida_config:
            env_kwargs["template_aliases"] = kida_config["template_aliases"]

        # Compile-time optimization (kida 0.4.1+)
        # Pass site config as static_context so the partial evaluator can fold
        # constant expressions like {% if config.fonts %} at compile time.
        # The evaluator eliminates dead branches and resolves scalar constants,
        # reducing work on every page render.
        #
        # Opt-in until Bengal's default theme and docs benchmarks prove there is
        # no semantic drift across the full template surface.
        static_context: dict[str, Any] | None = None
        if kida_config.get("static_context", False):
            static_context = {"config": site.config}

        # Create Kida environment
        # Note: strict mode (UndefinedError for undefined vars) is always enabled
        self._env = Environment(
            loader=self._build_loader(),
            autoescape=self._select_autoescape,
            auto_reload=site.config.get("development", {}).get("auto_reload", True),
            bytecode_cache=bytecode_cache,
            # Preserve AST for block metadata/dependency analysis (site-wide block caching)
            preserve_ast=True,
            # Fragment caching for {% cache "key" %}...{% end %} blocks
            fragment_cache_size=fragment_cache_size,
            fragment_ttl=fragment_ttl,
            # Compile-time optimization (kida 0.4.1+)
            static_context=static_context,
            pure_filters=_PURE_FILTERS,
            **env_kwargs,
        )
        from bengal.rendering.fragment_cache import AssetManifestFragmentCache

        self._env._fragment_cache = AssetManifestFragmentCache(
            self._env._fragment_cache,
            self.site,
        )

        # Register Bengal-specific globals and filters
        # Uses register_all() which works because Kida has same interface as Jinja2
        self._register_bengal_template_functions()

        # Expose directive template renderer on site for use by _render_directive()
        self._directive_template_renderer = self._create_directive_template_renderer()
        site._directive_template_renderer = self._directive_template_renderer

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
            except ImportError, AttributeError, OSError:
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

    def _resolve_providers(self) -> tuple:
        """Resolve theme library providers from the theme chain."""
        from bengal.core.theme.providers import resolve_theme_providers
        from bengal.rendering.template_engine.environment import resolve_theme_chain

        theme_chain = resolve_theme_chain(self.site.theme, self.site)
        return resolve_theme_providers(self.site.root_path, theme_chain)

    def _build_loader(self) -> FileSystemLoader | ChoiceLoader:
        """Build the template loader, incorporating provider loaders if present.

        When no providers declare loaders, returns a plain FileSystemLoader
        (zero overhead). When providers are present, returns a ChoiceLoader:
            1. FileSystemLoader(template_dirs)  — site + theme chain + default
            2. *provider.loader for each provider  — library templates
        """
        fs_loader = FileSystemLoader(self.template_dirs)
        provider_loaders = [p.loader for p in self._providers if p.loader is not None]
        if not provider_loaders:
            return fs_loader
        return ChoiceLoader([fs_loader, *provider_loaders])

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
        # Pass active plugin registry for plugin-provided template extensions
        from bengal.plugins import get_active_registry
        from bengal.rendering.template_functions import register_all

        register_all(
            self._env,
            self.site,
            engine_type="kida",
            plugin_registry=get_active_registry(),
        )

        # === Step 2: Add filters from TemplateEngine mixins ===
        # These are added by Jinja's environment.py but not by register_all()
        try:
            from bengal.rendering.template_engine.url_helpers import filter_dateformat

            # dateformat filter (from url_helpers, not dates module)
            self._env.filters["dateformat"] = filter_dateformat
            self._env.filters["date"] = filter_dateformat

            # breadcrumbs
            from bengal.rendering.template_functions.navigation import breadcrumbs

            self._env.globals["breadcrumbs"] = lambda page: breadcrumbs.get_breadcrumbs(page)
        except ImportError:
            pass

        # === Step 3: Engine-specific globals (menu functions) ===
        self._menu_dict_cache: dict[str, list[dict]] = {}
        self._env.globals["get_menu"] = self._get_menu
        self._env.globals["get_menu_lang"] = self._get_menu_lang
        self._env.globals["url_for"] = self._url_for
        self._env.globals["library_asset_tags"] = self._library_asset_tags
        self._env.globals["library_runtime"] = self._library_runtime

        # === Step 4: Theme library provider filters/globals ===
        self._register_provider_extensions()

    def _library_asset_tags(self):
        """Render tags for assets declared by active theme libraries."""
        from bengal.rendering.library_assets import render_library_asset_tags

        return render_library_asset_tags(self._providers, self.site)

    def _library_runtime(self) -> tuple[str, ...]:
        """Return runtime metadata declared by active theme libraries."""
        from bengal.rendering.library_assets import library_runtime_metadata

        return library_runtime_metadata(self._providers)

    def _register_provider_extensions(self) -> None:
        """Register filters/globals from theme library providers.

        Captures Bengal's built-in names before registration so collisions
        can be detected. Provider names that collide with built-ins or
        other providers produce a BengalConfigError.
        """
        if not self._providers:
            return

        from bengal.errors.exceptions import BengalConfigError

        builtin_filters = frozenset(self._env.filters.keys())
        builtin_globals = frozenset(self._env.globals.keys())
        filter_owners: dict[str, str] = {}  # filter name -> owning package
        global_owners: dict[str, str] = {}  # global name -> owning package

        for provider in self._providers:
            if provider.register_env is None:
                continue

            shim = _ProviderEnvShim(
                self._env,
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

    def _create_directive_template_renderer(
        self,
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
        env = self._env

        def render_directive_template(name: str, context: dict[str, Any]) -> str | None:
            template_name = f"directives/{name}.html"
            try:
                template = env.get_template(template_name)
            except KidaTemplateNotFoundError:
                return None
            return template.render(context)

        return render_directive_template

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
        Page-specific active state is computed in templates from the current
        page URL so cached menu dictionaries can be reused across renders.
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
        # Record template dependency for EffectTracer (via ContextVar)
        from bengal.effects.render_integration import (
            record_extra_dependency,
            record_template_include,
        )

        record_template_include(name)
        template_path = self.get_template_path(name)
        if template_path:
            record_extra_dependency(template_path)
        # Track all templates in the inheritance chain (extends/includes)
        self._track_referenced_templates(name)

        try:
            template = self._env.get_template(name)

            # Get page-aware functions (t, current_lang, etc.)
            # Instead of mutating env.globals (not thread-safe), we pass them in context.
            # Preserve LazyValue entries so Kida only evaluates fields the template reads.
            ctx = LazyPageContext()
            ctx.update(self._env.globals)
            ctx.update({"site": self.site, "config": self.site.config})
            ctx.update(context)

            page = context.get("page")
            if hasattr(self._env, "_page_aware_factory"):
                page_functions = self._env._page_aware_factory(page)
                ctx.update(page_functions)

            # Cached blocks are automatically used by Template.render()
            # Profile template rendering if enabled
            if self._profiler:
                self._profiler.start_template(name)
                try:
                    result = self._render_kida_template(template, ctx)
                finally:
                    self._profiler.end_template(name)
                return result
            return self._render_kida_template(template, ctx)

        except KidaTemplateNotFoundError as e:
            raise TemplateNotFoundError(name, self.template_dirs) from e
        except KidaTemplateSyntaxError as e:
            # Use format_compact() for a structured message when available
            if hasattr(e, "format_compact"):
                msg = f"Template syntax error in '{name}':\n{e.format_compact()}"
            else:
                msg = f"Template syntax error in '{name}': {e}"
            raise BengalRenderingError(
                message=msg,
                code=ErrorCode.R002,
                original_error=e,
                file_path=getattr(e, "filename", None),
                line_number=getattr(e, "lineno", None),
            ) from e
        except TypeError as e:
            # Enhanced error messages for common template callable errors
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
                    code=ErrorCode.R008,
                    original_error=e,
                ) from e
            if "_undefined" in error_str and "not callable" in error_str:
                raise BengalRenderingError(
                    message=(
                        f"Template '{name}': A macro from {{% from X import y %}} resolved to "
                        "Undefined. Check that the imported template defines the macro. "
                        "If this occurs during parallel builds, try --no-parallel."
                    ),
                    code=ErrorCode.R006,
                    original_error=e,
                    suggestion="Check that the imported template defines the macro. "
                    "If this occurs during parallel builds, try --no-parallel.",
                ) from e
            raise BengalRenderingError(
                message=f"Template render error in '{name}': {e}",
                code=ErrorCode.R010,
                original_error=e,
                file_path=getattr(e, "filename", None),
                line_number=getattr(e, "lineno", None),
            ) from e
        except Exception as e:
            # Use format_compact() for Kida errors that reach the generic handler
            if hasattr(e, "format_compact"):
                msg = f"Template render error in '{name}':\n{e.format_compact()}"
            else:
                msg = f"Template render error in '{name}': {e}"
            raise BengalRenderingError(
                message=msg,
                code=ErrorCode.R010,
                original_error=e,
                file_path=getattr(e, "filename", None),
                line_number=getattr(e, "lineno", None),
                suggestion=getattr(e, "hint", None) or getattr(e, "suggestion", None),
            ) from e

    def _render_kida_template(self, template: Any, context: LazyPageContext) -> str:
        """Render a compiled Kida template without materializing lazy values."""
        render_func = getattr(template, "_render_func", None)
        render_scaffold = getattr(template, "_render_scaffold", None)
        check_output_size = getattr(template, "_check_output_size", None)
        if render_func is None or render_scaffold is None or check_output_size is None:
            return template.render(context)

        with render_scaffold(
            (context,),
            {},
            "render",
            use_cached_blocks=True,
        ) as (_eager_context, _render_context, blocks_arg):
            return check_output_size(render_func(context, blocks_arg))

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
        import warnings

        from kida.environment.exceptions import UndefinedError

        try:
            # Dynamic strings bypass bytecode cache intentionally — suppress the
            # kida 0.4.0 UserWarning about from_string() without name=.
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="from_string.*bypasses bytecode cache")
                tmpl = self._env.from_string(template)

            # Get page-aware functions (t, current_lang, etc.)
            # Instead of mutating env.globals (not thread-safe), we pass them in context.
            ctx = LazyPageContext()
            ctx.update(self._env.globals)
            ctx.update({"site": self.site, "config": self.site.config})
            ctx.update(context)

            page = context.get("page")
            if hasattr(self._env, "_page_aware_factory"):
                page_functions = self._env._page_aware_factory(page)
                ctx.update(page_functions)

            return self._render_kida_template(tmpl, ctx)

        except UndefinedError as e:
            # When strict=False, return empty string for undefined variables
            # This allows preprocessing to handle documentation examples gracefully
            if not strict:
                return ""
            if hasattr(e, "format_compact"):
                msg = f"Template string render error:\n{e.format_compact()}"
            else:
                msg = f"Template string render error: {e}"
            raise BengalRenderingError(
                message=msg,
                code=ErrorCode.R003,
                original_error=e,
                file_path=getattr(e, "filename", None),
                line_number=getattr(e, "lineno", None),
                suggestion=getattr(e, "hint", None) or getattr(e, "suggestion", None),
            ) from e
        except Exception as e:
            if hasattr(e, "format_compact"):
                msg = f"Template string render error:\n{e.format_compact()}"
            else:
                msg = f"Template string render error: {e}"
            raise BengalRenderingError(
                message=msg,
                code=ErrorCode.R010,
                original_error=e,
                file_path=getattr(e, "filename", None),
                line_number=getattr(e, "lineno", None),
                suggestion=getattr(e, "hint", None) or getattr(e, "suggestion", None),
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
        except KidaTemplateNotFoundError, OSError:
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
        from bengal.effects.render_integration import (
            record_extra_dependency,
            record_template_include,
        )

        referenced_templates = self._get_referenced_template_names(template_name)
        for ref_name in referenced_templates:
            record_template_include(ref_name)
            ref_path = self.get_template_path(ref_name)
            if ref_path:
                record_extra_dependency(ref_path)

    def _get_referenced_template_names(self, template_name: str) -> tuple[str, ...]:
        """Return transitive referenced template names, cached for this engine."""
        with self._template_dependency_cache_lock:
            cached = self._template_dependency_cache.get(template_name)
        if cached is not None:
            return cached

        referenced_templates = self._discover_referenced_template_names(template_name)
        with self._template_dependency_cache_lock:
            existing = self._template_dependency_cache.setdefault(
                template_name,
                referenced_templates,
            )
        return existing

    def _discover_referenced_template_names(self, template_name: str) -> tuple[str, ...]:
        """Discover transitive referenced templates by walking Kida dependencies."""
        seen: set[str] = {template_name}
        to_process: list[str] = [template_name]
        ordered: list[str] = []

        while to_process:
            current_name = to_process.pop()

            try:
                template = self._env.get_template(current_name)

                # Prefer Kida's dependencies() API when available (cleaner, public API)
                referenced: set[str] = set()
                if hasattr(template, "dependencies"):
                    deps = template.dependencies()
                    for key in ("extends", "includes", "embeds", "imports"):
                        referenced.update(deps.get(key, []))

                # Fall back to AST walk if dependencies() returned nothing (e.g. bytecode cache)
                if not referenced:
                    ast = getattr(template, "_optimized_ast", None)
                    if ast is not None:
                        referenced = self._extract_referenced_templates(ast)

                for ref_name in referenced:
                    if ref_name in seen:
                        continue
                    seen.add(ref_name)
                    ordered.append(ref_name)

                    # Queue for recursive processing (catches nested includes)
                    to_process.append(ref_name)

            except AttributeError, TypeError, KeyError, OSError:
                # Template analysis is optional - don't fail the build
                continue

        return tuple(ordered)

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

    def validate_security(
        self,
        patterns: list[str] | None = None,
    ) -> list[TemplateError]:
        """Run Kida static escape and privacy analysis for templates.

        This intentionally reports only warning/error findings, not every
        escaped output site, so authors get actionable trust-boundary feedback
        without a dump of normal autoescape facts.
        """
        from fnmatch import fnmatch

        from kida.analysis import audit_escaping, lint_privacy

        findings: list[TemplateError] = []

        for name in self.list_templates():
            if patterns and not any(fnmatch(name, p) for p in patterns):
                continue

            try:
                template = self._env.get_template(name)
            except KidaTemplateSyntaxError, KidaTemplateNotFoundError:
                # Syntax validation reports compile failures. Static analysis
                # only runs on templates Kida can parse.
                continue
            except Exception as e:
                findings.append(
                    TemplateError(
                        template=name,
                        message=f"Kida static analysis failed: {e}",
                        error_type="kida_static_analysis",
                        severity="error",
                        original_exception=e,
                    )
                )
                continue

            raw_findings = [
                *audit_escaping(template, include_output_sites=False),
                *lint_privacy(template),
            ]
            for finding in raw_findings:
                severity = getattr(finding, "severity", "warning")
                if severity == "info":
                    continue
                findings.append(
                    TemplateError(
                        template=getattr(finding, "template_name", name) or name,
                        message=getattr(finding, "message", str(finding)),
                        line=getattr(finding, "lineno", None),
                        column=getattr(finding, "col_offset", None),
                        error_type=getattr(finding, "kind", "kida_static_analysis"),
                        severity=severity,
                        suggestion=getattr(finding, "suggestion", None),
                        diagnostic_code=getattr(finding, "code", None),
                    )
                )

        return findings

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
            except Exception:  # noqa: S110
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
