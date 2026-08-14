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

Environment setup, render, dependency tracking, validation, and
introspection live in sibling modules. This module remains the public
facade so ``from bengal.rendering.engines.kida import KidaTemplateEngine``
is unchanged. Strict undefined is always on and cannot be disabled.
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

from bengal.rendering.engines.kida.dependencies import (
    discover_referenced_template_names,
    extract_referenced_templates,
    get_referenced_template_names,
    track_referenced_templates,
)
from bengal.rendering.engines.kida.environment import (
    build_loader,
    build_template_dirs,
    create_directive_template_renderer,
    library_asset_tags,
    library_runtime,
    register_bengal_template_functions,
    register_provider_extensions,
    resolve_providers,
    resolve_theme_chain,
)
from bengal.rendering.engines.kida.introspection import (
    cache_info,
    capabilities,
    clear_template_cache,
    get_cacheable_blocks,
    get_template_introspection,
    get_template_profile,
    has_capability,
    precompile_templates,
)
from bengal.rendering.engines.kida.provider_shim import _ProviderEnvShim
from bengal.rendering.engines.kida.pure_filters import _PURE_FILTERS
from bengal.rendering.engines.kida.render import (
    get_menu,
    get_menu_lang,
    get_template_path,
    invalidate_menu_cache,
    render_kida_template,
    render_string,
    render_template,
    template_exists,
    url_for,
)
from bengal.rendering.engines.kida.validation import (
    list_templates,
    validate,
    validate_security,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from bengal.core import Site
    from bengal.protocols import EngineCapability, TemplateEngineProtocol
    from bengal.rendering.context.lazy import LazyPageContext
    from bengal.rendering.engines.errors import TemplateError
    from bengal.rendering.template_profiler import TemplateProfiler

__all__ = [
    "_PURE_FILTERS",
    "BytecodeCache",
    "ChoiceLoader",
    "Environment",
    "FileSystemLoader",
    "KidaTemplateEngine",
    "_ProviderEnvShim",
]


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
        return build_template_dirs(self)

    def _resolve_providers(self) -> tuple:
        return resolve_providers(self)

    def _build_loader(self):
        return build_loader(self)

    def _select_autoescape(self, name: str | None) -> bool:
        """Determine autoescape based on file extension."""
        if name is None:
            return True
        return name.endswith((".html", ".htm", ".xml"))

    def _register_bengal_template_functions(self) -> None:
        register_bengal_template_functions(self)

    def _library_asset_tags(self):
        return library_asset_tags(self)

    def _library_runtime(self) -> tuple[str, ...]:
        return library_runtime(self)

    def _register_provider_extensions(self) -> None:
        register_provider_extensions(self)

    def _create_directive_template_renderer(
        self,
    ) -> Callable[[str, dict[str, Any]], str | None]:
        return create_directive_template_renderer(self)

    def _get_menu(self, menu_name: str = "main") -> list[dict]:
        return get_menu(self, menu_name)

    def _get_menu_lang(self, menu_name: str = "main", lang: str = "") -> list[dict]:
        return get_menu_lang(self, menu_name, lang)

    def invalidate_menu_cache(self) -> None:
        invalidate_menu_cache(self)

    def _url_for(
        self,
        target: Any,
        page: Any = None,
        version: str | None = "current",
        baseurl: bool = True,
    ) -> str:
        return url_for(self, target, page, version, baseurl)

    def render_template(
        self,
        name: str,
        context: dict[str, Any],
    ) -> str:
        return render_template(self, name, context)

    def _render_kida_template(self, template: Any, context: LazyPageContext) -> str:
        return render_kida_template(self, template, context)

    def render_string(
        self,
        template: str,
        context: dict[str, Any],
        *,
        strict: bool = True,
    ) -> str:
        return render_string(self, template, context, strict=strict)

    def template_exists(self, name: str) -> bool:
        return template_exists(self, name)

    def get_template_path(self, name: str) -> Path | None:
        return get_template_path(self, name)

    def _track_referenced_templates(self, template_name: str) -> None:
        track_referenced_templates(self, template_name)

    def _get_referenced_template_names(self, template_name: str) -> tuple[str, ...]:
        return get_referenced_template_names(self, template_name)

    def _discover_referenced_template_names(self, template_name: str) -> tuple[str, ...]:
        return discover_referenced_template_names(self, template_name)

    def _extract_referenced_templates(self, ast: Any) -> set[str]:
        return extract_referenced_templates(self, ast)

    def list_templates(self) -> list[str]:
        return list_templates(self)

    def validate(
        self,
        patterns: list[str] | None = None,
    ) -> list[TemplateError]:
        return validate(self, patterns)

    def validate_security(
        self,
        patterns: list[str] | None = None,
    ) -> list[TemplateError]:
        return validate_security(self, patterns)

    @property
    def capabilities(self) -> EngineCapability:
        return capabilities(self)

    def has_capability(self, cap: EngineCapability) -> bool:
        return has_capability(self, cap)

    def get_template_introspection(self, name: str) -> dict[str, Any] | None:
        return get_template_introspection(self, name)

    def get_cacheable_blocks(self, name: str) -> dict[str, str]:
        return get_cacheable_blocks(self, name)

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
        return get_template_profile(self)

    def clear_template_cache(self, names: list[str] | None = None) -> None:
        clear_template_cache(self, names)

    def precompile_templates(self, template_names: list[str] | None = None) -> int:
        return precompile_templates(self, template_names)

    def cache_info(self) -> dict[str, Any]:
        return cache_info(self)

    def _resolve_theme_chain(self, active_theme: str | None) -> list[str]:
        return resolve_theme_chain(self, active_theme)


def _check_protocol() -> None:
    """Verify KidaTemplateEngine implements TemplateEngineProtocol."""
    import typing

    if typing.TYPE_CHECKING:
        _: TemplateEngineProtocol = KidaTemplateEngine(...)  # type: ignore
