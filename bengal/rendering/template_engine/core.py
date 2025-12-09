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
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.assets.manifest import AssetManifestEntry
from bengal.rendering.template_engine.asset_url import AssetURLMixin
from bengal.rendering.template_engine.environment import (
    create_jinja_environment,
    read_theme_extends,
    resolve_theme_chain,
)
from bengal.rendering.template_engine.manifest import ManifestHelpersMixin
from bengal.rendering.template_engine.menu import MenuHelpersMixin
from bengal.rendering.template_engine.url_helpers import url_for, with_baseurl
from bengal.rendering.template_profiler import (
    ProfiledTemplate,
    TemplateProfiler,
    get_profiler,
)
from bengal.utils.logger import get_logger, truncate_error

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class TemplateEngine(MenuHelpersMixin, ManifestHelpersMixin, AssetURLMixin):
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
          `output/.bengal-cache/templates` using a stable filename pattern.
        - Strict mode and auto reload: `strict_mode` enables `StrictUndefined`;
          `dev_server` enables `auto_reload` for faster iteration.

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
        self.template_dirs: list[Path] = []

        # Template profiling support
        self._profile_templates = profile_templates
        self._profiler: TemplateProfiler | None = None
        if profile_templates:
            self._profiler = get_profiler() or TemplateProfiler()
            logger.debug("template_profiling_enabled")

        # Create Jinja2 environment
        self.env, self.template_dirs = create_jinja_environment(site, self, profile_templates)

        # Dependency tracking (set by RenderingPipeline)
        self._dependency_tracker = None

        # Asset manifest handling
        self._asset_manifest_path = self.site.output_dir / "asset-manifest.json"
        self._asset_manifest_mtime: float | None = None
        self._asset_manifest_cache: dict[str, AssetManifestEntry] = {}
        self._asset_manifest_fallbacks: set[str] = set()

        # Menu dict cache
        self._menu_dict_cache: dict[str, list[dict[str, Any]]] = {}

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

        # Invalidate menu cache to ensure fresh active states for this page
        self.invalidate_menu_cache()

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

        # Invalidate menu cache
        self.invalidate_menu_cache()

        template = self.env.from_string(template_string)
        return template.render(**context)

    def _url_for(self, page: Any) -> str:
        """
        Generate URL for a page with base URL support.

        Args:
            page: Page object

        Returns:
            URL path with base URL prefix if configured
        """
        return url_for(page, self.site)

    def _with_baseurl(self, path: str) -> str:
        """
        Apply base URL prefix to a path.

        Args:
            path: Relative path starting with '/'

        Returns:
            Path with base URL prefix
        """
        return with_baseurl(path, self.site)

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
        return None

    def _resolve_theme_chain(self, active_theme: str | None) -> list[str]:
        """
        Resolve theme inheritance chain starting from the active theme.

        Compatibility method for tests. Delegates to resolve_theme_chain function.

        Args:
            active_theme: Active theme name

        Returns:
            List of theme names in inheritance order
        """
        return resolve_theme_chain(active_theme, self.site)

    def _read_theme_extends(self, theme_name: str) -> str | None:
        """
        Read theme.toml for 'extends' value.

        Compatibility method for tests. Delegates to read_theme_extends function.

        Args:
            theme_name: Theme name to look up

        Returns:
            Parent theme name if extends is set, None otherwise
        """
        return read_theme_extends(theme_name, self.site)
