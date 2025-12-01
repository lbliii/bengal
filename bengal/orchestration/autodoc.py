"""
Autodoc orchestration for Bengal SSG.

Handles loading autodoc manifest and generating virtual pages for rendering.
Similar to TaxonomyOrchestrator - creates Page objects that render through
normal pipeline with site templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.autodoc.base import DocElement
from bengal.autodoc.manifest import AutodocManifest
from bengal.utils.logger import get_logger
from bengal.utils.url_strategy import URLStrategy

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


class AutodocOrchestrator:
    """
    Generates autodoc pages from manifest during site build.

    Similar to TaxonomyOrchestrator - loads serialized data (manifest)
    and creates Page objects that render through normal pipeline.

    Architecture:
    1. Load manifest (saved by `bengal utils autodoc`)
    2. Deserialize DocElements
    3. Create Page objects with _api_doc metadata
    4. Create section hierarchy
    5. Pages render during normal build with site templates
    """

    def __init__(self, site: Site):
        """
        Initialize autodoc orchestrator.

        Args:
            site: Site instance
        """
        self.site = site
        self.url_strategy = URLStrategy()

    def generate_autodoc_pages(self) -> tuple[list[Section], list[Page]]:
        """
        Load all manifests and generate virtual pages.

        Loads both python-api and cli manifests (if they exist).

        Returns:
            Tuple of (sections, pages) to add to site
        """
        logger.info("autodoc_pages_generation_start")

        all_pages = []
        doc_types = ["python-api", "cli"]

        # Load each manifest type
        for doc_type in doc_types:
            try:
                manifest = AutodocManifest.load_by_type(self.site.root_path, doc_type)

                if not manifest:
                    logger.debug("autodoc_manifest_not_found", doc_type=doc_type)
                    continue

                if not manifest.pages:
                    logger.debug("autodoc_manifest_empty", doc_type=doc_type)
                    continue

                logger.info(
                    "autodoc_manifest_loaded",
                    doc_type=doc_type,
                    page_count=len(manifest.pages),
                )

                # Generate pages from this manifest
                for manifest_page in manifest.pages:
                    page = self._create_autodoc_page(manifest_page)
                    if page:
                        all_pages.append(page)

            except Exception as e:
                logger.error(
                    "autodoc_manifest_load_failed",
                    doc_type=doc_type,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue

        if not all_pages:
            logger.debug("no_autodoc_pages_generated")
            return [], []

        # Build section hierarchy from all pages
        sections = self._create_section_hierarchy(all_pages)

        logger.info(
            "autodoc_pages_generated",
            pages=len(all_pages),
            sections=len(sections),
        )

        return sections, all_pages

    def _create_autodoc_page(self, manifest_page) -> Page | None:
        """
        Create a Page object from manifest entry.

        Similar to how TaxonomyOrchestrator creates tag pages.

        Args:
            manifest_page: AutodocPage from manifest

        Returns:
            Page object or None if creation fails
        """
        from bengal.core.page import Page

        try:
            # Deserialize DocElement
            doc_element = None
            if manifest_page.doc_element:
                doc_element = DocElement.from_dict(manifest_page.doc_element)

            # Create virtual path (like taxonomy does)
            virtual_path = self.url_strategy.make_virtual_path(
                self.site, "autodoc", manifest_page.url.strip("/")
            )

            # Create Page with _api_doc (like taxonomy uses _tag, _posts)
            # NOTE: Do NOT mark as _generated - autodoc pages are backed by real source
            # files tracked in the manifest and should participate in incremental builds
            page = Page(
                source_path=virtual_path,
                content=manifest_page.search_content,  # For search indexing
                metadata={
                    "title": manifest_page.title,
                    "type": "api-reference",
                    "template": "api-reference/single.html",
                    "_virtual": True,
                    "_api_doc": doc_element,  # DocElement for template!
                    "qualified_name": doc_element.qualified_name if doc_element else "",
                },
            )

            # Set output path (like taxonomy does)
            # URL: /api/core/site/ -> output: public/api/core/site/index.html
            url_path = manifest_page.url.strip("/")
            page.output_path = self.site.output_dir / url_path / "index.html"
            page._site = self.site

            logger.debug(
                "autodoc_page_created",
                qualified_name=doc_element.qualified_name if doc_element else "unknown",
                url=manifest_page.url,
            )

            return page

        except Exception as e:
            logger.error(
                "autodoc_page_creation_failed",
                url=manifest_page.url,
                error=str(e)[:200],
            )
            return None

    def _create_section_index_page(self, section: Section, section_key: str) -> None:
        """
        Create an index page for a top-level autodoc section.

        Args:
            section: Section to create index for (api, cli)
            section_key: Section key ("api", "cli")
        """
        from bengal.core.page import Page

        # Get display name from config if available, otherwise use defaults
        autodoc_config = self.site.config.get("autodoc", {})
        if section_key == "api" and "python" in autodoc_config:
            display_name = autodoc_config["python"].get("display_name", "API Reference")
        elif section_key == "cli" and "cli" in autodoc_config:
            display_name = autodoc_config["cli"].get("display_name", "CLI Reference")
        else:
            # Fallback to default titles
            title_map = {
                "api": "API Reference",
                "cli": "CLI Reference",
            }
            display_name = title_map.get(section_key, section_key.upper())

        # Create virtual index page
        virtual_path = section.path / "_index.md"

        # Use appropriate type and template based on section
        if section_key == "cli":
            page_type = "cli-reference"
            template = "cli-reference/list.html"
        else:
            page_type = "api-reference"
            template = "api-reference/list.html"

        index_page = Page(
            source_path=virtual_path,
            content="",  # No content needed - template will render page list
            metadata={
                "title": display_name,
                "type": page_type,
                "template": template,
                "_virtual": True,
                "_section_index": True,  # Mark as section index
                "section_key": section_key,
            },
        )

        # Set output path and site reference
        index_page._site = self.site
        index_page.output_path = self.site.output_dir / section_key / "index.html"

        # Set as section's index page
        section.index_page = index_page

        logger.debug(
            "autodoc_section_index_created",
            section=section_key,
            title=index_page.metadata["title"],
            url=f"/{section_key}/",
        )

    def _create_section_hierarchy(self, pages: list[Page]) -> list[Section]:
        """
        Build section hierarchy from autodoc pages.

        Creates virtual sections for /api/, /api/core/, /cli/, etc.

        Args:
            pages: List of autodoc pages

        Returns:
            List of top-level sections
        """
        from bengal.core.section import Section

        sections_dict: dict[str, Section] = {}

        # Group pages by URL hierarchy
        for page in pages:
            url = page.metadata.get("url", page.url)
            url_parts = [p for p in url.strip("/").split("/") if p]

            if not url_parts:
                continue

            # Create all parent sections
            for i in range(len(url_parts)):
                section_path_parts = url_parts[: i + 1]
                section_key = "/".join(section_path_parts)

                if section_key not in sections_dict:
                    # Create virtual section
                    dummy_section_path = self.site.root_path / "content" / Path(*section_path_parts)

                    # Get display name from config for top-level sections
                    section_title = section_path_parts[-1].upper()  # Default: "api" -> "API"
                    if "/" not in section_key:  # Top-level section (api, cli)
                        autodoc_config = self.site.config.get("autodoc", {})
                        if section_key == "api" and "python" in autodoc_config:
                            section_title = autodoc_config["python"].get("display_name", "API Reference")
                        elif section_key == "cli" and "cli" in autodoc_config:
                            section_title = autodoc_config["cli"].get("display_name", "CLI Reference")

                    section = Section(
                        name=section_path_parts[-1],
                        path=dummy_section_path,
                        metadata={
                            "title": section_title,
                            "_virtual": True,
                            "_generated": True,
                        },
                    )
                    section._site = self.site
                    sections_dict[section_key] = section

                    # Link to parent section
                    if i > 0:
                        parent_key = "/".join(section_path_parts[:-1])
                        parent_section = sections_dict.get(parent_key)
                        if parent_section:
                            parent_section.add_subsection(section)

            # Add page to its deepest section
            if len(url_parts) > 1:
                parent_key = "/".join(url_parts[:-1])
                parent_section = sections_dict.get(parent_key)
                if parent_section:
                    parent_section.add_page(page)
            else:
                section_key = url_parts[0]
                section = sections_dict.get(section_key)
                if section:
                    section.add_page(page)

        # Create index pages for top-level sections
        for section_key, section in sections_dict.items():
            if "/" not in section_key:  # Top-level only (api, cli)
                self._create_section_index_page(section, section_key)

        # Return only top-level sections
        top_level_sections = [s for key, s in sections_dict.items() if "/" not in key]

        logger.debug(
            "autodoc_sections_created",
            top_level=len(top_level_sections),
            total=len(sections_dict),
        )

        return top_level_sections
