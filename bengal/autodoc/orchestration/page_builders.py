"""
Page builders for autodoc.

Creates virtual Page objects and handles rendering for autodoc elements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.autodoc.base import DocElement
from bengal.autodoc.orchestration.result import AutodocRunResult
from bengal.autodoc.orchestration.utils import format_source_file_for_display
from bengal.autodoc.utils import (
    get_openapi_method,
    get_openapi_path,
    get_openapi_tags,
    resolve_cli_url_path,
)
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


def create_pages(
    elements: list[DocElement],
    sections: dict[str, Section],
    site: Site,
    doc_type: str,
    resolve_output_prefix: callable,
    get_element_metadata: callable,
    find_parent_section: callable,
    result: AutodocRunResult | None = None,
) -> tuple[list[Page], AutodocRunResult]:
    """
    Create virtual pages for documentation elements.

    This uses a two-pass approach to ensure navigation works correctly:
    1. First pass: Create all Page objects and add them to sections
    2. Second pass: Render HTML (now sections have all their pages)

    Args:
        elements: DocElements to create pages for
        sections: Section hierarchy for page placement
        site: Site instance
        doc_type: Type of documentation ("python", "cli", "openapi")
        resolve_output_prefix: Function to resolve output prefix
        get_element_metadata: Function to get element metadata
        find_parent_section: Function to find parent section
        result: AutodocRunResult to track failures and warnings

    Returns:
        Tuple of (list of virtual Page objects, updated result)
    """
    if result is None:
        result = AutodocRunResult()

    # First pass: Create pages without HTML and add to sections
    page_data: list[Page] = []

    for element in elements:
        display_source_file = format_source_file_for_display(element.source_file, site.root_path)
        element.display_source_file = display_source_file
        source_file_for_tracking = element.source_file
        # Determine which elements get pages based on type
        if (
            doc_type == "python"
            and element.element_type != "module"
            or doc_type == "cli"
            and element.element_type not in ("command", "command-group")
            or doc_type == "openapi"
            and element.element_type
            not in (
                "openapi_endpoint",
                "openapi_schema",
                "openapi_overview",
            )
        ):
            continue

        # Determine section for this element
        parent_section = find_parent_section(element, sections, doc_type)

        # Create page metadata without rendering HTML yet
        template_name, url_path, page_type = get_element_metadata(element, doc_type)

        # Skip root command-groups - the section index page represents them
        # resolve_cli_url_path("bengal") returns "" which becomes just the prefix
        # This would output to /cli/index.html, same as the section index page
        prefix = resolve_output_prefix(doc_type)
        if doc_type == "cli" and url_path == prefix:
            logger.debug(
                "cli_root_group_skipped",
                element=element.qualified_name,
                reason="Section index page represents root command-group",
            )
            continue
        # Note: url_path already includes the prefix (e.g., "cli/assets/build")
        source_id = f"{url_path}.md"
        output_path = site.output_dir / f"{url_path}/index.html"

        # Create page with deferred rendering - HTML rendered in rendering phase
        page = Page.create_virtual(
            source_id=source_id,
            title=element.name,
            metadata={
                "type": page_type,
                "qualified_name": element.qualified_name,
                "element_type": element.element_type,
                "description": element.description or f"Documentation for {element.name}",
                "source_file": display_source_file,
                "line_number": getattr(element, "line_number", None),
                "is_autodoc": True,
                "autodoc_element": element,
                # Rendering metadata - used by RenderingPipeline to render with full context
                "_autodoc_template": template_name,
                "_autodoc_url_path": url_path,
                "_autodoc_page_type": page_type,
            },
            rendered_html=None,  # Deferred - rendered in rendering phase with full context
            template_name=template_name,
            output_path=output_path,
        )
        page._site = site
        # Set section reference via setter (handles virtual sections with URL-based lookup)
        page._section = parent_section

        # Claim URL in registry for ownership enforcement
        # Priority 80 = autodoc pages (derived from sections)
        if hasattr(site, "url_registry") and site.url_registry:
            try:
                from bengal.utils.url_strategy import URLStrategy

                url = URLStrategy.url_from_output_path(output_path, site)
                source = str(page.source_path)
                # Extract section_id from prefix (e.g., "api/python" -> "python")
                section_id = prefix.split("/")[-1] if "/" in prefix else prefix
                owner = f"autodoc:{section_id}"
                site.url_registry.claim(
                    url=url,
                    owner=owner,
                    source=source,
                    priority=80,  # Autodoc pages
                )
            except Exception:
                # Don't fail autodoc generation on registry errors (graceful degradation)
                pass

        # Check if this element corresponds to an existing section (e.g. it's a package)
        # If so, this page should be the index page of that section
        target_section = None

        # Get the prefix for this doc type to construct correct section paths
        prefix = resolve_output_prefix(doc_type)

        if doc_type == "python" and element.element_type == "module":
            # Check if we have a section for this module (i.e., it is a package)
            # Section path format from create_python_sections: {prefix}/part1/part2
            section_path = f"{prefix}/{element.qualified_name.replace('.', '/')}"
            target_section = sections.get(section_path)

        elif doc_type == "cli" and element.element_type == "command-group":
            # Section path format from create_cli_sections: {prefix}/part1/part2
            # resolve_cli_url_path strips the root command (e.g., "bengal.assets" → "assets")
            from bengal.autodoc.utils import resolve_cli_url_path

            group_path = resolve_cli_url_path(element.qualified_name)
            if group_path:  # Skip root command group (empty path)
                section_path = f"{prefix}/{group_path}"
                target_section = sections.get(section_path)

        # Add to section
        if target_section:
            # This page is the index for target_section
            # Set section reference to the target section (it belongs TO the section
            # as its index).
            page._section = target_section

            # Set as index page manually
            # We don't use add_page() because it relies on filename stem for index detection
            target_section.index_page = page
            target_section.pages.append(page)
            # Also add to page_data so it gets returned and rendered
            # (same pattern as create_index_pages which adds to both section.pages AND return list)
            page_data.append(page)
        else:
            # Regular page - add to parent section
            parent_section.add_page(page)
            # Store page for return (no HTML rendering yet - deferred to rendering phase)
            page_data.append(page)

        # Track source file → autodoc page dependency for incremental builds
        if source_file_for_tracking:
            result.add_dependency(str(source_file_for_tracking), source_id)

    # Note: HTML rendering is now DEFERRED to the rendering phase
    # This ensures menus and full template context are available.
    # See: RenderingPipeline._process_virtual_page() and _render_autodoc_page()
    logger.debug("autodoc_pages_created", count=len(page_data), type=doc_type)

    return page_data, result


def find_parent_section(
    element: DocElement,
    sections: dict[str, Section],
    doc_type: str,
    resolve_output_prefix: callable,
) -> Section:
    """Find the appropriate parent section for an element."""
    prefix = resolve_output_prefix(doc_type)

    # Get the first section from sections dict as fallback
    default_section = next(iter(sections.values()), None)
    if default_section is None:
        # Create a fallback section if none exists
        from bengal.utils.url_normalization import join_url_paths

        default_section = Section.create_virtual(
            name="api",
            relative_url=join_url_paths(prefix),
            title="API Reference",
            metadata={},
        )

    if doc_type == "python":
        parts = element.qualified_name.split(".")
        section_path = f"{prefix}/" + "/".join(parts[:-1]) if len(parts) > 1 else prefix
        return sections.get(section_path) or sections.get(prefix) or default_section
    elif doc_type == "cli":
        parts = element.qualified_name.split(".")
        if len(parts) > 1:
            # Parent is everything except the last part
            parent_qualified = ".".join(parts[:-1])
            parent_path = resolve_cli_url_path(parent_qualified)
            section_path = f"{prefix}/{parent_path}" if parent_path else prefix
            return sections.get(section_path) or sections.get(prefix) or default_section
        return sections.get(prefix) or default_section
    elif doc_type == "openapi":
        if element.element_type == "openapi_overview":
            return sections.get(prefix) or default_section
        elif element.element_type == "openapi_schema":
            return sections.get(f"{prefix}/schemas") or sections.get(prefix) or default_section
        elif element.element_type == "openapi_endpoint":
            tags = get_openapi_tags(element)
            if tags:
                tag_section = sections.get(f"{prefix}/tags/{tags[0]}")
                if tag_section:
                    return tag_section
            return sections.get(prefix) or default_section
    return sections.get(prefix) or default_section


def get_element_metadata(
    element: DocElement, doc_type: str, resolve_output_prefix: callable
) -> tuple[str, str, str]:
    """Get template name, URL path, and page type for an element."""
    prefix = resolve_output_prefix(doc_type)

    if doc_type == "python":
        url_path = f"{prefix}/{element.qualified_name.replace('.', '/')}"
        # Python API docs use python-reference type for prose-constrained layout
        return "autodoc/python/module", url_path, "autodoc-python"
    elif doc_type == "cli":
        cli_path = resolve_cli_url_path(element.qualified_name)
        url_path = f"{prefix}/{cli_path}" if cli_path else prefix

        if element.element_type == "command-group":
            return "autodoc/cli/command-group", url_path, "autodoc-cli"
        else:
            return "autodoc/cli/command", url_path, "autodoc-cli"
    elif doc_type == "openapi":
        # OpenAPI docs use openautodoc/python type for full-width 3-panel layout
        if element.element_type == "openapi_overview":
            return "openautodoc/python/overview", f"{prefix}/overview", "autodoc-rest"
        elif element.element_type == "openapi_schema":
            schema_name = element.name
            return (
                "openautodoc/python/schema",
                f"{prefix}/schemas/{schema_name}",
                "autodoc-rest",
            )
        elif element.element_type == "openapi_endpoint":
            method = get_openapi_method(element).lower()
            path = get_openapi_path(element).strip("/").replace("/", "-")
            return (
                "openautodoc/python/endpoint",
                f"{prefix}/endpoints/{method}-{path}",
                "autodoc-rest",
            )
    # Fallback - use python-reference for prose-constrained layout
    return "autodoc/python/module", f"{prefix}/{element.name}", "autodoc-python"


def prepare_element_for_template(element: DocElement) -> dict[str, Any]:
    """
    Prepare DocElement for Jinja2 template consumption.

    Converts DocElement to a clean dict that Jinja2 can handle without
    undefined attribute errors. This is the "middle ground" approach:
    Python prepares clean data, templates just display it.

    Args:
        element: DocElement to prepare

    Returns:
        Dict with all fields guaranteed to exist (no undefined errors in templates)
    """

    def prepare_child(child: DocElement) -> dict[str, Any]:
        """Recursively prepare child elements."""
        return {
            "name": child.name,
            "qualified_name": child.qualified_name,
            "description": child.description or "",
            "element_type": child.element_type,
            "source_file": str(child.source_file) if child.source_file else None,
            "line_number": child.line_number,
            "metadata": child.metadata or {},
            "children": [prepare_child(c) for c in (child.children or [])],
            "examples": child.examples or [],
            "see_also": child.see_also or [],
            "deprecated": child.deprecated,
        }

    return {
        "name": element.name,
        "qualified_name": element.qualified_name,
        "description": element.description or "",
        "element_type": element.element_type,
        "source_file": str(element.source_file) if element.source_file else None,
        "line_number": element.line_number,
        "metadata": element.metadata or {},
        "children": [prepare_child(c) for c in (element.children or [])],
        "examples": element.examples or [],
        "see_also": element.see_also or [],
        "deprecated": element.deprecated,
        # Expose display_source_file if available
        "display_source_file": getattr(element, "display_source_file", None),
    }
