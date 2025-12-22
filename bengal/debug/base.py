"""
Base classes and registry for Bengal debug tools.

Provides the foundational infrastructure for all debug and diagnostic tools.
All debug tools inherit from DebugTool, produce DebugReport instances, and
can be discovered via DebugRegistry.

Architecture:
    The debug tool infrastructure follows a consistent pattern:

    1. Tools inherit from DebugTool and implement analyze()
    2. Analysis produces a DebugReport with DebugFinding instances
    3. Findings have severity levels (Severity enum)
    4. Reports can be formatted for CLI, JSON, or markdown
    5. Tools register via @DebugRegistry.register decorator

Key Components:
    - Severity: Enum for finding severity levels (INFO, WARNING, ERROR, CRITICAL)
    - DebugFinding: Single observation with severity, category, and suggestion
    - DebugReport: Aggregates findings, statistics, and recommendations
    - DebugTool: Abstract base class with analyze() contract
    - DebugRegistry: Tool discovery, registration, and factory

Example:
    Creating a custom debug tool:

    >>> @DebugRegistry.register
    ... class MyDebugTool(DebugTool):
    ...     name = "my-tool"
    ...     description = "Analyzes custom aspects"
    ...
    ...     def analyze(self) -> DebugReport:
    ...         report = self.create_report()
    ...         report.add_finding(
    ...             title="Issue found",
    ...             description="Something needs attention",
    ...             severity=Severity.WARNING,
    ...             suggestion="Fix by doing X",
    ...         )
    ...         return report

    Using a tool:

    >>> tool = DebugRegistry.create("my-tool", site=site)
    >>> report = tool.run()
    >>> print(report.format_summary())

Related Modules:
    - bengal.debug.incremental_debugger: Incremental build debugging
    - bengal.debug.delta_analyzer: Build comparison analysis
    - bengal.debug.dependency_visualizer: Dependency graph visualization
    - bengal.debug.config_inspector: Configuration comparison
    - bengal.debug.shortcode_sandbox: Directive testing sandbox

See Also:
    - bengal/cli/commands/debug.py: CLI integration for debug tools
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
    """
    Severity levels for debug findings.

    Used to categorize the importance and urgency of findings from debug
    tools. Severity determines visual indicators and helps prioritize
    which issues to address first.

    Levels:
        INFO: Informational observations, no action required
        WARNING: Potential issues that should be reviewed
        ERROR: Problems that need to be fixed
        CRITICAL: Severe issues requiring immediate attention

    Example:
        >>> finding = DebugFinding(
        ...     title="Missing template",
        ...     description="Template not found",
        ...     severity=Severity.ERROR,
        ... )
        >>> print(finding.severity.emoji)
        ❌
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def emoji(self) -> str:
        """
        Get emoji indicator for this severity level.

        Returns:
            Unicode emoji: ℹ️ (info), ⚠️ (warning), ❌ (error), 🔴 (critical)
        """
        return {
            Severity.INFO: "ℹ️",
            Severity.WARNING: "⚠️",
            Severity.ERROR: "❌",
            Severity.CRITICAL: "🔴",
        }[self]

    @property
    def color(self) -> str:
        """
        Get Rich library color token for this severity level.

        Used when formatting output with the Rich console library.

        Returns:
            Color name string compatible with Rich markup.
        """
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
        """
        Format finding as single line for quick scanning.

        Returns:
            Single-line string with emoji, title, and optional location.

        Example:
            >>> finding.format_short()
            '⚠️ Cache inconsistency (build_cache.json)'
        """
        loc = f" ({self.location})" if self.location else ""
        return f"{self.severity.emoji} {self.title}{loc}"

    def format_full(self) -> str:
        """
        Format finding with full details for detailed output.

        Includes severity emoji, title, location, description,
        and actionable suggestion if available.

        Returns:
            Multi-line formatted string.

        Example:
            >>> print(finding.format_full())
            ⚠️ Cache inconsistency
               Location: build_cache.json
               Cache entry references non-existent file
               💡 Run 'bengal clean --cache' to clear stale entries
        """
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
        """
        Group findings by severity level.

        Returns:
            Dictionary mapping each Severity to list of findings at that level.
            All severity levels are included as keys, even if empty.
        """
        result: dict[Severity, list[DebugFinding]] = {s: [] for s in Severity}
        for finding in self.findings:
            result[finding.severity].append(finding)
        return result

    @property
    def findings_by_category(self) -> dict[str, list[DebugFinding]]:
        """
        Group findings by category.

        Returns:
            Dictionary mapping category names to lists of findings.
            Only categories with findings are included.
        """
        result: dict[str, list[DebugFinding]] = {}
        for finding in self.findings:
            if finding.category not in result:
                result[finding.category] = []
            result[finding.category].append(finding)
        return result

    @property
    def has_issues(self) -> bool:
        """
        Check if report contains any actionable issues.

        Returns:
            True if any findings have WARNING, ERROR, or CRITICAL severity.
        """
        return any(
            f.severity in (Severity.WARNING, Severity.ERROR, Severity.CRITICAL)
            for f in self.findings
        )

    @property
    def error_count(self) -> int:
        """
        Count of error and critical findings.

        Returns:
            Number of findings with ERROR or CRITICAL severity.
        """
        return sum(1 for f in self.findings if f.severity in (Severity.ERROR, Severity.CRITICAL))

    @property
    def warning_count(self) -> int:
        """
        Count of warning findings.

        Returns:
            Number of findings with WARNING severity.
        """
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    def add_finding(
        self,
        title: str,
        description: str,
        severity: Severity = Severity.INFO,
        **kwargs: Any,
    ) -> DebugFinding:
        """
        Add a finding to the report.

        Convenience method for creating and appending a DebugFinding.

        Args:
            title: Short title describing the finding.
            description: Detailed explanation of what was found.
            severity: Severity level (defaults to INFO).
            **kwargs: Additional DebugFinding attributes (category, location,
                suggestion, metadata, line).

        Returns:
            The created DebugFinding instance.

        Example:
            >>> report.add_finding(
            ...     title="Orphaned cache entry",
            ...     description="Cache references deleted file",
            ...     severity=Severity.WARNING,
            ...     category="cache",
            ...     location="content/old-post.md",
            ...     suggestion="Run 'bengal clean --cache'",
            ... )
        """
        finding = DebugFinding(
            title=title,
            description=description,
            severity=severity,
            **kwargs,
        )
        self.findings.append(finding)
        return finding

    def to_dict(self) -> dict[str, Any]:
        """
        Convert report to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for json.dumps().
            Timestamps are converted to ISO format strings.
            Severity enums are converted to their string values.
        """
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
        """
        Format a brief summary for CLI output.

        Produces a compact multi-line summary showing tool name,
        summary text, finding counts by severity, and top recommendations.

        Returns:
            Formatted summary string suitable for terminal display.
        """
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
    Abstract base class for all Bengal debug tools.

    Provides common infrastructure for analysis tools including standardized
    report generation, access to site and cache data, and consistent output
    formatting. All debug tools follow a read-only introspection pattern
    with no side effects.

    Subclasses must:
        1. Set class attributes `name` and `description`
        2. Implement the analyze() method
        3. Optionally register with @DebugRegistry.register

    Attributes:
        name: Tool identifier used for CLI and registry lookup.
        description: Human-readable description for help text.
        site: Optional Site instance providing page access.
        cache: Optional BuildCache for cache inspection.
        root_path: Project root path for file operations.

    Thread Safety:
        Thread-safe for read-only operations. Do not mutate site or cache.

    Example:
        >>> @DebugRegistry.register
        ... class MyDebugTool(DebugTool):
        ...     name = "my-tool"
        ...     description = "Analyzes custom aspects"
        ...
        ...     def analyze(self) -> DebugReport:
        ...         report = self.create_report()
        ...         report.summary = "Analysis complete"
        ...         # ... analysis logic ...
        ...         return report
        ...
        >>> tool = MyDebugTool(site=site)
        >>> report = tool.run()
        >>> print(report.format_summary())
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
        Initialize debug tool with optional site and cache context.

        Args:
            site: Optional Site instance for accessing pages, sections,
                and configuration during analysis.
            cache: Optional BuildCache for inspecting cached content,
                dependencies, and file fingerprints.
            root_path: Root path of the project. Defaults to current
                working directory if not provided.
        """
        self.site = site
        self.cache = cache
        self.root_path = root_path or Path.cwd()

    def create_report(self) -> DebugReport:
        """
        Create a new DebugReport for this tool.

        Returns:
            Empty DebugReport with tool_name pre-populated.
        """
        return DebugReport(tool_name=self.name)

    @abstractmethod
    def analyze(self) -> DebugReport:
        """
        Perform analysis and return report.

        Subclasses must implement this method to perform their specific
        analysis. The method should:

        1. Create a report via self.create_report()
        2. Set report.summary with a brief description
        3. Add findings via report.add_finding()
        4. Populate report.statistics with relevant metrics
        5. Add report.recommendations for actionable items
        6. Return the completed report

        Returns:
            DebugReport containing all analysis results and findings.
        """
        ...

    def run(self) -> DebugReport:
        """
        Run analysis with execution timing.

        Wraps analyze() with timing measurement and populates
        the report's execution_time_ms field.

        Returns:
            DebugReport with execution_time_ms populated.

        Example:
            >>> tool = IncrementalBuildDebugger(site=site, cache=cache)
            >>> report = tool.run()
            >>> print(f"Analysis took {report.execution_time_ms:.1f}ms")
        """
        import time

        start = time.perf_counter()
        report = self.analyze()
        report.execution_time_ms = (time.perf_counter() - start) * 1000
        return report


class DebugRegistry:
    """
    Registry for debug tool discovery and instantiation.

    Provides a central point for tool registration, lookup, and creation.
    Tools register themselves using the @DebugRegistry.register decorator,
    making them discoverable by CLI commands and other tooling.

    Class Attributes:
        _tools: Internal dictionary mapping tool names to classes.

    Example:
        Register a tool:

        >>> @DebugRegistry.register
        ... class MyTool(DebugTool):
        ...     name = "my-tool"
        ...     description = "Does something useful"
        ...
        ...     def analyze(self) -> DebugReport:
        ...         return self.create_report()

        List available tools:

        >>> for name, description in DebugRegistry.list_tools():
        ...     print(f"{name}: {description}")
        my-tool: Does something useful
        incremental: Debug incremental build issues

        Create and run a tool:

        >>> tool = DebugRegistry.create("my-tool", site=site)
        >>> report = tool.run()
    """

    _tools: dict[str, type[DebugTool]] = {}

    @classmethod
    def register(cls, tool_class: type[DebugTool]) -> type[DebugTool]:
        """
        Register a debug tool class with the registry.

        Designed to be used as a class decorator. The tool is registered
        under its `name` class attribute.

        Args:
            tool_class: The DebugTool subclass to register.

        Returns:
            The tool class unchanged (for decorator usage).

        Example:
            >>> @DebugRegistry.register
            ... class CacheDebugger(DebugTool):
            ...     name = "cache"
            ...     description = "Debug cache issues"
            ...
            ...     def analyze(self) -> DebugReport:
            ...         return self.create_report()
        """
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get(cls, name: str) -> type[DebugTool] | None:
        """
        Get a tool class by name.

        Args:
            name: The tool name to look up.

        Returns:
            The tool class if found, None otherwise.
        """
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> list[tuple[str, str]]:
        """
        List all registered tools with descriptions.

        Returns:
            List of (name, description) tuples for all registered tools.
        """
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

        Factory method that looks up a tool by name and instantiates it
        with the provided arguments.

        Args:
            name: Tool name to look up in the registry.
            site: Optional Site instance to pass to the tool.
            cache: Optional BuildCache instance to pass to the tool.
            **kwargs: Additional keyword arguments passed to the tool
                constructor (e.g., root_path, rebuild_log).

        Returns:
            Instantiated tool if found, None if the tool name is not
            registered.

        Example:
            >>> tool = DebugRegistry.create(
            ...     "incremental",
            ...     site=site,
            ...     cache=cache,
            ...     rebuild_log=["content/post.md"],
            ... )
            >>> if tool:
            ...     report = tool.run()
        """
        tool_class = cls.get(name)
        if tool_class:
            return tool_class(site=site, cache=cache, **kwargs)
        return None
