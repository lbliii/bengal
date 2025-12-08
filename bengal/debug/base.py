"""
Base classes and registry for Bengal debug tools.

Provides common infrastructure for all debug/diagnostic tools including
output formatting, data collection patterns, and tool registration.

Key Components:
    - DebugTool: Base class for all debug tools
    - DebugReport: Structured output from debug tools
    - DebugRegistry: Tool discovery and registration

Related Modules:
    - bengal.debug.incremental_debugger: Incremental build debugging
    - bengal.debug.delta_analyzer: Build comparison
    - bengal.debug.dependency_visualizer: Dependency graph visualization

See Also:
    - bengal/cli/commands/debug.py: CLI integration
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.core.site import Site


class Severity(Enum):
    """Severity levels for debug findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def emoji(self) -> str:
        """Get emoji for severity level."""
        return {
            Severity.INFO: "ℹ️",
            Severity.WARNING: "⚠️",
            Severity.ERROR: "❌",
            Severity.CRITICAL: "🔴",
        }[self]

    @property
    def color(self) -> str:
        """Get Rich color token for severity."""
        return {
            Severity.INFO: "info",
            Severity.WARNING: "warning",
            Severity.ERROR: "error",
            Severity.CRITICAL: "error",
        }[self]


@dataclass
class DebugFinding:
    """
    A single finding from a debug tool.

    Represents an observation, issue, or insight discovered during analysis.
    Findings can range from informational to critical and include actionable
    suggestions where applicable.

    Attributes:
        title: Short title describing the finding
        description: Detailed explanation of what was found
        severity: Severity level (info, warning, error, critical)
        category: Category for grouping (e.g., "cache", "dependency", "performance")
        location: Optional file path or identifier related to finding
        suggestion: Optional actionable suggestion for resolution
        metadata: Additional context-specific data
        line: Optional line number for file-based findings
    """

    title: str
    description: str
    severity: Severity = Severity.INFO
    category: str = "general"
    location: str | None = None
    suggestion: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    line: int | None = None

    def format_short(self) -> str:
        """Format as single line."""
        loc = f" ({self.location})" if self.location else ""
        return f"{self.severity.emoji} {self.title}{loc}"

    def format_full(self) -> str:
        """Format with full details."""
        lines = [f"{self.severity.emoji} {self.title}"]
        if self.location:
            lines.append(f"   Location: {self.location}")
        lines.append(f"   {self.description}")
        if self.suggestion:
            lines.append(f"   💡 {self.suggestion}")
        return "\n".join(lines)


@dataclass
class DebugReport:
    """
    Structured output from a debug tool.

    Aggregates findings, statistics, and recommendations from a debug analysis.
    Provides multiple output formats for CLI, JSON, and markdown export.

    Attributes:
        tool_name: Name of the tool that generated this report
        timestamp: When the report was generated
        findings: List of findings discovered during analysis
        summary: Brief summary of analysis results
        statistics: Numeric statistics from analysis
        recommendations: High-level recommendations based on findings
        execution_time_ms: How long the analysis took
        metadata: Additional tool-specific data
    """

    tool_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    findings: list[DebugFinding] = field(default_factory=list)
    summary: str = ""
    statistics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    execution_time_ms: float = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def findings_by_severity(self) -> dict[Severity, list[DebugFinding]]:
        """Group findings by severity level."""
        result: dict[Severity, list[DebugFinding]] = {s: [] for s in Severity}
        for finding in self.findings:
            result[finding.severity].append(finding)
        return result

    @property
    def findings_by_category(self) -> dict[str, list[DebugFinding]]:
        """Group findings by category."""
        result: dict[str, list[DebugFinding]] = {}
        for finding in self.findings:
            if finding.category not in result:
                result[finding.category] = []
            result[finding.category].append(finding)
        return result

    @property
    def has_issues(self) -> bool:
        """Check if report contains warnings or errors."""
        return any(
            f.severity in (Severity.WARNING, Severity.ERROR, Severity.CRITICAL)
            for f in self.findings
        )

    @property
    def error_count(self) -> int:
        """Count of error and critical findings."""
        return sum(
            1
            for f in self.findings
            if f.severity in (Severity.ERROR, Severity.CRITICAL)
        )

    @property
    def warning_count(self) -> int:
        """Count of warning findings."""
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    def add_finding(
        self,
        title: str,
        description: str,
        severity: Severity = Severity.INFO,
        **kwargs: Any,
    ) -> DebugFinding:
        """Add a finding to the report."""
        finding = DebugFinding(
            title=title,
            description=description,
            severity=severity,
            **kwargs,
        )
        self.findings.append(finding)
        return finding

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "tool_name": self.tool_name,
            "timestamp": self.timestamp.isoformat(),
            "summary": self.summary,
            "findings": [
                {
                    "title": f.title,
                    "description": f.description,
                    "severity": f.severity.value,
                    "category": f.category,
                    "location": f.location,
                    "suggestion": f.suggestion,
                    "metadata": f.metadata,
                    "line": f.line,
                }
                for f in self.findings
            ],
            "statistics": self.statistics,
            "recommendations": self.recommendations,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }

    def format_summary(self) -> str:
        """Format a brief summary for CLI output."""
        lines = [f"📊 {self.tool_name} Report"]
        lines.append(f"   {self.summary}")
        lines.append("")

        by_severity = self.findings_by_severity
        counts = []
        for severity in [Severity.CRITICAL, Severity.ERROR, Severity.WARNING, Severity.INFO]:
            count = len(by_severity[severity])
            if count > 0:
                counts.append(f"{count} {severity.value}")

        if counts:
            lines.append(f"   Findings: {', '.join(counts)}")

        if self.recommendations:
            lines.append("")
            lines.append("   💡 Top Recommendations:")
            for rec in self.recommendations[:3]:
                lines.append(f"      • {rec}")

        return "\n".join(lines)


class DebugTool(ABC):
    """
    Base class for all Bengal debug tools.

    Provides common infrastructure for analysis tools including:
    - Standardized report generation
    - Access to site and cache data
    - Consistent output formatting

    Subclasses implement analyze() to perform their specific analysis.

    Creation:
        Subclass and implement analyze() method.

    Example:
        >>> class MyDebugTool(DebugTool):
        ...     name = "my-tool"
        ...     description = "Analyzes something"
        ...
        ...     def analyze(self) -> DebugReport:
        ...         report = self.create_report()
        ...         # ... analysis logic ...
        ...         return report
    """

    name: str = "base-tool"
    description: str = "Base debug tool"

    def __init__(
        self,
        site: Site | None = None,
        cache: BuildCache | None = None,
        root_path: Path | None = None,
    ):
        """
        Initialize debug tool.

        Args:
            site: Optional Site instance for analysis
            cache: Optional BuildCache for cache inspection
            root_path: Root path of the project (defaults to cwd)
        """
        self.site = site
        self.cache = cache
        self.root_path = root_path or Path.cwd()

    def create_report(self) -> DebugReport:
        """Create a new report for this tool."""
        return DebugReport(tool_name=self.name)

    @abstractmethod
    def analyze(self) -> DebugReport:
        """
        Perform analysis and return report.

        Subclasses must implement this method to perform their specific
        analysis and return a DebugReport with findings.

        Returns:
            DebugReport containing analysis results
        """
        ...

    def run(self) -> DebugReport:
        """
        Run analysis with timing.

        Wraps analyze() with timing measurement.

        Returns:
            DebugReport with execution time populated
        """
        import time

        start = time.perf_counter()
        report = self.analyze()
        report.execution_time_ms = (time.perf_counter() - start) * 1000
        return report


class DebugRegistry:
    """
    Registry for debug tools.

    Enables tool discovery and provides CLI integration point.

    Usage:
        >>> registry = DebugRegistry()
        >>> registry.register(IncrementalBuildDebugger)
        >>> tool = registry.get("incremental")
    """

    _tools: dict[str, type[DebugTool]] = {}

    @classmethod
    def register(cls, tool_class: type[DebugTool]) -> type[DebugTool]:
        """
        Register a debug tool class.

        Can be used as a decorator:

            @DebugRegistry.register
            class MyTool(DebugTool):
                name = "my-tool"
                ...

        Args:
            tool_class: The tool class to register

        Returns:
            The tool class (for decorator usage)
        """
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get(cls, name: str) -> type[DebugTool] | None:
        """Get a tool class by name."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> list[tuple[str, str]]:
        """List all registered tools with descriptions."""
        return [(name, tool.description) for name, tool in cls._tools.items()]

    @classmethod
    def create(
        cls,
        name: str,
        site: Site | None = None,
        cache: BuildCache | None = None,
        **kwargs: Any,
    ) -> DebugTool | None:
        """
        Create a tool instance by name.

        Args:
            name: Tool name
            site: Optional Site instance
            cache: Optional BuildCache instance
            **kwargs: Additional arguments passed to tool

        Returns:
            Tool instance or None if not found
        """
        tool_class = cls.get(name)
        if tool_class:
            return tool_class(site=site, cache=cache, **kwargs)
        return None

