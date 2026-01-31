"""
Health check report formatting and data structures.

This module provides the core data structures for health check results and
multiple output formats for different contexts (console, JSON, CI integration).

Data Models:
    CheckStatus: Severity enum (ERROR, WARNING, SUGGESTION, INFO, SUCCESS)
    CheckResult: Individual check result with status, message, recommendations
    ValidatorStats: Observability metrics for validator execution
    ValidatorReport: Results from a single validator
    HealthReport: Aggregate report from all validators

Output Formats:
    - Console: Rich text with colors, progressive disclosure for readability
    - JSON: Machine-readable for CI integration and automation
    - Quality scoring: 0-100 score with ratings (Excellent/Good/Fair/Needs Improvement)

Architecture:
    Reports are immutable data containers with computed properties. Formatting
    logic is kept in methods rather than separate functions to enable easy
    serialization and manipulation.

Related:
    - bengal.health.health_check: Orchestrator that produces HealthReport
    - bengal.health.base: Validators that produce CheckResult objects

"""

from .health_report import HealthReport
from .models import CheckResult, CheckStatus, ValidatorReport, ValidatorStats

__all__ = [
    "CheckResult",
    "CheckStatus",
    "HealthReport",
    "ValidatorReport",
    "ValidatorStats",
]
