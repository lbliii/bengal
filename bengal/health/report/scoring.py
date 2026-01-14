"""
Quality scoring algorithms for health reports.

This module provides functions and methods for calculating build quality
scores based on health check results.
"""

from __future__ import annotations


def calculate_quality_score(total_errors: int, total_warnings: int, total_checks: int) -> int:
    """
    Calculate build quality score (0-100).

    Uses a penalty-based system where:
    - Base score is 100 (no problems = perfect)
    - Errors subtract significantly (blockers)
    - Warnings subtract moderately (should fix)
    - Diminishing returns prevent extreme scores for many small issues

    This ensures same problems always give the same score, regardless
    of how many checks ran.

    Args:
        total_errors: Total number of error-level issues
        total_warnings: Total number of warning-level issues
        total_checks: Total number of checks run

    Returns:
        Score from 0-100 (100 = perfect)
    """
    if total_checks == 0:
        return 100

    # No problems = 100%
    if total_errors == 0 and total_warnings == 0:
        return 100

    # Penalty system with diminishing returns
    # Errors: 20 points each, but diminish after 2 (avoids 0% for many issues)
    # Formula: min(70, errors * 20 - max(0, errors - 2) * 5)
    # This gives: 1 error=20, 2 errors=40, 3 errors=55, 4 errors=70 (cap)
    error_penalty = min(70, total_errors * 20 - max(0, total_errors - 2) * 5)

    # Warnings: 5 points each, capped at 25
    warning_penalty = min(25, total_warnings * 5)

    score = 100 - error_penalty - warning_penalty
    return max(0, score)


def get_quality_rating(score: int) -> str:
    """
    Get quality rating based on score.

    Thresholds aligned with penalty-based scoring:
    - Excellent (90+): No errors, 0-2 warnings
    - Good (75-89): 1 error or 3-5 warnings
    - Fair (50-74): 2-3 errors or many warnings
    - Needs Improvement (<50): 4+ errors

    Args:
        score: Quality score (0-100)

    Returns:
        Rating string: "Excellent", "Good", "Fair", or "Needs Improvement"
    """
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 50:
        return "Fair"
    else:
        return "Needs Improvement"
