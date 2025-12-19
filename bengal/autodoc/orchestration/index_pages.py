"""
Index page builders for autodoc.

Creates and renders section index pages for autodoc sections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.autodoc.orchestration.utils import get_template_dir_for_type
from bengal.core.page import Page
from bengal.core.section import Section

if TYPE_CHECKING:
    from bengal.core.site import Site


def create_index_pages(
    sections: dict[str, Section],
    site: Site,
) -> list[Page]:
    """
    Create index pages for sections that need them.

    Args:
        sections: Section dictionary to process
        site: Site instance

    Returns:
        List of created index pages (to add to main pages list)
    """
    created_pages: list[Page] = []

    for section_path, section in sections.items():
        if section.index_page is not None:
            continue

        # output_path must be absolute for correct URL generation
        output_path = site.output_dir / f"{section_path}/index.html"

        # Determine template and page type based on section metadata
        # Page type controls CSS styling, template dir may differ
        section_type = section.metadata.get("type", "autodoc-python")
        template_dir = get_template_dir_for_type(section_type)

        # api-hub sections use 'home' template for the premium landing page
        # with banner and tiles; other sections use 'section-index'
        if section_type == "autodoc-hub":
            template_name = f"{template_dir}/home"
        else:
            template_name = f"{template_dir}/section-index"

        # Create page with deferred rendering - HTML rendered in rendering phase
        # NOTE: We pass autodoc_element=None for section-index pages because:
        # - Templates expect 'element' to be a DocElement with properties like
        #   element_type, qualified_name, children, description, etc.
        # - Section objects don't have these properties and would cause StrictUndefined errors
        # - The section data is already available via the 'section' template variable
        index_page = Page.create_virtual(
            source_id=f"__virtual__/{section_path}/section-index.md",
            title=section.title,
            metadata={
                "type": section_type,
                "is_section_index": True,
                "description": section.metadata.get("description", ""),
                # Autodoc deferred rendering metadata
                "is_autodoc": True,
                "autodoc_element": None,  # Section data available via 'section' variable
                "_autodoc_template": template_name,
            },
            rendered_html=None,  # Deferred - rendered in rendering phase with full context
            template_name=template_name,
            output_path=output_path,
        )

        # Set site reference for URL computation
        index_page._site = site
        # Set section reference via setter (handles virtual sections with URL-based lookup)
        index_page._section = section

        # Set as section index directly (don't use add_page which would
        # trigger index collision detection)
        section.index_page = index_page
        section.pages.append(index_page)
        created_pages.append(index_page)

    return created_pages
