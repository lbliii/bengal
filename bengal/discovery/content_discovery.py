"""
Content discovery - finds and organizes pages and sections.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import frontmatter

from bengal.core.page import Page, PageProxy
from bengal.core.section import Section
from bengal.utils.logger import get_logger


class ContentDiscovery:
    """
    Discovers and organizes content files into pages and sections.

    Notes:
    - YAML errors in front matter are downgraded to debug; we fall back to using the content
      and synthesize minimal metadata to keep the build progressing.
    - UTF-8 BOM is stripped at read time by `bengal.utils.file_io.read_text_file` to avoid
      confusing the YAML/front matter parser.
    - I18n dir-prefix strategy is supported (e.g., `content/en/...`); hidden files/dirs are
      skipped except `_index.md`.
    - Parsing uses a thread pool for concurrency; unchanged pages can be represented as
      `PageProxy` in lazy modes.
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
        # Deprecated: do not store mutable current section on the instance; pass explicitly
        self.current_section: Section | None = None

    def discover(
        self,
        use_cache: bool = False,
        cache: Any | None = None,
    ) -> tuple[list[Section], list[Page]]:
        """
        Discover all content in the content directory.

        Supports optional lazy loading with PageProxy for incremental builds.

        Args:
            use_cache: Whether to use PageDiscoveryCache for lazy loading
            cache: PageDiscoveryCache instance (if use_cache=True)

        Returns:
            Tuple of (sections, pages)

        Note:
            When use_cache=True and cache is provided:
            - Unchanged pages are returned as PageProxy (metadata only, lazy load on demand)
            - Changed pages are fully parsed and returned as normal Page objects
            - This saves disk I/O and parsing time for unchanged pages

            When use_cache=False (default):
            - All pages are fully discovered and parsed (current behavior)
            - Backward compatible - no changes to calling code needed
        """
        if use_cache and cache:
            return self._discover_with_cache(cache)
        else:
            return self._discover_full()

    def _discover_full(self) -> tuple[list[Section], list[Page]]:
        """
        Full discovery (current behavior) - discover all pages completely.

        Returns:
            Tuple of (sections, pages)
        """
        self.logger.info("content_discovery_start", content_dir=str(self.content_dir))

        # One-time performance hint: check if PyYAML has C extensions
        try:
            import yaml  # noqa: F401

            has_libyaml = getattr(yaml, "__with_libyaml__", False)
            if not has_libyaml:
                self.logger.info(
                    "pyyaml_c_extensions_missing",
                    hint="Install pyyaml[libyaml] for faster frontmatter parsing",
                )
        except Exception:
            # If yaml isn't importable here, frontmatter will raise later; do nothing now
            pass

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
        def process_item(item_path: Path, current_lang: str | None) -> list[Page]:
            pending_pages: list = []
            produced_pages: list[Page] = []
            # Skip hidden files and directories
            if item_path.name.startswith((".", "_")) and item_path.name not in (
                "_index.md",
                "_index.markdown",
            ):
                return produced_pages
            if item_path.is_file() and self._is_content_file(item_path):
                # Defer parsing to thread pool
                if not hasattr(self, "_executor") or self._executor is None:
                    # Fallback to synchronous create if executor not initialized
                    page = self._create_page(item_path, current_lang=current_lang, section=None)
                    self.pages.append(page)
                    produced_pages.append(page)
                else:
                    pending_pages.append(
                        self._executor.submit(self._create_page, item_path, current_lang, None)
                    )
            elif item_path.is_dir():
                section = Section(
                    name=item_path.name,
                    path=item_path,
                )
                self._walk_directory(item_path, section, current_lang=current_lang)
                if section.pages or section.subsections:
                    self.sections.append(section)
            # Resolve any pending page futures (top-level pages not in a section)
            for fut in pending_pages:
                try:
                    page = fut.result()
                    self.pages.append(page)
                    produced_pages.append(page)
                except Exception as e:  # pragma: no cover - guarded logging
                    self.logger.error(
                        "page_future_failed",
                        path=str(item_path),
                        error=str(e),
                        error_type=type(e).__name__,
                    )

            return produced_pages

        # Initialize a thread pool for parallel file parsing
        max_workers = min(8, (os.cpu_count() or 4))
        self._executor: ThreadPoolExecutor | None = ThreadPoolExecutor(max_workers=max_workers)

        top_level_results: list[Page] = []

        try:
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
                        top_level_results.extend(process_item(sub, current_lang=current_lang))
                    continue

                # Non-language-root items → treat as default language (or None if not configured)
                current_lang = (
                    default_lang if (strategy == "prefix" and content_structure == "dir") else None
                )
                top_level_results.extend(process_item(item, current_lang=current_lang))
        finally:
            # Ensure all threads are joined
            if self._executor:
                self._executor.shutdown(wait=True)
                self._executor = None

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

    def _discover_with_cache(self, cache: Any) -> tuple[list[Section], list[Page]]:
        """
        Discover content with lazy loading from cache.

        Uses PageProxy for unchanged pages (metadata only) and parses changed pages.

        Args:
            cache: PageDiscoveryCache instance

        Returns:
            Tuple of (sections, pages) with mixed Page and PageProxy objects
        """
        self.logger.info(
            "content_discovery_with_cache_start",
            content_dir=str(self.content_dir),
            cached_pages=len(cache.pages) if hasattr(cache, "pages") else 0,
        )

        # First, do a full discovery to find all files and sections
        # We need sections regardless, and we need to know which files exist
        sections, all_discovered_pages = self._discover_full()

        # Now, enhance with cache for unchanged pages
        proxy_count = 0
        full_page_count = 0

        for i, page in enumerate(all_discovered_pages):
            # Check if this page is in cache
            cached_metadata = cache.get_metadata(page.source_path)

            if cached_metadata and self._cache_is_valid(page, cached_metadata):
                # Page is unchanged - create PageProxy instead
                def make_loader(source_path, current_lang=page.lang, section=page._section):
                    def loader(_):
                        # Load full page from disk when needed
                        return self._create_page(
                            source_path, current_lang=current_lang, section=section
                        )

                    return loader

                proxy = PageProxy(
                    source_path=page.source_path,
                    metadata=cached_metadata,
                    loader=make_loader(page.source_path),
                )

                # Copy section and site relationships
                proxy._section = page._section
                proxy._site = page._site

                # Copy output_path for postprocessing (needed for .txt/.json generation)
                if page.output_path:
                    proxy.output_path = page.output_path

                # Replace full page with proxy
                all_discovered_pages[i] = proxy
                proxy_count += 1

                self.logger.debug(
                    "page_proxy_created",
                    source_path=str(page.source_path),
                    from_cache=True,
                )
            else:
                # Page is changed or not in cache - keep as full Page
                full_page_count += 1

        # Update self.pages with the mixed list
        self.pages = all_discovered_pages

        self.logger.info(
            "content_discovery_with_cache_complete",
            total_pages=len(all_discovered_pages),
            proxies=proxy_count,
            full_pages=full_page_count,
            sections=len(sections),
        )

        return sections, all_discovered_pages

    def _cache_is_valid(self, page: Page, cached_metadata: Any) -> bool:
        """
        Check if cached metadata is still valid for a page.

        Args:
            page: Discovered page
            cached_metadata: Cached metadata from PageDiscoveryCache

        Returns:
            True if cache is valid and can be used (unchanged page)
        """
        # Compare key metadata that indicates a change
        # If any of these changed, the page needs to be reparsed

        # Title
        if page.title != cached_metadata.title:
            return False

        # Tags
        if set(page.tags or []) != set(cached_metadata.tags or []):
            return False

        # Date
        page_date_str = page.date.isoformat() if page.date else None
        if page_date_str != cached_metadata.date:
            return False

        # Slug
        if page.slug != cached_metadata.slug:
            return False

        # Section
        page_section_str = str(page._section.path) if page._section else None
        return page_section_str == cached_metadata.section

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
        # Collect files in this directory for parallel page creation
        file_futures = []
        for item in sorted(directory.iterdir()):
            # Skip hidden files and directories
            if item.name.startswith((".", "_")) and item.name not in (
                "_index.md",
                "_index.markdown",
            ):
                continue

            if item.is_file() and self._is_content_file(item):
                # Create a page (in parallel when executor is available)
                if hasattr(self, "_executor") and self._executor is not None:
                    file_futures.append(
                        self._executor.submit(self._create_page, item, current_lang, parent_section)
                    )
                else:
                    page = self._create_page(
                        item, current_lang=current_lang, section=parent_section
                    )
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
                    # Note: Don't add to self.sections here - only top-level sections
                    # should be in self.sections. Subsections are accessible via parent.subsections

        # Resolve parallel page futures and attach to section
        for fut in file_futures:
            try:
                page = fut.result()
                parent_section.add_page(page)
                self.pages.append(page)
            except Exception as e:  # pragma: no cover - guarded logging
                self.logger.error(
                    "page_future_failed",
                    path=str(directory),
                    error=str(e),
                    error_type=type(e).__name__,
                )

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

    def _create_page(
        self, file_path: Path, current_lang: str | None = None, section: Section | None = None
    ) -> Page:
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

            # Create page without passing section into constructor
            page = Page(
                source_path=file_path,
                content=content,
                metadata=metadata,
            )

            # Attach section relationship post-construction when provided
            if section is not None:
                page._section = section

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
