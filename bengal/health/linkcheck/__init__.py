"""
Link checking subpackage for internal and external URL validation.

This package provides comprehensive link checking capabilities:

Features:
    - Internal link validation (page-to-page, anchor links)
    - Async external link checking with httpx
    - Configurable ignore policies (patterns, domains, status codes)
    - Exponential backoff with jitter for retries
    - Per-host concurrency limits to avoid rate limiting

Components:
    LinkCheckOrchestrator: Coordinates internal and external checking
    AsyncLinkChecker: Async external HTTP link checker
    InternalLinkChecker: Validates internal page and anchor links
    IgnorePolicy: Configures which links/statuses to skip

Data Models:
    LinkCheckResult: Result of checking a single link
    LinkCheckSummary: Aggregate statistics for a check run
    LinkKind: INTERNAL or EXTERNAL classification
    LinkStatus: OK, BROKEN, IGNORED, or ERROR

Example:
    >>> from bengal.health.linkcheck import LinkCheckOrchestrator
    >>> orchestrator = LinkCheckOrchestrator(site, check_external=True)
    >>> results, summary = orchestrator.check_all_links()
    >>> print(orchestrator.format_console_report(results, summary))

Related:
    - bengal.health.validators.links: LinkValidator health check
    - bengal.config: linkcheck configuration options
"""

from __future__ import annotations

from bengal.health.linkcheck.async_checker import AsyncLinkChecker
from bengal.health.linkcheck.internal_checker import InternalLinkChecker
from bengal.health.linkcheck.models import LinkCheckResult, LinkKind, LinkStatus
from bengal.health.linkcheck.orchestrator import LinkCheckOrchestrator

__all__ = [
    "AsyncLinkChecker",
    "InternalLinkChecker",
    "LinkCheckOrchestrator",
    "LinkCheckResult",
    "LinkKind",
    "LinkStatus",
]
