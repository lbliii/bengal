"""
Data models for link checking results and summaries.

Provides dataclasses and enums for representing link check outcomes:

Models:
    LinkKind: Classification enum (INTERNAL, EXTERNAL)
    LinkStatus: Result status enum (OK, BROKEN, IGNORED, ERROR)
    LinkCheckResult: Individual link check result with metadata
    LinkCheckSummary: Aggregate statistics for a check run

All models support JSON serialization via to_dict() methods for
reporting and CI integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LinkKind(str, Enum):
    """
    Classification of link type.

    Values:
        INTERNAL: Links within the same site (relative or absolute site paths)
        EXTERNAL: Links to other domains (http://, https://)
    """

    INTERNAL = "internal"
    EXTERNAL = "external"


class LinkStatus(str, Enum):
    """
    Result status from checking a link.

    Values:
        OK: Link is valid (2xx-3xx response or page exists)
        BROKEN: Link is broken (4xx response or page not found)
        IGNORED: Link was skipped due to ignore policy
        ERROR: Network error, timeout, or other check failure
    """

    OK = "ok"
    BROKEN = "broken"
    IGNORED = "ignored"
    ERROR = "error"


@dataclass
class LinkCheckResult:
    """
    Result of checking a single link.

    Captures all information about a link check including the URL, status,
    HTTP details, and reference information for reporting.

    Attributes:
        url: The URL that was checked
        kind: LinkKind.INTERNAL or LinkKind.EXTERNAL
        status: LinkStatus result (OK, BROKEN, IGNORED, ERROR)
        status_code: HTTP status code (external links only)
        reason: HTTP reason phrase or error description
        first_ref: Path of first page that references this link
        ref_count: Number of pages referencing this link
        ignored: True if link was skipped by ignore policy
        ignore_reason: Why the link was ignored
        error_message: Error details if status is ERROR
        metadata: Additional data (e.g., available_anchors for broken anchor)
    """

    url: str
    kind: LinkKind
    status: LinkStatus
    status_code: int | None = None
    reason: str | None = None
    first_ref: str | None = None
    ref_count: int = 1
    ignored: bool = False
    ignore_reason: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dict with all fields suitable for JSON output.
        """
        return {
            "url": self.url,
            "kind": self.kind.value,
            "status": self.status.value,
            "status_code": self.status_code,
            "reason": self.reason,
            "first_ref": self.first_ref,
            "ref_count": self.ref_count,
            "ignored": self.ignored,
            "ignore_reason": self.ignore_reason,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class LinkCheckSummary:
    """
    Aggregate statistics for a link check run.

    Used by LinkCheckOrchestrator to summarize results and determine
    pass/fail status for CI integration.

    Attributes:
        total_checked: Total number of unique URLs checked
        ok_count: Count of OK (valid) links
        broken_count: Count of BROKEN links
        ignored_count: Count of IGNORED links
        error_count: Count of ERROR results
        duration_ms: Total check duration in milliseconds
    """

    total_checked: int = 0
    ok_count: int = 0
    broken_count: int = 0
    ignored_count: int = 0
    error_count: int = 0
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        """
        Check if the link check passed (no broken or error links).

        Returns:
            True if broken_count == 0 and error_count == 0.
        """
        return self.broken_count == 0 and self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dict with counts, duration, and pass/fail status.
        """
        return {
            "total_checked": self.total_checked,
            "ok": self.ok_count,
            "broken": self.broken_count,
            "ignored": self.ignored_count,
            "errors": self.error_count,
            "duration_ms": round(self.duration_ms, 2),
            "passed": self.passed,
        }
