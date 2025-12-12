"""
Index page builders for autodoc.

Creates and renders section index pages for autodoc sections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment

from bengal.autodoc.orchestration.result import PageContext
from bengal.autodoc.orchestration.template_env import relativize_paths
from bengal.autodoc.orchestration.utils import get_template_dir_for_type
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


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
        section_type = section.metadata.get("type", "python-reference")
        template_dir = get_template_dir_for_type(section_type)
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


def render_section_index(
    section: Section,
    site: Site,
    template_env: Environment,
    config: dict,
) -> str:
    """Render section index page HTML."""
    section_type = section.metadata.get("type", "python-reference")
    template_dir = get_template_dir_for_type(section_type)
    template_name = f"{template_dir}/section-index"

    # Create a page-like context for templates that expect a 'page' variable
    page_context = PageContext(
        title=section.title,
        metadata={
            "type": section_type,
            "is_section_index": True,
            "description": section.metadata.get("description", ""),
        },
        tags=[],
        relative_url=section.relative_url,
        section=section,
    )

    # Try theme template first
    try:
        template = template_env.get_template(f"{template_name}.html")
        return template.render(
            section=section,
            page=page_context,
            config=config,
            site=site,
        )
    except Exception as e:
        # Fall back to generic section-index or legacy path
        try:
            template = template_env.get_template("api-reference/section-index.html")
            return template.render(
                section=section,
                page=page_context,
                config=config,
                site=site,
            )
        except Exception as e2:
            try:
                template = template_env.get_template("section-index.html")
                return template.render(
                    section=section,
                    page=page_context,
                    config=config,
                    site=site,
                )
            except Exception as e3:
                logger.warning(
                    "autodoc_template_fallback",
                    template=template_name,
                    section=section.name,
                    error=relativize_paths(str(e), site),
                    secondary_error=relativize_paths(str(e2), site),
                    tertiary_error=relativize_paths(str(e3), site),
                )
                # Fallback rendering with cards
                return render_section_index_fallback(section)


def render_section_index_fallback(section: Section) -> str:
    """Fallback card-based rendering when template fails."""
    from bengal.rendering.template_functions.icons import icon

    # SVG icons for cards (already preloaded during site build)
    folder_icon = icon("folder", size=20, css_class="icon-muted")
    code_icon = icon("code", size=16, css_class="icon-muted")

    subsections_cards = []
    for s in section.sorted_subsections:
        desc = s.metadata.get("description", "")
        desc_preview = (desc[:80] + "..." if len(desc) > 80 else desc) if desc else ""
        child_count = len(s.subsections) + len(s.pages)
        desc_span = f'<p class="api-card__description">{desc_preview}</p>' if desc_preview else ""
        subsections_cards.append(f'''
      <a href="{s.relative_url}" class="api-card api-card--link api-card--package">
        <div class="api-card__header">
          <span class="api-card__icon">{folder_icon}</span>
          <span class="api-card__title">{s.name}</span>
        </div>
        <div class="api-card__body">
          {desc_span}
        </div>
        <div class="api-card__footer">
          <span class="api-card__meta">
            {child_count} item{"s" if child_count != 1 else ""}
          </span>
        </div>
      </a>''')

    module_cards = []
    for p in section.sorted_pages:
        if p == section.index_page:
            continue
        desc = p.metadata.get("description", "")
        desc_preview = (desc[:80] + "..." if len(desc) > 80 else desc) if desc else ""
        element_type = p.metadata.get("element_type", "")
        desc_span = f'<p class="api-card__description">{desc_preview}</p>' if desc_preview else ""
        badge_span = (
            f'<span class="api-badge--mini api-badge--{element_type}">{element_type}</span>'
            if element_type
            else ""
        )
        module_cards.append(f'''
      <a href="{p.relative_url}" class="api-card api-card--link">
        <div class="api-card__header">
          <span class="api-card__icon">{code_icon}</span>
          <span class="api-card__title">{p.title}</span>
          {badge_span}
        </div>
        <div class="api-card__body">
          {desc_span}
        </div>
      </a>''')

    subsections_section = ""
    if subsections_cards:
        subsections_section = f"""
  <section class="api-section api-section--packages">
    <h2 class="api-section__title">Packages</h2>
    <div class="api-grid api-grid--packages">
      {"".join(subsections_cards)}
    </div>
  </section>"""

    modules_section = ""
    if module_cards:
        modules_section = f"""
  <section class="api-section api-section--modules">
    <h2 class="api-section__title">Modules</h2>
    <div class="api-grid api-grid--modules">
      {"".join(module_cards)}
    </div>
  </section>"""

    desc_html = ""
    section_desc = section.metadata.get("description", "")
    if section_desc:
        desc_html = f'<p class="api-section-header__description">{section_desc}</p>'

    return f"""
<div class="autodoc-explorer autodoc-explorer--index">
  <header class="api-section-header">
    <h1 class="api-section-header__title">{section.title}</h1>
    {desc_html}
  </header>
  {subsections_section}
  {modules_section}
</div>
"""
