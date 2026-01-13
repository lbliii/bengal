"""
Autodoc page rendering for the rendering pipeline.

This module handles rendering autodoc pages (API documentation) through
the site's template engine with full context. Extracted from core.py
per RFC: rfc-modularize-large-files.

Classes:
AutodocRenderer: Renders autodoc pages.
MetadataView: Dict wrapper for dotted attribute access.

"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Any

from kida.environment.exceptions import (
    TemplateNotFoundError,
    TemplateSyntaxError,
)
from bengal.rendering.pipeline.output import determine_output_path, format_html, write_output
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.protocols import TemplateEngine
    from kida.template import Template
    from bengal.rendering.renderer import Renderer

logger = get_logger(__name__)


class MetadataView(dict[str, Any]):
    """
    Dict that also supports attribute-style access (dotted) used by templates.
        
    """

    def __getattr__(self, item: str) -> Any:
        return self.get(item)


class AutodocRenderer:
    """
    Renders autodoc pages through the site's template engine.
    
    Handles both pre-rendered virtual pages and deferred autodoc pages
    that need full template context (menus, navigation, versioning).
    
    Attributes:
        site: Site instance for configuration
        template_engine: TemplateEngine for template rendering
        renderer: Renderer for fallback rendering
        dependency_tracker: Optional DependencyTracker for dependency tracking
        output_collector: Optional collector for hot reload tracking
    
    Example:
            >>> autodoc = AutodocRenderer(
            ...     site=site,
            ...     template_engine=engine,
            ...     renderer=renderer,
            ... )
            >>> autodoc.process_virtual_page(page)
        
    """

    def __init__(
        self,
        site: Any,
        template_engine: TemplateEngine,
        renderer: Renderer,
        dependency_tracker: Any = None,
        output_collector: Any = None,
        build_stats: Any = None,
    ):
        """
        Initialize the autodoc renderer.

        Args:
            site: Site instance for configuration
            template_engine: TemplateEngine for template rendering
            renderer: Renderer for fallback rendering
            dependency_tracker: Optional DependencyTracker for dependency tracking
            output_collector: Optional output collector for hot reload tracking
            build_stats: Optional BuildStats for error tracking and deduplication
        """
        self.site = site
        self.template_engine = template_engine
        self.renderer = renderer
        self.dependency_tracker = dependency_tracker
        self.output_collector = output_collector
        self.build_stats = build_stats

    def process_virtual_page(self, page: Page) -> None:
        """
        Process a virtual page with pre-rendered HTML content.

        Virtual pages (like autodoc pages) may have pre-rendered HTML that is either:
        1. A complete HTML page (extends base.html) - use directly
        2. A content fragment - wrap with template
        3. Deferred autodoc page - render now with full context (menus available)

        Complete pages start with <!DOCTYPE or <html and should not be wrapped.

        Args:
            page: Virtual page to process
        """
        if not page.output_path:
            page.output_path = determine_output_path(page, self.site)
        elif not page.output_path.is_absolute():
            page.output_path = self.site.output_dir / page.output_path

        # Check if this is a deferred autodoc page (render with full context)
        # Note: Section-index pages have autodoc_element=None but still need autodoc rendering
        if page.metadata.get("is_autodoc") and (
            page.metadata.get("autodoc_element") is not None
            or page.metadata.get("is_section_index")
        ):
            self._render_autodoc_page(page)
            write_output(page, self.site, self.dependency_tracker, collector=self.output_collector)
            logger.debug(
                "autodoc_page_rendered",
                source_path=str(page.source_path),
                output_path=str(page.output_path),
            )
            return

        page.parsed_ast = page._prerendered_html
        page.toc = ""

        # Check if pre-rendered HTML is already a complete page (extends base.html)
        # Complete pages should not be wrapped with another template
        prerendered = page._prerendered_html or ""
        prerendered_stripped = prerendered.strip()
        is_complete_page = (
            prerendered_stripped.startswith("<!DOCTYPE")
            or prerendered_stripped.startswith("<html")
            or prerendered_stripped.startswith("<!doctype")
        )

        if is_complete_page:
            # Use pre-rendered HTML directly (it's already a complete page)
            page.rendered_html = prerendered
            page.rendered_html = format_html(page.rendered_html, page, self.site)
        else:
            # Wrap content fragment with template
            html_content = self.renderer.render_content(page.parsed_ast or "")
            page.rendered_html = self.renderer.render_page(page, html_content)
            page.rendered_html = format_html(page.rendered_html, page, self.site)

        write_output(page, self.site, self.dependency_tracker, collector=self.output_collector)

        logger.debug(
            "virtual_page_rendered",
            source_path=str(page.source_path),
            output_path=str(page.output_path),
            is_complete_page=is_complete_page,
        )

    def _render_autodoc_page(self, page: Page) -> None:
        """
        Render an autodoc page using the site's template engine.

        NOTE: This is the ONLY rendering path for autodoc pages. The deferred
        rendering architecture ensures full template context (menus, active states,
        versioning) is available. See bengal/autodoc/README.md for details.

        This is called during the rendering phase (after menus are built),
        ensuring full template context is available for proper header/nav rendering.

        Args:
            page: Virtual page with autodoc_element in metadata
        """
        element = self._normalize_autodoc_element(page.metadata.get("autodoc_element"))
        template_name = page.metadata.get("_autodoc_template", "autodoc/python/module")

        # Mark active menu items for this page
        if hasattr(self.site, "mark_active_menu_items"):
            self.site.mark_active_menu_items(page)

        # Load template with proper error handling
        # Distinguishes between syntax errors (fail fast) and not-found errors (fallback)
        try:
            template = self._load_autodoc_template(template_name)
        except TemplateSyntaxError:
            # Syntax error = fail fast, no fallback
            # Error already logged by _load_autodoc_template
            raise
        except TemplateNotFoundError as e:
            # Template not found = use fallback rendering
            logger.warning(
                "autodoc_template_not_found",
                template=template_name,
                error=str(e),
            )
            # Tag page metadata to indicate fallback was used
            page.metadata["_autodoc_fallback_template"] = True
            page.metadata["_autodoc_fallback_reason"] = str(e)
            # Fall back to rendering as regular virtual page
            fallback_desc = getattr(element, "description", "") if element else ""
            page._prerendered_html = f"<h1>{page.title}</h1><p>{fallback_desc}</p>"
            page.parsed_ast = page._prerendered_html
            page.toc = ""
            page.rendered_html = self.renderer.render_page(page, page._prerendered_html)
            page.rendered_html = format_html(page.rendered_html, page, self.site)
            return

        # Render with full site context (same as regular pages)
        # Prefer explicit _section reference set by orchestrators; fall back to page.section
        section = getattr(page, "_section", None) or getattr(page, "section", None)

        try:
            # NOTE: We intentionally do NOT pass site= here. The template environment
            # already has site=SiteContext(site) as a global (set in environment.py).
            # Passing site= would shadow the global with a raw Site object, breaking
            # template access to site.logo_text, site.params, etc.
            html_content = template.render(
                element=element,
                page=page,
                section=section,  # Pass section explicitly for section index pages
                config=self._normalize_config(self.site.config),
                toc_items=getattr(page, "toc_items", []) or [],
                toc=getattr(page, "toc", "") or "",
                # Versioning context - autodoc pages are not versioned
                current_version=None,
                is_latest_version=True,
                # Page context expected by base.html templates
                params=page.metadata,  # Alias for metadata (required by base.html)
                metadata=page.metadata,
                content="",  # Autodoc content is rendered by element templates
                meta_desc=getattr(page, "meta_description", "") or "",
                reading_time=getattr(page, "reading_time", 0) or 0,
                excerpt=getattr(page, "excerpt", "") or "",
            )
        except Exception as e:  # Capture template errors with context
            # Create rich error object for better debugging
            from bengal.rendering.errors import (
                TemplateRenderError,
                display_template_error,
            )

            rich_error = TemplateRenderError.from_jinja2_error(
                e, template_name, page.source_path, self.template_engine
            )

            # Display the rich error (with deduplication to reduce noise if stats available)
            should_display = True
            if self.build_stats is not None:
                dedup = self.build_stats.get_error_deduplicator()
                should_display = dedup.should_display(rich_error)

            if should_display:
                display_template_error(rich_error)

            # Also log with structured data for machine parsing
            logger.error(
                "autodoc_template_render_failed",
                template=template_name,
                page=str(page.source_path),
                element=getattr(element, "qualified_name", getattr(element, "name", None)),
                element_type=getattr(element, "element_type", None),
                metadata=_safe_metadata_summary(getattr(element, "metadata", None)),
                error=str(e),
                error_type=rich_error.error_type,
                template_line=rich_error.template_context.line_number,
                source_line=rich_error.template_context.source_line,
            )
            # Fallback minimal HTML to keep build moving
            fallback_desc = getattr(element, "description", "") if element else ""
            page._prerendered_html = f"<h1>{page.title}</h1><p>{fallback_desc}</p>"
            page.parsed_ast = page._prerendered_html
            page.toc = ""
            page._toc_items_cache = []  # Set private cache, not read-only property
            page.rendered_html = self.renderer.render_page(page, page._prerendered_html)
            page.rendered_html = format_html(page.rendered_html, page, self.site)
            return

        page._prerendered_html = html_content
        page.parsed_ast = html_content
        page.toc = ""
        page._toc_items_cache = []  # Set private cache, not read-only property
        page.rendered_html = html_content
        page.rendered_html = format_html(page.rendered_html, page, self.site)

    def _load_autodoc_template(self, template_name: str) -> Template:
        """Load autodoc template with proper error handling.

        Distinguishes between:
        - TemplateSyntaxError: Parse errors (fail fast, don't try fallback)
        - TemplateNotFoundError: Template doesn't exist (try fallback names)

        Args:
            template_name: Base template name (e.g., "autodoc/python/module")

        Returns:
            Loaded Template object

        Raises:
            TemplateSyntaxError: Template has parse errors (fail fast)
            TemplateNotFoundError: Template doesn't exist after trying all names
        """
        names_to_try = [f"{template_name}.html", template_name]
        last_error: TemplateNotFoundError | None = None

        for name in names_to_try:
            try:
                return self.template_engine.env.get_template(name)
            except TemplateSyntaxError as e:
                # Syntax error = fail fast, don't try fallback
                logger.error(
                    "autodoc_template_syntax_error",
                    template=name,
                    error=str(e),
                    line=getattr(e, "lineno", None),
                    file=getattr(e, "filename", None),
                )
                raise  # Don't silently continue
            except TemplateNotFoundError as e:
                last_error = e
                continue  # Try next name

        # All names exhausted - actually not found
        if last_error:
            raise last_error
        raise TemplateNotFoundError(f"Template '{template_name}' not found")

    def _normalize_autodoc_element(self, element: Any) -> Any:
        """
        Ensure autodoc element metadata supports both dotted and mapping access.
        Also adds href property to elements and their children for URL access.

        Args:
            element: Autodoc element to normalize

        Returns:
            Normalized element with MetadataView wrappers
        """
        if element is None:
            return None

        # Determine doc_type from page metadata or template name
        doc_type = None
        autodoc_config: dict[str, Any] = {}
        if hasattr(self, "site") and self.site and hasattr(self.site, "config"):
            config = self.site.config
            if isinstance(config, dict):
                autodoc_config = config.get("autodoc", {})
                if "python" in autodoc_config:
                    doc_type = "python"
                elif "cli" in autodoc_config:
                    doc_type = "cli"
                elif "openapi" in autodoc_config:
                    doc_type = "openapi"

        def _compute_element_url(elem: Any, elem_type: str | None = None) -> str:
            """Compute URL for an element based on its qualified_name and type."""
            if not hasattr(elem, "qualified_name"):
                return "#"

            qualified_name = elem.qualified_name
            element_type = elem_type or getattr(elem, "element_type", None)

            # Get prefixes from config with safe defaults
            if doc_type == "python":
                prefix = autodoc_config.get("python", {}).get("output_prefix", "api")
                url_path = f"{prefix}/{qualified_name.replace('.', '/')}"
                return f"/{url_path}/"
            elif doc_type == "cli":
                prefix = autodoc_config.get("cli", {}).get("output_prefix", "cli")
                from bengal.autodoc.utils import resolve_cli_url_path

                cli_path = resolve_cli_url_path(qualified_name)
                url_path = f"{prefix}/{cli_path}" if cli_path else prefix
                return f"/{url_path}/"
            elif doc_type == "openapi":
                prefix = autodoc_config.get("openapi", {}).get("output_prefix", "api")
                if element_type == "openapi_endpoint":
                    from bengal.autodoc.utils import get_openapi_method, get_openapi_path

                    method = get_openapi_method(elem).lower()
                    path = get_openapi_path(elem).strip("/").replace("/", "-")
                    return f"/{prefix}/endpoints/{method}-{path}/"
                elif element_type == "openapi_schema":
                    return f"/{prefix}/schemas/{elem.name}/"
                else:
                    return f"/{prefix}/overview/"

            # Fallback: infer from element_type
            if element_type in ["command", "command-group"]:
                prefix = autodoc_config.get("cli", {}).get("output_prefix", "cli")
                from bengal.autodoc.utils import resolve_cli_url_path

                cli_path = resolve_cli_url_path(qualified_name)
                url_path = f"{prefix}/{cli_path}" if cli_path else prefix
                return f"/{url_path}/"
            elif element_type in ["class", "function", "method", "module"]:
                prefix = autodoc_config.get("python", {}).get("output_prefix", "api")
                url_path = f"{prefix}/{qualified_name.replace('.', '/')}"
                return f"/{url_path}/"

            # Ultimate fallback
            return "#"

        def _wrap_metadata(meta: Any) -> Any:
            if isinstance(meta, dict):
                return MetadataView(meta)
            # Fallback to empty metadata view for non-dict types (avoid str access errors)
            return MetadataView({})

        def _coerce(obj: Any) -> None:
            # Ensure children attribute exists and is a list (templates rely on it)
            # Use try/except to handle objects that don't support attribute assignment
            try:
                children = getattr(obj, "children", None)
                if children is None or not isinstance(children, list):
                    obj.children = []
            except (AttributeError, TypeError):
                # Object doesn't support attribute assignment - set in __dict__ if possible
                with suppress(AttributeError, TypeError):
                    obj.__dict__["children"] = []

            if hasattr(obj, "metadata"):
                meta_wrapped = _wrap_metadata(obj.metadata)
                obj.metadata = meta_wrapped
                meta = meta_wrapped if isinstance(meta_wrapped, dict) else None
                if meta is not None:
                    if not hasattr(obj, "description") and "description" in meta:
                        obj.description = meta.get("description", "")
                    if not hasattr(obj, "title") and "title" in meta:
                        obj.title = meta.get("title", "")
                    # Ensure is_dataclass key exists for templates
                    if "is_dataclass" not in meta:
                        meta["is_dataclass"] = False
                    # Common defaults to avoid Jinja UndefinedError
                    meta.setdefault("signature", "")
                    meta.setdefault("parameters", [])
                    meta.setdefault("properties", {})
                    meta.setdefault("required", [])
                    meta.setdefault("example", None)
                    # Normalize properties values to MetadataView so .type works
                    if isinstance(meta.get("properties"), dict):
                        normalized_props: dict[str, Any] = {}
                        for k, v in meta["properties"].items():
                            if isinstance(v, dict):
                                normalized_props[k] = MetadataView(v)
                            elif isinstance(v, str):
                                # If property schema is a string, treat it as a type name
                                normalized_props[k] = MetadataView({"type": v})
                            else:
                                normalized_props[k] = MetadataView({})
                        meta["properties"] = normalized_props

            # Add href property for URL access in templates
            if not hasattr(obj, "href"):
                try:
                    href = _compute_element_url(obj, getattr(obj, "element_type", None))
                    obj.href = href
                except Exception:
                    # If URL computation fails, set to None (template will use fallback)
                    with suppress(AttributeError, TypeError):
                        obj.href = None

            # Recursively coerce children if they exist and are iterable
            children = getattr(obj, "children", None)
            if children and isinstance(children, (list, tuple)):
                for child in children:
                    _coerce(child)

        _coerce(element)
        return element

    def _normalize_config(self, config: Any) -> Any:
        """
        Wrap config to allow dotted access with safe defaults for github metadata.

        Extracts github_repo and github_branch from the autodoc section of the config
        and normalizes github_repo to a full URL if provided in owner/repo format.

        Args:
            config: Config dict to normalize

        Returns:
            MetadataView wrapped config
        """
        base: dict[str, Any] = {}
        if isinstance(config, dict):
            base.update(config)
        else:
            return config

        # Extract github metadata from autodoc config section if not at top level
        autodoc_config = base.get("autodoc", {})

        # Get github_repo: prefer top-level, fall back to autodoc section
        github_repo = base.get("github_repo") or autodoc_config.get("github_repo", "")

        # Normalize owner/repo format to full GitHub URL
        if github_repo and not github_repo.startswith(("http://", "https://")):
            github_repo = f"https://github.com/{github_repo}"

        base["github_repo"] = github_repo

        # Get github_branch: prefer top-level, fall back to autodoc section
        github_branch = base.get("github_branch") or autodoc_config.get("github_branch", "main")
        base["github_branch"] = github_branch

        return MetadataView(base)


def _safe_metadata_summary(meta: Any) -> str:
    """
    Summarize metadata for logging without raising on missing attributes.
        
    """
    try:
        if isinstance(meta, dict):
            keys = list(meta.keys())[:10]
            return f"dict keys={keys}"
        return str(meta)
    except Exception:
        return "<unavailable>"
