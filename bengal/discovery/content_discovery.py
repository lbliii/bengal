"""
Content discovery - finds and organizes pages and sections.
"""

from pathlib import Path
from typing import Any

import frontmatter

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.utils.logger import get_logger


class ContentDiscovery:
    """
    Discovers and organizes content files into pages and sections.
    """

    def __init__(self, content_dir: Path, site: Any | None = None) -> None:
        """
        Initialize content discovery.

        Args:
            content_dir: Root content directory
        """
        self.content_dir = content_dir
        self.site = site  # Optional reference for accessing configuration (i18n, etc.)
        self.sections: list[Section] = []
        self.pages: list[Page] = []
        self.logger = get_logger(__name__)

    def discover(self) -> tuple[list[Section], list[Page]]:
        """
        Discover all content in the content directory.

        Returns:
            Tuple of (sections, pages)
        """
        self.logger.info("content_discovery_start", content_dir=str(self.content_dir))

        if not self.content_dir.exists():
            self.logger.warning(
                "content_dir_missing", content_dir=str(self.content_dir), action="returning_empty"
            )
            return self.sections, self.pages

        # i18n configuration (optional)
        i18n: dict[str, Any] = {}
        strategy = "none"
        content_structure = "dir"
        default_lang = None
        language_codes: list[str] = []
        if self.site and isinstance(self.site.config, dict):
            i18n = self.site.config.get("i18n", {}) or {}
            strategy = i18n.get("strategy", "none")
            content_structure = i18n.get("content_structure", "dir")
            default_lang = i18n.get("default_language", "en")
            bool(i18n.get("default_in_subdir", False))
            langs = i18n.get("languages") or []
            # languages may be list of dicts with 'code'
            for entry in langs:
                if isinstance(entry, dict) and "code" in entry:
                    language_codes.append(entry["code"])
                elif isinstance(entry, str):
                    language_codes.append(entry)
        # Ensure default language is present in codes
        if default_lang and default_lang not in language_codes:
            language_codes.append(default_lang)

        # Helper: process a single item with optional current language context
        def process_item(item_path: Path, current_lang: str | None) -> None:
            # Skip hidden files and directories
            if item_path.name.startswith((".", "_")) and item_path.name not in (
                "_index.md",
                "_index.markdown",
            ):
                return
            if item_path.is_file() and self._is_content_file(item_path):
                page = self._create_page(item_path, current_lang=current_lang)
                self.pages.append(page)
            elif item_path.is_dir():
                section = Section(
                    name=item_path.name,
                    path=item_path,
                )
                self._walk_directory(item_path, section, current_lang=current_lang)
                if section.pages or section.subsections:
                    self.sections.append(section)

        # Walk top-level items, with i18n-aware handling when enabled
        for item in sorted(self.content_dir.iterdir()):
            # Skip hidden files and directories
            if item.name.startswith((".", "_")) and item.name not in (
                "_index.md",
                "_index.markdown",
            ):
                continue

            # Detect language-root directories for i18n dir structure
            if (
                strategy == "prefix"
                and content_structure == "dir"
                and item.is_dir()
                and item.name in language_codes
            ):
                # Treat children of this directory as top-level within this language
                current_lang = item.name
                for sub in sorted(item.iterdir()):
                    process_item(sub, current_lang=current_lang)
                continue

            # Non-language-root items → treat as default language (or None if not configured)
            current_lang = (
                default_lang if (strategy == "prefix" and content_structure == "dir") else None
            )
            process_item(item, current_lang=current_lang)

        # Sort all sections by weight
        self._sort_all_sections()

        # Calculate metrics
        top_level_sections = len(
            [s for s in self.sections if not hasattr(s, "parent") or s.parent is None]
        )
        top_level_pages = len(
            [p for p in self.pages if not any(p in s.pages for s in self.sections)]
        )

        self.logger.info(
            "content_discovery_complete",
            total_sections=len(self.sections),
            total_pages=len(self.pages),
            top_level_sections=top_level_sections,
            top_level_pages=top_level_pages,
        )

        return self.sections, self.pages

    def _walk_directory(
        self, directory: Path, parent_section: Section, current_lang: str | None = None
    ) -> None:
        """
        Recursively walk a directory to discover content.

        Args:
            directory: Directory to walk
            parent_section: Parent section to add content to
        """
        if not directory.exists():
            return

        # Iterate through items in directory (non-recursively for control)
        for item in sorted(directory.iterdir()):
            # Skip hidden files and directories
            if item.name.startswith((".", "_")) and item.name not in (
                "_index.md",
                "_index.markdown",
            ):
                continue

            if item.is_file() and self._is_content_file(item):
                # Create a page
                page = self._create_page(item, current_lang=current_lang)
                parent_section.add_page(page)
                self.pages.append(page)

            elif item.is_dir():
                # Create a subsection
                section = Section(
                    name=item.name,
                    path=item,
                )

                # Recursively walk the subdirectory
                self._walk_directory(item, section, current_lang=current_lang)

                # Only add section if it has content
                if section.pages or section.subsections:
                    parent_section.add_subsection(section)
                    self.sections.append(section)

    def _is_content_file(self, file_path: Path) -> bool:
        """
        Check if a file is a content file.

        Args:
            file_path: Path to check

        Returns:
            True if it's a content file
        """
        content_extensions = {".md", ".markdown", ".rst", ".txt"}
        return file_path.suffix.lower() in content_extensions

    def _create_page(self, file_path: Path, current_lang: str | None = None) -> Page:
        """
        Create a Page object from a file with robust error handling.

        Handles:
        - Valid frontmatter
        - Invalid YAML in frontmatter
        - Missing frontmatter
        - File encoding issues
        - IO errors

        Args:
            file_path: Path to content file

        Returns:
            Page object (always succeeds with fallback metadata)

        Raises:
            IOError: Only if file cannot be read at all
        """
        try:
            content, metadata = self._parse_content_file(file_path)

            page = Page(
                source_path=file_path,
                content=content,
                metadata=metadata,
            )

            # i18n: assign language and translation key if available
            try:
                if current_lang:
                    page.lang = current_lang
                # Frontmatter overrides
                if isinstance(metadata, dict):
                    if metadata.get("lang"):
                        page.lang = str(metadata.get("lang"))
                    if metadata.get("translation_key"):
                        page.translation_key = str(metadata.get("translation_key"))
                # Derive translation key for dir structure: path without language segment
                if self.site and isinstance(self.site.config, dict):
                    i18n = self.site.config.get("i18n", {}) or {}
                    strategy = i18n.get("strategy", "none")
                    content_structure = i18n.get("content_structure", "dir")
                    i18n.get("default_language", "en")
                    bool(i18n.get("default_in_subdir", False))
                    if (
                        not page.translation_key
                        and strategy == "prefix"
                        and content_structure == "dir"
                    ):
                        content_dir = self.content_dir
                        rel = None
                        try:
                            rel = file_path.relative_to(content_dir)
                        except ValueError:
                            rel = file_path.name
                        rel_path = Path(rel)
                        parts = list(rel_path.parts)
                        if parts:
                            # If first part is a language code, strip it
                            if current_lang and parts[0] == current_lang:
                                key_parts = parts[1:]
                            else:
                                # Default language may be at root (no subdir)
                                key_parts = parts
                            if key_parts:
                                # Use path without extension for stability
                                key = str(Path(*key_parts).with_suffix(""))
                                page.translation_key = key
            except Exception:
                # Do not fail discovery on i18n enrichment errors
                pass

            self.logger.debug(
                "page_created",
                page_path=str(file_path),
                has_metadata=bool(metadata),
                has_parse_error="_parse_error" in metadata,
            )

            return page
        except Exception as e:
            self.logger.error(
                "page_creation_failed",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _parse_content_file(self, file_path: Path) -> tuple:
        """
        Parse content file with robust error handling.

        Args:
            file_path: Path to content file

        Returns:
            Tuple of (content, metadata)

        Raises:
            IOError: If file cannot be read
        """
        import yaml

        # Read file once using file_io utility for robust encoding handling
        from bengal.utils.file_io import read_text_file

        file_content = read_text_file(
            file_path, fallback_encoding="latin-1", on_error="raise", caller="content_discovery"
        )

        # Parse frontmatter
        try:
            post = frontmatter.loads(file_content)
            content = post.content
            metadata = dict(post.metadata)
            return content, metadata

        except yaml.YAMLError as e:
            # YAML syntax error in frontmatter - use debug to avoid noise
            self.logger.debug(
                "frontmatter_parse_failed",
                file_path=str(file_path),
                error=str(e),
                error_type="yaml_syntax",
                action="processing_without_metadata",
                suggestion="Fix frontmatter YAML syntax",
            )

            # Try to extract content (skip broken frontmatter)
            content = self._extract_content_skip_frontmatter(file_content)

            # Create minimal metadata for identification
            metadata = {
                "_parse_error": str(e),
                "_parse_error_type": "yaml",
                "_source_file": str(file_path),
                "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
            }

            return content, metadata

        except Exception as e:
            # Unexpected error
            self.logger.warning(
                "content_parse_unexpected_error",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
                action="using_full_file_as_content",
            )

            # Use entire file as content
            metadata = {
                "_parse_error": str(e),
                "_parse_error_type": "unknown",
                "_source_file": str(file_path),
                "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
            }

            return file_content, metadata

    def _extract_content_skip_frontmatter(self, file_content: str) -> str:
        """
        Extract content, skipping broken frontmatter section.

        Frontmatter is between --- delimiters at start of file.
        If parsing failed, skip the section entirely.

        Args:
            file_content: Full file content

        Returns:
            Content without frontmatter section
        """
        # Split on --- delimiters
        parts = file_content.split("---", 2)

        if len(parts) >= 3:
            # Format: --- frontmatter --- content
            # Return content (3rd part)
            return parts[2].strip()
        elif len(parts) == 2:
            # Format: --- frontmatter (no closing delimiter)
            # Return second part
            return parts[1].strip()
        else:
            # No frontmatter delimiters, return whole file
            return file_content.strip()

    def _sort_all_sections(self) -> None:
        """
        Sort all sections and their children by weight.

        This recursively sorts:
        - Pages within each section
        - Subsections within each section

        Called after content discovery is complete.
        """
        self.logger.debug("sorting_sections_by_weight", total_sections=len(self.sections))

        # Sort all sections recursively
        for section in self.sections:
            self._sort_section_recursive(section)

        # Also sort top-level sections
        self.sections.sort(key=lambda s: (s.metadata.get("weight", 0), s.title.lower()))

        self.logger.debug("sections_sorted", total_sections=len(self.sections))

    def _sort_section_recursive(self, section: Section) -> None:
        """
        Recursively sort a section and all its subsections.

        Args:
            section: Section to sort
        """
        # Sort this section's children
        section.sort_children_by_weight()

        # Recursively sort all subsections
        for subsection in section.subsections:
            self._sort_section_recursive(subsection)
