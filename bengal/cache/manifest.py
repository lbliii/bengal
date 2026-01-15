"""
Rebuild manifest for tracking what was rebuilt and why.

Provides complete record of what was rebuilt during a build:
- Page paths and their rebuild reasons
- Triggers (what caused the rebuild)
- Duration information
- Skipped pages (cache hits)

Key Concepts:
- Build-level tracking: Complete picture of a single build
- Reason-based categorization: Group rebuilds by reason
- JSON export: For debugging and observability
- Performance analysis: Duration tracking per page

Related Modules:
- bengal.orchestration.build.coordinator: Generates invalidation events
- bengal.orchestration.build.results: Build statistics
- bengal.cli.commands.build: --explain-json flag

See Also:
- plan/rfc-cache-invalidation-architecture.md: Design RFC

"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RebuildEntry:
    """Record of a single page rebuild."""

    page_path: str
    reason: str
    trigger: str
    duration_ms: float = 0.0
    from_cache: bool = False


@dataclass
class RebuildManifest:
    """
    Complete record of what was rebuilt during a build.

    Used for:
    - Debugging stale content issues
    - Build observability (--explain flag)
    - Performance analysis

    Example:
        >>> manifest = RebuildManifest(build_id="abc123", incremental=True)
        >>> manifest.add_rebuild(
        ...     page_path=Path("content/about.md"),
        ...     reason="DATA_FILE_CHANGED",
        ...     trigger="data/team.yaml",
        ...     duration_ms=45.2,
        ... )
        >>> print(manifest.to_json())
    """

    build_id: str
    incremental: bool
    entries: list[RebuildEntry] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    invalidation_summary: dict[str, Any] = field(default_factory=dict)

    def add_rebuild(
        self,
        page_path: Path,
        reason: str,
        trigger: str,
        duration_ms: float = 0.0,
    ) -> None:
        """
        Record that a page was rebuilt.

        Args:
            page_path: Path to the page source file
            reason: Reason for the rebuild (from PageInvalidationReason)
            trigger: What caused the rebuild (e.g., file path)
            duration_ms: Time taken to rebuild the page
        """
        self.entries.append(
            RebuildEntry(
                page_path=str(page_path),
                reason=reason,
                trigger=trigger,
                duration_ms=duration_ms,
            )
        )

    def add_cache_hit(
        self,
        page_path: Path,
        reason: str = "cache_hit",
        trigger: str = "",
        duration_ms: float = 0.0,
    ) -> None:
        """
        Record that a page was served from cache.

        Args:
            page_path: Path to the page source file
            reason: Reason (usually "cache_hit")
            trigger: What caused the cache hit (usually empty)
            duration_ms: Time taken (usually very low)
        """
        self.entries.append(
            RebuildEntry(
                page_path=str(page_path),
                reason=reason,
                trigger=trigger,
                duration_ms=duration_ms,
                from_cache=True,
            )
        )

    def add_skipped(self, page_path: Path) -> None:
        """
        Record that a page was skipped (cache hit).

        Args:
            page_path: Path to the page source file
        """
        self.skipped.append(str(page_path))

    def to_json(self, indent: int = 2) -> str:
        """
        Export manifest as JSON for debugging.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string representation of the manifest
        """
        return json.dumps(
            {
                "build_id": self.build_id,
                "incremental": self.incremental,
                "rebuilt": len([e for e in self.entries if not e.from_cache]),
                "cache_hits": len([e for e in self.entries if e.from_cache]),
                "skipped": len(self.skipped),
                "entries": [
                    {
                        "page": e.page_path,
                        "reason": e.reason,
                        "trigger": e.trigger,
                        "duration_ms": e.duration_ms,
                        "from_cache": e.from_cache,
                    }
                    for e in self.entries
                ],
                "invalidation_summary": self.invalidation_summary,
            },
            indent=indent,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Export manifest as dictionary.

        Returns:
            Dictionary representation of the manifest
        """
        return {
            "build_id": self.build_id,
            "incremental": self.incremental,
            "rebuilt": len([e for e in self.entries if not e.from_cache]),
            "cache_hits": len([e for e in self.entries if e.from_cache]),
            "skipped": len(self.skipped),
            "by_reason": self.summary()["by_reason"],
            "total_duration_ms": self.summary()["total_duration_ms"],
        }

    def summary(self) -> dict[str, Any]:
        """
        Get summary statistics.

        Returns:
            Dictionary with:
            - total_rebuilt: Number of pages rebuilt
            - total_skipped: Number of pages skipped
            - total_cache_hits: Number of cache hits
            - by_reason: Dict mapping reason to count
            - total_duration_ms: Total rebuild time
        """
        by_reason: dict[str, int] = {}
        for entry in self.entries:
            if not entry.from_cache:
                by_reason[entry.reason] = by_reason.get(entry.reason, 0) + 1

        return {
            "total_rebuilt": len([e for e in self.entries if not e.from_cache]),
            "total_skipped": len(self.skipped),
            "total_cache_hits": len([e for e in self.entries if e.from_cache]),
            "by_reason": by_reason,
            "total_duration_ms": sum(e.duration_ms for e in self.entries),
        }

    def merge(self, other: RebuildManifest) -> None:
        """
        Merge another manifest into this one.

        Useful for combining manifests from parallel builds.

        Args:
            other: Another RebuildManifest to merge
        """
        self.entries.extend(other.entries)
        self.skipped.extend(other.skipped)

        # Merge invalidation summaries
        for key, value in other.invalidation_summary.items():
            if key in self.invalidation_summary:
                if isinstance(value, list):
                    self.invalidation_summary[key].extend(value)
                elif isinstance(value, dict):
                    self.invalidation_summary[key].update(value)
            else:
                self.invalidation_summary[key] = value

    def __repr__(self) -> str:
        """Return string representation."""
        summary = self.summary()
        return (
            f"RebuildManifest(build_id={self.build_id!r}, "
            f"rebuilt={summary['total_rebuilt']}, "
            f"skipped={summary['total_skipped']})"
        )
