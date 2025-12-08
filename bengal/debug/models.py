"""
Data models for page explanation.

Defines dataclasses for representing different aspects of page building:
source info, template chains, dependencies, shortcodes, cache status, etc.

All models are designed to be JSON-serializable for potential export
and are display-friendly with human-readable formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SourceInfo:
    """Information about the source file."""

    path: Path
    size_bytes: int
    line_count: int
    modified: datetime | None
    encoding: str = "UTF-8"

    @property
    def size_human(self) -> str:
        """Human-readable file size."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        else:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"


@dataclass
class TemplateInfo:
    """Information about a template in the chain."""

    name: str
    source_path: Path | None
    theme: str | None
    extends: str | None = None
    includes: list[str] = field(default_factory=list)


@dataclass
class DependencyInfo:
    """Dependencies for a page."""

    content: list[str] = field(default_factory=list)  # Other content files
    templates: list[str] = field(default_factory=list)  # Template files
    data: list[str] = field(default_factory=list)  # Data files
    assets: list[str] = field(default_factory=list)  # Referenced assets
    includes: list[str] = field(default_factory=list)  # Included files


@dataclass
class ShortcodeUsage:
    """Information about shortcode usage in a page."""

    name: str
    count: int
    lines: list[int] = field(default_factory=list)
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheInfo:
    """Cache status for a page."""

    status: str  # HIT, MISS, STALE
    reason: str | None  # Why stale or miss
    cache_key: str | None
    last_hit: datetime | None = None
    content_cached: bool = False
    rendered_cached: bool = False

    @property
    def status_emoji(self) -> str:
        """Emoji for cache status."""
        if self.status == "HIT":
            return "✅"
        elif self.status == "STALE":
            return "⚠️"
        else:
            return "❌"


@dataclass
class OutputInfo:
    """Output information for a page."""

    path: Path | None
    url: str
    size_bytes: int | None = None

    @property
    def size_human(self) -> str | None:
        """Human-readable output size."""
        if self.size_bytes is None:
            return None
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        else:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"


@dataclass
class Issue:
    """A detected issue with a page."""

    severity: str  # error, warning, info
    issue_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    suggestion: str | None = None
    line: int | None = None

    @property
    def severity_emoji(self) -> str:
        """Emoji for severity level."""
        if self.severity == "error":
            return "❌"
        elif self.severity == "warning":
            return "⚠️"
        else:
            return "ℹ️"


@dataclass
class PerformanceInfo:
    """Performance timing information."""

    total_ms: float
    parse_ms: float | None = None
    shortcode_ms: float | None = None
    render_ms: float | None = None
    breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class PageExplanation:
    """
    Complete explanation of how a page is built.

    Aggregates all aspects of page building: source file info, frontmatter,
    template chain, dependencies, shortcodes, cache status, and output.
    """

    # Source information
    source: SourceInfo

    # Parsed frontmatter
    frontmatter: dict[str, Any]

    # Template resolution
    template_chain: list[TemplateInfo]

    # Dependencies
    dependencies: DependencyInfo

    # Shortcodes used
    shortcodes: list[ShortcodeUsage]

    # Cache status
    cache: CacheInfo

    # Output
    output: OutputInfo

    # Optional: Performance (if measured)
    performance: PerformanceInfo | None = None

    # Optional: Issues (if diagnosed)
    issues: list[Issue] | None = None

