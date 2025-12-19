"""
Jinja2 implementation of the standardized TemplateEngine protocol.

This wraps the existing Bengal template engine functionality while
conforming to the new standardized protocol interface.

Example:
    from bengal.rendering.engines import create_engine

    engine = create_engine(site)  # Returns JinjaTemplateEngine
    html = engine.render_template("page.html", {"page": page})
"""

from __future__ import annotations

import contextlib
import threading
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import TemplateNotFound, TemplateSyntaxError

from bengal.assets.manifest import AssetManifestEntry
from bengal.rendering.engines.errors import (
    TemplateError,
    TemplateNotFoundError,
)
from bengal.rendering.template_engine.asset_url import AssetURLMixin
from bengal.rendering.template_engine.environment import (
    create_jinja_environment,
    read_theme_extends,
    resolve_theme_chain,
)
from bengal.rendering.template_engine.manifest import ManifestHelpersMixin
from bengal.rendering.template_engine.menu import MenuHelpersMixin
from bengal.rendering.template_profiler import (
    ProfiledTemplate,
    TemplateProfiler,
    get_profiler,
)
from bengal.utils.logger import get_logger, truncate_error

if TYPE_CHECKING:
    from bengal.core import Site

logger = get_logger(__name__)


class JinjaTemplateEngine(MenuHelpersMixin, ManifestHelpersMixin, AssetURLMixin):
    """
    Jinja2 implementation of the TemplateEngineProtocol.

    Implements ALL required protocol methods with Jinja2-specific behavior.
    Includes mixins for Bengal-specific functionality (menus, assets).

    This is the default template engine for Bengal and provides full
    backward compatibility with existing Jinja2 templates.

    Attributes:
        site: Site instance with theme and configuration
        template_dirs: List of template directories (populated during init)
        env: Jinja2 Environment instance
    """

    def __init__(self, site: Site, *, profile: bool = False) -> None:
        """
        Initialize Jinja2 engine.

        Args:
            site: Site instance
            profile: Enable template profiling
        """
        logger.debug("initializing_jinja_engine", theme=site.theme, root_path=str(site.root_path))

        self.site = site
        self.template_dirs: list[Path] = []

        # Profiling
        self._profile: bool = profile
        self._profiler: TemplateProfiler | None = None
        if profile:
            self._profiler = get_profiler() or TemplateProfiler()
            logger.debug("template_profiling_enabled")

        # Create Jinja2 environment
        self.env, self.template_dirs = create_jinja_environment(site, self, profile)

        # Dependency tracking (injected by RenderingPipeline)
        self._dependency_tracker = None

        # Initialize mixins
        self._init_asset_manifest()
        self._init_menu_cache()
        self._init_template_cache()

    def _init_asset_manifest(self) -> None:
        """Initialize asset manifest caching."""
        self._asset_manifest_path = self.site.output_dir / "asset-manifest.json"
        self._asset_manifest_mtime: float | None = None
        self._asset_manifest_cache: dict[str, AssetManifestEntry] = {}
        self._asset_manifest_fallbacks: set[str] = set()
        self._asset_manifest_present = self._asset_manifest_path.exists()
        self._asset_manifest_loaded = False
        self._fingerprinted_asset_cache: dict[str, str | None] = {}

        # Thread-safe warnings
        try:
            if not hasattr(self.site, "_asset_manifest_fallbacks_global"):
                self.site._asset_manifest_fallbacks_global = set()  # type: ignore[attr-defined]
            if not hasattr(self.site, "_asset_manifest_fallbacks_lock"):
                self.site._asset_manifest_fallbacks_lock = threading.Lock()  # type: ignore[attr-defined]
        except Exception:
            pass

    def _init_menu_cache(self) -> None:
        """Initialize menu caching."""
        self._menu_dict_cache: dict[str, list[dict[str, Any]]] = {}

    def _init_template_cache(self) -> None:
        """Initialize template path caching."""
        dev_mode = self.site.config.get("dev_server", False)
        self._template_path_cache_enabled = not dev_mode
        self._template_path_cache: dict[str, Path | None] = {}
        self._referenced_template_cache: dict[str, set[str]] = {}
        self._referenced_template_paths_cache: dict[str, tuple[Path, ...]] = {}

    # =========================================================================
    # PROTOCOL IMPLEMENTATION (required methods)
    # =========================================================================

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """
        Render a named template with the given context.

        Args:
            name: Template identifier (e.g., "blog/single.html")
            context: Variables available to the template

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        logger.debug("render_template", template=name, context_keys=list(context.keys()))

        # Track template dependency
        if self._dependency_tracker:
            template_path = self.get_template_path(name)
            if template_path:
                self._dependency_tracker.track_template(template_path)
                logger.debug("tracked_template_dependency", template=name, path=str(template_path))
            self._track_referenced_templates(name)

        # Inject standard context
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)

        # Invalidate menu cache for fresh active states
        self.invalidate_menu_cache()

        try:
            template = self.env.get_template(name)

            if self._profiler:
                result = ProfiledTemplate(template, self._profiler).render(**context)
            else:
                result = template.render(**context)

            logger.debug("template_rendered", template=name, output_size=len(result))
            return result

        except TemplateNotFound as e:
            raise TemplateNotFoundError(name, self.template_dirs) from e
        except Exception as e:
            logger.error(
                "template_render_failed",
                template=name,
                error_type=type(e).__name__,
                error=truncate_error(e, 500),
                context_keys=list(context.keys()),
            )
            raise

    def render_string(self, template: str, context: dict[str, Any]) -> str:
        """
        Render a template string with the given context.

        Args:
            template: Template content as string
            context: Variables available to the template

        Returns:
            Rendered HTML string
        """
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)
        self.invalidate_menu_cache()

        return self.env.from_string(template).render(**context)

    def template_exists(self, name: str) -> bool:
        """
        Check if a template exists.

        Args:
            name: Template identifier

        Returns:
            True if template can be loaded, False otherwise
        """
        try:
            self.env.get_template(name)
            return True
        except TemplateNotFound:
            return False

    def get_template_path(self, name: str) -> Path | None:
        """
        Resolve a template name to its filesystem path.

        Args:
            name: Template identifier

        Returns:
            Absolute path to template file, or None if not found
        """
        if self._template_path_cache_enabled and name in self._template_path_cache:
            return self._template_path_cache[name]

        found: Path | None = None
        for template_dir in self.template_dirs:
            path = template_dir / name
            if path.exists():
                logger.debug(
                    "template_found",
                    template=name,
                    path=str(path),
                    dir=str(template_dir),
                )
                found = path
                break

        if self._template_path_cache_enabled:
            self._template_path_cache[name] = found
        return found

    def list_templates(self) -> list[str]:
        """
        List all available template names.

        Returns:
            Sorted list of template names (relative to template_dirs)
        """
        return sorted(self.env.list_templates())

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        """
        Validate all templates for syntax errors.

        Args:
            patterns: Optional glob patterns to filter (e.g., ["*.html"])
                      If None, validates all templates.

        Returns:
            List of TemplateError for any invalid templates.
            Empty list if all templates are valid.
        """
        errors: list[TemplateError] = []
        validated: set[str] = set()
        patterns = patterns or ["*.html", "*.xml"]

        for template_dir in self.template_dirs:
            if not template_dir.exists():
                continue

            for file in template_dir.rglob("*"):
                if not file.is_file():
                    continue

                try:
                    name = str(file.relative_to(template_dir))
                except ValueError:
                    continue

                if name in validated:
                    continue

                if not any(fnmatch(name, p) or fnmatch(file.name, p) for p in patterns):
                    continue

                validated.add(name)

                try:
                    self.env.get_template(name)
                except TemplateSyntaxError as e:
                    errors.append(
                        TemplateError(
                            template=name,
                            line=e.lineno,
                            message=str(e),
                            path=file,
                        )
                    )
                except Exception:
                    pass  # Skip non-syntax errors

        logger.info(
            "template_validation_complete",
            validated=len(validated),
            errors=len(errors),
        )

        return errors

    # =========================================================================
    # BACKWARD COMPATIBILITY (legacy method names)
    # =========================================================================

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Legacy method: use render_template() instead.

        Provided for backward compatibility during migration.
        """
        return self.render_template(template_name, context)

    def validate_templates(self, include_patterns: list[str] | None = None) -> list[Any]:
        """
        Legacy method: use validate() instead.

        Provided for backward compatibility during migration.
        """
        from bengal.rendering.errors import TemplateRenderError as LegacyError

        errors = self.validate(include_patterns)
        # Convert to legacy error format
        legacy_errors: list[Any] = []
        for err in errors:
            legacy_errors.append(
                LegacyError(
                    template_name=err.template,
                    line_number=err.line,
                    message=err.message,
                    source_path=err.path,
                    template_engine=self,
                )
            )
        return legacy_errors

    def _find_template_path(self, template_name: str) -> Path | None:
        """
        Legacy method: use get_template_path() instead.

        Provided for backward compatibility during migration.
        """
        return self.get_template_path(template_name)

    # =========================================================================
    # JINJA-SPECIFIC HELPERS (not part of protocol)
    # =========================================================================

    def get_template_profile(self) -> dict[str, Any] | None:
        """
        Get template profiling report.

        Returns:
            Dictionary with template and function timing statistics,
            or None if profiling is not enabled.
        """
        if self._profiler:
            return self._profiler.get_report()
        return None

    def _track_referenced_templates(self, template_name: str) -> None:
        """
        Track referenced templates (extends/include/import) as dependencies.
        """
        if not self._dependency_tracker:
            return

        cached_paths = self._referenced_template_paths_cache.get(template_name)
        if cached_paths is not None:
            for ref_path in cached_paths:
                with contextlib.suppress(Exception):
                    self._dependency_tracker.track_partial(ref_path)
            return

        # Resolve direct references
        referenced = self._referenced_template_cache.get(template_name)
        if referenced is None:
            referenced = set()
            try:
                from jinja2 import meta

                source, _filename, _uptodate = self.env.loader.get_source(self.env, template_name)
                ast = self.env.parse(source)
                for ref in meta.find_referenced_templates(ast) or []:
                    if isinstance(ref, str):
                        referenced.add(ref)
            except Exception:
                referenced = set()
            self._referenced_template_cache[template_name] = referenced

        # Expand transitively
        stack = list(referenced)
        seen: set[str] = set()
        resolved_paths: list[Path] = []

        while stack:
            ref_name = stack.pop()
            if ref_name in seen:
                continue
            seen.add(ref_name)

            ref_path = self.get_template_path(ref_name)
            if ref_path:
                resolved_paths.append(ref_path)

            if ref_name not in self._referenced_template_cache:
                try:
                    from jinja2 import meta

                    src, _filename, _uptodate = self.env.loader.get_source(self.env, ref_name)
                    ast = self.env.parse(src)
                    self._referenced_template_cache[ref_name] = {
                        r for r in (meta.find_referenced_templates(ast) or []) if isinstance(r, str)
                    }
                except Exception:
                    self._referenced_template_cache[ref_name] = set()

            stack.extend(self._referenced_template_cache.get(ref_name, set()))

        self._referenced_template_paths_cache[template_name] = tuple(resolved_paths)
        for ref_path in resolved_paths:
            with contextlib.suppress(Exception):
                self._dependency_tracker.track_partial(ref_path)

    def _resolve_theme_chain(self, active_theme: str | None) -> list[str]:
        """
        Resolve theme inheritance chain.

        Compatibility method for code that accesses this directly.
        """
        return resolve_theme_chain(active_theme, self.site)

    def _read_theme_extends(self, theme_name: str) -> str | None:
        """
        Read theme.toml for 'extends' value.

        Compatibility method for code that accesses this directly.
        """
        return read_theme_extends(theme_name, self.site)

    # URL helpers (exposed to templates via mixins)
    def _url_for(self, page: Any) -> str:
        """Generate URL for a page with base URL support."""
        from bengal.rendering.template_engine.url_helpers import url_for

        return url_for(page, self.site)

    def _with_baseurl(self, path: str) -> str:
        """Apply base URL prefix to a path."""
        from bengal.rendering.template_engine.url_helpers import with_baseurl

        return with_baseurl(path, self.site)
