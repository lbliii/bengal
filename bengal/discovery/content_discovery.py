"""
Content discovery for Bengal SSG.

This module provides the ContentDiscovery class that finds and organizes
markdown content files into Page and Section hierarchies during site builds.

Key Features:
    - Parallel parsing via ThreadPoolExecutor for performance
    - Frontmatter parsing with YAML error recovery
    - i18n support (language detection from directory structure)
    - Content collection schema validation (opt-in)
    - Symlink loop detection via inode tracking
    - Content caching for build-integrated validation
    - Versioned documentation support (_versions/, _shared/)

Robustness:
    - YAML errors in frontmatter are downgraded to debug; content is preserved
    - UTF-8 BOM is stripped at read time to avoid parser confusion
    - Permission errors and missing directories are handled gracefully
    - Hidden files/directories are skipped (except _index.md)

Architecture:
    ContentDiscovery is responsible ONLY for finding and parsing content.
    Rendering, writing, and other operations are handled by orchestrators.
    The class integrates with BuildContext for content caching, eliminating
    redundant disk I/O during health checks.

Related:
    - bengal/core/page/: Page, PageProxy, and PageCore data models
    - bengal/core/section.py: Section data model
    - bengal/orchestration/: Build orchestration
    - bengal/collections.py: Content collection schemas
    - bengal/health/: Validators that consume cached content
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

import frontmatter  # type: ignore[import-untyped]

from bengal.config.defaults import get_max_workers
from bengal.core.page import Page, PageProxy
from bengal.core.section import Section
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.collections import CollectionConfig
    from bengal.utils.build_context import BuildContext


class ContentDiscovery:
    """
    Discovers and organizes content files into Page and Section hierarchies.

    This class walks the content directory, parses markdown files with frontmatter,
    and builds a structured representation of the site's content.

    Key Behaviors:
        - YAML errors in frontmatter are downgraded to debug level; content is
          preserved with synthesized minimal metadata to keep builds progressing.
        - UTF-8 BOM is stripped at read time to avoid parser confusion.
        - i18n directory-prefix strategy is supported (e.g., `content/en/...`).
        - Hidden files/directories are skipped except `_index.md` and versioning
          directories (`_versions/`, `_shared/`).
        - Parsing uses a ThreadPoolExecutor for concurrent file processing.
        - Unchanged pages can be represented as PageProxy for incremental builds.
        - Symlink loops are detected via inode tracking to prevent infinite recursion.
        - Content collections: When collections.py is present, frontmatter is
          validated against schemas during discovery (fail fast).

    Attributes:
        content_dir: Root content directory to scan
        site: Optional Site reference for configuration access
        sections: List of discovered Section objects (populated after discover())
        pages: List of discovered Page objects (populated after discover())

    Example:
        >>> from bengal.discovery import ContentDiscovery
        >>> from pathlib import Path
        >>>
        >>> # Basic usage
        >>> discovery = ContentDiscovery(Path("content"))
        >>> sections, pages = discovery.discover()
        >>> print(f"Found {len(pages)} pages in {len(sections)} sections")
        >>>
        >>> # With caching for incremental builds
        >>> discovery = ContentDiscovery(Path("content"), site=site)
        >>> sections, pages = discovery.discover(use_cache=True, cache=page_cache)
    """

    def __init__(
        self,
        content_dir: Path,
        site: Any | None = None,
        *,
        collections: dict[str, CollectionConfig[Any]] | None = None,
        strict_validation: bool = True,
        build_context: BuildContext | None = None,
    ) -> None:
        """
        Initialize content discovery.

        Args:
            content_dir: Root content directory
            site: Optional Site reference for configuration access
            collections: Optional dict of collection configs for schema validation
            strict_validation: If True, raise errors on validation failure;
                if False, log warnings and continue
            build_context: Optional BuildContext for caching content during discovery.
                          When provided, raw file content is cached for later use by
                          validators, eliminating redundant disk I/O during health checks.
        """
        self.content_dir = content_dir
        self.site = site  # Optional reference for accessing configuration (i18n, etc.)
        self.sections: list[Section] = []
        self.pages: list[Page] = []
        self.logger = get_logger(__name__)
        # Do not store mutable current section on the instance; pass explicitly
        self.current_section: Section | None = None
        # Symlink loop detection: track visited (device, inode) pairs
        self._visited_inodes: set[tuple[int, int]] = set()
        # Content collections for schema validation
        self._collections = collections or {}
        self._strict_validation = strict_validation
        # Track validation errors for reporting
        self._validation_errors: list[tuple[Path, str, list[Any]]] = []
        # BuildContext for content caching (build-integrated validation)
        self._build_context = build_context

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

        # Reset symlink loop detection set for new discovery
        self._visited_inodes.clear()

        # One-time performance hint: check if PyYAML has C extensions
        try:
            import yaml  # type: ignore[import-untyped]  # noqa: F401

            has_libyaml = getattr(yaml, "__with_libyaml__", False)
            if not has_libyaml:
                self.logger.info(
                    "pyyaml_c_extensions_missing",
                    hint="Install pyyaml[libyaml] for faster frontmatter parsing",
                )
        except ImportError:
            # If yaml isn't importable here, frontmatter will raise later; do nothing now
            pass
        except Exception as e:
            # Unexpected error during yaml import check
            self.logger.debug("yaml_import_check_failed", error=str(e))

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
            pending_pages: list[Any] = []
            produced_pages: list[Page] = []
            # Skip hidden files and directories
            # NOTE: We allow _index.md, and versioning directories (_versions, _shared) if enabled
            is_versioning_dir = item_path.name in ("_versions", "_shared") and getattr(
                self.site, "versioning_enabled", False
            )
            if (
                item_path.name.startswith((".", "_"))
                and item_path.name not in ("_index.md", "_index.markdown")
                and not is_versioning_dir
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
                # Skip _versions and _shared directories themselves - they're versioning infrastructure
                # Their contents (like _versions/v1/docs/) will be discovered as separate sections
                if item_path.name in ("_versions", "_shared"):
                    # Still walk the directory to discover content inside, but don't add _versions/_shared as a section
                    section = Section(
                        name=item_path.name,
                        path=item_path,
                        _site=self.site,
                    )
                    self._walk_directory(item_path, section, current_lang=current_lang)
                    # Don't add _versions/_shared itself as a section
                    # BUT we need to add its nested content sections (e.g., _versions/v1/docs) to self.sections
                    # so they're accessible for version-filtered navigation
                    self._add_versioned_sections_recursive(section)
                    return produced_pages

                section = Section(
                    name=item_path.name,
                    path=item_path,
                    _site=self.site,
                )
                self._walk_directory(item_path, section, current_lang=current_lang)
                if section.pages or section.subsections:
                    self.sections.append(section)
            # Resolve any pending page futures (top-level pages not in a section)
            from bengal.errors import with_error_recovery

            strict_mode = self._strict_validation

            for fut in pending_pages:

                def get_page_result(f=fut):  # Capture fut in closure
                    return f.result()

                page = with_error_recovery(
                    get_page_result,
                    on_error=lambda e: None,  # Skip failed pages, continue processing others
                    error_types=(Exception,),
                    strict_mode=strict_mode,
                    logger=self.logger,
                )
                if page is not None:
                    self.pages.append(page)
                    produced_pages.append(page)

            return produced_pages

        # Initialize a thread pool for parallel file parsing
        # Use auto-detected workers but cap at 8 for discovery (I/O bound)
        max_workers = min(8, get_max_workers())
        self._executor: ThreadPoolExecutor | None = ThreadPoolExecutor(max_workers=max_workers)

        top_level_results: list[Page] = []

        try:
            # Walk top-level items, with i18n-aware handling when enabled
            for item in sorted(self.content_dir.iterdir()):
                # Skip hidden files and directories
                # NOTE: We allow _index.md, and versioning directories (_versions, _shared) if enabled
                is_versioning_dir = item.name in ("_versions", "_shared") and getattr(
                    self.site, "versioning_enabled", False
                )
                if (
                    item.name.startswith((".", "_"))
                    and item.name not in ("_index.md", "_index.markdown")
                    and not is_versioning_dir
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
                    current_lang: str | None = item.name
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
            # Cache stores relative paths (after normalize_core_paths), so convert to relative
            cache_lookup_path = page.source_path
            if self.site and page.source_path.is_absolute():
                with contextlib.suppress(ValueError):
                    cache_lookup_path = page.source_path.relative_to(self.site.root_path)

            cached_metadata = cache.get_metadata(cache_lookup_path)

            if cached_metadata and self._cache_is_valid(page, cached_metadata):
                # Page is unchanged - create PageProxy instead
                # Capture page.lang and page._section_path at call time to avoid closure issues
                # where loop variables would otherwise be shared across iterations
                def make_loader(
                    source_path: Path, current_lang: str | None, section_path: Path | None
                ) -> Callable[[Any], Page]:
                    def loader(_: Any) -> Page:
                        # Resolve section from path when loading
                        section = None
                        if section_path and self.site is not None:
                            section = self.site.get_section_by_path(section_path)
                        # Load full page from disk when needed
                        return self._create_page(
                            source_path, current_lang=current_lang, section=section
                        )

                    return loader

                # Pass page.lang and page._section_path explicitly to bind current iteration values
                proxy = PageProxy(
                    source_path=page.source_path,
                    metadata=cached_metadata,
                    loader=make_loader(page.source_path, page.lang, page._section_path),
                )

                # Copy section path and site relationships (avoid triggering lazy lookup)
                proxy._section_path = page._section_path
                proxy._site = page._site

                # Copy output_path for postprocessing (needed for .txt/.json generation)
                if page.output_path:
                    proxy.output_path = page.output_path

                # Replace full page with proxy (PageProxy is compatible with Page)
                all_discovered_pages[i] = proxy  # type: ignore[call-overload]
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

        # Section (compare paths, not object identity)
        # Use _section_path directly to avoid triggering lazy lookup
        page_section_str = str(page._section_path) if page._section_path else None
        return bool(page_section_str == cached_metadata.section)

    def _add_versioned_sections_recursive(self, version_container: Section) -> None:
        """
        Extract content sections from _versions hierarchy and add to self.sections.

        The _versions directory structure is:
            _versions/
                v1/
                    docs/           <- This is a content section (add to self.sections)
                        about/      <- This is a subsection (already linked via docs)
                v2/
                    docs/

        We skip _versions itself and version-id directories (v1, v2), but add their
        content sections (docs, etc.) to self.sections so they're accessible for
        version-filtered navigation.

        Args:
            version_container: The _versions or _shared section after walking
        """
        # version_container is _versions - iterate its subsections (v1, v2, etc.)
        for version_section in version_container.subsections:
            # version_section is v1, v2, etc. - iterate its content sections
            for content_section in version_section.subsections:
                # content_section is docs, tutorials, etc. - add to self.sections
                if content_section.pages or content_section.subsections:
                    self.sections.append(content_section)
                    self.logger.debug(
                        "versioned_section_added",
                        section_name=content_section.name,
                        version=version_section.name,
                        page_count=len(content_section.pages),
                        subsection_count=len(content_section.subsections),
                    )

    def _walk_directory(
        self, directory: Path, parent_section: Section, current_lang: str | None = None
    ) -> None:
        """
        Recursively walk a directory to discover content.

        Uses inode tracking to detect and skip symlink loops.

        Args:
            directory: Directory to walk
            parent_section: Parent section to add content to
        """
        if not directory.exists():
            return

        # Check for symlink loops using inode tracking
        try:
            stat = directory.stat()
            inode_key = (stat.st_dev, stat.st_ino)

            if inode_key in self._visited_inodes:
                self.logger.warning(
                    "symlink_loop_detected",
                    path=str(directory),
                    action="skipping_to_prevent_infinite_recursion",
                )
                return

            self._visited_inodes.add(inode_key)
        except (OSError, PermissionError) as e:
            self.logger.warning(
                "directory_stat_failed",
                path=str(directory),
                error=str(e),
                error_type=type(e).__name__,
                action="skipping",
            )
            return

        # Iterate through items in directory (non-recursively for control)
        # Collect files in this directory for parallel page creation
        file_futures = []
        try:
            dir_items = sorted(directory.iterdir())
        except PermissionError as e:
            self.logger.warning(
                "directory_permission_denied",
                path=str(directory),
                error=str(e),
                action="skipping",
            )
            return

        for item in dir_items:
            # Skip hidden files and directories
            # NOTE: We allow _index.md, and versioning directories (_versions, _shared) if enabled
            is_versioning_dir = item.name in ("_versions", "_shared") and getattr(
                self.site, "versioning_enabled", False
            )
            if (
                item.name.startswith((".", "_"))
                and item.name not in ("_index.md", "_index.markdown")
                and not is_versioning_dir
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
                    _site=self.site,
                )

                # Recursively walk the subdirectory
                self._walk_directory(item, section, current_lang=current_lang)

                # Only add section if it has content
                if section.pages or section.subsections:
                    parent_section.add_subsection(section)
                    # Note: Don't add to self.sections here - only top-level sections
                    # should be in self.sections. Subsections are accessible via parent.subsections

        # Resolve parallel page futures and attach to section
        from bengal.errors import with_error_recovery

        strict_mode = self._strict_validation

        for fut in file_futures:

            def get_page_result(f=fut):  # Capture fut in closure
                return f.result()

            page = with_error_recovery(
                get_page_result,
                on_error=lambda e: None,  # Skip failed pages, continue processing others
                error_types=(Exception,),
                strict_mode=strict_mode,
                logger=self.logger,
            )
            if page is not None:
                parent_section.add_page(page)
                self.pages.append(page)

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

    def _validate_against_collection(
        self, file_path: Path, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate frontmatter against collection schema if applicable.

        Args:
            file_path: Path to content file
            metadata: Parsed frontmatter metadata

        Returns:
            Validated metadata (possibly with schema-enforced defaults)

        Raises:
            ContentValidationError: If strict_validation=True and validation fails
        """
        if not self._collections:
            return metadata

        # Find applicable collection
        collection_name, config = self._get_collection_for_file(file_path)

        if config is None:
            return metadata

        # Import here to avoid circular dependency
        from bengal.collections import ContentValidationError, SchemaValidator

        # Apply optional transform
        if config.transform:
            try:
                metadata = config.transform(metadata)
            except Exception as e:
                self.logger.warning(
                    "collection_transform_failed",
                    path=str(file_path),
                    collection=collection_name,
                    error=str(e),
                )

        # Validate
        validator = SchemaValidator(config.schema, strict=config.strict)
        result = validator.validate(metadata, source_file=file_path)

        if not result.valid:
            error_summary = result.error_summary
            self._validation_errors.append((file_path, collection_name or "", result.errors))

            if self._strict_validation:
                raise ContentValidationError(
                    message=f"Validation failed for {file_path}",
                    path=file_path,
                    errors=result.errors,
                    collection_name=collection_name,
                )
            else:
                self.logger.warning(
                    "collection_validation_failed",
                    path=str(file_path),
                    collection=collection_name,
                    errors=error_summary,
                    action="continuing_with_original_metadata",
                )
                return metadata

        # Return validated data as dict (from schema instance)
        if result.data is not None:
            # Convert validated instance back to dict for Page metadata
            from dataclasses import asdict, is_dataclass

            if is_dataclass(result.data) and not isinstance(result.data, type):
                return dict(asdict(result.data))
            elif hasattr(result.data, "model_dump"):
                # Pydantic model
                return dict(result.data.model_dump())

        return metadata

    def _get_collection_for_file(
        self, file_path: Path
    ) -> tuple[str | None, CollectionConfig[Any] | None]:
        """
        Find which collection a file belongs to based on its path.

        Args:
            file_path: Path to content file

        Returns:
            Tuple of (collection_name, CollectionConfig) or (None, None)
        """
        try:
            rel_path = file_path.relative_to(self.content_dir)
        except ValueError:
            return None, None

        for name, config in self._collections.items():
            try:
                # Check if file is under this collection's directory
                if config.directory is not None:
                    rel_path.relative_to(config.directory)
                    return name, config
            except ValueError:
                continue

        return None, None

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
        - Collection schema validation (when collections defined)

        Args:
            file_path: Path to content file

        Returns:
            Page object (always succeeds with fallback metadata)

        Raises:
            IOError: Only if file cannot be read at all
            ContentValidationError: If strict_validation=True and validation fails
        """
        try:
            content, metadata = self._parse_content_file(file_path)

            # Validate against collection schema if applicable
            metadata = self._validate_against_collection(file_path, metadata)

            # Create page without passing section into constructor
            page = Page(
                source_path=file_path,
                content=content,
                metadata=metadata,
            )

            # Set site reference for path-based section lookups
            if self.site is not None:
                page._site = self.site

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
                    if (
                        not page.translation_key
                        and strategy == "prefix"
                        and content_structure == "dir"
                    ):
                        content_dir = self.content_dir
                        rel: Path | str | None = None
                        try:
                            rel = file_path.relative_to(content_dir)
                        except ValueError:
                            rel = file_path.name
                        rel_path = Path(rel) if rel else file_path
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
            except Exception as e:
                # Do not fail discovery on i18n enrichment errors
                self.logger.debug(
                    "page_i18n_enrichment_failed",
                    page=str(file_path),
                    error=str(e),
                )

            # Versioning: assign version to page if versioning is enabled
            # Fast path: skip if versioning is disabled (most sites)
            if self.site is not None and getattr(self.site, "versioning_enabled", False):
                version = self.site.version_config.get_version_for_path(file_path)
                if version:
                    # Store version ID in page metadata for URL generation
                    if page.metadata is None:
                        page.metadata = {}
                    page.metadata["_version"] = version.id
                    # Set version attribute directly on page for URLStrategy and templates
                    page.version = version.id
                    # Also update PageCore if it exists
                    if page.core:
                        object.__setattr__(page.core, "version", version.id)

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

    def _parse_content_file(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """
        Parse content file with robust error handling.

        Caches raw content in BuildContext for later use by validators,
        eliminating redundant disk I/O during health checks.

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

        # Cache raw content for validators (build-integrated validation)
        # This eliminates 4+ seconds of redundant disk I/O during health checks
        if self._build_context is not None and file_content is not None:
            self._build_context.cache_content(file_path, file_content)

        # Parse frontmatter
        try:
            post = frontmatter.loads(file_content)
            content = post.content
            metadata = dict(post.metadata)
            return content, metadata

        except yaml.YAMLError as e:
            # YAML syntax error in frontmatter - use debug to avoid noise
            from bengal.errors import BengalDiscoveryError, ErrorContext, enrich_error

            context = ErrorContext(
                file_path=file_path,
                operation="parsing frontmatter",
                suggestion="Fix frontmatter YAML syntax",
                original_error=e,
            )
            # Enrich error for better error messages (context captured for logging)
            enrich_error(e, context, BengalDiscoveryError)

            self.logger.debug(
                "frontmatter_parse_failed",
                file_path=str(file_path),
                error=str(e),
                error_type="yaml_syntax",
                action="processing_without_metadata",
                suggestion="Fix frontmatter YAML syntax",
            )

            # Try to extract content (skip broken frontmatter)
            content = self._extract_content_skip_frontmatter(file_content or "")

            # Create minimal metadata for identification
            from bengal.utils.text import humanize_slug

            metadata = {
                "_parse_error": str(e),
                "_parse_error_type": "yaml",
                "_source_file": str(file_path),
                "title": humanize_slug(file_path.stem),
            }

            return content, metadata

        except Exception as e:
            # Unexpected error - enrich with context
            from bengal.errors import BengalDiscoveryError, ErrorContext, enrich_error

            context = ErrorContext(
                file_path=file_path,
                operation="parsing content file",
                suggestion="Check file encoding and format",
                original_error=e,
            )
            # Enrich error and collect in build stats if available
            enriched_error = enrich_error(e, context, BengalDiscoveryError)
            if self._build_context and hasattr(self._build_context, "build_stats"):
                build_stats = self._build_context.build_stats
                if build_stats:
                    build_stats.add_error(enriched_error, category="discovery")

            self.logger.warning(
                "content_parse_unexpected_error",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
                action="using_full_file_as_content",
            )

            # Use entire file as content
            from bengal.utils.text import humanize_slug

            metadata = {
                "_parse_error": str(e),
                "_parse_error_type": "unknown",
                "_source_file": str(file_path),
                "title": humanize_slug(file_path.stem),
            }

            return file_content or "", metadata

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
