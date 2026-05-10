"""
Directive validator package - checks directive syntax, usage, and performance.

This package validates:
- Directive syntax is well-formed
- Required directive options present
- Tab markers properly formatted
- Nesting depth reasonable
- Performance warnings for directive-heavy pages

Structure:
- constants.py: Known directives, thresholds, configuration
- analysis.py: DirectiveAnalyzer for extracting and analyzing directives
- checkers.py: Validation check functions
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, ValidatorStats
from bengal.utils.observability.logger import get_logger

from .analysis import DirectiveAnalyzer
from .checkers import (
    check_directive_completeness,
    check_directive_performance,
    check_directive_syntax,
)
from .constants import (
    ADMONITION_TYPES,
    CODE_BLOCK_DIRECTIVES,
    KNOWN_DIRECTIVES,
    MAX_NESTING_DEPTH,
    MAX_TABS_PER_BLOCK,
)

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

# Re-export for public API
__all__ = [
    "ADMONITION_TYPES",
    "CODE_BLOCK_DIRECTIVES",
    "KNOWN_DIRECTIVES",
    "MAX_NESTING_DEPTH",
    "MAX_TABS_PER_BLOCK",
    "DirectiveAnalyzer",
    "DirectiveValidator",
]

logger = get_logger(__name__)


class DirectiveValidator(BaseValidator):
    """
    Validates directive syntax and usage across the site.

    Orchestrates validation by:
    1. Analyzing directives across all pages (DirectiveAnalyzer)
    2. Checking syntax validity (check_directive_syntax)
    3. Checking completeness (check_directive_completeness)
    4. Checking performance (check_directive_performance)

    Checks:
    - Directive blocks are well-formed (opening and closing)
    - Required options are present
    - Tab markers are properly formatted
    - Nesting depth is reasonable
    - Performance warnings for heavy directive usage

    Note: Rendering validation (H207) was removed - syntax validation catches
    directive problems at source level, making output scanning redundant.

    """

    name = "Directives"
    description = "Validates directive syntax, completeness, and performance"
    enabled_by_default = True

    # Expose constants as class attributes for backward compatibility
    KNOWN_DIRECTIVES = KNOWN_DIRECTIVES
    ADMONITION_TYPES = ADMONITION_TYPES
    CODE_BLOCK_DIRECTIVES = CODE_BLOCK_DIRECTIVES
    MAX_NESTING_DEPTH = MAX_NESTING_DEPTH
    MAX_TABS_PER_BLOCK = MAX_TABS_PER_BLOCK

    # Store stats from last validation for observability
    last_stats: ValidatorStats | None = None
    last_file_results: dict[Path, list[CheckResult]] | None = None

    @override
    def validate(self, site: SiteLike, build_context: Any = None) -> list[CheckResult]:
        """
        Run directive validation checks.

        Uses cached content from build_context when available to avoid
        redundant disk I/O (build-integrated validation).

        Args:
            site: SiteLike instance to validate
            build_context: Optional BuildContext with cached page contents.
                          When provided, uses cached content instead of
                          reading from disk (~4 seconds saved for large sites).

        Returns:
            List of CheckResult objects
        """
        results = []
        sub_timings: dict[str, float] = {}
        self.last_file_results = None

        # Gather all directive data from source files
        # Uses cached content if build_context is provided (build-integrated validation)
        t0 = time.time()
        analyzer = DirectiveAnalyzer()
        directive_data = analyzer.analyze(site, build_context=build_context)
        sub_timings["analyze"] = (time.time() - t0) * 1000

        # Check 1: Syntax validation
        t1 = time.time()
        results.extend(check_directive_syntax(directive_data))
        sub_timings["syntax"] = (time.time() - t1) * 1000

        # Check 2: Completeness validation
        t2 = time.time()
        results.extend(check_directive_completeness(directive_data))
        sub_timings["completeness"] = (time.time() - t2) * 1000

        # Check 3: Performance warnings
        t3 = time.time()
        results.extend(check_directive_performance(directive_data))
        sub_timings["performance"] = (time.time() - t3) * 1000
        self.last_file_results = _file_results_by_source(directive_data)

        # Note: Rendering validation (H207) was removed - it parsed all HTML output
        # files which took ~1.2s and never caught any issues. Syntax validation (H201)
        # catches directive problems at source level, making H207 redundant.

        # Build and store stats for observability
        analyzer_stats = directive_data.get("_stats", {})
        self.last_stats = ValidatorStats(
            pages_total=analyzer_stats.get("pages_total", 0),
            pages_processed=analyzer_stats.get("pages_processed", 0),
            pages_skipped=analyzer_stats.get("pages_skipped", {}),
            cache_hits=analyzer_stats.get("cache_hits", 0),
            cache_misses=analyzer_stats.get("cache_misses", 0),
            sub_timings=sub_timings,
        )

        # Log stats at debug level for observability
        logger.debug(
            "directive_validator_complete",
            pages_processed=self.last_stats.pages_processed,
            pages_total=self.last_stats.pages_total,
            cache_hits=self.last_stats.cache_hits,
            cache_misses=self.last_stats.cache_misses,
            analyze_ms=sub_timings.get("analyze", 0),
        )

        return results


def _file_results_by_source(directive_data: dict[str, Any]) -> dict[Path, list[CheckResult]]:
    """Build per-source directive results for incremental health caching."""
    results_by_source: dict[Path, list[CheckResult]] = {}
    for source_path in directive_data.get("_analyzed_paths", []):
        if not isinstance(source_path, Path):
            continue
        file_data = _directive_data_for_source(directive_data, source_path)
        results: list[CheckResult] = []
        results.extend(check_directive_syntax(file_data))
        results.extend(check_directive_completeness(file_data))
        results.extend(check_directive_performance(file_data))
        results_by_source[source_path] = results
    return results_by_source


def _directive_data_for_source(directive_data: dict[str, Any], source_path: Path) -> dict[str, Any]:
    """Filter aggregate directive data down to one source path."""
    source_key = str(source_path)
    return {
        "total_directives": len(directive_data.get("by_page", {}).get(source_key, [])),
        "by_type": {},
        "by_page": {source_key: directive_data.get("by_page", {}).get(source_key, [])},
        "syntax_errors": [
            item
            for item in directive_data.get("syntax_errors", [])
            if item.get("page") == source_path
        ],
        "completeness_errors": [
            item
            for item in directive_data.get("completeness_errors", [])
            if item.get("page") == source_path
        ],
        "performance_warnings": [
            item
            for item in directive_data.get("performance_warnings", [])
            if item.get("page") == source_path
        ],
        "fence_nesting_warnings": [
            item
            for item in directive_data.get("fence_nesting_warnings", [])
            if item.get("page") == source_path
        ],
    }
