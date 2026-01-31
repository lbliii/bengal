"""
Site-wide index.json generator for Bengal SSG.

Generates a comprehensive JSON index of all pages suitable for client-side
search with Lunr.js, filtering, faceted navigation, and programmatic access.

Output Format:
The index.json contains:

    ```json
    {
      "site": {
        "title": "My Site",
        "description": "Site description",
        "baseurl": "/docs",
        "build_time": "2024-01-15T10:30:00"
      },
      "pages": [
        {
          "objectID": "/docs/getting-started/",
          "url": "/docs/getting-started/",
          "title": "Getting Started",
          "excerpt": "...",
          "content": "...",
          "tags": ["tutorial"],
          "section": "docs",
          "word_count": 500,
          "reading_time": 3
        }
      ],
      "sections": [{"name": "docs", "count": 10}],
      "tags": [{"name": "tutorial", "count": 5}]
    }
    ```

Features:
- Search-optimized page summaries with excerpts
- Section and tag aggregations for faceted search
- Enhanced metadata (author, category, difficulty, etc.)
- Version-scoped indexes when versioning is enabled
- i18n support with per-locale indexes
- Autodoc page flagging for result grouping
- Hash-based change detection: O(1) comparison instead of O(n) string compare

Versioning:
When versioning is enabled, generates per-version indexes:
- Latest version: output_dir/index.json
- Older versions: output_dir/docs/v1/index.json

Configuration:
Controlled via [output_formats] in bengal.toml:

    ```toml
    [output_formats]
    site_wide = ["index_json"]
    options.excerpt_length = 200
    options.include_full_content_in_index = false
    options.json_indent = null  # null = compact
    ```

Example:
    >>> generator = SiteIndexGenerator(site, excerpt_length=200)
    >>> path = generator.generate(pages)
    >>> print(f"Index written to: {path}")

Related:
- bengal.postprocess.output_formats: OutputFormatsGenerator facade
- bengal.postprocess.output_formats.lunr_index_generator: Pre-built Lunr index
- themes/*/static/js/search.js: Client-side search using index.json

"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from bengal.postprocess.output_formats.utils import (
    generate_excerpt,
    get_page_relative_url,
)
from bengal.utils.autodoc import is_autodoc_page
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.orchestration.build_context import AccumulatedPageData, BuildContext
    from bengal.protocols import SiteLike
else:
    from bengal.orchestration.build_context import AccumulatedPageData, BuildContext
    from bengal.protocols import SiteLike
    from bengal.protocols import PageLike as Page

logger = get_logger(__name__)


class SiteIndexGenerator:
    """
    Generates site-wide index.json for search and navigation.

    Creates a comprehensive JSON index optimized for Lunr.js client-side
    search, faceted filtering, and programmatic access to site content.

    Creation:
        Direct instantiation: SiteIndexGenerator(site, excerpt_length=200)
            - Created by OutputFormatsGenerator for index generation
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with pages and configuration
        excerpt_length: Character length for page excerpts (default: 200)
        json_indent: JSON indentation (None for compact)
        include_full_content: Include full content in index (default: False)

    Relationships:
        - Used by: OutputFormatsGenerator facade
        - Uses: Site for pages, LunrIndexGenerator for pre-built search index

    Features:
        - Search-optimized summaries with objectID for Lunr
        - Section and tag aggregations for faceted navigation
        - Enhanced metadata fields (author, category, difficulty)
        - Per-version indexes when versioning enabled
        - i18n support with per-locale indexes
        - Write-if-changed optimization

    Example:
            >>> generator = SiteIndexGenerator(site, excerpt_length=200)
            >>> path = generator.generate(pages)  # Returns Path or list[Path]

    """

    def __init__(
        self,
        site: SiteLike,
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

    def generate(
        self,
        pages: list[Page],
        accumulated_data: list[AccumulatedPageData] | None = None,
        build_context: BuildContext | None = None,
    ) -> Path | list[Path]:
        """
        Generate site-wide index.json.

        When versioning is enabled, generates per-version indexes:
        - Latest version: output_dir/index.json
        - Older versions: output_dir/docs/v1/index.json, etc.

        Args:
            pages: List of pages to include (always needed for versioning grouping)
            accumulated_data: Optional pre-computed page data from rendering.
                            If provided, uses this instead of iterating pages.
            build_context: Optional BuildContext for hybrid mode lookups.

        Modes:
            - Full: accumulated_data covers all pages → use accumulated only
            - Hybrid: partial accumulated_data → use accumulated + fallback
            - Legacy: no accumulated_data → iterate all pages

        Returns:
            Path to the generated index.json file (single index)
            or list of Paths (per-version indexes)

        See: plan/drafted/rfc-unified-page-data-accumulation.md
        """
        # Store for hybrid mode lookups
        self._build_context = build_context
        self._accumulated_index: dict[Path, AccumulatedPageData] = {
            data.source_path: data for data in (accumulated_data or [])
        }

        # Check if versioning is enabled
        versioning_enabled = getattr(self.site, "versioning_enabled", False)

        if not versioning_enabled:
            # Single index
            return self._generate_single_index(pages, accumulated_data)

        # Per-version indexes
        generated = []
        by_version = self._group_by_version(pages)

        for version_id, version_pages in by_version.items():
            # Filter accumulated data for this version
            version_accumulated = None
            if accumulated_data:
                version_paths = {p.source_path for p in version_pages}
                version_accumulated = [
                    d for d in accumulated_data if d.source_path in version_paths
                ]
            path = self._generate_version_index(version_id, version_pages, version_accumulated)
            generated.append(path)

        return generated

    def _generate_single_index(
        self,
        pages: list[Page],
        accumulated_data: list[AccumulatedPageData] | None = None,
    ) -> Path:
        """
        Generate single index.json with hybrid mode support.

        Modes:
            - Full: accumulated_data covers all pages → use accumulated only (fast)
            - Hybrid: partial accumulated_data → use accumulated + fallback
            - Legacy: no accumulated_data → iterate all pages (original behavior)

        See: plan/drafted/rfc-unified-page-data-accumulation.md
        """
        logger.debug("generating_site_index_json", page_count=len(pages))

        # Build site metadata (per-locale when i18n is enabled)
        # Ensure all values are strings, not Mock objects
        site_metadata = {
            "title": str(self.site.title or "Bengal Site"),
            "description": str(getattr(self.site, "description", "") or ""),
            "baseurl": str(self.site.baseurl or ""),
        }

        # Only include build_time in production builds
        # Use site.build_time (set once at build start) for deterministic output
        if not self.site.dev_mode:
            build_time = getattr(self.site, "build_time", None)
            # Verify it's a real datetime (not a Mock) with a working isoformat method
            if isinstance(build_time, datetime):
                site_metadata["build_time"] = build_time.isoformat()

        site_data: dict[str, Any] = {
            "site": site_metadata,
            "pages": [],
            "sections": {},
            "tags": {},
        }

        # Determine mode
        accumulated_count = len(accumulated_data) if accumulated_data else 0
        use_hybrid = 0 < accumulated_count < len(pages)
        use_accumulated_only = accumulated_count == len(pages) and accumulated_count > 0

        if use_accumulated_only:
            # FAST PATH: All pages have accumulated data
            logger.debug("index_generator_mode", mode="accumulated_only")
            for data in accumulated_data:  # type: ignore[union-attr]
                page_summary = self._accumulated_to_summary(data)
                self._add_to_site_data(site_data, page_summary)
        elif use_hybrid:
            # HYBRID PATH: Mix of accumulated + computed
            logger.debug(
                "index_generator_mode",
                mode="hybrid",
                accumulated=accumulated_count,
                total=len(pages),
            )
            for page in pages:
                if acc_data := self._accumulated_index.get(page.source_path):
                    page_summary = self._accumulated_to_summary(acc_data)
                else:
                    page_summary = self.page_to_summary(page)
                self._add_to_site_data(site_data, page_summary)
        else:
            # LEGACY PATH: Compute from pages
            logger.debug("index_generator_mode", mode="legacy")
            for page in pages:
                page_summary = self.page_to_summary(page)
                self._add_to_site_data(site_data, page_summary)

        # Convert counts to lists (sorted for deterministic output)
        site_data["sections"] = [
            {"name": name, "count": count} for name, count in sorted(site_data["sections"].items())
        ]
        site_data["tags"] = [
            {"name": name, "count": count}
            for name, count in sorted(site_data["tags"].items(), key=lambda x: -x[1])
        ]
        # Sort pages by URL for deterministic output (important for idempotent builds)
        site_data["pages"] = sorted(site_data["pages"], key=lambda p: p.get("url", ""))

        logger.debug(
            "site_index_data_aggregated",
            total_pages=len(site_data["pages"]),
            sections=len(site_data["sections"]),
            tags=len(site_data["tags"]),
        )

        # Determine output path
        index_path = self._get_index_path()

        # Write only if content changed (sort_keys for deterministic JSON)
        new_json_str = json.dumps(
            site_data, indent=self.json_indent, ensure_ascii=False, sort_keys=True
        )
        self._write_if_changed(index_path, new_json_str)

        logger.debug(
            "site_index_json_written",
            path=str(index_path),
            size_kb=index_path.stat().st_size / 1024,
        )

        return index_path

    def _add_to_site_data(self, site_data: dict[str, Any], page_summary: dict[str, Any]) -> None:
        """Add page summary to site data and update aggregations."""
        site_data["pages"].append(page_summary)

        # Count sections
        section = page_summary.get("section", "")
        if section:
            site_data["sections"][section] = site_data["sections"].get(section, 0) + 1

        # Count tags
        for tag in page_summary.get("tags", []):
            site_data["tags"][tag] = site_data["tags"].get(tag, 0) + 1

    def _accumulated_to_summary(self, data: AccumulatedPageData) -> dict[str, Any]:
        """
        Convert accumulated data to index summary format.

        Produces identical output to page_to_summary() for consistency.
        Uses pre-computed values from rendering phase instead of
        re-computing from page objects.

        See: plan/drafted/rfc-unified-page-data-accumulation.md
        """
        baseurl = (self.site.baseurl or "").rstrip("/")

        summary: dict[str, Any] = {
            "objectID": data.uri,
            # url includes baseurl when configured; uri stays relative
            "url": f"{baseurl}{data.uri}" if baseurl else data.uri,
            "href": f"{baseurl}{data.uri}" if baseurl else data.uri,
            "uri": data.uri,
            "title": data.title,
            "description": data.description,
            "excerpt": data.excerpt,
            "section": data.section,
            "tags": data.tags,
            "word_count": data.word_count,
            "reading_time": data.reading_time,
            "dir": data.dir,
        }

        # Optional date
        if data.date:
            summary["date"] = data.date

        # Content for full-text search
        if data.content_preview:
            if self.include_full_content:
                summary["content"] = data.plain_text
            else:
                summary["content"] = data.content_preview

        # Enhanced metadata (type, author, draft, etc.)
        for key, value in data.enhanced_metadata.items():
            summary[key] = value

        # Content type alias
        if result_type := summary.get("type"):
            summary["kind"] = result_type

        return summary

    def _generate_version_index(
        self,
        version_id: str | None,
        pages: list[Page],
        accumulated_data: list[AccumulatedPageData] | None = None,
    ) -> Path:
        """Generate index for a specific version with hybrid mode support."""
        logger.debug(
            "generating_version_index",
            version_id=version_id or "latest",
            page_count=len(pages),
        )

        # Build site metadata
        site_metadata = {
            "title": self.site.title or "Bengal Site",
            "description": getattr(self.site, "description", "") or "",
            "baseurl": self.site.baseurl or "",
        }

        # Only include build_time in production builds
        # Use site.build_time (set once at build start) for deterministic output
        if not self.site.dev_mode:
            build_time = getattr(self.site, "build_time", None)
            # Verify it's a real datetime (not a Mock) with a working isoformat method
            if isinstance(build_time, datetime):
                site_metadata["build_time"] = build_time.isoformat()

        site_data: dict[str, Any] = {
            "site": site_metadata,
            "pages": [],
            "sections": {},
            "tags": {},
        }

        # Determine mode
        accumulated_count = len(accumulated_data) if accumulated_data else 0
        use_hybrid = 0 < accumulated_count < len(pages)
        use_accumulated_only = accumulated_count == len(pages) and accumulated_count > 0

        if use_accumulated_only:
            # FAST PATH: All pages have accumulated data
            for data in accumulated_data:  # type: ignore[union-attr]
                page_summary = self._accumulated_to_summary(data)
                self._add_to_site_data(site_data, page_summary)
        elif use_hybrid:
            # HYBRID PATH: Mix of accumulated + computed
            for page in pages:
                if acc_data := self._accumulated_index.get(page.source_path):
                    page_summary = self._accumulated_to_summary(acc_data)
                else:
                    page_summary = self.page_to_summary(page)
                self._add_to_site_data(site_data, page_summary)
        else:
            # LEGACY PATH: Compute from pages
            for page in pages:
                page_summary = self.page_to_summary(page)
                self._add_to_site_data(site_data, page_summary)

        # Convert counts to lists (sorted for deterministic output)
        site_data["sections"] = [
            {"name": name, "count": count} for name, count in sorted(site_data["sections"].items())
        ]
        site_data["tags"] = [
            {"name": name, "count": count}
            for name, count in sorted(site_data["tags"].items(), key=lambda x: -x[1])
        ]
        # Sort pages by URL for deterministic output (important for idempotent builds)
        site_data["pages"] = sorted(site_data["pages"], key=lambda p: p.get("url", ""))

        # Determine output path
        if version_id is None or self._is_latest_version(version_id):
            # Latest version: output_dir/index.json
            index_path = self._get_index_path()
        else:
            # Older version: output_dir/docs/v1/index.json
            index_path = self.site.output_dir / "docs" / version_id / "index.json"
            index_path.parent.mkdir(parents=True, exist_ok=True)

        # Write only if content changed (sort_keys for deterministic JSON)
        new_json_str = json.dumps(
            site_data, indent=self.json_indent, ensure_ascii=False, sort_keys=True
        )
        self._write_if_changed(index_path, new_json_str)

        logger.debug(
            "version_index_json_written",
            version_id=version_id or "latest",
            path=str(index_path),
            size_kb=index_path.stat().st_size / 1024,
        )

        return index_path

    def _group_by_version(self, pages: list[Page]) -> dict[str | None, list[Page]]:
        """Group pages by version ID (None for unversioned)."""
        by_version: dict[str | None, list[Page]] = {}
        for page in pages:
            version = getattr(page, "version", None)
            by_version.setdefault(version, []).append(page)
        return by_version

    def _is_latest_version(self, version_id: str) -> bool:
        """Check if version_id is the latest version."""
        if not hasattr(self.site, "version_config") or not self.site.version_config:
            return True
        version_config = self.site.version_config
        # Type narrowing: check if enabled attribute exists
        if not hasattr(version_config, "enabled") or not getattr(version_config, "enabled", False):
            return True
        # Type narrowing: check if get_version method exists
        get_version_method = getattr(version_config, "get_version", None)
        if not callable(get_version_method):
            return True
        version = get_version_method(version_id)
        return version is not None and getattr(version, "latest", False)

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
        """
        Write content only if content hash differs from stored hash.

        Uses SHA-256 hash comparison instead of full string comparison:
        - O(1) hash comparison vs O(n) string comparison
        - Avoids reading entire existing file into memory
        - Hash stored in .hash sidecar file
        """
        hash_path = path.with_suffix(".json.hash")
        new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Check hash instead of full content comparison
        try:
            if hash_path.exists():
                existing_hash = hash_path.read_text(encoding="utf-8").strip()
                if existing_hash == new_hash:
                    logger.debug(
                        "index_generator_skipped",
                        reason="content_unchanged",
                        path=str(path),
                    )
                    return
        except Exception as e:
            logger.debug(
                "index_generator_hash_check_failed",
                path=str(hash_path),
                error=str(e),
                error_type=type(e).__name__,
                action="proceeding_to_write",
            )

        # Write content and hash atomically
        # Both files use atomic writes to prevent inconsistent state on crash
        with AtomicFile(path, "w", encoding="utf-8") as f:
            f.write(content)
        with AtomicFile(hash_path, "w", encoding="utf-8") as f:
            f.write(new_hash)

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
        baseurl = (self.site.baseurl or "").rstrip("/")
        page_url = f"{baseurl}{page_uri}" if baseurl else page_uri

        summary: dict[str, Any] = {
            "objectID": page_uri,  # Unique identifier (relative path)
            # url includes baseurl when configured; uri stays relative
            "url": page_url,  # Full URL with baseurl (alias for consistency)
            "href": page_url,  # Full URL with baseurl (alias for consistency)
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

        # Version field for version-scoped search
        if hasattr(page, "version") and page.version:
            summary["version"] = page.version

        return summary

    def _is_json_serializable(self, value: Any) -> bool:
        """Check if value is JSON serializable (excluding Mock objects)."""
        if isinstance(value, Mock):
            return False
        try:
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False

    def _safe_get_metadata_value(self, metadata: dict[str, Any], key: str) -> Any | None:
        """Safely get metadata value, ensuring it's JSON-serializable."""
        value = metadata.get(key)
        if value is None:
            return None
        # Filter out Mock objects and non-serializable values
        if isinstance(value, Mock):
            return None
        if isinstance(value, (list, tuple)):
            # Filter out Mock objects from lists
            filtered_list = [
                v for v in value if not isinstance(v, Mock) and self._is_json_serializable(v)
            ]
            return filtered_list if filtered_list else None
        if isinstance(value, dict):
            # Recursively filter dict values
            filtered_dict = {
                k: v
                for k, v in value.items()
                if not isinstance(v, Mock) and self._is_json_serializable(v)
            }
            return filtered_dict if filtered_dict else None
        if self._is_json_serializable(value):
            return value
        return None

    def _add_enhanced_metadata(self, summary: dict[str, Any], metadata: dict[str, Any]) -> None:
        """Add enhanced metadata fields to summary, ensuring JSON serializability."""
        # Content type and layout
        if value := self._safe_get_metadata_value(metadata, "type"):
            summary["type"] = value
        if value := self._safe_get_metadata_value(metadata, "layout"):
            summary["layout"] = value

        # Authorship
        if value := self._safe_get_metadata_value(metadata, "author"):
            summary["author"] = value
        if value := self._safe_get_metadata_value(metadata, "authors"):
            summary["authors"] = value

        # Categories
        if value := self._safe_get_metadata_value(metadata, "category"):
            summary["category"] = value
        if value := self._safe_get_metadata_value(metadata, "categories"):
            summary["categories"] = value

        # Weight for sorting
        if value := self._safe_get_metadata_value(metadata, "weight"):
            summary["weight"] = value

        # Status flags
        if metadata.get("draft"):
            summary["draft"] = True
        if metadata.get("featured"):
            summary["featured"] = True

        # Search-specific
        if value := self._safe_get_metadata_value(metadata, "search_keywords"):
            summary["search_keywords"] = value
        if metadata.get("search_exclude"):
            summary["search_exclude"] = True

        # Visibility system integration
        # Check hidden frontmatter or visibility.search setting
        visibility = self._safe_get_metadata_value(metadata, "visibility")
        if metadata.get("hidden", False) or (
            isinstance(visibility, dict) and not visibility.get("search", True)
        ):
            summary["search_exclude"] = True

        # API/CLI specific
        if value := self._safe_get_metadata_value(metadata, "cli_name"):
            summary["cli_name"] = value
        if value := self._safe_get_metadata_value(metadata, "api_module"):
            summary["api_module"] = value

        # Difficulty/level
        if value := self._safe_get_metadata_value(metadata, "difficulty"):
            summary["difficulty"] = value
        if value := self._safe_get_metadata_value(metadata, "level"):
            summary["level"] = value

        # Related content
        if value := self._safe_get_metadata_value(metadata, "related"):
            summary["related"] = value

        # Last modified
        if value := self._safe_get_metadata_value(metadata, "lastmod"):
            if hasattr(value, "isoformat"):
                summary["lastmod"] = value.isoformat()
            else:
                summary["lastmod"] = str(value)

        # Source file path
        if value := self._safe_get_metadata_value(metadata, "source_file"):
            summary["source_file"] = value
