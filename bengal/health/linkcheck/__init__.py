"""
Link checker for internal and external URLs.

Provides async external link checking with retries, backoff, and ignore policies.
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
