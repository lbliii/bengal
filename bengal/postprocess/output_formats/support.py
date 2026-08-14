"""Config normalization, page filtering, and progress helpers."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from bengal.postprocess.utils import get_section_name
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.postprocess.output_formats.generator import OutputFormatsGenerator
    from bengal.protocols import PageLike

logger = get_logger(__name__)


def default_config() -> dict[str, Any]:
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


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
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
    normalized = default_config()

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


def _normalize_config(self: OutputFormatsGenerator, config: dict[str, Any]) -> dict[str, Any]:
    """Normalize configuration to support both simple and advanced formats."""
    return normalize_config(config)


def _default_config(self: OutputFormatsGenerator) -> dict[str, Any]:
    """Return default configuration."""
    return default_config()


def _get_graph_data_if_needed(
    self: OutputFormatsGenerator,
    pages: list[PageLike],
) -> dict[str, Any] | None:
    """Build graph data lazily only when page JSON will actually use it."""
    if not pages:
        return None
    if not self.config.get("options", {}).get("include_graph_connections", True):
        return None
    if self._graph_data_loaded:
        return self.graph_data
    if self._graph_data_provider is None:
        self._graph_data_loaded = True
        return self.graph_data

    start = time.perf_counter()
    self.graph_data = self._graph_data_provider()
    self._graph_data_loaded = True
    duration_ms = (time.perf_counter() - start) * 1000
    stats = getattr(self.build_context, "stats", None)
    timings = getattr(stats, "postprocess_task_timings_ms", None)
    if isinstance(timings, dict):
        timings["graph data"] = round(duration_ms, 1)
    return self.graph_data


def _timed_generate(
    self: OutputFormatsGenerator,
    timings: dict[str, float],
    format_name: str,
    generate_fn: Callable[[], Any],
) -> Any:
    """Run one output-format generator and record its elapsed time."""
    start = time.perf_counter()
    self._emit_output_format_started(format_name)
    try:
        result = generate_fn()
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        self._emit_output_format_finished(format_name, duration_ms)
        raise
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
    self._emit_output_format_finished(format_name, duration_ms)
    return result


def _emit_output_format_started(self: OutputFormatsGenerator, format_name: str) -> None:
    """Show long-running output-format work before it completes."""
    if not self._should_emit_cli_progress():
        return
    from bengal.output import get_cli_output

    cli = get_cli_output()
    cli.detail(f"output formats: {format_name}...", indent=2, icon=cli.icons.arrow)


def _emit_output_format_finished(
    self: OutputFormatsGenerator,
    format_name: str,
    duration_ms: float,
) -> None:
    """Show a completed output-format generator with elapsed time."""
    if not self._should_emit_cli_progress():
        return
    from bengal.output import get_cli_output

    cli = get_cli_output()
    cli.detail(
        f"output formats: {format_name} {int(duration_ms)}ms",
        indent=2,
        icon=cli.icons.success,
    )


def _should_emit_cli_progress(self: OutputFormatsGenerator) -> bool:
    """Return whether output-format progress should be printed directly."""
    progress_manager = getattr(self.build_context, "progress_manager", None)
    return progress_manager is None


def _filter_pages(self: OutputFormatsGenerator) -> list[PageLike]:
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
