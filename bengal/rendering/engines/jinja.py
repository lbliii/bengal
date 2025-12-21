"""
Jinja2 template engine implementation.

This is the canonical template engine implementation for Bengal.
All template rendering goes through this class.

Example:
    from bengal.rendering.engines import create_engine

    engine = create_engine(site)
    html = engine.render_template("page.html", {"page": page})
"""

from __future__ import annotations

import contextlib
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import TemplateSyntaxError

from bengal.assets.manifest import AssetManifestEntry
from bengal.rendering.engines.errors import TemplateError
from bengal.rendering.template_engine.asset_url import AssetURLMixin
from bengal.rendering.template_engine.environment import (
    create_jinja_environment,
    read_theme_extends,
    resolve_theme_chain,
)
from bengal.rendering.template_engine.manifest import ManifestHelpersMixin
from bengal.rendering.template_engine.menu import MenuHelpersMixin
from bengal.rendering.template_engine.url_helpers import href_for, with_baseurl
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
    Jinja2 template engine for rendering pages.

    Provides Jinja2 template rendering with theme inheritance, template function
    registration, asset manifest access, and optional template profiling.

    Attributes:
        site: Site instance with theme and configuration
        template_dirs: List of template directories (populated during init)
        env: Jinja2 Environment instance

    Example:
        engine = JinjaTemplateEngine(site, profile=True)
        html = engine.render_template("page.html", {"page": page})
    """

    def __init__(self, site: Site, *, profile: bool = False) -> None:
        """
        Initialize the Jinja2 template engine.

        Args:
            site: Site instance
            profile: Enable template profiling for performance analysis
        """
        logger.debug(
            "initializing_template_engine", theme=site.theme, root_path=str(site.root_path)
        )

        self.site = site
        self.template_dirs: list[Path] = []

        # Template profiling support
        self._profile = profile
        self._profiler: TemplateProfiler | None = None
        if profile:
            self._profiler = get_profiler() or TemplateProfiler()
            logger.debug("template_profiling_enabled")

        # Create Jinja2 environment
        self.env, self.template_dirs = create_jinja_environment(site, self, profile)

        # Dependency tracking (set by RenderingPipeline)
        self._dependency_tracker = None

        # Asset manifest handling
        self._asset_manifest_path = self.site.output_dir / "asset-manifest.json"
        self._asset_manifest_mtime: float | None = None
        self._asset_manifest_cache: dict[str, AssetManifestEntry] = {}
        self._asset_manifest_fallbacks: set[str] = set()
        self._asset_manifest_present: bool = self._asset_manifest_path.exists()
        self._asset_manifest_loaded: bool = False
        self._fingerprinted_asset_cache: dict[str, str | None] = {}

        # Thread-safe warnings - fields are pre-initialized in Site.__post_init__()
        # No setup needed here, just use the formalized Site attributes directly

        # Menu dict cache
        self._menu_dict_cache: dict[str, list[dict[str, Any]]] = {}

        # Template caches
        self._referenced_template_cache: dict[str, set[str]] = {}
        self._referenced_template_paths_cache: dict[str, tuple[Path, ...]] = {}
        self._template_path_cache_enabled: bool = not bool(
            self.site.dev_mode if isinstance(self.site.config, dict) else False
        )
        self._template_path_cache: dict[str, Path | None] = {}

    # =========================================================================
    # PROTOCOL METHODS (public API)
    # =========================================================================

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            name: Name of the template file
            context: Template context variables

        Returns:
            Rendered HTML string
        """
        logger.debug("rendering_template", template=name, context_keys=list(context.keys()))

        # Track template dependency
        if self._dependency_tracker:
            template_path = self.get_template_path(name)
            if template_path:
                self._dependency_tracker.track_template(template_path)
                logger.debug("tracked_template_dependency", template=name, path=str(template_path))
            self._track_referenced_templates(name)

        # Add site to context
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)

        # Invalidate menu cache to ensure fresh active states
        self.invalidate_menu_cache()

        try:
            template = self.env.get_template(name)

            if self._profiler:
                profiled_template = ProfiledTemplate(template, self._profiler)
                result = profiled_template.render(**context)
            else:
                result = template.render(**context)

            logger.debug("template_rendered", template=name, output_size=len(result))
            return result

        except Exception as e:
            logger.error(
                "template_render_failed",
                template=name,
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
            Rendered HTML string
        """
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)
        self.invalidate_menu_cache()

        template = self.env.from_string(template_string)
        return template.render(**context)

    def template_exists(self, name: str) -> bool:
        """
        Check if a template exists.

        Args:
            name: Template identifier

        Returns:
            True if template can be loaded, False otherwise
        """
        from jinja2 import TemplateNotFound

        try:
            self.env.get_template(name)
            return True
        except TemplateNotFound:
            return False

    def get_template_path(self, name: str) -> Path | None:
        """
        Find the full path to a template file.

        Args:
            name: Name of the template

        Returns:
            Full path to template file, or None if not found
        """
        if self._template_path_cache_enabled and name in self._template_path_cache:
            return self._template_path_cache[name]

        found: Path | None = None
        for template_dir in self.template_dirs:
            template_path = template_dir / name
            if template_path.exists():
                logger.debug(
                    "template_found",
                    template=name,
                    path=str(template_path),
                    dir=str(template_dir),
                )
                found = template_path
                break

        if self._template_path_cache_enabled:
            self._template_path_cache[name] = found
        return found

    def list_templates(self) -> list[str]:
        """
        List all available template names.

        Returns:
            Sorted list of template names
        """
        return sorted(self.env.list_templates())

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        """
        Validate syntax of all templates.

        Args:
            patterns: Optional glob patterns to limit validation
                      (e.g., ["*.html"]). If None, validates all templates.

        Returns:
            List of TemplateError for any invalid templates.
        """
        errors: list[TemplateError] = []
        validated_names: set[str] = set()
        patterns = patterns or ["*.html", "*.xml"]

        for template_dir in self.template_dirs:
            if not template_dir.exists():
                continue

            for template_file in template_dir.rglob("*"):
                if not template_file.is_file():
                    continue

                try:
                    rel_name = str(template_file.relative_to(template_dir))
                except ValueError:
                    continue

                if rel_name in validated_names:
                    continue

                matches_pattern = any(
                    fnmatch(rel_name, pattern) or fnmatch(template_file.name, pattern)
                    for pattern in patterns
                )
                if not matches_pattern:
                    continue

                validated_names.add(rel_name)

                try:
                    self.env.get_template(rel_name)
                    logger.debug("template_validated", template=rel_name, dir=str(template_dir))
                except TemplateSyntaxError as e:
                    logger.warning(
                        "template_syntax_error",
                        template=rel_name,
                        error=str(e),
                        line=getattr(e, "lineno", None),
                    )
                    errors.append(
                        TemplateError(
                            template=rel_name,
                            line=e.lineno,
                            message=str(e),
                            path=template_file,
                            original_exception=e,
                        )
                    )
                except Exception:
                    pass  # Skip non-syntax errors

        logger.info(
            "template_validation_complete",
            validated=len(validated_names),
            errors=len(errors),
        )

        return errors

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with the given context."""
        return self.render_template(template_name, context)

    def _find_template_path(self, template_name: str) -> Path | None:
        """Find the path to a template file."""
        return self.get_template_path(template_name)

    def validate_templates(self, include_patterns: list[str] | None = None) -> list[Any]:
        """
        Validate templates and return TemplateRenderError objects.
        """
        from bengal.rendering.errors import TemplateRenderError

        errors = self.validate(include_patterns)
        render_errors: list[Any] = []
        for err in errors:
            exc = err.original_exception
            if exc is None:
                exc = TemplateSyntaxError(err.message, lineno=err.line)
            render_error = TemplateRenderError.from_jinja2_error(exc, err.template, err.path, self)
            render_errors.append(render_error)
        return render_errors

    # =========================================================================
    # PROFILING
    # =========================================================================

    def get_template_profile(self) -> dict[str, Any] | None:
        """
        Get template profiling report.

        Returns:
            Dictionary with timing statistics, or None if profiling disabled.
        """
        if self._profiler:
            return self._profiler.get_report()
        return None

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _track_referenced_templates(self, template_name: str) -> None:
        """Track referenced templates (extends/include/import) as dependencies."""
        if not self._dependency_tracker:
            return

        cached_paths = self._referenced_template_paths_cache.get(template_name)
        if cached_paths is not None:
            for ref_path in cached_paths:
                with contextlib.suppress(Exception):
                    self._dependency_tracker.track_partial(ref_path)
            return

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
        """Resolve theme inheritance chain."""
        return resolve_theme_chain(active_theme, self.site)

    def _read_theme_extends(self, theme_name: str) -> str | None:
        """Read theme.toml for 'extends' value."""
        return read_theme_extends(theme_name, self.site)

    def _url_for(self, page: Any) -> str:
        """Generate URL for a page with base URL support."""
        # If page has _path, use it to apply baseurl (for MockPage and similar)
        # Otherwise, use href property which should already include baseurl
        if hasattr(page, "_path") and page._path:
            from bengal.rendering.template_engine.url_helpers import with_baseurl

            return with_baseurl(page._path, self.site)
        return href_for(page, self.site)

    def _with_baseurl(self, path: str) -> str:
        """Apply base URL prefix to a path."""
        return with_baseurl(path, self.site)
