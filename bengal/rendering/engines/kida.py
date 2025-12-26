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

    __slots__ = ("site", "template_dirs", "_env", "_dependency_tracker")

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

        # Register Bengal-specific globals
        self._register_globals()

        # Register Bengal-specific filters
        self._register_filters()

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

    def _register_globals(self) -> None:
        """Register Bengal-specific template globals."""
        self._env.globals["site"] = self.site
        self._env.globals["config"] = self.site.config

        # Register global functions
        try:
            from bengal.rendering.template_functions import (
                get_page,
                i18n,
                icons,
                navigation,
                seo,
                theme,
                urls,
            )

            # URL helpers
            base_url = self.site.config.get("baseurl", "")
            self._env.globals["url"] = lambda u: urls.url(u, base_url)
            self._env.globals["absolute_url"] = lambda u: urls.absolute_url(u, base_url)

            # Page lookup
            self._env.globals["get_page"] = lambda path: get_page.get_page(path, self.site)

            # Navigation
            self._env.globals["breadcrumbs"] = lambda page: navigation.breadcrumbs.get_breadcrumbs(
                page, self.site
            )

            # Theme
            self._env.globals["asset_url"] = lambda path: theme.asset_url(path, self.site)
            self._env.globals["theme"] = self.site.theme_config

            # Icons
            self._env.globals["icon"] = lambda name, **kw: icons.icon(name, self.site, **kw)

            # i18n
            self._env.globals["t"] = lambda key, **kw: i18n._translate(key, self.site, **kw)
            self._env.globals["current_lang"] = lambda: i18n._current_lang(self.site)

            # SEO
            self._env.globals["og_image"] = lambda img, page=None: seo.og_image(
                img, page, self.site
            )
            self._env.globals["canonical_url"] = lambda path: seo.canonical_url(path, self.site)

        except ImportError:
            # Template functions not available
            pass
        except AttributeError:
            # Individual function not found
            pass

    def _register_filters(self) -> None:
        """Register Bengal-specific filters (Jinja2-compatible)."""
        # Use Jinja2's filter registration pattern with Kida's environment
        # The FilterRegistry class provides dict-like .update() support
        try:
            from bengal.rendering.template_functions import (
                advanced_collections,
                advanced_strings,
                collections,
                data,
                dates,
                files,
                math_functions,
                strings,
                urls,
            )

            # Phase 1: Essential string filters
            self._env.filters.update(
                {
                    "truncatewords": strings.truncatewords,
                    "truncatewords_html": strings.truncatewords_html,
                    "slugify": strings.slugify,
                    "markdownify": strings.markdownify,
                    "strip_html": strings.strip_html,
                    "truncate_chars": strings.truncate_chars,
                    "replace_regex": strings.replace_regex,
                    "pluralize": strings.pluralize,
                    "reading_time": strings.reading_time,
                    "word_count": strings.word_count,
                    "wordcount": strings.word_count,
                    "excerpt": strings.excerpt,
                    "strip_whitespace": strings.strip_whitespace,
                    "get": strings.dict_get,
                    "first_sentence": strings.first_sentence,
                    "filesize": strings.filesize,
                }
            )

            # Phase 1: Collection filters
            self._env.filters.update(
                {
                    "sort_by": collections.sort_by,
                    "group_by": collections.group_by,
                    "where": collections.where,
                    "where_exp": collections.where_exp,
                    "pluck": collections.pluck,
                    "flatten": collections.flatten,
                    "uniq": collections.uniq,
                    "shuffle_list": collections.shuffle_list,
                    "slice_list": collections.slice_list,
                    "concat": collections.concat,
                    "zip_lists": collections.zip_lists,
                    "dict_merge": collections.dict_merge,
                }
            )

            # Phase 1: Math filters
            self._env.filters.update(
                {
                    "percentage": math_functions.percentage,
                    "floor": math_functions.floor,
                    "ceil": math_functions.ceil,
                    "add": math_functions.add,
                }
            )

            # Phase 1: Date filters
            self._env.filters.update(
                {
                    "date": dates.format_date,
                    "datetime": dates.format_datetime,
                    "time": dates.format_time,
                    "dateformat": dates.format_date,
                    "time_ago": dates.time_ago,
                    "iso_date": dates.iso_date,
                }
            )

            # Phase 1: URL filters
            base_url = self.site.config.get("baseurl", "")
            self._env.filters.update(
                {
                    "url": lambda u: urls.url(u, base_url),
                    "absolute_url": lambda u: urls.absolute_url(u, base_url),
                    "relative_url": urls.relative_url,
                }
            )

            # Phase 2: Data filters
            self._env.filters.update(
                {
                    "jsonify": data.jsonify,
                    "merge": data.merge,
                    "has_key": data.has_key,
                    "get_nested": data.get_nested,
                    "keys": data.keys_filter,
                    "values": data.values_filter,
                    "items": data.items_filter,
                }
            )

            # Phase 2: Advanced string filters
            self._env.filters.update(
                {
                    "regex_replace": advanced_strings.regex_replace,
                    "regex_match": advanced_strings.regex_match,
                    "regex_findall": advanced_strings.regex_findall,
                    "titleize": advanced_strings.titleize,
                    "parameterize": advanced_strings.parameterize,
                    "camelize": advanced_strings.camelize,
                    "underscore": advanced_strings.underscore,
                    "dasherize": advanced_strings.dasherize,
                    "humanize": advanced_strings.humanize,
                    "pluralize_word": advanced_strings.pluralize_word,
                    "singularize": advanced_strings.singularize,
                    "ordinalize": advanced_strings.ordinalize,
                    "number_to_words": advanced_strings.number_to_words,
                }
            )

            # Phase 2: Advanced collection filters
            self._env.filters.update(
                {
                    "chunk": advanced_collections.chunk,
                    "paginate": advanced_collections.paginate,
                    "tree": advanced_collections.tree,
                    "find": advanced_collections.find,
                    "reject_where": advanced_collections.reject_where,
                    "compact": advanced_collections.compact,
                    "sample": advanced_collections.sample,
                    "partition": advanced_collections.partition,
                    "index_by": advanced_collections.index_by,
                    "count_by": advanced_collections.count_by,
                    "frequencies": advanced_collections.frequencies,
                }
            )

            # Phase 2: File filters
            self._env.filters.update(
                {
                    "extension": files.extension,
                    "basename": files.basename,
                    "dirname": files.dirname,
                }
            )

        except ImportError:
            # Template functions not available - use defaults only
            pass
        except Exception:
            # Individual filter import failed - continue with what we have
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
