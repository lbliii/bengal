"""Facade that coordinates per-page and site-wide output format generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.incremental import (
    _changed_page_source_keys,
    _expected_search_backend_outputs,
    _expected_site_wide_outputs,
    _generate_search_backend_if_needed,
    _generate_site_wide_if_needed,
    _merge_cached_page_artifacts,
    _per_page_target_pages,
    _search_backend_fingerprint_options,
    _site_wide_input_fingerprint,
)
from bengal.postprocess.output_formats.json_generator import PageJSONGenerator
from bengal.postprocess.output_formats.md_generator import PageMarkdownGenerator
from bengal.postprocess.output_formats.site_wide import generate_site_wide_formats
from bengal.postprocess.output_formats.support import (
    _default_config,
    _emit_output_format_finished,
    _emit_output_format_started,
    _filter_pages,
    _get_graph_data_if_needed,
    _normalize_config,
    _should_emit_cli_progress,
    _timed_generate,
    normalize_config,
)
from bengal.postprocess.output_formats.txt_generator import PageTxtGenerator
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)


class OutputFormatsGenerator:
    """
    Facade for generating all output format variants.

    Coordinates generation of alternative content formats to enable
    client-side search, AI/LLM discovery, and programmatic API access.

    Creation:
        Direct instantiation: OutputFormatsGenerator(site, config=config)
            - Created by PostprocessOrchestrator for output format generation
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with pages
        config: Normalized configuration dict
        graph_data: Optional pre-computed graph data for contextual minimap
        build_context: Optional BuildContext with accumulated JSON data

    Relationships:
        - Used by: PostprocessOrchestrator for output format generation
        - Delegates to: PageJSONGenerator, PageTxtGenerator,
                        SiteIndexGenerator, SiteLlmTxtGenerator

    Output Formats:
        Per-Page:
            - json: page.json with metadata, content, graph connections
            - llm_txt: page.txt with structured plain text

        Site-Wide:
            - index_json: index.json for client-side search
            - llm_full: llm-full.txt with all site content

    Configuration Formats:
        Simple (from [build.output_formats]):
            {'enabled': True, 'json': True, 'llm_txt': True}

        Advanced (from [output_formats]):
            {'per_page': ['json', 'llm_txt'], 'site_wide': ['index_json']}

    Example:
            >>> generator = OutputFormatsGenerator(site, config=config)
            >>> generator.generate()

    """

    def __init__(
        self,
        site: SiteLike,
        config: dict[str, Any] | None = None,
        graph_data: dict[str, Any] | None = None,
        graph_data_provider: Callable[[], dict[str, Any] | None] | None = None,
        build_context: BuildContext | Any | None = None,
    ) -> None:
        """
        Initialize output formats generator.

        Args:
            site: Site instance
            config: Configuration dict from bengal.toml
            graph_data: Optional pre-computed graph data for including in page JSON
            graph_data_provider: Optional lazy graph builder for page JSON
            build_context: Optional BuildContext with accumulated JSON data from rendering phase
        """
        self.site = site
        self.config = normalize_config(config or {})
        self.graph_data = graph_data
        self._graph_data_provider = graph_data_provider
        self._graph_data_loaded = graph_data is not None
        self._pending_site_wide_page_hashes: dict[str, dict[str, str]] = {}
        self.build_context = build_context

    def generate(self) -> None:
        """
        Generate all enabled output formats.

        Checks configuration to determine which formats to generate,
        filters pages based on exclusion rules and content signals,
        then generates:
        1. Per-page formats (JSON, LLM text) — only for ai_input-permitted pages
        2. Site-wide formats (index.json, llm-full.txt) — respecting search/ai_train

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

        # Content-signal-aware subsets: enforce signals at the output level
        ai_input_pages = [p for p in pages if getattr(p, "in_ai_input", True)]
        ai_train_pages = [p for p in pages if getattr(p, "in_ai_train", True)]
        search_pages = [p for p in pages if getattr(p, "in_search", True)]

        excluded_ai_input = len(pages) - len(ai_input_pages)
        excluded_ai_train = len(pages) - len(ai_train_pages)
        excluded_search = len(pages) - len(search_pages)
        if excluded_ai_input or excluded_ai_train or excluded_search:
            logger.info(
                "content_signals_enforcement",
                excluded_ai_input=excluded_ai_input,
                excluded_ai_train=excluded_ai_train,
                excluded_search=excluded_search,
            )

        # Track what we generated
        generated = []
        timings: dict[str, float] = {}
        options = self.config.get("options", {})
        per_page_targets: dict[str, list[PageLike]] = {}

        # Get accumulated page data once (shared by multiple generators)
        # See: plan/drafted/rfc-unified-page-data-accumulation.md
        accumulated_data = None
        if self.build_context and (
            self.build_context.has_accumulated_page_data
            or getattr(self.build_context, "incremental", False)
        ):
            accumulated_data = self.build_context.get_accumulated_page_data()
            accumulated_data = self._merge_cached_page_artifacts(pages, accumulated_data)
            logger.debug(
                "using_accumulated_page_data",
                count=len(accumulated_data),
                total_pages=len(pages),
            )

        # Per-page outputs — use ai_input_pages (machine-readable for AI)
        if "json" in per_page:
            per_page_targets["json"] = self._per_page_target_pages(ai_input_pages, "json")
            graph_data = self._get_graph_data_if_needed(per_page_targets["json"])
            # Get config options for HTML/text inclusion
            include_html = options.get("include_html_content", False)
            include_text = options.get("include_plain_text", True)
            include_chunks = options.get("include_chunks", True)
            json_gen = PageJSONGenerator(
                self.site,
                graph_data=graph_data,
                include_html=include_html,
                include_text=include_text,
                include_chunks=include_chunks,
            )
            # OPTIMIZATION: Use accumulated page data if available
            # Extract JSON-specific data from unified accumulator
            # See: plan/drafted/rfc-unified-page-data-accumulation.md
            accumulated_json = None
            if accumulated_data:
                # Filter accumulated data to ai_input-permitted pages
                ai_input_urls = {p.href for p in per_page_targets["json"]}
                accumulated_json = [
                    (data.json_output_path, data.full_json_data)
                    for data in accumulated_data
                    if data.full_json_data is not None
                    and data.full_json_data.get("url") in ai_input_urls
                ]
            count = self._timed_generate(
                timings,
                "page_json",
                lambda: json_gen.generate(
                    per_page_targets["json"],
                    accumulated_json=accumulated_json,
                ),
            )
            generated.append(f"JSON ({count} files)")
            logger.debug("generated_page_json", file_count=count)

        if "llm_txt" in per_page:
            per_page_targets["llm_txt"] = self._per_page_target_pages(ai_input_pages, "llm_txt")
            separator_width = options.get("llm_separator_width", 80)
            txt_gen = PageTxtGenerator(self.site, separator_width=separator_width)
            count = self._timed_generate(
                timings,
                "page_llm_txt",
                lambda: txt_gen.generate(per_page_targets["llm_txt"]),
            )
            generated.append(f"LLM text ({count} files)")
            logger.debug("generated_page_txt", file_count=count)

        if "markdown" in per_page:
            per_page_targets["markdown"] = self._per_page_target_pages(
                ai_input_pages,
                "markdown",
            )
            md_gen = PageMarkdownGenerator(self.site)
            count = self._timed_generate(
                timings,
                "page_markdown",
                lambda: md_gen.generate(per_page_targets["markdown"]),
            )
            generated.append(f"Markdown ({count} files)")
            logger.debug("generated_page_markdown", file_count=count)

        generate_site_wide_formats(
            self,
            generated=generated,
            timings=timings,
            options=options,
            site_wide=site_wide,
            accumulated_data=accumulated_data,
            ai_input_pages=ai_input_pages,
            ai_train_pages=ai_train_pages,
            search_pages=search_pages,
        )

        if generated:
            logger.info("output_formats_complete", formats=generated, timings_ms=timings)

    _normalize_config = _normalize_config
    _default_config = _default_config
    _filter_pages = _filter_pages
    _get_graph_data_if_needed = _get_graph_data_if_needed
    _timed_generate = _timed_generate
    _emit_output_format_started = _emit_output_format_started
    _emit_output_format_finished = _emit_output_format_finished
    _should_emit_cli_progress = _should_emit_cli_progress
    _merge_cached_page_artifacts = _merge_cached_page_artifacts
    _per_page_target_pages = _per_page_target_pages
    _changed_page_source_keys = _changed_page_source_keys
    _generate_site_wide_if_needed = _generate_site_wide_if_needed
    _generate_search_backend_if_needed = _generate_search_backend_if_needed
    _search_backend_fingerprint_options = _search_backend_fingerprint_options
    _expected_search_backend_outputs = _expected_search_backend_outputs
    _site_wide_input_fingerprint = _site_wide_input_fingerprint
    _expected_site_wide_outputs = _expected_site_wide_outputs
