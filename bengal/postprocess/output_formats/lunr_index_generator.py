"""
Pre-built Lunr.js search index generator for Bengal SSG.

Generates a serialized Lunr index at build time using the Python `lunr` package,
enabling faster client-side search by avoiding runtime index construction.

The pre-built index is written to `search-index.json` alongside `index.json`.
Client-side search.js loads the pre-built index via `lunr.Index.load()` instead
of rebuilding from raw page data on every page load.

Configuration:

```yaml
search:
  lunr:
    prebuilt: true  # Enable pre-built index (default: true)
```

Performance Impact:
    - Build time: +5-10s for index pre-building
    - Runtime: ~50% faster initial search (no client-side index build)
    - Index size: ~60% smaller (pre-built is more compact)

Related:
    - index_generator.py: Source of page data (index.json)
    - search.js: Client-side search using pre-built or runtime index
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)

# Check if lunr is available (optional dependency)
try:
    from lunr import lunr  # type: ignore[import-untyped]

    LUNR_AVAILABLE = True
except ImportError:
    LUNR_AVAILABLE = False
    lunr = None


class LunrIndexGenerator:
    """
    Generate pre-built Lunr.js search index at build time.

    Uses the Python `lunr` package (pure Python implementation of Lunr.js)
    to build a serialized search index that can be loaded directly by the
    client-side Lunr.js library.

    Field Boosts (matching search.js):
        - title: 10x (most important)
        - search_keywords: 8x (explicit search terms)
        - description: 5x (page summary)
        - tags: 3x (categorization)
        - section: 2x (content organization)
        - author: 2x (authorship)
        - content: 1x (full text)
        - kind: 1x (content type)

    Example:
        >>> generator = LunrIndexGenerator(site)
        >>> path = generator.generate()
        >>> print(f"Index written to: {path}")
    """

    # Field boost values (matching search.js for consistency)
    BOOSTS = {
        "title": 10,
        "description": 5,
        "content": 1,
        "tags": 3,
        "section": 2,
        "author": 2,
        "search_keywords": 8,
        "kind": 1,
    }

    def __init__(self, site: Site) -> None:
        """
        Initialize the Lunr index generator.

        Args:
            site: Site instance with rendered pages
        """
        self.site = site

    def is_available(self) -> bool:
        """
        Check if the lunr Python package is available.

        Returns:
            True if lunr can be imported, False otherwise
        """
        return LUNR_AVAILABLE

    def generate(self, index_json_path: Path | None = None) -> Path | None:
        """
        Generate pre-built Lunr index from index.json.

        Args:
            index_json_path: Path to index.json. If None, uses default location.

        Returns:
            Path to the generated search-index.json, or None if generation failed.
        """
        if not LUNR_AVAILABLE:
            logger.warning(
                "lunr_dependency_not_available",
                hint="pip install lunr",
            )
            return None

        # Determine index.json location
        if index_json_path is None:
            index_json_path = self._get_index_json_path()

        if not index_json_path.exists():
            logger.warning(
                "index_json_not_found",
                path=str(index_json_path),
            )
            return None

        try:
            # Load index.json
            data = json.loads(index_json_path.read_text(encoding="utf-8"))
            pages = data.get("pages", [])

            if not pages:
                logger.warning("no_pages_for_lunr_index", reason="index.json has no pages")
                return None

            # Build documents for Lunr
            documents = self._build_documents(pages)

            if not documents:
                logger.warning(
                    "no_searchable_documents",
                    reason="all pages excluded from search",
                )
                return None

            # Build Lunr index
            logger.debug("building_lunr_index", document_count=len(documents))

            idx = lunr(
                ref="objectID",
                fields=[
                    {"field_name": name, "boost": boost} for name, boost in self.BOOSTS.items()
                ],
                documents=documents,
            )

            # Serialize and write
            output_path = self._get_output_path(index_json_path)
            serialized = idx.serialize()

            output_path.write_text(
                json.dumps(serialized, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )

            size_kb = output_path.stat().st_size / 1024
            logger.info(
                "prebuilt_lunr_index_written",
                path=str(output_path),
                documents=len(documents),
                size_kb=round(size_kb, 1),
            )

            return output_path

        except Exception as e:
            logger.warning(
                "lunr_index_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
                fallback="runtime index building",
            )
            return None

    def _build_documents(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Build document list for Lunr indexing.

        Filters out pages marked for exclusion and transforms page data
        into the format expected by Lunr.

        Args:
            pages: List of page dictionaries from index.json

        Returns:
            List of documents ready for Lunr indexing
        """
        documents = []

        for page in pages:
            # Skip excluded or draft pages
            if page.get("search_exclude") or page.get("draft"):
                continue

            # Build document with all searchable fields
            doc = {
                "objectID": page.get("objectID") or page.get("uri") or page.get("url", ""),
                "title": page.get("title", ""),
                "description": page.get("description", ""),
                "content": page.get("content") or page.get("excerpt", ""),
                "tags": self._join_list(page.get("tags")),
                "section": page.get("section", ""),
                "author": self._get_author(page),
                "search_keywords": self._join_list(page.get("search_keywords")),
                "kind": page.get("kind") or page.get("type", ""),
            }

            documents.append(doc)

        return documents

    def _get_author(self, page: dict[str, Any]) -> str:
        """Extract author string from page data."""
        author = page.get("author", "")
        if author:
            return str(author)

        authors = page.get("authors", [])
        if authors:
            return " ".join(str(a) for a in authors)

        return ""

    def _join_list(self, items: list[str] | None) -> str:
        """Join list items into space-separated string."""
        if not items:
            return ""
        if isinstance(items, str):
            return items
        return " ".join(str(item) for item in items)

    def _get_index_json_path(self) -> Path:
        """Get the path to index.json, handling i18n prefixes."""
        i18n = self.site.config.get("i18n", {}) or {}
        if i18n.get("strategy") == "prefix":
            current_lang = getattr(self.site, "current_language", None) or i18n.get(
                "default_language", "en"
            )
            default_in_subdir = bool(i18n.get("default_in_subdir", False))
            if default_in_subdir or current_lang != i18n.get("default_language", "en"):
                return Path(self.site.output_dir) / str(current_lang) / "index.json"
        return Path(self.site.output_dir) / "index.json"

    def _get_output_path(self, index_json_path: Path | None = None) -> Path:
        """
        Get the output path for search-index.json.

        If index_json_path is provided, generates search-index.json alongside it.
        Otherwise, uses default location handling i18n prefixes.

        Args:
            index_json_path: Optional path to index.json (for version-specific paths)

        Returns:
            Path to search-index.json
        """
        # If index path provided, generate search-index.json alongside it
        if index_json_path is not None:
            return index_json_path.parent / "search-index.json"

        # Default behavior: handle i18n prefixes
        i18n = self.site.config.get("i18n", {}) or {}
        if i18n.get("strategy") == "prefix":
            current_lang = getattr(self.site, "current_language", None) or i18n.get(
                "default_language", "en"
            )
            default_in_subdir = bool(i18n.get("default_in_subdir", False))
            if default_in_subdir or current_lang != i18n.get("default_language", "en"):
                return Path(self.site.output_dir) / str(current_lang) / "search-index.json"
        return Path(self.site.output_dir) / "search-index.json"
