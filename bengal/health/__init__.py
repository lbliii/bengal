"""
Health check system for Bengal SSG.

This package provides comprehensive build validation through a modular validator
architecture. Validators are organized into execution phases optimized for speed
and dependencies:

Validation Phases:
    Phase 1 (Basic): Config, output, URL collisions, ownership policy
    Phase 2 (Content): Rendering, directives, navigation, menus, taxonomy, links
    Phase 3 (Advanced): Cache integrity, performance metrics
    Phase 4 (Production): RSS, sitemap, fonts, assets
    Phase 5 (Knowledge): Connectivity and orphan detection

Key Components:
    HealthCheck: Main orchestrator coordinating all validators
    HealthReport: Structured report with formatting for console/JSON output
    BaseValidator: Abstract base class for implementing custom validators
    CheckResult: Individual check result with status, message, and recommendations
    CheckStatus: Severity levels (ERROR, WARNING, SUGGESTION, INFO, SUCCESS)

Architecture:
    The health check system follows Bengal's orchestrator pattern. HealthCheck
    coordinates validators but does not perform I/O directly. Each validator
    is independent and returns CheckResult objects. Parallel execution is
    supported for validators without interdependencies.

Related:
    - bengal.health.validators: Built-in validators (20+)
    - bengal.health.linkcheck: External and internal link checking
    - bengal.health.autofix: Automated fixes for common issues

Example:
    >>> from bengal.health import HealthCheck
    >>> health = HealthCheck(site)
    >>> report = health.run()
    >>> print(report.format_console())
    >>> # Or get JSON for CI integration
    >>> data = report.format_json()
"""

from __future__ import annotations

from bengal.health.base import BaseValidator
from bengal.health.health_check import HealthCheck
from bengal.health.report import CheckResult, CheckStatus, HealthReport

__all__ = [
    "BaseValidator",
    "CheckResult",
    "CheckStatus",
    "HealthCheck",
    "HealthReport",
]
