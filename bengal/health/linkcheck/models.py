"""
Data models for link checking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LinkKind(str, Enum):
    """Kind of link being checked."""

    INTERNAL = "internal"
    EXTERNAL = "external"


class LinkStatus(str, Enum):
    """Status of link check result."""

    OK = "ok"
    BROKEN = "broken"
    IGNORED = "ignored"
    ERROR = "error"  # For network errors, timeouts, etc.


@dataclass
class LinkCheckResult:
    """Result of checking a single link."""

    url: str
    kind: LinkKind
    status: LinkStatus
    status_code: int | None = None
    reason: str | None = None
    first_ref: str | None = None  # First page that references this link
    ref_count: int = 1
    ignored: bool = False
    ignore_reason: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
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
    """Summary of link check results."""

    total_checked: int = 0
    ok_count: int = 0
    broken_count: int = 0
    ignored_count: int = 0
    error_count: int = 0
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        """Return True if no broken or error links found."""
        return self.broken_count == 0 and self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_checked": self.total_checked,
            "ok": self.ok_count,
            "broken": self.broken_count,
            "ignored": self.ignored_count,
            "errors": self.error_count,
            "duration_ms": round(self.duration_ms, 2),
            "passed": self.passed,
        }
