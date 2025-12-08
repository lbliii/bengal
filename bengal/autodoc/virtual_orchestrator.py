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
        1. Extract DocElements from source (Python, CLI, or OpenAPI)
        2. Create virtual Section hierarchy based on element type
        3. Create virtual Pages for each documentable element
        4. Return (pages, sections) tuple for integration into site

    Supports:
        - Python API docs (modules, classes, functions)
        - CLI docs (commands, command groups)
        - OpenAPI docs (endpoints, schemas)

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
        self.cli_config = self.config.get("cli", {})
        self.openapi_config = self.config.get("openapi", {})
        self.template_env = self._create_template_environment()

    def _create_template_environment(self) -> Environment:
        """Create Jinja2 environment for HTML templates."""
        import re

        # Import icon function from main template system
        # Icons are already preloaded during main template engine initialization
        from bengal.rendering.template_functions.icons import icon

        # Template directories in priority order
        template_dirs = []

        # User templates (highest priority) - check all reference types
        for ref_type in ["api-reference", "cli-reference", "openapi-reference"]:
            user_templates = self.site.root_path / "templates" / ref_type
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
        """Check if virtual autodoc is enabled for any type."""
        # Virtual pages are now the default (and only) option
        # Only check if explicitly disabled via virtual_pages: false
        # Check Python
        python_enabled = (
            self.python_config.get("virtual_pages", True)  # Default to True
            and self.python_config.get("enabled", True)
        )

        # Check CLI
        cli_enabled = (
            self.cli_config.get("virtual_pages", True)  # Default to True
            and self.cli_config.get("enabled", True)
        )

        # Check OpenAPI
        openapi_enabled = (
            self.openapi_config.get("virtual_pages", True)  # Default to True
            and self.openapi_config.get("enabled", True)
        )

        return python_enabled or cli_enabled or openapi_enabled

    def generate(self) -> tuple[list[Page], list[Section]]:
        """
        Generate documentation as virtual pages and sections for all enabled types.

        Returns:
            Tuple of (pages, sections) to add to site

        Raises:
            ValueError: If autodoc configuration is invalid
        """
        if not self.is_enabled():
            logger.debug("virtual_autodoc_disabled")
            return [], []

        all_elements: list[DocElement] = []
        all_sections: dict[str, Section] = {}
        all_pages: list[Page] = []

        # 1. Extract Python documentation
        # Virtual pages are now the default (and only) option
        if self.python_config.get("virtual_pages", True) and self.python_config.get(
            "enabled", True
        ):
            python_elements = self._extract_python()
            if python_elements:
                all_elements.extend(python_elements)
                python_sections = self._create_python_sections(python_elements)
                all_sections.update(python_sections)
                python_pages = self._create_pages(
                    python_elements, python_sections, doc_type="python"
                )
                all_pages.extend(python_pages)

        # 2. Extract CLI documentation
        # Virtual pages are now the default (and only) option
        if self.cli_config.get("virtual_pages", True) and self.cli_config.get("enabled", True):
            cli_elements = self._extract_cli()
            if cli_elements:
                all_elements.extend(cli_elements)
                cli_sections = self._create_cli_sections(cli_elements)
                all_sections.update(cli_sections)
                cli_pages = self._create_pages(cli_elements, cli_sections, doc_type="cli")
                all_pages.extend(cli_pages)

        # 3. Extract OpenAPI documentation
        # Pass existing sections so OpenAPI can reuse "api" section if Python already created it
        # Virtual pages are now the default (and only) option
        if self.openapi_config.get("virtual_pages", True) and self.openapi_config.get(
            "enabled", True
        ):
            openapi_elements = self._extract_openapi()
            if openapi_elements:
                all_elements.extend(openapi_elements)
                openapi_sections = self._create_openapi_sections(openapi_elements, all_sections)
                all_sections.update(openapi_sections)
                openapi_pages = self._create_pages(
                    openapi_elements, openapi_sections, doc_type="openapi"
                )
                all_pages.extend(openapi_pages)

        if not all_elements:
            logger.info("autodoc_no_elements_found")
            return [], []

        # 4. Create index pages for all sections
        index_pages = self._create_index_pages(all_sections)
        all_pages.extend(index_pages)

        logger.info(
            "virtual_autodoc_complete",
            pages=len(all_pages),
            sections=len(all_sections),
        )

        # Return root-level sections only (e.g., "api", "cli")
        # These are the sections that will appear in the navigation menu
        root_sections = [s for key, s in all_sections.items() if "/" not in key.replace("\\", "/")]

        logger.debug(
            "virtual_autodoc_root_sections",
            count=len(root_sections),
            names=[s.name for s in root_sections],
        )

        return all_pages, root_sections

    def _create_python_sections(self, elements: list[DocElement]) -> dict[str, Section]:
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

    def _create_cli_sections(self, elements: list[DocElement]) -> dict[str, Section]:
        """Create CLI section hierarchy."""
        sections: dict[str, Section] = {}

        # Create root CLI section
        cli_section = Section.create_virtual(
            name="cli",
            relative_url="/cli/",
            title="CLI Reference",
            metadata={
                "type": "cli-reference",
                "weight": 100,
                "icon": "terminal",
                "description": "Command-line interface documentation.",
            },
        )
        sections["cli"] = cli_section

        # Group commands by command-group
        command_groups: dict[str, list[DocElement]] = {}
        standalone_commands: list[DocElement] = []

        for element in elements:
            if element.element_type == "command-group":
                command_groups[element.qualified_name] = []
            elif element.element_type == "command":
                # Check if command has a parent group
                parts = element.qualified_name.split(".")
                if len(parts) > 1:
                    parent_group = ".".join(parts[:-1])
                    if parent_group not in command_groups:
                        command_groups[parent_group] = []
                    command_groups[parent_group].append(element)
                else:
                    standalone_commands.append(element)

        # Create sections for command groups
        for group_name, commands in command_groups.items():
            if not commands:
                continue

            section_path = f"cli/{group_name.replace('.', '/')}"
            group_section = Section.create_virtual(
                name=group_name.split(".")[-1],
                relative_url=f"/{section_path}/",
                title=group_name.split(".")[-1].replace("_", " ").title(),
                metadata={
                    "type": "cli-reference",
                    "qualified_name": group_name,
                },
            )
            cli_section.add_subsection(group_section)
            sections[section_path] = group_section

        logger.debug("autodoc_sections_created", count=len(sections), type="cli")
        return sections

    def _create_openapi_sections(
        self, elements: list[DocElement], existing_sections: dict[str, Section] | None = None
    ) -> dict[str, Section]:
        """Create OpenAPI section hierarchy."""
        sections: dict[str, Section] = {}
        existing_sections = existing_sections or {}

        # Create root API section (or use existing if Python also enabled)
        if "api" not in existing_sections:
            api_section = Section.create_virtual(
                name="api",
                relative_url="/api/",
                title="API Reference",
                metadata={
                    "type": "api-reference",
                    "weight": 100,
                    "icon": "book",
                    "description": "REST API documentation.",
                },
            )
            sections["api"] = api_section
        else:
            # Reuse existing API section from Python
            api_section = existing_sections["api"]
            sections["api"] = api_section

        # Group endpoints by tags
        tagged_endpoints: dict[str, list[DocElement]] = {}
        untagged_endpoints: list[DocElement] = []

        for element in elements:
            if element.element_type == "openapi_endpoint":
                tags = element.metadata.get("tags", [])
                if tags:
                    for tag in tags:
                        if tag not in tagged_endpoints:
                            tagged_endpoints[tag] = []
                        tagged_endpoints[tag].append(element)
                else:
                    untagged_endpoints.append(element)
            elif element.element_type == "openapi_overview":
                # Overview goes at root
                pass
            elif element.element_type == "openapi_schema":
                # Schemas go in a schemas section
                if "api/schemas" not in sections:
                    schemas_section = Section.create_virtual(
                        name="schemas",
                        relative_url="/api/schemas/",
                        title="Schemas",
                        metadata={
                            "type": "api-reference",
                            "description": "API data schemas and models.",
                        },
                    )
                    api_section.add_subsection(schemas_section)
                    sections["api/schemas"] = schemas_section

        # Create sections for tags
        for tag, _endpoints in tagged_endpoints.items():
            section_path = f"api/tags/{tag}"
            tag_section = Section.create_virtual(
                name=tag,
                relative_url=f"/{section_path}/",
                title=tag.replace("-", " ").title(),
                metadata={
                    "type": "api-reference",
                    "tag": tag,
                },
            )
            api_section.add_subsection(tag_section)
            sections[section_path] = tag_section

        logger.debug("autodoc_sections_created", count=len(sections), type="openapi")
        return sections

    def _create_pages(
        self,
        elements: list[DocElement],
        sections: dict[str, Section],
        doc_type: str = "python",
    ) -> list[Page]:
        """
        Create virtual pages for documentation elements.

        Args:
            elements: DocElements to create pages for
            sections: Section hierarchy for page placement
            doc_type: Type of documentation ("python", "cli", "openapi")

        Returns:
            List of virtual Page objects
        """
        pages: list[Page] = []

        for element in elements:
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
            parent_section = self._find_parent_section(element, sections, doc_type)

            # Create page
            page = self._create_element_page(element, parent_section, doc_type)
            pages.append(page)
            parent_section.add_page(page)

        logger.debug("autodoc_pages_created", count=len(pages), type=doc_type)

        return pages

    def _find_parent_section(
        self, element: DocElement, sections: dict[str, Section], doc_type: str
    ) -> Section:
        """Find the appropriate parent section for an element."""
        if doc_type == "python":
            parts = element.qualified_name.split(".")
            section_path = "api/" + "/".join(parts[:-1]) if len(parts) > 1 else "api"
            return sections.get(section_path, sections.get("api"))
        elif doc_type == "cli":
            if element.element_type == "command-group":
                return sections.get("cli")
            parts = element.qualified_name.split(".")
            if len(parts) > 1:
                section_path = f"cli/{'.'.join(parts[:-1]).replace('.', '/')}"
                return sections.get(section_path, sections.get("cli"))
            return sections.get("cli")
        elif doc_type == "openapi":
            if element.element_type == "openapi_overview":
                return sections.get("api")
            elif element.element_type == "openapi_schema":
                return sections.get("api/schemas", sections.get("api"))
            elif element.element_type == "openapi_endpoint":
                tags = element.metadata.get("tags", [])
                if tags:
                    tag_section = sections.get(f"api/tags/{tags[0]}")
                    if tag_section:
                        return tag_section
                return sections.get("api")
        return sections.get("api", sections.get("cli"))

    def _create_element_page(
        self,
        element: DocElement,
        section: Section,
        doc_type: str,
    ) -> Page:
        """
        Create a virtual page for any element type.

        Args:
            element: DocElement to create page for
            section: Parent section for this page
            doc_type: Type of documentation ("python", "cli", "openapi")

        Returns:
            Virtual Page object
        """
        # Determine URL path and template based on element type
        template_name, url_path, page_type = self._get_element_metadata(element, doc_type)

        # Build source ID (synthetic path)
        source_id = f"{doc_type}/{url_path}.md"

        # Generate HTML content using appropriate template
        html_content = self._render_element(element, template_name)

        # Create virtual page with absolute output path
        output_path = self.site.output_dir / f"{url_path}/index.html"

        page = Page.create_virtual(
            source_id=source_id,
            title=element.name,
            metadata={
                "type": page_type,
                "qualified_name": element.qualified_name,
                "element_type": element.element_type,
                "description": element.description or f"Documentation for {element.name}",
                "source_file": str(element.source_file) if element.source_file else None,
                "line_number": getattr(element, "line_number", None),
                "is_autodoc": True,
                "autodoc_element": element,
            },
            rendered_html=html_content,
            template_name=template_name,
            section_path=section.path,
            output_path=output_path,
        )

        # Set site reference for URL computation
        page._site = self.site

        return page

    def _get_element_metadata(self, element: DocElement, doc_type: str) -> tuple[str, str, str]:
        """Get template name, URL path, and page type for an element."""
        if doc_type == "python":
            url_path = f"api/{element.qualified_name.replace('.', '/')}"
            return "api-reference/module", url_path, "api-reference"
        elif doc_type == "cli":
            if element.element_type == "command-group":
                url_path = f"cli/{element.qualified_name.replace('.', '/')}"
                return "cli-reference/command-group", url_path, "cli-reference"
            else:
                url_path = f"cli/{element.qualified_name.replace('.', '/')}"
                return "cli-reference/command", url_path, "cli-reference"
        elif doc_type == "openapi":
            if element.element_type == "openapi_overview":
                return "openapi-reference/overview", "api/overview", "api-reference"
            elif element.element_type == "openapi_schema":
                schema_name = element.name
                return (
                    "openapi-reference/schema",
                    f"api/schemas/{schema_name}",
                    "api-reference",
                )
            elif element.element_type == "openapi_endpoint":
                method = element.metadata.get("method", "").lower()
                path = element.metadata.get("path", "").strip("/").replace("/", "-")
                return (
                    "openapi-reference/endpoint",
                    f"api/endpoints/{method}-{path}",
                    "api-reference",
                )
        # Fallback
        return "api-reference/module", f"api/{element.name}", "api-reference"

    def _render_element(self, element: DocElement, template_name: str) -> str:
        """
        Render element documentation to HTML.

        Args:
            element: DocElement to render
            template_name: Template name (e.g., "api-reference/module")

        Returns:
            Rendered HTML string
        """
        # Try theme template first
        try:
            template = self.template_env.get_template(f"{template_name}.html")
            return template.render(
                element=element,
                config=self.config,
                site=self.site,
            )
        except Exception as e:
            # Fall back to generic template or legacy path
            try:
                # Try without .html extension
                template = self.template_env.get_template(template_name)
                return template.render(
                    element=element,
                    config=self.config,
                    site=self.site,
                )
            except Exception:
                logger.warning(
                    "autodoc_template_render_failed",
                    element=element.qualified_name,
                    template=template_name,
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

            # Determine template and page type based on section metadata
            section_type = section.metadata.get("type", "api-reference")
            template_name = f"{section_type}/section-index"

            index_page = Page.create_virtual(
                source_id=f"__virtual__/{section_path}/section-index.md",
                title=section.title,
                metadata={
                    "type": section_type,
                    "is_section_index": True,
                },
                rendered_html=html_content,
                template_name=template_name,
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
        section_type = section.metadata.get("type", "api-reference")
        template_name = f"{section_type}/section-index"

        # Try theme template first
        try:
            template = self.template_env.get_template(f"{template_name}.html")
            return template.render(
                section=section,
                config=self.config,
                site=self.site,
            )
        except Exception as e:
            # Fall back to generic section-index or legacy path
            try:
                template = self.template_env.get_template("api-reference/section-index.html")
                return template.render(
                    section=section,
                    config=self.config,
                    site=self.site,
                )
            except Exception:
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
                        template=template_name,
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
        <span class="api-package-card__meta">
          {child_count} item{"s" if child_count != 1 else ""}
        </span>
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

    def _extract_python(self) -> list[DocElement]:
        """Extract Python API documentation."""
        from bengal.autodoc.extractors.python import PythonExtractor

        source_dirs = self.python_config.get("source_dirs", [])
        exclude_patterns = self.python_config.get("exclude", [])

        extractor = PythonExtractor(exclude_patterns=exclude_patterns, config=self.python_config)
        all_elements = []

        for source_dir in source_dirs:
            source_path = Path(source_dir)
            if not source_path.exists():
                logger.warning(
                    "autodoc_source_dir_not_found",
                    path=str(source_path),
                    type="python",
                )
                continue

            elements = extractor.extract(source_path)
            all_elements.extend(elements)

        logger.debug("autodoc_python_extracted", count=len(all_elements))
        return all_elements

    def _extract_cli(self) -> list[DocElement]:
        """Extract CLI documentation."""
        import importlib

        from bengal.autodoc.extractors.cli import CLIExtractor

        app_module = self.cli_config.get("app_module")
        if not app_module:
            logger.warning("autodoc_cli_no_app_module")
            return []

        framework = self.cli_config.get("framework", "click")
        include_hidden = self.cli_config.get("include_hidden", False)

        # Load CLI app from module path (e.g., "bengal.cli:main")
        try:
            module_path, attr_name = app_module.split(":")
            module = importlib.import_module(module_path)
            cli_app = getattr(module, attr_name)
        except (ValueError, ImportError, AttributeError) as e:
            logger.warning("autodoc_cli_load_failed", app_module=app_module, error=str(e))
            return []

        # Extract documentation
        extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
        elements = extractor.extract(cli_app)

        logger.debug("autodoc_cli_extracted", count=len(elements))
        return elements

    def _extract_openapi(self) -> list[DocElement]:
        """Extract OpenAPI documentation."""
        from bengal.autodoc.extractors.openapi import OpenAPIExtractor

        spec_file = self.openapi_config.get("spec_file")
        if not spec_file:
            logger.warning("autodoc_openapi_no_spec_file")
            return []

        spec_path = Path(spec_file)
        if not spec_path.exists():
            logger.warning("autodoc_openapi_spec_not_found", path=str(spec_path))
            return []

        # Extract documentation
        extractor = OpenAPIExtractor()
        elements = extractor.extract(spec_path)

        logger.debug("autodoc_openapi_extracted", count=len(elements))
        return elements
