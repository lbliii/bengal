"""
Template function for retrieving a page by path.

Used by tracks feature to resolve track item pages.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: Environment, site: Site) -> None:
    """Register the get_page function with Jinja2 environment."""

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

        # Lazy-build lookup maps on the site object
        if not hasattr(site, "_page_lookup_maps"):
            # Build maps for robust lookup
            # 1. Full source path (str) -> Page
            # 2. Content-relative path (str) -> Page (e.g. "guides/setup.md")

            by_full_path = {}
            by_content_relative = {}

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

        maps = site._page_lookup_maps

        # Strategy 1: Direct lookup in relative map (exact match)
        if normalized_path in maps["relative"]:
            return maps["relative"][normalized_path]

        # Strategy 2: Try adding .md extension
        path_with_ext = (
            f"{normalized_path}.md" if not normalized_path.endswith(".md") else normalized_path
        )
        if path_with_ext in maps["relative"]:
            return maps["relative"][path_with_ext]

        # Strategy 3: Try full path (rarely used in templates but possible)
        if path in maps["full"]:
            return maps["full"][path]

        # Strategy 4: Try stripping leading "content/" prefix if present
        if normalized_path.startswith("content/"):
            stripped = normalized_path[8:]  # len("content/") = 8
            if stripped in maps["relative"]:
                return maps["relative"][stripped]
            # Also try with .md extension
            stripped_with_ext = f"{stripped}.md" if not stripped.endswith(".md") else stripped
            if stripped_with_ext in maps["relative"]:
                return maps["relative"][stripped_with_ext]

        # Page not found
        logger.debug("get_page_not_found", path=path, caller="template")
        return None

    env.globals["get_page"] = get_page
