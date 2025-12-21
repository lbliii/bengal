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
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, ValidatorStats
from bengal.utils.logger import get_logger

from .analysis import DirectiveAnalyzer
from .checkers import (
    check_directive_completeness,
    check_directive_performance,
    check_directive_rendering,
    check_directive_syntax,
)
from .constants import (
    ADMONITION_TYPES,
    CODE_BLOCK_DIRECTIVES,
    KNOWN_DIRECTIVES,
    MAX_DIRECTIVES_PER_PAGE,
    MAX_NESTING_DEPTH,
    MAX_TABS_PER_BLOCK,
)

if TYPE_CHECKING:
    from bengal.core.site import Site

# Re-export for public API
__all__ = [
    "DirectiveValidator",
    "DirectiveAnalyzer",
    "KNOWN_DIRECTIVES",
    "ADMONITION_TYPES",
    "CODE_BLOCK_DIRECTIVES",
    "MAX_DIRECTIVES_PER_PAGE",
    "MAX_NESTING_DEPTH",
    "MAX_TABS_PER_BLOCK",
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
    5. Checking rendering output (check_directive_rendering)

    Checks:
    - Directive blocks are well-formed (opening and closing)
    - Required options are present
    - Tab markers are properly formatted
    - Nesting depth is reasonable
    - Performance warnings for heavy directive usage
    """

    name = "Directives"
    description = "Validates directive syntax, completeness, and performance"
    enabled_by_default = True

    # Expose constants as class attributes for backward compatibility
    KNOWN_DIRECTIVES = KNOWN_DIRECTIVES
    ADMONITION_TYPES = ADMONITION_TYPES
    CODE_BLOCK_DIRECTIVES = CODE_BLOCK_DIRECTIVES
    MAX_DIRECTIVES_PER_PAGE = MAX_DIRECTIVES_PER_PAGE
    MAX_NESTING_DEPTH = MAX_NESTING_DEPTH
    MAX_TABS_PER_BLOCK = MAX_TABS_PER_BLOCK

    # Store stats from last validation for observability
    last_stats: ValidatorStats | None = None

    @override
    def validate(self, site: Site, build_context: Any = None) -> list[CheckResult]:
        """
        Run directive validation checks.

        Uses cached content from build_context when available to avoid
        redundant disk I/O (build-integrated validation).

        Args:
            site: Site instance to validate
            build_context: Optional BuildContext with cached page contents.
                          When provided, uses cached content instead of
                          reading from disk (~4 seconds saved for large sites).

        Returns:
            List of CheckResult objects
        """
        results = []
        sub_timings: dict[str, float] = {}

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

        # Check 4: Rendering validation (check output HTML)
        t4 = time.time()
        results.extend(check_directive_rendering(site, directive_data))
        sub_timings["rendering"] = (time.time() - t4) * 1000

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
            **{
                "pages_processed": self.last_stats.pages_processed,
                "pages_total": self.last_stats.pages_total,
                "cache_hits": self.last_stats.cache_hits,
                "cache_misses": self.last_stats.cache_misses,
                "analyze_ms": sub_timings.get("analyze", 0),
                "rendering_ms": sub_timings.get("rendering", 0),
            },
        )

        return results
