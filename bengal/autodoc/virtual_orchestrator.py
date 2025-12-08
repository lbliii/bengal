"""
Virtual page orchestrator for autodoc.

Generates API documentation as virtual Page and Section objects
that integrate directly into the build pipeline without intermediate
markdown files.

This is the new architecture that replaces markdown-based autodoc generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from bengal.autodoc.base import DocElement
from bengal.autodoc.extractors.python import PythonExtractor
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class VirtualAutodocOrchestrator:
    """
    Orchestrate API documentation generation as virtual pages.

    Unlike the traditional DocumentationGenerator which writes markdown files,
    this orchestrator creates virtual Page and Section objects that integrate
    directly into the site's build pipeline.

    Architecture:
        1. Extract DocElements from Python source code
        2. Create virtual Section hierarchy (api/ -> packages/ -> modules/)
        3. Create virtual Pages for each documentable element
        4. Return (pages, sections) tuple for integration into site

    Benefits over markdown-based approach:
        - No intermediate markdown files to manage
        - Direct HTML rendering (bypass markdown parsing)
        - Better layout control (card-based API Explorer)
        - Faster builds (no parse → render → parse cycle)
    """

    def __init__(self, site: Site):
        """
        Initialize virtual autodoc orchestrator.

        Args:
            site: Site instance for configuration and context

        Note:
            Uses the site's already-loaded config, which supports both
            YAML (config/_default/autodoc.yaml) and TOML (bengal.toml) formats.
        """
        self.site = site
        # Use site's config directly (supports both YAML and TOML)
        self.config = site.config.get("autodoc", {})
        self.python_config = self.config.get("python", {})
        self.template_env = self._create_template_environment()

    def _create_template_environment(self) -> Environment:
        """Create Jinja2 environment for HTML templates."""
        import re

        # Import icon function from main template system
        # Icons are already preloaded during main template engine initialization
        from bengal.rendering.template_functions.icons import icon

        # Template directories in priority order
        template_dirs = []

        # User templates (highest priority)
        user_templates = self.site.root_path / "templates" / "api-reference"
        if user_templates.exists():
            template_dirs.append(str(user_templates))

        # Theme templates (for inheriting theme styles) - prefer theme templates
        if self.site.theme:
            theme_templates = self._get_theme_templates_dir()
            if theme_templates:
                template_dirs.append(str(theme_templates))

        # Built-in fallback templates (lowest priority)
        import bengal

        builtin_templates = Path(bengal.__file__).parent / "autodoc" / "fallback"
        if builtin_templates.exists():
            template_dirs.append(str(builtin_templates))

        if not template_dirs:
            logger.warning("autodoc_no_template_dirs", fallback="inline_templates")
            # Use a minimal fallback
            return Environment(autoescape=select_autoescape())

        env = Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=select_autoescape(["html", "htm", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add icon function from main template system
        env.globals["icon"] = icon

        # Add custom tests for template filtering
        def test_match(value: str | None, pattern: str) -> bool:
            """Test if value matches a regex pattern."""
            if value is None:
                return False
            return bool(re.search(pattern, str(value)))

        env.tests["match"] = test_match

        # Add custom filters for description extraction
        def filter_first_sentence(text: str | None, max_length: int = 120) -> str:
            """Extract first sentence or truncate description."""
            if not text:
                return ""
            text = text.strip()
            # Try to get first sentence
            for end in [". ", ".\n", "!\n", "?\n"]:
                if end in text:
                    first = text.split(end)[0] + end[0]
                    if len(first) <= max_length:
                        return first
                    break
            # Truncate if too long
            if len(text) > max_length:
                return text[: max_length - 3].rsplit(" ", 1)[0] + "..."
            return text

        env.filters["first_sentence"] = filter_first_sentence

        return env

    def _get_theme_templates_dir(self) -> Path | None:
        """Get theme templates directory if available."""
        if not self.site.theme:
            return None

        import bengal

        bengal_dir = Path(bengal.__file__).parent
        theme_dir = bengal_dir / "themes" / self.site.theme / "templates"
        return theme_dir if theme_dir.exists() else None

    def is_enabled(self) -> bool:
        """Check if virtual autodoc is enabled in config."""
        # Check for explicit virtual_pages setting
        virtual_enabled = self.python_config.get("virtual_pages", False)

        # Also check if autodoc is enabled at all
        autodoc_enabled = self.python_config.get("enabled", True)

        return virtual_enabled and autodoc_enabled

    def generate(self) -> tuple[list[Page], list[Section]]:
        """
        Generate API documentation as virtual pages and sections.

        Returns:
            Tuple of (pages, sections) to add to site

        Raises:
            ValueError: If autodoc configuration is invalid
        """
        if not self.is_enabled():
            logger.debug("virtual_autodoc_disabled")
            return [], []

        # 1. Discover source directories
        source_dirs = self.python_config.get("source_dirs", [])
        if not source_dirs:
            logger.warning("autodoc_no_source_dirs")
            return [], []

        # 2. Extract documentation from Python source
        exclude_patterns = self.python_config.get("exclude", [])
        extractor = PythonExtractor(
            exclude_patterns=exclude_patterns,
            config=self.python_config,
        )

        all_elements: list[DocElement] = []
        for source_dir in source_dirs:
            source_path = Path(source_dir)
            if not source_path.is_absolute():
                source_path = self.site.root_path / source_path
            # Always resolve to absolute path for consistent module name resolution
            source_path = source_path.resolve()

            if source_path.exists():
                elements = extractor.extract(source_path)
                all_elements.extend(elements)
                logger.debug(
                    "autodoc_elements_extracted",
                    source=str(source_path),
                    count=len(elements),
                )

        if not all_elements:
            logger.info("autodoc_no_elements_found")
            return [], []

        # 3. Create virtual section hierarchy
        sections = self._create_sections(all_elements)

        # 4. Create virtual pages
        pages = self._create_pages(all_elements, sections)

        # 5. Create index pages for sections (adds to pages list)
        index_pages = self._create_index_pages(sections)
        pages.extend(index_pages)

        # Count total sections (including nested) for logging
        total_section_count = len(sections)

        logger.info(
            "virtual_autodoc_complete",
            pages=len(pages),
            sections=total_section_count,
        )

        # Only return root-level sections (e.g., "api")
        # Nested sections are accessible via parent.subsections
        # This matches how ContentDiscovery handles section hierarchy
        root_sections = [sections["api"]] if "api" in sections else []

        return pages, root_sections

    def _create_sections(self, elements: list[DocElement]) -> dict[str, Section]:
        """
        Create virtual section hierarchy from doc elements.

        Creates sections for:
        - /api/ (root API section)
        - /api/<package>/ (for each top-level package)
        - /api/<package>/<subpackage>/ (nested packages)

        Args:
            elements: List of DocElements (modules) to process

        Returns:
            Dictionary mapping section path to Section object
        """
        sections: dict[str, Section] = {}

        # Build lookup of package descriptions from __init__.py modules
        # Key: qualified_name (e.g., "bengal.core"), Value: description
        package_descriptions: dict[str, str] = {}
        for element in elements:
            if element.element_type == "module" and element.description:
                # This module's description can describe its package
                package_descriptions[element.qualified_name] = element.description

        # Create root API section
        api_section = Section.create_virtual(
            name="api",
            relative_url="/api/",
            title="API Reference",
            metadata={
                "type": "api-reference",
                "weight": 100,
                "icon": "book",
                "description": "Browse Bengal's Python API documentation by package.",
            },
        )
        sections["api"] = api_section

        # Track package hierarchy
        for element in elements:
            if element.element_type != "module":
                continue

            # Parse module qualified name (e.g., "bengal.core.page")
            parts = element.qualified_name.split(".")

            # Create sections for package hierarchy
            current_section = api_section
            section_path = "api"

            for i, part in enumerate(parts[:-1]):  # Skip the final module
                section_path = f"{section_path}/{part}"

                if section_path not in sections:
                    # Create new package section
                    relative_url = f"/{section_path}/"
                    qualified_name = ".".join(parts[: i + 1])

                    # Try to find description from the package's __init__.py
                    description = package_descriptions.get(qualified_name, "")

                    package_section = Section.create_virtual(
                        name=part,
                        relative_url=relative_url,
                        title=part.replace("_", " ").title(),
                        metadata={
                            "type": "api-reference",
                            "qualified_name": qualified_name,
                            "description": description,
                        },
                    )
                    current_section.add_subsection(package_section)
                    sections[section_path] = package_section
                    current_section = package_section
                else:
                    current_section = sections[section_path]

        logger.debug(
            "autodoc_sections_created",
            count=len(sections),
            paths=list(sections.keys()),
        )

        return sections

    def _create_pages(
        self,
        elements: list[DocElement],
        sections: dict[str, Section],
    ) -> list[Page]:
        """
        Create virtual pages for documentation elements.

        Args:
            elements: DocElements to create pages for
            sections: Section hierarchy for page placement

        Returns:
            List of virtual Page objects
        """
        pages: list[Page] = []

        for element in elements:
            if element.element_type != "module":
                continue

            # Determine section for this module
            parts = element.qualified_name.split(".")
            section_path = "api/" + "/".join(parts[:-1]) if len(parts) > 1 else "api"

            parent_section = sections.get(section_path, sections["api"])

            # Create page for module
            page = self._create_module_page(element, parent_section)
            pages.append(page)
            parent_section.add_page(page)

        logger.debug("autodoc_pages_created", count=len(pages))

        return pages

    def _create_module_page(
        self,
        element: DocElement,
        section: Section,
    ) -> Page:
        """
        Create a virtual page for a module.

        Args:
            element: DocElement for the module
            section: Parent section for this page

        Returns:
            Virtual Page object
        """
        # Build source ID (synthetic path)
        module_path = element.qualified_name.replace(".", "/")
        source_id = f"api/{module_path}.md"

        # Generate HTML content using API Explorer template
        html_content = self._render_module(element)

        # Create virtual page with absolute output path
        # (output_path must be absolute for correct URL generation)
        output_path = self.site.output_dir / f"api/{module_path}/index.html"

        page = Page.create_virtual(
            source_id=source_id,
            title=element.name,
            metadata={
                "type": "api-reference",
                "qualified_name": element.qualified_name,
                "element_type": element.element_type,
                "description": element.description or f"API reference for {element.name}",
                # Convert Path to string for JSON serialization
                "source_file": str(element.source_file)
                if hasattr(element, "source_file") and element.source_file
                else None,
                "line_number": getattr(element, "line_number", None),
                # Extra metadata for templates
                "is_autodoc": True,
                "autodoc_element": element,
            },
            rendered_html=html_content,
            template_name="api-reference/module",
            section_path=section.path,
            output_path=output_path,
        )

        # Set site reference for URL computation
        page._site = self.site

        return page

    def _render_module(self, element: DocElement) -> str:
        """
        Render module documentation to HTML.

        Args:
            element: DocElement for the module

        Returns:
            Rendered HTML string
        """
        # Try theme template first (api-reference/module.html)
        try:
            template = self.template_env.get_template("api-reference/module.html")
            return template.render(
                element=element,
                config=self.config,
                site=self.site,
            )
        except Exception as e:
            # Fall back to minimal template or legacy path
            try:
                template = self.template_env.get_template("module.html")
                return template.render(
                    element=element,
                    config=self.config,
                    site=self.site,
                )
            except Exception:
                logger.warning(
                    "autodoc_template_render_failed",
                    element=element.qualified_name,
                    error=str(e),
                )
                # Return minimal fallback HTML
                return self._render_fallback(element)

    def _render_fallback(self, element: DocElement) -> str:
        """Render minimal fallback HTML when template fails."""
        classes = [c for c in element.children if c.element_type == "class"]
        functions = [f for f in element.children if f.element_type == "function"]

        return f"""
<div class="api-explorer">
    <div class="api-module">
        <h1 class="api-module__title">{element.name}</h1>
        <p class="api-module__description">{element.description or "No description available."}</p>

        <div class="api-module__stats">
            <span class="api-stat">Classes: {len(classes)}</span>
            <span class="api-stat">Functions: {len(functions)}</span>
        </div>

        <div class="api-classes">
            {"".join(self._render_fallback_class(c) for c in classes)}
        </div>

        <div class="api-functions">
            {"".join(self._render_fallback_function(f) for f in functions)}
        </div>
    </div>
</div>
"""

    def _render_fallback_class(self, element: DocElement) -> str:
        """Render minimal class HTML."""
        return f"""
<div class="api-card api-card--class">
    <h2 class="api-card__title">{element.name}</h2>
    <p class="api-card__description">{element.description or ""}</p>
</div>
"""

    def _render_fallback_function(self, element: DocElement) -> str:
        """Render minimal function HTML."""
        return f"""
<div class="api-card api-card--function">
    <h3 class="api-card__title">{element.name}</h3>
    <p class="api-card__description">{element.description or ""}</p>
</div>
"""

    def _create_index_pages(self, sections: dict[str, Section]) -> list[Page]:
        """
        Create index pages for sections that need them.

        Args:
            sections: Section dictionary to process

        Returns:
            List of created index pages (to add to main pages list)
        """
        created_pages: list[Page] = []

        for section_path, section in sections.items():
            if section.index_page is not None:
                continue

            # Create index page for this section
            html_content = self._render_section_index(section)

            # Use non-index filename to avoid triggering index page detection
            # in add_page (we set index_page directly below)
            # output_path must be absolute for correct URL generation
            output_path = self.site.output_dir / f"{section_path}/index.html"

            index_page = Page.create_virtual(
                source_id=f"__virtual__/{section_path}/section-index.md",
                title=section.title,
                metadata={
                    "type": "api-reference",
                    "is_section_index": True,
                },
                rendered_html=html_content,
                template_name="api-reference/section-index",
                section_path=section.path,
                output_path=output_path,
            )

            # Set site reference for URL computation
            index_page._site = self.site

            # Set as section index directly (don't use add_page which would
            # trigger index collision detection)
            section.index_page = index_page
            section.pages.append(index_page)
            created_pages.append(index_page)

        return created_pages

    def _render_section_index(self, section: Section) -> str:
        """Render section index page HTML."""
        # Try theme template first (api-reference/section-index.html)
        try:
            template = self.template_env.get_template("api-reference/section-index.html")
            return template.render(
                section=section,
                config=self.config,
                site=self.site,
            )
        except Exception as e:
            # Fall back to legacy path or minimal template
            try:
                template = self.template_env.get_template("section-index.html")
                return template.render(
                    section=section,
                    config=self.config,
                    site=self.site,
                )
            except Exception:
                logger.warning(
                    "autodoc_template_fallback",
                    template="api-reference/section-index.html",
                    section=section.name,
                    error=str(e),
                )
                # Fallback rendering with cards
                return self._render_section_index_fallback(section)

    def _render_section_index_fallback(self, section: Section) -> str:
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
            subsections_cards.append(f'''
      <a href="{s.relative_url}" class="api-package-card">
        <span class="api-package-card__icon">{folder_icon}</span>
        <span class="api-package-card__name">{s.name}</span>
        {f'<span class="api-package-card__description">{desc_preview}</span>' if desc_preview else ""}
        <span class="api-package-card__meta">{child_count} item{"s" if child_count != 1 else ""}</span>
      </a>''')

        module_cards = []
        for p in section.sorted_pages:
            if p == section.index_page:
                continue
            desc = p.metadata.get("description", "")
            desc_preview = (desc[:80] + "..." if len(desc) > 80 else desc) if desc else ""
            element_type = p.metadata.get("element_type", "")
            module_cards.append(f'''
      <a href="{p.relative_url}" class="api-module-card">
        <span class="api-module-card__icon">{code_icon}</span>
        <span class="api-module-card__name">{p.title}</span>
        {f'<span class="api-module-card__description">{desc_preview}</span>' if desc_preview else ""}
        {f'<span class="api-module-card__badges"><span class="api-badge--mini">{element_type}</span></span>' if element_type else ""}
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
<div class="api-explorer api-explorer--index">
  <header class="api-section-header">
    <h1 class="api-section-header__title">{section.title}</h1>
    {desc_html}
  </header>
  {subsections_section}
  {modules_section}
</div>
"""
