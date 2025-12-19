"""
Template function for retrieving a page by path.

Used by tracks feature to resolve track item pages.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def _ensure_page_parsed(page: Page, site: Site) -> None:
    """
    Ensure a page is parsed if it hasn't been parsed yet.

    This is used when pages are accessed via get_page() from templates
    (e.g., track item pages) and need to be parsed on-demand.

    Args:
        page: Page to parse if needed
        site: Site instance for parser access
    """
    # Skip if already parsed
    if hasattr(page, "parsed_ast") and page.parsed_ast is not None:
        return

    # Skip if no content
    if not hasattr(page, "content") or not page.content:
        return

    # Lazy-create parser on site object for reuse
    if site._template_parser is None:
        from bengal.rendering.parsers import create_markdown_parser

        # Get parser engine from config (same logic as RenderingPipeline)
        markdown_engine = site.config.get("markdown_engine")
        if not markdown_engine:
            markdown_config = site.config.get("markdown", {})
            markdown_engine = markdown_config.get("parser", "mistune")

        site._template_parser = create_markdown_parser(markdown_engine)

        # Enable cross-references if available
        if hasattr(site, "xref_index") and hasattr(
            site._template_parser,
            "enable_cross_references",  # type: ignore[attr-defined]
        ):
            # Pass version_config for cross-version linking support [[v2:path]]
            version_config = getattr(site, "version_config", None)
            site._template_parser.enable_cross_references(site.xref_index, version_config)  # type: ignore[attr-defined]

    parser = site._template_parser

    # Determine if TOC is needed
    need_toc = True
    if page.metadata.get("toc") is False:
        need_toc = False
    else:
        # Quick heuristic: only generate TOC if markdown likely contains headings
        content_text = page.content or ""
        likely_has_atx = re.search(r"^(?:\s{0,3})(?:##|###|####)\s+.+", content_text, re.MULTILINE)
        if not likely_has_atx:
            likely_has_setext = re.search(
                r"^.+\n\s{0,3}(?:===+|---+)\s*$", content_text, re.MULTILINE
            )
            need_toc = bool(likely_has_setext)
        else:
            need_toc = True

    # Parse content
    try:
        context = {"page": page, "site": site, "config": site.config}

        if hasattr(parser, "parse_with_toc_and_context"):
            # Mistune with variable substitution (preferred)
            if page.metadata.get("preprocess") is False:
                # Parse without variable substitution
                if need_toc:
                    parsed_content, toc = parser.parse_with_toc(page.content, page.metadata)
                else:
                    parsed_content = parser.parse(page.content, page.metadata)
                    toc = ""
                # Escape template syntax
                parsed_content = parser._escape_template_syntax_in_html(parsed_content)
            else:
                # Parse with variable substitution
                if need_toc:
                    parsed_content, toc = parser.parse_with_toc_and_context(
                        page.content, page.metadata, context
                    )
                else:
                    parsed_content = parser.parse_with_context(page.content, page.metadata, context)
                    toc = ""
        elif hasattr(parser, "parse_with_toc"):
            # Fallback parser
            if need_toc:
                parsed_content, toc = parser.parse_with_toc(page.content, page.metadata)
            else:
                parsed_content = parser.parse(page.content, page.metadata)
                toc = ""
        else:
            # Basic parser
            parsed_content = parser.parse(page.content, page.metadata)
            toc = ""

        # Escape Jinja blocks
        if hasattr(parser, "_escape_jinja_blocks"):
            parsed_content = parser._escape_jinja_blocks(parsed_content)

        # Store parsed content
        page.parsed_ast = parsed_content
        if need_toc:
            page.toc = toc

        # Post-process: API doc enhancement (if applicable)
        try:
            from bengal.rendering.api_doc_enhancer import get_enhancer

            enhancer = get_enhancer()
            page_type = page.metadata.get("type")
            if enhancer and enhancer.should_enhance(page_type):
                page.parsed_ast = enhancer.enhance(page.parsed_ast, page_type)
        except Exception as e:
            logger.debug(
                "page_enhancement_failed",
                page_path=str(page.source_path) if hasattr(page, "source_path") else None,
                error=str(e),
                error_type=type(e).__name__,
                action="skipping_enhancement",
            )
            pass  # Enhancement is optional, don't fail if it errors

    except Exception as e:
        logger.warning(
            "get_page_parse_failed",
            path=str(page.source_path),
            error=str(e),
            error_type=type(e).__name__,
            action="using_raw_content",
        )
        # On parse failure, leave parsed_ast as None so template can fall back to content


def _build_lookup_maps(site: Site) -> None:
    """
    Build page lookup maps on the site object if not already built.

    Creates two maps for O(1) page lookups:
    - 'full': Full source path (str) -> Page
    - 'relative': Content-relative path (str) -> Page

    Args:
        site: Site instance to build maps on
    """
    if site._page_lookup_maps is not None:
        return

    by_full_path: dict[str, Page] = {}
    by_content_relative: dict[str, Page] = {}

    content_root = site.root_path / "content"

    for p in site.pages:
        # Full path
        by_full_path[str(p.source_path)] = p

        # Content relative
        try:
            rel = p.source_path.relative_to(content_root)
            # Normalize path separators to forward slashes for consistent lookup
            rel_str = str(rel).replace("\\", "/")
            by_content_relative[rel_str] = p
        except ValueError:
            # Path not relative to content root (maybe outside?), skip
            pass

    site._page_lookup_maps = {"full": by_full_path, "relative": by_content_relative}


def page_exists(path: str, site: Site) -> bool:
    """
    Check if a page exists without loading it.

    Uses cached lookup maps for O(1) existence check.
    More efficient than get_page() when you only need existence.

    Args:
        path: Page path (e.g., 'guides/setup.md' or 'guides/setup')
        site: Site instance

    Returns:
        True if page exists, False otherwise

    Example:
        {% if page_exists('guides/advanced') %}
          <a href="/guides/advanced/">Advanced Guide</a>
        {% endif %}
    """
    if not path:
        return False

    _build_lookup_maps(site)

    maps = site._page_lookup_maps
    normalized = path.replace("\\", "/")

    if normalized in maps["relative"]:
        return True
    if f"{normalized}.md" in maps["relative"]:
        return True
    if normalized.startswith("content/"):
        stripped = normalized[8:]  # len("content/") = 8
        return stripped in maps["relative"] or f"{stripped}.md" in maps["relative"]
    return False


def register(env: Environment, site: Site) -> None:
    """Register the get_page and page_exists functions with Jinja2 environment."""

    def page_exists_wrapper(path: str) -> bool:
        """Wrapper with site closure."""
        return page_exists(path, site)

    env.globals["page_exists"] = page_exists_wrapper

    def get_page(path: str) -> Page | None:
        """
        Get a page by its relative path or slug.

        Args:
            path: The relative path (e.g. "guides/about.md") or slug (e.g. "about")

        Returns:
            Page object if found, None otherwise.

        Robustness features:
        - Normalizes path separators (Windows/Unix)
        - Validates paths (rejects absolute paths, path traversal)
        - Handles paths with/without .md extension
        - Caches lookup maps for performance
        - Parses pages on-demand if accessed before rendering pipeline
        """
        if not path:
            return None

        # Validate path for security and correctness
        path_obj = Path(path)

        # Reject absolute paths (security)
        if path_obj.is_absolute():
            logger.debug("get_page_absolute_path_rejected", path=path, caller="template")
            return None

        # Reject path traversal attempts (security)
        normalized_path = path.replace("\\", "/")
        if "../" in normalized_path or normalized_path.startswith("../"):
            logger.debug("get_page_path_traversal_rejected", path=path, caller="template")
            return None

        # Build lookup maps if not already built (shared helper)
        _build_lookup_maps(site)

        maps = site._page_lookup_maps

        # Strategy 1: Direct lookup in relative map (exact match)
        page = None
        if normalized_path in maps["relative"]:
            page = maps["relative"][normalized_path]

        # Strategy 2: Try adding .md extension
        if not page:
            path_with_ext = (
                f"{normalized_path}.md" if not normalized_path.endswith(".md") else normalized_path
            )
            if path_with_ext in maps["relative"]:
                page = maps["relative"][path_with_ext]

        # Strategy 3: Try full path (rarely used in templates but possible)
        if not page and path in maps["full"]:
            page = maps["full"][path]

        # Strategy 4: Try stripping leading "content/" prefix if present
        if not page and normalized_path.startswith("content/"):
            stripped = normalized_path[8:]  # len("content/") = 8
            if stripped in maps["relative"]:
                page = maps["relative"][stripped]
            else:
                # Also try with .md extension
                stripped_with_ext = f"{stripped}.md" if not stripped.endswith(".md") else stripped
                if stripped_with_ext in maps["relative"]:
                    page = maps["relative"][stripped_with_ext]

        if not page:
            # Page not found
            logger.debug("get_page_not_found", path=path, caller="template")
            return None

        # Ensure page is parsed if needed (for track rendering)
        _ensure_page_parsed(page, site)

        return page

    env.globals["get_page"] = get_page
