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
- llms_txt_generator.py: Site-wide llms.txt (curated overview per llmstxt.org)
- utils.py: Shared utilities

Configuration (bengal.toml):
[output_formats]
    enabled = true
    per_page = ["json", "llm_txt"]
    site_wide = ["index_json", "llm_full", "llms_txt"]

"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.agent_manifest_generator import (
    AgentManifestGenerator,
)
from bengal.postprocess.output_formats.base import BaseOutputGenerator
from bengal.postprocess.output_formats.changelog_generator import ChangelogGenerator
from bengal.postprocess.output_formats.index_generator import SiteIndexGenerator
from bengal.postprocess.output_formats.json_generator import PageJSONGenerator
from bengal.postprocess.output_formats.llm_generator import SiteLlmTxtGenerator
from bengal.postprocess.output_formats.llms_txt_generator import SiteLlmsTxtGenerator
from bengal.postprocess.output_formats.lunr_index_generator import LunrIndexGenerator
from bengal.postprocess.output_formats.md_generator import PageMarkdownGenerator
from bengal.postprocess.output_formats.txt_generator import PageTxtGenerator
from bengal.postprocess.output_formats.utils import get_i18n_output_path
from bengal.postprocess.utils import get_section_name
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)

__all__ = [
    "BaseOutputGenerator",
    "LunrIndexGenerator",
    "OutputFormatsGenerator",
    "PageJSONGenerator",
    "PageMarkdownGenerator",
    "PageTxtGenerator",
    "SiteIndexGenerator",
    "SiteLlmTxtGenerator",
    "SiteLlmsTxtGenerator",
]


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
        build_context: BuildContext | Any | None = None,
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
            per_page: list[str] = []
            site_wide: list[str] = []

            # Track whether user explicitly configured per_page or site_wide options
            # This distinguishes "not configured" (use defaults) from "all disabled"
            per_page_keys = {"json", "llm_txt"}
            site_wide_keys = {"site_json", "site_llm"}
            has_per_page_config = any(key in config for key in per_page_keys)
            has_site_wide_config = any(key in config for key in site_wide_keys)

            if config.get("json", False):
                per_page.append("json")
            if config.get("llm_txt", False):
                per_page.append("llm_txt")
            if config.get("site_json", False):
                site_wide.append("index_json")
            if config.get("site_llm", False):
                site_wide.append("llm_full")

            # Only override defaults if user explicitly configured these options
            # This allows {"json": False, "llm_txt": False} to disable all per-page formats
            if has_per_page_config or per_page:
                normalized["per_page"] = per_page
            if has_site_wide_config or site_wide:
                normalized["site_wide"] = site_wide

        # Propagate enabled flag
        if "enabled" in config:
            normalized["enabled"] = config["enabled"]

        return normalized

    def _default_config(self) -> dict[str, Any]:
        """Return default configuration."""
        return {
            "enabled": True,
            "per_page": ["json", "llm_txt", "markdown"],  # JSON + LLM text + Markdown by default
            "site_wide": [
                "index_json",
                "llm_full",
                "llms_txt",
                "changelog",
                "agent_manifest",
            ],  # Search index + LLM texts
            "options": {
                "include_html_content": False,  # HTML file already exists, no need to duplicate
                "include_plain_text": True,
                "include_chunks": True,
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

        # Get accumulated page data once (shared by multiple generators)
        # See: plan/drafted/rfc-unified-page-data-accumulation.md
        accumulated_data = None
        if self.build_context and self.build_context.has_accumulated_page_data:
            accumulated_data = self.build_context.get_accumulated_page_data()
            accumulated_data = self._merge_cached_page_artifacts(pages, accumulated_data)
            logger.debug(
                "using_accumulated_page_data",
                count=len(accumulated_data),
                total_pages=len(pages),
            )

        # Per-page outputs — use ai_input_pages (machine-readable for AI)
        if "json" in per_page:
            # Get config options for HTML/text inclusion
            include_html = options.get("include_html_content", False)
            include_text = options.get("include_plain_text", True)
            include_chunks = options.get("include_chunks", True)
            json_gen = PageJSONGenerator(
                self.site,
                graph_data=self.graph_data,
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
                ai_input_urls = {p.href for p in ai_input_pages}
                accumulated_json = [
                    (data.json_output_path, data.full_json_data)
                    for data in accumulated_data
                    if data.full_json_data is not None
                    and data.full_json_data.get("url") in ai_input_urls
                ]
            count = self._timed_generate(
                timings,
                "page_json",
                lambda: json_gen.generate(ai_input_pages, accumulated_json=accumulated_json),
            )
            generated.append(f"JSON ({count} files)")
            logger.debug("generated_page_json", file_count=count)

        if "llm_txt" in per_page:
            separator_width = options.get("llm_separator_width", 80)
            txt_gen = PageTxtGenerator(self.site, separator_width=separator_width)
            count = self._timed_generate(
                timings,
                "page_llm_txt",
                lambda: txt_gen.generate(ai_input_pages),
            )
            generated.append(f"LLM text ({count} files)")
            logger.debug("generated_page_txt", file_count=count)

        if "markdown" in per_page:
            md_gen = PageMarkdownGenerator(self.site)
            count = self._timed_generate(
                timings,
                "page_markdown",
                lambda: md_gen.generate(ai_input_pages),
            )
            generated.append(f"Markdown ({count} files)")
            logger.debug("generated_page_markdown", file_count=count)

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
            # OPTIMIZATION: Pass accumulated page data for hybrid mode
            # See: plan/drafted/rfc-unified-page-data-accumulation.md
            index_result = self._generate_site_wide_if_needed(
                timings,
                "site_index_json",
                search_pages,
                accumulated_data,
                {
                    "excerpt_length": excerpt_length,
                    "json_indent": json_indent,
                    "include_full_content": include_full_content,
                },
                self._expected_site_wide_outputs("site_index_json"),
                lambda: index_gen.generate(
                    search_pages,
                    accumulated_data=accumulated_data,
                    build_context=self.build_context,
                ),
            )

            # Handle both single Path and list[Path] return
            if isinstance(index_result, list):
                # Per-version indexes
                index_paths = index_result
                generated.extend([f"index.json ({len(index_paths)} versions)"])
                logger.debug("generated_versioned_index_json", count=len(index_paths))
            else:
                # Single index
                index_paths = [index_result]
                generated.append("index.json")
                logger.debug("generated_site_index_json")

            # Generate pre-built Lunr index if enabled
            search_config = self.site.config.get("search", {})
            lunr_config = search_config.get("lunr", {})
            prebuilt_enabled = lunr_config.get("prebuilt", True)  # Default: enabled

            if prebuilt_enabled:
                lunr_gen = LunrIndexGenerator(self.site)
                if lunr_gen.is_available():
                    # Generate Lunr index for each version index
                    for index_path in index_paths:
                        lunr_path = self._timed_generate(
                            timings,
                            "site_lunr_index",
                            lambda index_path=index_path: lunr_gen.generate(index_path),
                        )
                        if lunr_path:
                            generated.append("search-index.json")
                            logger.debug("generated_prebuilt_lunr_index", path=str(lunr_path))
                else:
                    logger.debug(
                        "lunr_prebuilt_skipped",
                        reason="lunr package not installed",
                    )

        if "llm_full" in site_wide:
            separator_width = options.get("llm_separator_width", 80)
            llm_gen = SiteLlmTxtGenerator(self.site, separator_width=separator_width)
            self._generate_site_wide_if_needed(
                timings,
                "site_llm_full",
                ai_train_pages,
                accumulated_data,
                {"separator_width": separator_width},
                self._expected_site_wide_outputs("site_llm_full"),
                lambda: llm_gen.generate(ai_train_pages),
            )
            generated.append("llm-full.txt")
            logger.debug("generated_site_llm_full")

        if "llms_txt" in site_wide:
            llms_gen = SiteLlmsTxtGenerator(self.site)
            self._generate_site_wide_if_needed(
                timings,
                "site_llms_txt",
                ai_input_pages,
                accumulated_data,
                {
                    "max_pages": getattr(llms_gen, "max_pages", None),
                    "max_chars": getattr(llms_gen, "max_chars", None),
                },
                self._expected_site_wide_outputs("site_llms_txt"),
                lambda: llms_gen.generate(ai_input_pages),
            )
            generated.append("llms.txt")
            logger.debug("generated_site_llms_txt")

        if "changelog" in site_wide:
            changelog_gen = ChangelogGenerator(self.site)
            self._generate_site_wide_if_needed(
                timings,
                "site_changelog",
                ai_input_pages,
                accumulated_data,
                {},
                self._expected_site_wide_outputs("site_changelog"),
                lambda: changelog_gen.generate(ai_input_pages),
            )
            generated.append("changelog.json")
            logger.debug("generated_changelog_json")

        if "agent_manifest" in site_wide:
            agent_gen = AgentManifestGenerator(self.site)
            self._generate_site_wide_if_needed(
                timings,
                "site_agent_manifest",
                ai_input_pages,
                accumulated_data,
                {},
                self._expected_site_wide_outputs("site_agent_manifest"),
                lambda: agent_gen.generate(ai_input_pages),
            )
            generated.append("agent.json")
            logger.debug("generated_agent_manifest")

        if generated:
            logger.info("output_formats_complete", formats=generated, timings_ms=timings)

    def _merge_cached_page_artifacts(
        self,
        pages: list[PageLike],
        accumulated_data: list[Any],
    ) -> list[Any]:
        """Merge current rendered page data with cached records for unchanged pages."""
        if not self.build_context or not getattr(self.build_context, "incremental", False):
            return accumulated_data
        cache = getattr(self.build_context, "cache", None)
        page_artifacts = getattr(cache, "page_artifacts", None)
        if not cache or not isinstance(page_artifacts, dict):
            return accumulated_data

        from bengal.orchestration.build_context import AccumulatedPageData

        by_source = {data.source_path: data for data in accumulated_data}
        merged = list(accumulated_data)
        for page in pages:
            source_path = getattr(page, "source_path", None)
            if not source_path or source_path in by_source:
                continue
            cache_key = str(cache._cache_key(_site_relative_path(self.site, source_path)))
            record = page_artifacts.get(cache_key)
            if not isinstance(record, dict):
                continue
            merged.append(_page_artifact_to_accumulated(record, AccumulatedPageData))
        return merged

    def _generate_site_wide_if_needed(
        self,
        timings: dict[str, float],
        format_name: str,
        pages: list[PageLike],
        accumulated_data: list[Any] | None,
        options: dict[str, Any],
        expected_outputs: list[Path] | None,
        generate_fn: Callable[[], Any],
    ) -> Any:
        """Skip unchanged site-wide generators when their artifact input fingerprint matches."""
        fingerprint = self._site_wide_input_fingerprint(
            format_name, pages, accumulated_data, options
        )
        cache = getattr(self.build_context, "cache", None)
        fingerprints = getattr(cache, "output_format_fingerprints", None)
        can_skip = (
            fingerprint is not None
            and isinstance(fingerprints, dict)
            and expected_outputs is not None
            and all(path.exists() for path in expected_outputs)
            and fingerprints.get(format_name) == fingerprint
        )
        if can_skip:
            timings[format_name] = 0.0
            stats = getattr(self.build_context, "stats", None)
            if stats is not None:
                stats.postprocess_output_timings_ms[format_name] = 0.0
            logger.debug(
                "site_wide_output_skipped",
                format=format_name,
                reason="input_fingerprint_unchanged",
            )
            return expected_outputs if len(expected_outputs) > 1 else expected_outputs[0]

        result = self._timed_generate(timings, format_name, generate_fn)
        if fingerprint is not None and isinstance(fingerprints, dict):
            fingerprints[format_name] = fingerprint
        return result

    def _site_wide_input_fingerprint(
        self,
        format_name: str,
        pages: list[PageLike],
        accumulated_data: list[Any] | None,
        options: dict[str, Any],
    ) -> str | None:
        """Fingerprint complete site-wide generator inputs from page artifacts."""
        if not self.build_context or not getattr(self.build_context, "incremental", False):
            return None
        if not accumulated_data:
            return None

        by_source = {data.source_path: data for data in accumulated_data}
        records = []
        for page in pages:
            source_path = getattr(page, "source_path", None)
            if not source_path:
                return None
            data = by_source.get(source_path)
            if data is None:
                return None
            records.append(_fingerprint_page_artifact(data))

        payload = {
            "format": format_name,
            "options": options,
            "site": _site_fingerprint(self.site),
            "pages": records,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _expected_site_wide_outputs(self, format_name: str) -> list[Path] | None:
        """Return outputs that must exist before a site-wide generator can be skipped."""
        if format_name == "site_index_json":
            if getattr(self.site, "versioning_enabled", False):
                return None
            return [get_i18n_output_path(self.site, "index.json")]
        if format_name == "site_llm_full":
            return [self.site.output_dir / "llm-full.txt"]
        if format_name == "site_llms_txt":
            return [self.site.output_dir / "llms.txt"]
        if format_name == "site_changelog":
            return [get_i18n_output_path(self.site, "changelog.json")]
        if format_name == "site_agent_manifest":
            return [get_i18n_output_path(self.site, "agent.json")]
        return None

    def _timed_generate(
        self,
        timings: dict[str, float],
        format_name: str,
        generate_fn: Callable[[], Any],
    ) -> Any:
        """Run one output-format generator and record its elapsed time."""
        start = time.perf_counter()
        result = generate_fn()
        duration_ms = (time.perf_counter() - start) * 1000
        timings[format_name] = round(duration_ms, 1)
        stats = getattr(self.build_context, "stats", None)
        if stats is not None:
            stats.postprocess_output_timings_ms[format_name] = timings[format_name]
        logger.info(
            "output_format_generated",
            format=format_name,
            duration_ms=timings[format_name],
        )
        return result

    def _filter_pages(self) -> list[PageLike]:
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
            section_name = get_section_name(page)
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


def _page_artifact_to_accumulated(record: dict[str, Any], accumulated_type: Any) -> Any:
    """Rehydrate a cached page artifact into an AccumulatedPageData record."""
    json_output_path = record.get("json_output_path")
    return accumulated_type(
        source_path=Path(record["source_path"]),
        url=record["url"],
        uri=record["uri"],
        title=record["title"],
        description=record.get("description", ""),
        date=record.get("date"),
        date_iso=record.get("date_iso"),
        plain_text=record.get("plain_text", ""),
        excerpt=record.get("excerpt", ""),
        content_preview=record.get("content_preview", ""),
        word_count=int(record.get("word_count") or 0),
        reading_time=int(record.get("reading_time") or 0),
        section=record.get("section", ""),
        tags=list(record.get("tags") or []),
        dir=record.get("dir", ""),
        enhanced_metadata=dict(record.get("enhanced_metadata") or {}),
        is_autodoc=bool(record.get("is_autodoc", False)),
        full_json_data=record.get("full_json_data"),
        json_output_path=Path(json_output_path) if json_output_path else None,
        raw_metadata=dict(record.get("raw_metadata") or {}),
    )


def _site_relative_path(site: SiteLike, source_path: Path) -> Path:
    """Resolve relative source paths against the site root before cache lookup."""
    if source_path.is_absolute():
        return source_path
    root_path = getattr(site, "root_path", None)
    return root_path / source_path if root_path else source_path


def _fingerprint_page_artifact(data: Any) -> dict[str, Any]:
    """Return stable page artifact fields that affect site-wide output formats."""
    return {
        "source_path": str(data.source_path),
        "url": data.url,
        "uri": data.uri,
        "title": data.title,
        "description": data.description,
        "date": data.date,
        "date_iso": data.date_iso,
        "plain_text": data.plain_text,
        "excerpt": data.excerpt,
        "content_preview": data.content_preview,
        "word_count": data.word_count,
        "reading_time": data.reading_time,
        "section": data.section,
        "tags": list(data.tags),
        "dir": data.dir,
        "enhanced_metadata": _json_safe(data.enhanced_metadata),
        "is_autodoc": data.is_autodoc,
        "full_json_data": _json_safe(data.full_json_data),
        "raw_metadata": _json_safe(data.raw_metadata),
    }


def _site_fingerprint(site: SiteLike) -> dict[str, Any]:
    """Return site metadata that can affect site-wide output content."""
    build_time = getattr(site, "build_time", None)
    build_time_value = build_time.isoformat() if hasattr(build_time, "isoformat") else None
    return {
        "title": getattr(site, "title", "") or "",
        "description": getattr(site, "description", "") or "",
        "baseurl": getattr(site, "baseurl", "") or "",
        "dev_mode": bool(getattr(site, "dev_mode", False)),
        "build_time": None if getattr(site, "dev_mode", False) else build_time_value,
    }


def _json_safe(value: Any) -> Any:
    """Return a stable JSON-serializable representation for fingerprinting."""
    if isinstance(value, str | int | float | bool | type(None)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted(_json_safe(item) for item in value)
    return str(value)
