"""
Page initialization and validation utilities.

This module provides the PageInitializer class that ensures pages are correctly
set up with all required references before use. It helps prevent common bugs
like missing `_site` references or unset `output_path` attributes.

Design Principles:
    - Fail fast: Catch initialization errors early, not during URL generation
    - Clear errors: Tell developers exactly what's wrong and how to fix it
    - Single responsibility: Only validates, doesn't create pages
    - Lightweight: Minimal logic, mostly validation checks

Architecture:
    PageInitializer is used by orchestrators after creating pages to validate
    they are ready for use. This separates page creation (discovery) from
    page validation (orchestration), maintaining Bengal's separation of concerns.

Related:
    - bengal/core/page/: Page data model
    - bengal/orchestration/: Orchestrators that use PageInitializer
    - bengal/discovery/content_discovery.py: Page creation during discovery
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site

logger = get_logger(__name__)


class PageInitializer:
    """
    Ensures pages are correctly initialized with all required references.

    Used by orchestrators after creating pages to validate they're ready for use.
    This helps catch configuration errors early rather than during URL generation
    or template rendering.

    Validation Checks:
        - Page has `_site` reference set (or sets it automatically)
        - Page has `output_path` set to an absolute path
        - Page URL generation works correctly

    Attributes:
        site: Site object to associate with pages

    Example:
        >>> from bengal.discovery.page_factory import PageInitializer
        >>>
        >>> # In an orchestrator
        >>> class MyOrchestrator:
        ...     def __init__(self, site):
        ...         self.site = site
        ...         self.initializer = PageInitializer(site)
        ...
        ...     def create_page(self, source_path: Path) -> Page:
        ...         page = Page(source_path=source_path, ...)
        ...         page.output_path = self.site.output_dir / "path" / "index.html"
        ...         self.initializer.ensure_initialized(page)  # Validate!
        ...         return page
    """

    def __init__(self, site: Site):
        """
        Initialize the page initializer.

        Args:
            site: Site object to associate with pages
        """
        self.site = site

    def ensure_initialized(self, page: Page) -> None:
        """
        Ensure a page is correctly initialized.

        Checks:
        1. Page has _site reference (or sets it)
        2. Page has output_path set
        3. Page URL generation works

        Args:
            page: Page to validate and initialize

        Raises:
            ValueError: If page is missing required attributes or URL generation fails
        """
        # Set site reference if missing
        if not page._site:
            page._site = self.site

        # Validate output_path is set
        if not page.output_path:
            from bengal.errors import BengalContentError

            raise BengalContentError(
                f"Page '{page.title}' has no output_path set. "
                f"Orchestrator must compute and set output_path before calling ensure_initialized().\n"
                f"Source: {page.source_path}",
                file_path=page.source_path,
                suggestion="Ensure the orchestrator computes output_path before calling ensure_initialized()",
            )

        # Validate output_path is absolute
        if not page.output_path.is_absolute():
            from bengal.errors import BengalContentError

            raise BengalContentError(
                f"Page '{page.title}' has relative output_path: {page.output_path}\n"
                f"Output paths must be absolute. "
                f"Use site.output_dir as base.",
                file_path=page.source_path,
                suggestion=f"Use site.output_dir ({self.site.output_dir}) as base for absolute paths",
            )

        # Verify URL generation works
        try:
            # Warn if output_path is outside site's output_dir; URL will fallback
            try:
                _ = page.output_path.relative_to(self.site.output_dir)
            except Exception as e:
                logger.warning(
                    "page_initializer_output_path_check_failed",
                    output_path=str(page.output_path),
                    output_dir=str(self.site.output_dir),
                    error=str(e),
                    error_type=type(e).__name__,
                    action="falling_back_to_slug_url",
                )
                print(
                    f"Warning: output_path {page.output_path} is not under output directory {self.site.output_dir}; "
                    f"falling back to slug-based URL"
                )
            # Use _path for validation (site-relative path without baseurl)
            rel_url = getattr(page, "_path", None) or f"/{page.slug}/"
            if not rel_url.startswith("/"):
                from bengal.errors import BengalContentError

                raise BengalContentError(
                    f"Generated URL doesn't start with '/': {rel_url}",
                    file_path=page.source_path,
                    suggestion="URLs must start with '/' - check page slug and output_path configuration",
                )
        except Exception as e:
            from bengal.errors import BengalContentError, ErrorContext, enrich_error

            context = ErrorContext(
                file_path=page.source_path,
                operation="generating page URL",
                suggestion="Check page slug, output_path, and site.output_dir configuration",
                original_error=e,
            )
            enriched = enrich_error(e, context, BengalContentError)
            raise enriched from e

    def ensure_initialized_for_section(self, page: Page, section: Section) -> None:
        """
        Ensure a page is initialized with section reference.

        Like ensure_initialized() but also sets and validates the section reference.
        Used for archive pages and section index pages.

        Args:
            page: Page to validate and initialize
            section: Section this page belongs to

        Raises:
            ValueError: If page is missing required attributes or validation fails
        """
        # First do standard initialization
        self.ensure_initialized(page)

        # Set section reference
        if not page._section:
            page._section = section
