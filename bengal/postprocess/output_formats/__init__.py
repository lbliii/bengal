"""
Output formats generation package for Bengal SSG.

Generates alternative output formats for pages to enable:
- Client-side search (JSON index)
- AI/LLM discovery (plain text format)
- Programmatic access (JSON API)

Structure:
    - json_generator.py: Per-page JSON files
    - txt_generator.py: Per-page LLM text files
    - index_generator.py: Site-wide index.json
    - llm_generator.py: Site-wide llm-full.txt
    - utils.py: Shared utilities

Configuration (bengal.toml):
    [output_formats]
    enabled = true
    per_page = ["json", "llm_txt"]
    site_wide = ["index_json", "llm_full"]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.index_generator import SiteIndexGenerator
from bengal.postprocess.output_formats.json_generator import PageJSONGenerator
from bengal.postprocess.output_formats.llm_generator import SiteLlmTxtGenerator
from bengal.postprocess.output_formats.lunr_index_generator import LunrIndexGenerator
from bengal.postprocess.output_formats.txt_generator import PageTxtGenerator
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)

__all__ = [
    "LunrIndexGenerator",
    "OutputFormatsGenerator",
    "PageJSONGenerator",
    "PageTxtGenerator",
    "SiteIndexGenerator",
    "SiteLlmTxtGenerator",
]


class OutputFormatsGenerator:
    """
    Generates custom output formats for pages.

    Provides alternative content formats to enable:
    - Client-side search via JSON index
    - AI/LLM discovery via plain text
    - Programmatic API access via JSON

    Output Formats:
    - Per-page JSON: page.json next to each page.html (metadata + content)
    - Per-page LLM text: page.txt next to each page.html (AI-friendly format)
    - Site-wide index.json: Searchable index of all pages with summaries
    - Site-wide llm-full.txt: Full site content in single text file

    This class acts as a facade, delegating to specialized generators:
    - PageJSONGenerator: Per-page JSON files
    - PageTxtGenerator: Per-page LLM text files
    - SiteIndexGenerator: Site-wide index.json
    - SiteLlmTxtGenerator: Site-wide llm-full.txt

    Example:
        >>> generator = OutputFormatsGenerator(site, config=config)
        >>> generator.generate()
    """

    def __init__(
        self,
        site: Site,
        config: dict[str, Any] | None = None,
        graph_data: dict[str, Any] | None = None,
        build_context=None,
    ) -> None:
        """
        Initialize output formats generator.

        Args:
            site: Site instance
            config: Configuration dict from bengal.toml
            graph_data: Optional pre-computed graph data for including in page JSON
            build_context: Optional BuildContext with accumulated JSON data from rendering phase
        """
        self.site = site
        self.config = self._normalize_config(config or {})
        self.graph_data = graph_data
        self.build_context = build_context

    def _normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize configuration to support both simple and advanced formats.

        Simple format (from [build.output_formats]):
            {
                'enabled': True,
                'json': True,
                'llm_txt': True,
                'site_json': True,
                'site_llm': True
            }

        Advanced format (from [output_formats]):
            {
                'enabled': True,
                'per_page': ['json', 'llm_txt'],
                'site_wide': ['index_json', 'llm_full'],
                'options': {...}
            }
        """
        normalized = self._default_config()

        if not config:
            return normalized

        # Check if advanced format
        is_advanced = "per_page" in config or "site_wide" in config

        if is_advanced:
            normalized.update(config)
        else:
            # Simple format conversion
            per_page = []
            site_wide = []

            if config.get("json", False):
                per_page.append("json")
            if config.get("llm_txt", False):
                per_page.append("llm_txt")
            if config.get("site_json", False):
                site_wide.append("index_json")
            if config.get("site_llm", False):
                site_wide.append("llm_full")

            normalized["per_page"] = per_page if per_page else normalized["per_page"]
            normalized["site_wide"] = site_wide if site_wide else normalized["site_wide"]

        # Propagate enabled flag
        if "enabled" in config:
            normalized["enabled"] = config["enabled"]

        return normalized

    def _default_config(self) -> dict[str, Any]:
        """Return default configuration."""
        return {
            "enabled": True,
            "per_page": ["json", "llm_txt"],  # JSON + LLM text by default
            "site_wide": ["index_json", "llm_full"],  # Search index + full LLM text
            "options": {
                "include_html_content": True,
                "include_plain_text": True,
                "excerpt_length": 200,
                "exclude_sections": [],
                "exclude_patterns": ["404.html", "search.html"],
                "json_indent": None,  # None = compact, 2 = pretty
                "llm_separator_width": 80,
                "include_full_content_in_index": False,
            },
        }

    def generate(self) -> None:
        """
        Generate all enabled output formats.

        Checks configuration to determine which formats to generate,
        filters pages based on exclusion rules, then generates:
        1. Per-page formats (JSON, LLM text)
        2. Site-wide formats (index.json, llm-full.txt)

        All file writes are atomic to prevent corruption during builds.
        """
        if not self.config.get("enabled", True):
            logger.debug("output_formats_disabled")
            return

        per_page = self.config.get("per_page", ["json"])
        site_wide = self.config.get("site_wide", ["index_json"])

        logger.debug(
            "generating_output_formats",
            per_page_formats=per_page,
            site_wide_formats=site_wide,
        )

        # Filter pages based on exclusions
        pages = self._filter_pages()

        # Track what we generated
        generated = []
        options = self.config.get("options", {})

        # Per-page outputs
        if "json" in per_page:
            json_gen = PageJSONGenerator(self.site, graph_data=self.graph_data)
            # OPTIMIZATION: Use accumulated JSON data if available (Phase 2 of post-processing optimization)
            # This eliminates double iteration of pages, saving ~500-700ms on large sites
            # See: plan/active/rfc-postprocess-optimization.md
            accumulated_json = None
            if self.build_context and self.build_context.has_accumulated_json:
                accumulated_json = self.build_context.get_accumulated_json()
            count = json_gen.generate(pages, accumulated_json=accumulated_json)
            generated.append(f"JSON ({count} files)")
            logger.debug("generated_page_json", file_count=count)

        if "llm_txt" in per_page:
            separator_width = options.get("llm_separator_width", 80)
            txt_gen = PageTxtGenerator(self.site, separator_width=separator_width)
            count = txt_gen.generate(pages)
            generated.append(f"LLM text ({count} files)")
            logger.debug("generated_page_txt", file_count=count)

        # Site-wide outputs
        if "index_json" in site_wide:
            excerpt_length = options.get("excerpt_length", 200)
            json_indent = options.get("json_indent")
            include_full_content = options.get("include_full_content_in_index", False)
            index_gen = SiteIndexGenerator(
                self.site,
                excerpt_length=excerpt_length,
                json_indent=json_indent,
                include_full_content=include_full_content,
            )
            index_path = index_gen.generate(pages)
            generated.append("index.json")
            logger.debug("generated_site_index_json")

            # Generate pre-built Lunr index if enabled
            search_config = self.site.config.get("search", {})
            lunr_config = search_config.get("lunr", {})
            prebuilt_enabled = lunr_config.get("prebuilt", True)  # Default: enabled

            if prebuilt_enabled:
                lunr_gen = LunrIndexGenerator(self.site)
                if lunr_gen.is_available():
                    lunr_path = lunr_gen.generate(index_path)
                    if lunr_path:
                        generated.append("search-index.json")
                        logger.debug("generated_prebuilt_lunr_index")
                else:
                    logger.debug(
                        "lunr_prebuilt_skipped",
                        reason="lunr package not installed",
                    )

        if "llm_full" in site_wide:
            separator_width = options.get("llm_separator_width", 80)
            llm_gen = SiteLlmTxtGenerator(self.site, separator_width=separator_width)
            llm_gen.generate(pages)
            generated.append("llm-full.txt")
            logger.debug("generated_site_llm_full")

        if generated:
            logger.info("output_formats_complete", formats=generated)

    def _filter_pages(self) -> list[Page]:
        """
        Filter pages based on exclusion rules.

        Excludes pages that:
        - Have no output path (not rendered yet)
        - Are in excluded sections
        - Match excluded patterns (e.g., '404.html', 'search.html')

        Returns:
            List of pages to include in output formats
        """
        options = self.config.get("options", {})
        exclude_sections = options.get("exclude_sections", [])
        exclude_patterns = options.get("exclude_patterns", ["404.html", "search.html"])

        logger.debug(
            "filtering_pages_for_output",
            total_pages=len(self.site.pages),
            exclude_sections=exclude_sections,
            exclude_patterns=exclude_patterns,
        )

        filtered = []
        excluded_by_section = 0
        excluded_by_pattern = 0
        excluded_no_output = 0

        for page in self.site.pages:
            # Skip if no output path
            if not page.output_path:
                excluded_no_output += 1
                continue

            # Check section exclusions
            section_name = (
                getattr(page._section, "name", "")
                if hasattr(page, "_section") and page._section
                else ""
            )
            if section_name in exclude_sections:
                excluded_by_section += 1
                continue

            # Check pattern exclusions
            output_str = str(page.output_path)
            if any(pattern in output_str for pattern in exclude_patterns):
                excluded_by_pattern += 1
                continue

            filtered.append(page)

        logger.debug(
            "page_filtering_complete",
            filtered_pages=len(filtered),
            excluded_no_output=excluded_no_output,
            excluded_by_section=excluded_by_section,
            excluded_by_pattern=excluded_by_pattern,
        )

        return filtered
