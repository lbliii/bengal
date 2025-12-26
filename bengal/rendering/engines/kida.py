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

from bengal.rendering.engines.errors import TemplateError, TemplateNotFoundError
from bengal.rendering.engines.protocol import TemplateEngineProtocol
from bengal.rendering.errors import TemplateRenderError
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

    __slots__ = ("site", "template_dirs", "_env")

    def __init__(self, site: Site, *, profile: bool = False):
        """Initialize Kida engine for site.

        Args:
            site: Bengal Site instance
            profile: Enable template profiling (not yet implemented)
        """
        self.site = site
        self.template_dirs = self._build_template_dirs()

        # Create Kida environment
        self._env = Environment(
            loader=FileSystemLoader(self.template_dirs),
            autoescape=self._select_autoescape,
            auto_reload=site.config.get("development", {}).get("auto_reload", True),
        )

        # Register Bengal-specific globals
        self._register_globals()

        # Register Bengal-specific filters
        self._register_filters()

    def _build_template_dirs(self) -> list[Path]:
        """Build ordered list of template search directories."""
        dirs = []

        # Theme templates first
        theme_path = self.site.theme_path
        if theme_path and (theme_path / "templates").is_dir():
            dirs.append(theme_path / "templates")

        # Site-level templates override
        site_templates = self.site.root_path / "templates"
        if site_templates.is_dir():
            dirs.insert(0, site_templates)

        return dirs

    def _select_autoescape(self, name: str | None) -> bool:
        """Determine autoescape based on file extension."""
        if name is None:
            return True
        return name.endswith((".html", ".htm", ".xml"))

    def _register_globals(self) -> None:
        """Register Bengal-specific template globals."""
        self._env.globals["site"] = self.site
        self._env.globals["config"] = self.site.config

    def _register_filters(self) -> None:
        """Register Bengal-specific filters."""
        # Import Bengal's template functions
        try:
            from bengal.rendering.template_functions import (
                dates,
                strings,
                urls,
            )

            # Date filters
            self._env.add_filter("date", dates.format_date)
            self._env.add_filter("datetime", dates.format_datetime)
            self._env.add_filter("time", dates.format_time)

            # String filters
            self._env.add_filter("slugify", strings.slugify)
            self._env.add_filter("truncate_words", strings.truncate_words)

            # URL filters
            self._env.add_filter("url", urls.url)
            self._env.add_filter("absolute_url", urls.absolute_url)
        except ImportError:
            # Template functions not available
            pass

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
            raise TemplateNotFoundError(str(e)) from e
        except KidaTemplateSyntaxError as e:
            raise TemplateRenderError(
                message=str(e),
                template_name=name,
            ) from e
        except Exception as e:
            raise TemplateRenderError(
                message=str(e),
                template_name=name,
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
            raise TemplateRenderError(
                message=str(e),
                template_name="<string>",
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


# Verify protocol compliance
def _check_protocol() -> None:
    """Verify KidaTemplateEngine implements TemplateEngineProtocol."""
    import typing

    if typing.TYPE_CHECKING:
        _: TemplateEngineProtocol = KidaTemplateEngine(...)  # type: ignore
