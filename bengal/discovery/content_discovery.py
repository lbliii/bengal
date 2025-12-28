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
    - bengal/discovery/directory_walker.py: Directory walking logic
    - bengal/discovery/content_parser.py: Content file parsing
    - bengal/discovery/section_builder.py: Section building and sorting
    - bengal/core/page/: Page, PageProxy, and PageCore data models
    - bengal/core/section.py: Section data model
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.page import Page, PageProxy
from bengal.core.section import Section
from bengal.discovery.content_parser import ContentParser
from bengal.discovery.directory_walker import DirectoryWalker
from bengal.discovery.section_builder import SectionBuilder
from bengal.utils.logger import get_logger
from bengal.utils.workers import WorkloadType, get_optimal_workers

logger = get_logger(__name__)

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
        """
        self.content_dir = content_dir
        self.site = site
        self.sections: list[Section] = []
        self.pages: list[Page] = []
        self.current_section: Section | None = None
        self._strict_validation = strict_validation
        self._build_context = build_context

        # Initialize helper components (composition)
        self._walker = DirectoryWalker(content_dir, site)
        self._parser = ContentParser(
            content_dir,
            collections=collections,
            strict_validation=strict_validation,
            build_context=build_context,
        )
        self._section_builder = SectionBuilder(site)

        # Thread pool for parallel processing (initialized during discovery)
        self._executor: ThreadPoolExecutor | None = None

    @property
    def _validation_errors(self) -> list[tuple[Path, str, list[Any]]]:
        """Get validation errors from parser (backward compatibility)."""
        return self._parser.validation_errors

    @property
    def _visited_inodes(self) -> set[tuple[int, int]]:
        """Get visited inodes from walker (backward compatibility)."""
        return self._walker.visited_inodes

    @property
    def _collections(self) -> dict[str, CollectionConfig[Any]]:
        """Get collections from parser (backward compatibility)."""
        return self._parser._collections

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
        """
        if use_cache and cache:
            return self._discover_with_cache(cache)
        else:
            return self._discover_full()

    def _discover_full(self) -> tuple[list[Section], list[Page]]:
        """Full discovery - discover all pages completely."""
        logger.info("content_discovery_start", content_dir=str(self.content_dir))

        # Reset for new discovery
        self._walker.reset()
        self._section_builder.sections = []
        self._section_builder.pages = []

        # Check for PyYAML C extensions
        self._check_yaml_extensions()

        if not self.content_dir.exists():
            from bengal.errors import BengalDiscoveryError, ErrorCode, record_error

            error = BengalDiscoveryError(
                f"Content directory not found: {self.content_dir}",
                code=ErrorCode.D001,
                file_path=self.content_dir,
                suggestion="Create content directory or check bengal.yaml config",
            )
            record_error(error, file_path=str(self.content_dir))
            logger.warning(
                "content_dir_missing",
                content_dir=str(self.content_dir),
                action="returning_empty",
                code="D001",
            )
            return self.sections, self.pages

        # Get i18n configuration
        i18n_config = self._get_i18n_config()

        # Initialize thread pool for parallel parsing (I/O-bound file discovery)
        max_workers = get_optimal_workers(
            100,  # Estimate - content discovery typically processes many files
            workload_type=WorkloadType.IO_BOUND,
            config_override=self.site.config.get("max_workers"),
        )
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        try:
            # Walk top-level items
            for item in sorted(self.content_dir.iterdir()):
                if self._walker.should_skip_item(item):
                    continue

                # Detect language-root directories for i18n
                if self._is_language_root(item, i18n_config):
                    for sub in sorted(item.iterdir()):
                        self._process_top_level_item(sub, current_lang=item.name)
                    continue

                current_lang = (
                    i18n_config.get("default_lang")
                    if i18n_config.get("strategy") == "prefix"
                    else None
                )
                self._process_top_level_item(item, current_lang=current_lang)
        finally:
            if self._executor:
                self._executor.shutdown(wait=True)
                self._executor = None

        # Sort sections
        self._section_builder.sort_all_sections()

        # Copy results from builder
        self.sections = self._section_builder.sections
        self.pages = self._section_builder.pages

        # Log metrics
        top_sections, top_pages = self._section_builder.get_top_level_counts()
        logger.info(
            "content_discovery_complete",
            total_sections=len(self.sections),
            total_pages=len(self.pages),
            top_level_sections=top_sections,
            top_level_pages=top_pages,
        )

        return self.sections, self.pages

    def _check_yaml_extensions(self) -> None:
        """Check for PyYAML C extensions (performance hint)."""
        try:
            import yaml  # type: ignore[import-untyped]  # noqa: F401

            has_libyaml = getattr(yaml, "__with_libyaml__", False)
            if not has_libyaml:
                logger.info(
                    "pyyaml_c_extensions_missing",
                    hint="Install pyyaml[libyaml] for faster frontmatter parsing",
                )
        except ImportError:
            pass
        except Exception as e:
            logger.debug("yaml_import_check_failed", error=str(e))

    def _get_i18n_config(self) -> dict[str, Any]:
        """Get i18n configuration from site config."""
        if not self.site or not isinstance(self.site.config, dict):
            return {}

        i18n = self.site.config.get("i18n", {}) or {}
        strategy = i18n.get("strategy", "none")
        content_structure = i18n.get("content_structure", "dir")
        default_lang = i18n.get("default_language", "en")

        language_codes: list[str] = []
        for entry in i18n.get("languages") or []:
            if isinstance(entry, dict) and "code" in entry:
                language_codes.append(entry["code"])
            elif isinstance(entry, str):
                language_codes.append(entry)

        if default_lang and default_lang not in language_codes:
            language_codes.append(default_lang)

        return {
            "strategy": strategy,
            "content_structure": content_structure,
            "default_lang": default_lang,
            "language_codes": language_codes,
        }

    def _is_language_root(self, item: Path, i18n_config: dict[str, Any]) -> bool:
        """Check if item is a language root directory."""
        return (
            i18n_config.get("strategy") == "prefix"
            and i18n_config.get("content_structure") == "dir"
            and item.is_dir()
            and item.name in i18n_config.get("language_codes", [])
        )

    def _process_top_level_item(self, item_path: Path, current_lang: str | None) -> list[Page]:
        """Process a top-level item (file or directory)."""
        produced_pages: list[Page] = []
        pending_pages: list[Any] = []

        if self._walker.should_skip_item(item_path):
            return produced_pages

        if item_path.is_file() and self._walker.is_content_file(item_path):
            if self._executor:
                pending_pages.append(
                    self._executor.submit(self._create_page, item_path, current_lang, None)
                )
            else:
                page = self._create_page(item_path, current_lang=current_lang, section=None)
                self._section_builder.pages.append(page)
                produced_pages.append(page)

        elif item_path.is_dir():
            if self._walker.is_versioning_infrastructure(item_path):
                section = self._section_builder.create_section(item_path)
                self._walk_directory(item_path, section, current_lang=current_lang)
                self._section_builder.add_versioned_sections_recursive(section)
                return produced_pages

            section = self._section_builder.create_section(item_path)
            self._walk_directory(item_path, section, current_lang=current_lang)
            self._section_builder.add_section(section)

        # Resolve pending futures
        produced_pages.extend(self._resolve_page_futures(pending_pages))
        return produced_pages

    def _walk_directory(
        self, directory: Path, parent_section: Section, current_lang: str | None = None
    ) -> None:
        """Recursively walk a directory to discover content."""
        if not directory.exists():
            return

        if self._walker.check_symlink_loop(directory):
            return

        file_futures = []
        for item in self._walker.list_directory(directory):
            if self._walker.should_skip_item(item):
                continue

            if item.is_file() and self._walker.is_content_file(item):
                if self._executor:
                    file_futures.append(
                        self._executor.submit(self._create_page, item, current_lang, parent_section)
                    )
                else:
                    page = self._create_page(
                        item, current_lang=current_lang, section=parent_section
                    )
                    parent_section.add_page(page)
                    self._section_builder.pages.append(page)

            elif item.is_dir():
                section = self._section_builder.create_section(item)
                self._walk_directory(item, section, current_lang=current_lang)
                if section.pages or section.subsections:
                    parent_section.add_subsection(section)

        # Resolve futures and add to section
        for _page in self._resolve_page_futures(file_futures, parent_section):
            pass  # Pages added in _resolve_page_futures

    def _resolve_page_futures(
        self, futures: list[Any], section: Section | None = None
    ) -> list[Page]:
        """Resolve page creation futures and add to section/builder."""
        from bengal.errors import with_error_recovery

        pages: list[Page] = []
        for fut in futures:

            def get_page_result(f=fut):
                return f.result()

            page = with_error_recovery(
                get_page_result,
                on_error=lambda e: None,
                error_types=(Exception,),
                strict_mode=self._strict_validation,
                logger=logger,
            )
            if page is not None:
                if section:
                    section.add_page(page)
                self._section_builder.pages.append(page)
                pages.append(page)

        return pages

    def _create_page(
        self, file_path: Path, current_lang: str | None = None, section: Section | None = None
    ) -> Page:
        """Create a Page object from a file with robust error handling."""
        try:
            content, metadata = self._parser.parse_file(file_path)
            metadata = self._parser.validate_against_collection(file_path, metadata)

            page = Page(
                source_path=file_path,
                content=content,
                metadata=metadata,
            )

            if self.site is not None:
                page._site = self.site

            if section is not None:
                page._section = section

            # i18n enrichment
            self._enrich_page_i18n(page, file_path, current_lang, metadata)

            # Versioning enrichment
            self._enrich_page_versioning(page, file_path)

            logger.debug(
                "page_created",
                page_path=str(file_path),
                has_metadata=bool(metadata),
                has_parse_error="_parse_error" in metadata,
            )

            return page
        except Exception as e:
            from bengal.errors import BengalDiscoveryError, ErrorCode, record_error

            error = BengalDiscoveryError(
                f"Failed to create page from {file_path}",
                code=ErrorCode.D002,
                file_path=file_path,
                original_error=e,
                suggestion="Check file encoding and frontmatter syntax",
            )
            record_error(error, file_path=str(file_path))
            logger.error(
                "page_creation_failed",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
                code="D002",
            )
            raise

    def _enrich_page_i18n(
        self, page: Page, file_path: Path, current_lang: str | None, metadata: dict[str, Any]
    ) -> None:
        """Enrich page with i18n attributes."""
        try:
            if current_lang:
                page.lang = current_lang
            if isinstance(metadata, dict):
                if metadata.get("lang"):
                    page.lang = str(metadata.get("lang"))
                if metadata.get("translation_key"):
                    page.translation_key = str(metadata.get("translation_key"))

            # Derive translation key for dir structure
            if self.site and isinstance(self.site.config, dict):
                i18n = self.site.config.get("i18n", {}) or {}
                strategy = i18n.get("strategy", "none")
                content_structure = i18n.get("content_structure", "dir")
                if not page.translation_key and strategy == "prefix" and content_structure == "dir":
                    try:
                        rel = file_path.relative_to(self.content_dir)
                    except ValueError:
                        rel = Path(file_path.name)
                    parts = list(rel.parts)
                    if parts:
                        if current_lang and parts[0] == current_lang:
                            key_parts = parts[1:]
                        else:
                            key_parts = parts
                        if key_parts:
                            key = str(Path(*key_parts).with_suffix(""))
                            page.translation_key = key
        except Exception as e:
            logger.debug(
                "page_i18n_enrichment_failed",
                page=str(file_path),
                error=str(e),
            )

    def _enrich_page_versioning(self, page: Page, file_path: Path) -> None:
        """Enrich page with versioning attributes."""
        if self.site is None or not getattr(self.site, "versioning_enabled", False):
            return

        version = self.site.version_config.get_version_for_path(file_path)
        if version:
            if page.metadata is None:
                page.metadata = {}
            page.metadata["_version"] = version.id
            page.version = version.id
            if page.core:
                object.__setattr__(page.core, "version", version.id)

    def _discover_with_cache(self, cache: Any) -> tuple[list[Section], list[Page]]:
        """Discover content with lazy loading from cache."""
        logger.info(
            "content_discovery_with_cache_start",
            content_dir=str(self.content_dir),
            cached_pages=len(cache.pages) if hasattr(cache, "pages") else 0,
        )

        sections, all_discovered_pages = self._discover_full()

        proxy_count = 0
        full_page_count = 0

        for i, page in enumerate(all_discovered_pages):
            cache_lookup_path = page.source_path
            if self.site and page.source_path.is_absolute():
                with contextlib.suppress(ValueError):
                    cache_lookup_path = page.source_path.relative_to(self.site.root_path)

            cached_metadata = cache.get_metadata(cache_lookup_path)

            if cached_metadata and self._cache_is_valid(page, cached_metadata):

                def make_loader(
                    source_path: Path, lang: str | None, section_path: Path | None
                ) -> Callable[[Any], Page]:
                    def loader(_: Any) -> Page:
                        section = None
                        if section_path and self.site is not None:
                            section = self.site.get_section_by_path(section_path)
                        return self._create_page(source_path, current_lang=lang, section=section)

                    return loader

                proxy = PageProxy(
                    source_path=page.source_path,
                    metadata=cached_metadata,
                    loader=make_loader(page.source_path, page.lang, page._section_path),
                )
                proxy._section_path = page._section_path
                proxy._site = page._site
                if page.output_path:
                    proxy.output_path = page.output_path

                all_discovered_pages[i] = proxy  # type: ignore[call-overload]
                proxy_count += 1

                logger.debug(
                    "page_proxy_created",
                    source_path=str(page.source_path),
                    from_cache=True,
                )
            else:
                full_page_count += 1

        self.pages = all_discovered_pages

        logger.info(
            "content_discovery_with_cache_complete",
            total_pages=len(all_discovered_pages),
            proxies=proxy_count,
            full_pages=full_page_count,
            sections=len(sections),
        )

        return sections, all_discovered_pages

    def _cache_is_valid(self, page: Page, cached_metadata: Any) -> bool:
        """Check if cached metadata is still valid for a page."""
        if page.title != cached_metadata.title:
            return False
        if set(page.tags or []) != set(cached_metadata.tags or []):
            return False
        page_date_str = page.date.isoformat() if page.date else None
        if page_date_str != cached_metadata.date:
            return False
        if page.slug != cached_metadata.slug:
            return False
        page_section_str = str(page._section_path) if page._section_path else None
        return bool(page_section_str == cached_metadata.section)

    # Backward compatibility methods
    def _is_content_file(self, file_path: Path) -> bool:
        """Backward compatibility wrapper for DirectoryWalker.is_content_file."""
        return self._walker.is_content_file(file_path)

    def _parse_content_file(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Backward compatibility wrapper for ContentParser.parse_file."""
        return self._parser.parse_file(file_path)

    def _validate_against_collection(
        self, file_path: Path, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Backward compatibility wrapper for ContentParser.validate_against_collection."""
        return self._parser.validate_against_collection(file_path, metadata)

    def _get_collection_for_file(
        self, file_path: Path
    ) -> tuple[str | None, CollectionConfig[Any] | None]:
        """Backward compatibility wrapper for ContentParser._get_collection_for_file."""
        return self._parser._get_collection_for_file(file_path)

    def _extract_content_skip_frontmatter(self, file_content: str) -> str:
        """Backward compatibility wrapper for ContentParser._extract_content_skip_frontmatter."""
        return self._parser._extract_content_skip_frontmatter(file_content)

    def _sort_all_sections(self) -> None:
        """Backward compatibility wrapper for SectionBuilder.sort_all_sections."""
        self._section_builder.sort_all_sections()

    def _add_versioned_sections_recursive(self, version_container: Section) -> None:
        """Backward compatibility wrapper for SectionBuilder.add_versioned_sections_recursive."""
        self._section_builder.add_versioned_sections_recursive(version_container)
