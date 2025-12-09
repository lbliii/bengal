"""
Site-wide index.json generator for Bengal SSG.

Generates a comprehensive JSON index of all pages suitable for
client-side search, filtering, and navigation.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.utils import (
    generate_excerpt,
    get_page_relative_url,
)
from bengal.utils.atomic_write import AtomicFile
from bengal.utils.autodoc import is_autodoc_page
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class SiteIndexGenerator:
    """
    Generates site-wide index.json for search and navigation.

    Creates a comprehensive JSON index with:
    - Page summaries (title, URL, excerpt, metadata)
    - Section counts and tag counts
    - Site metadata

    Example:
        >>> generator = SiteIndexGenerator(site, excerpt_length=200)
        >>> generator.generate(pages)
    """

    def __init__(
        self,
        site: Site,
        excerpt_length: int = 200,
        json_indent: int | None = None,
        include_full_content: bool = False,
    ) -> None:
        """
        Initialize the index generator.

        Args:
            site: Site instance
            excerpt_length: Length of excerpts in characters
            json_indent: JSON indentation (None for compact)
            include_full_content: Include full content in index (increases size)
        """
        self.site = site
        self.excerpt_length = excerpt_length
        self.json_indent = json_indent
        self.include_full_content = include_full_content

    def generate(self, pages: list[Page]) -> Path:
        """
        Generate site-wide index.json.

        Args:
            pages: List of pages to include

        Returns:
            Path to the generated index.json file
        """
        logger.debug("generating_site_index_json", page_count=len(pages))

        # Build site metadata (per-locale when i18n is enabled)
        site_metadata = {
            "title": self.site.config.get("title", "Bengal Site"),
            "description": self.site.config.get("description", ""),
            "baseurl": self.site.config.get("baseurl", ""),
        }

        # Only include build_time in production builds
        if not self.site.config.get("dev_server", False):
            site_metadata["build_time"] = datetime.now().isoformat()

        site_data: dict[str, Any] = {
            "site": site_metadata,
            "pages": [],
            "sections": {},
            "tags": {},
        }

        # Add each page (summary only, no full content)
        for page in pages:
            page_summary = self.page_to_summary(page)
            site_data["pages"].append(page_summary)

            # Count sections
            section = page_summary.get("section", "")
            if section:
                site_data["sections"][section] = site_data["sections"].get(section, 0) + 1

            # Count tags
            for tag in page_summary.get("tags", []):
                site_data["tags"][tag] = site_data["tags"].get(tag, 0) + 1

        # Convert counts to lists
        site_data["sections"] = [
            {"name": name, "count": count} for name, count in sorted(site_data["sections"].items())
        ]
        site_data["tags"] = [
            {"name": name, "count": count}
            for name, count in sorted(site_data["tags"].items(), key=lambda x: -x[1])
        ]

        logger.debug(
            "site_index_data_aggregated",
            total_pages=len(site_data["pages"]),
            sections=len(site_data["sections"]),
            tags=len(site_data["tags"]),
        )

        # Determine output path
        index_path = self._get_index_path()

        # Write only if content changed
        new_json_str = json.dumps(site_data, indent=self.json_indent, ensure_ascii=False)
        self._write_if_changed(index_path, new_json_str)

        logger.debug(
            "site_index_json_written",
            path=str(index_path),
            size_kb=index_path.stat().st_size / 1024,
        )

        return index_path

    def _get_index_path(self) -> Path:
        """Get the output path for index.json, handling i18n prefixes."""
        i18n = self.site.config.get("i18n", {}) or {}
        if i18n.get("strategy") == "prefix":
            current_lang = getattr(self.site, "current_language", None) or i18n.get(
                "default_language", "en"
            )
            default_in_subdir = bool(i18n.get("default_in_subdir", False))
            if default_in_subdir or current_lang != i18n.get("default_language", "en"):
                return self.site.output_dir / current_lang / "index.json"
        return self.site.output_dir / "index.json"

    def _write_if_changed(self, path: Path, content: str) -> None:
        """Write content only if it differs from existing file."""
        try:
            if path.exists():
                existing = path.read_text(encoding="utf-8")
                if existing == content:
                    return
        except Exception as e:
            # If we can't read existing file, proceed to write new content
            logger.debug(
                "index_generator_read_existing_failed",
                path=str(path),
                error=str(e),
                error_type=type(e).__name__,
                action="proceeding_to_write",
            )
            pass

        with AtomicFile(path, "w", encoding="utf-8") as f:
            f.write(content)

    def page_to_summary(self, page: Page) -> dict[str, Any]:
        """
        Convert page to summary for site index.

        Creates a search-optimized page summary with enhanced metadata.

        Args:
            page: Page object

        Returns:
            Dictionary with page summary for search indexing
        """
        # Use page.plain_text for AST-based extraction (faster than regex stripping)
        content_text = page.plain_text

        # Get relative URI (without baseurl) for objectID and uri
        page_uri = get_page_relative_url(page, self.site)

        # Construct full URL by combining baseurl with relative URI
        # This avoids double/triple baseurl that occurred when page.url already had baseurl
        baseurl = self.site.config.get("baseurl", "").rstrip("/")
        page_url = f"{baseurl}{page_uri}" if baseurl else page_uri

        summary: dict[str, Any] = {
            "objectID": page_uri,  # Unique identifier (relative path)
            "url": page_url,  # Full URL with baseurl
            "uri": page_uri,  # Relative path (without baseurl)
            "title": page.title,
            "description": page.metadata.get("description", ""),
            "excerpt": generate_excerpt(content_text, self.excerpt_length),
        }

        # Optional fields
        if page.date:
            summary["date"] = page.date.strftime("%Y-%m-%d")

        if hasattr(page, "_section") and page._section:
            summary["section"] = getattr(page._section, "name", "")

        # Tags
        if page.tags:
            tags = page.tags
            if isinstance(tags, list | tuple):
                summary["tags"] = list(tags)
            else:
                try:
                    summary["tags"] = list(tags) if tags else []
                except (TypeError, ValueError):
                    summary["tags"] = []

        # Stats
        word_count = len(content_text.split())
        summary["word_count"] = word_count
        summary["reading_time"] = max(1, round(word_count / 200))

        # Enhanced metadata
        metadata = page.metadata
        self._add_enhanced_metadata(summary, metadata)

        # Content for full-text search
        if len(content_text) > 0:
            if self.include_full_content:
                summary["content"] = content_text
            else:
                summary["content"] = generate_excerpt(content_text, self.excerpt_length * 3)

        # Directory structure
        if page_uri and isinstance(page_uri, str):
            path_parts = page_uri.strip("/").split("/")
            if len(path_parts) > 1:
                summary["dir"] = "/" + "/".join(path_parts[:-1]) + "/"
            else:
                summary["dir"] = "/"

        # Content type alias
        if result_type := summary.get("type"):
            summary["kind"] = result_type

        # Autodoc flag for search result grouping
        # Only set when True to keep index.json smaller
        if is_autodoc_page(page):
            summary["isAutodoc"] = True

        return summary

    def _add_enhanced_metadata(self, summary: dict[str, Any], metadata: dict[str, Any]) -> None:
        """Add enhanced metadata fields to summary."""
        # Content type and layout
        if metadata.get("type"):
            summary["type"] = metadata["type"]
        if metadata.get("layout"):
            summary["layout"] = metadata["layout"]

        # Authorship
        if metadata.get("author"):
            summary["author"] = metadata["author"]
        if metadata.get("authors"):
            summary["authors"] = metadata["authors"]

        # Categories
        if metadata.get("category"):
            summary["category"] = metadata["category"]
        if metadata.get("categories"):
            summary["categories"] = metadata["categories"]

        # Weight for sorting
        if metadata.get("weight") is not None:
            summary["weight"] = metadata["weight"]

        # Status flags
        if metadata.get("draft"):
            summary["draft"] = True
        if metadata.get("featured"):
            summary["featured"] = True

        # Search-specific
        if metadata.get("search_keywords"):
            summary["search_keywords"] = metadata["search_keywords"]
        if metadata.get("search_exclude"):
            summary["search_exclude"] = True

        # Visibility system integration
        # Check hidden frontmatter or visibility.search setting
        if metadata.get("hidden", False) or (
            isinstance(metadata.get("visibility"), dict)
            and not metadata["visibility"].get("search", True)
        ):
            summary["search_exclude"] = True

        # API/CLI specific
        if metadata.get("cli_name"):
            summary["cli_name"] = metadata["cli_name"]
        if metadata.get("api_module"):
            summary["api_module"] = metadata["api_module"]

        # Difficulty/level
        if metadata.get("difficulty"):
            summary["difficulty"] = metadata["difficulty"]
        if metadata.get("level"):
            summary["level"] = metadata["level"]

        # Related content
        if metadata.get("related"):
            summary["related"] = metadata["related"]

        # Last modified
        if metadata.get("lastmod"):
            lastmod = metadata["lastmod"]
            if hasattr(lastmod, "isoformat"):
                summary["lastmod"] = lastmod.isoformat()
            else:
                summary["lastmod"] = str(lastmod)

        # Source file path
        if metadata.get("source_file"):
            summary["source_file"] = metadata["source_file"]
