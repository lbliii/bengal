"""
JSON and unified page data accumulation for the rendering pipeline.

This module handles accumulating JSON data during rendering for post-processing
optimization. Extracted from core.py per RFC: rfc-modularize-large-files.

Classes:
JsonAccumulator: Accumulates page data during rendering.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.url_normalization import split_url_path

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import PageLike

logger = get_logger(__name__)


class JsonAccumulator:
    """
    Accumulates JSON and unified page data during rendering.

    Computes all per-page derivatives once (excerpt, word_count, etc.)
    for consumption by multiple post-processing generators:
    - PageJSONGenerator (per-page JSON files)
    - SiteIndexGenerator (index.json for search)

    Attributes:
        site: Site instance for configuration
        build_context: BuildContext for data accumulation
        page_json_generator: Cached PageJSONGenerator instance
        page_json_generator_opts: Cached options for generator

    Example:
            >>> accumulator = JsonAccumulator(site, build_context)
            >>> accumulator.accumulate_unified_page_data(page)

    """

    def __init__(self, site: Any, build_context: BuildContext | None):
        """
        Initialize the JSON accumulator.

        Args:
            site: Site instance for configuration
            build_context: BuildContext for data accumulation
        """
        self.site = site
        self.build_context = build_context
        self._page_json_generator: Any = None
        self._page_json_generator_opts: tuple[bool, bool] | None = None

    def accumulate_unified_page_data(self, page: PageLike) -> None:
        """
        Accumulate unified page data during rendering.

        Computes all per-page derivatives once (excerpt, word_count, etc.)
        for consumption by multiple post-processing generators:
        - PageJSONGenerator (per-page JSON files)
        - SiteIndexGenerator (index.json for search)

        See: plan/drafted/rfc-unified-page-data-accumulation.md

        Args:
            page: Page to accumulate data for
        """
        if not self.build_context or not self.site:
            return

        from bengal.orchestration.build_context import AccumulatedPageData
        from bengal.postprocess.output_formats.utils import (
            generate_excerpt,
            get_page_json_path,
            get_page_relative_url,
            get_page_url,
        )

        try:
            # Compute URLs
            url = get_page_url(page, self.site)  # Full URL with baseurl
            uri = get_page_relative_url(page, self.site)  # Relative path

            # Content derivatives (computed once)
            plain_text = page.plain_text
            word_count = len(plain_text.split())
            excerpt_length = 200  # Standard excerpt length
            excerpt = generate_excerpt(plain_text, excerpt_length)
            content_preview = generate_excerpt(plain_text, excerpt_length * 3)

            # Directory structure for SiteIndexGenerator
            dir_path = "/"
            if uri and isinstance(uri, str):
                path_parts = split_url_path(uri)
                if len(path_parts) > 1:
                    dir_path = "/" + "/".join(path_parts[:-1]) + "/"

            # Extract enhanced metadata for SiteIndexGenerator
            enhanced = self.extract_enhanced_metadata(page)

            # Date handling
            page_date = getattr(page, "date", None)
            date_str = page_date.strftime("%Y-%m-%d") if page_date else None
            date_iso = page_date.isoformat() if page_date else None

            # Build unified data
            data = AccumulatedPageData(
                source_path=page.source_path,
                url=url,
                uri=uri,
                title=page.title or "",
                description=page.metadata.get("description", "") or "",
                date=date_str,
                date_iso=date_iso,
                plain_text=plain_text,
                excerpt=excerpt,
                content_preview=content_preview,
                word_count=word_count,
                reading_time=max(1, round(word_count / 200)),
                section=page._section.name if getattr(page, "_section", None) else "",
                tags=list(page.tags) if page.tags else [],
                dir=dir_path,
                enhanced_metadata=enhanced,
                raw_metadata=dict(page.metadata),
            )

            # Extended JSON data (only if per-page JSON enabled)
            output_formats_config = self.site.config.get("output_formats", {})
            if output_formats_config.get("enabled", True):
                per_page = output_formats_config.get("per_page", ["json", "llm_txt"])
                if "json" in per_page:
                    json_path = get_page_json_path(page)
                    if json_path:
                        data.json_output_path = json_path
                        data.full_json_data = self.build_full_json_data(page)

            self.build_context.accumulate_page_data(data)

        except Exception as e:
            logger.debug(
                "unified_page_data_accumulation_failed",
                page=str(page.source_path),
                error=str(e)[:100],
            )

    def extract_enhanced_metadata(self, page: PageLike) -> dict[str, Any]:
        """
        Extract enhanced metadata fields for SiteIndexGenerator.

        Mirrors the fields extracted by SiteIndexGenerator._add_enhanced_metadata()
        to ensure index.json output is identical.

        Args:
            page: Page to extract metadata from

        Returns:
            Dict of enhanced metadata fields
        """
        from bengal.utils.autodoc import is_autodoc_page

        metadata = page.metadata
        enhanced: dict[str, Any] = {}

        # Content type and layout
        if value := metadata.get("type"):
            enhanced["type"] = value
        if value := metadata.get("layout"):
            enhanced["layout"] = value

        # Authorship
        if value := metadata.get("author"):
            enhanced["author"] = value
        if value := metadata.get("authors"):
            enhanced["authors"] = value

        # Categories
        if value := metadata.get("category"):
            enhanced["category"] = value
        if value := metadata.get("categories"):
            enhanced["categories"] = value

        # Weight for sorting
        if value := metadata.get("weight"):
            enhanced["weight"] = value

        # Status flags
        if metadata.get("draft"):
            enhanced["draft"] = True
        if metadata.get("featured"):
            enhanced["featured"] = True

        # Search-specific
        if value := metadata.get("search_keywords"):
            enhanced["search_keywords"] = value
        if metadata.get("search_exclude"):
            enhanced["search_exclude"] = True

        # Visibility system integration
        visibility = metadata.get("visibility")
        if metadata.get("hidden", False) or (
            isinstance(visibility, dict) and not visibility.get("search", True)
        ):
            enhanced["search_exclude"] = True

        # API/CLI specific
        if value := metadata.get("cli_name"):
            enhanced["cli_name"] = value
        if value := metadata.get("api_module"):
            enhanced["api_module"] = value

        # Difficulty/level
        if value := metadata.get("difficulty"):
            enhanced["difficulty"] = value
        if value := metadata.get("level"):
            enhanced["level"] = value

        # Related content
        if value := metadata.get("related"):
            enhanced["related"] = value

        # Last modified
        if value := metadata.get("lastmod"):
            if hasattr(value, "isoformat"):
                enhanced["lastmod"] = value.isoformat()
            else:
                enhanced["lastmod"] = str(value)

        # Source file path
        if value := metadata.get("source_file"):
            enhanced["source_file"] = value

        # Version field
        if hasattr(page, "version") and page.version:
            enhanced["version"] = page.version

        # Autodoc flag
        if is_autodoc_page(page):
            enhanced["isAutodoc"] = True

        return enhanced

    def build_full_json_data(self, page: PageLike) -> dict[str, Any]:
        """
        Build full JSON data for per-page JSON files.

        Args:
            page: Page to build JSON data for

        Returns:
            Dict of full JSON data for the page
        """
        from bengal.postprocess.output_formats.json_generator import PageJSONGenerator

        output_formats_config = self.site.config.get("output_formats", {})
        options = output_formats_config.get("options", {})
        include_html = options.get("include_html_content", False)
        include_text = options.get("include_plain_text", True)

        # Reuse per-pipeline generator instance for speed.
        opts = (include_html, include_text)
        if self._page_json_generator is None or self._page_json_generator_opts != opts:
            self._page_json_generator = PageJSONGenerator(self.site, graph_data=None)
            self._page_json_generator_opts = opts

        return self._page_json_generator.page_to_json(
            page, include_html=include_html, include_text=include_text
        )
