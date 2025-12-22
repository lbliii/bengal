"""
Incremental build debugger for diagnosing rebuild issues.

Provides diagnostic tools for understanding why pages rebuild during
incremental builds, identifying phantom rebuilds (pages that rebuild
without apparent cause), validating cache consistency, and simulating
the impact of changes before making them.

Key Features:
    - explain_rebuild(): Detailed analysis of why a page was rebuilt
    - find_phantom_rebuilds(): Detect pages rebuilding without tracked changes
    - validate_cache_consistency(): Check cache integrity and find orphans
    - simulate_change(): Preview what would rebuild if a file changed
    - analyze(): Comprehensive incremental build health report

Architecture:
    Registered as "incremental" in DebugRegistry. Works with BuildCache
    to inspect file fingerprints, dependencies, and cache entries.
    Optionally accepts a rebuild_log from the last build to detect
    phantom rebuilds.

Example:
    >>> from bengal.debug import IncrementalBuildDebugger
    >>> debugger = IncrementalBuildDebugger(site=site, cache=cache)
    >>> explanation = debugger.explain_rebuild("content/posts/my-post.md")
    >>> print(explanation.format_detailed())

    >>> # Check what would rebuild if a template changed
    >>> affected = debugger.simulate_change("templates/post.html")
    >>> print(f"{len(affected)} pages would rebuild")

Related Modules:
    - bengal.cache.build_cache: Cache storage and fingerprinting
    - bengal.cache.dependency_tracker: Dependency graph construction
    - bengal.orchestration.incremental: Incremental build coordination
    - bengal.debug.base: Debug tool infrastructure

See Also:
    - bengal/cli/commands/debug.py: CLI integration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.debug.base import DebugFinding, DebugRegistry, DebugReport, DebugTool, Severity

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.core.site import Site


class RebuildReason(Enum):
    """
    Reasons why a page might be rebuilt during incremental builds.

    Used to categorize and explain what triggered a page rebuild.
    A page may have multiple reasons (e.g., both content and template changed).

    Values:
        CONTENT_CHANGED: The page's source content file was modified.
        TEMPLATE_CHANGED: A template in the page's template chain changed.
        PARTIAL_CHANGED: An included partial/component was modified.
        CONFIG_CHANGED: Site or build configuration changed.
        DATA_CHANGED: A data file referenced by the page changed.
        DEPENDENCY_CHANGED: Some other tracked dependency changed.
        NEW_FILE: The page is new and not yet in the cache.
        CACHE_MISS: Page exists but is not in the build cache.
        CACHE_INVALID: Cache entry exists but is corrupted/invalid.
        FORCED: Rebuild was explicitly requested (--force flag).
        UNKNOWN: No tracked dependency changed (phantom rebuild).

    Example:
        >>> reason = RebuildReason.TEMPLATE_CHANGED
        >>> print(reason.description)
        Template file was modified
    """

    CONTENT_CHANGED = "content_changed"
    TEMPLATE_CHANGED = "template_changed"
    PARTIAL_CHANGED = "partial_changed"
    CONFIG_CHANGED = "config_changed"
    DATA_CHANGED = "data_changed"
    DEPENDENCY_CHANGED = "dependency_changed"
    NEW_FILE = "new_file"
    CACHE_MISS = "cache_miss"
    CACHE_INVALID = "cache_invalid"
    FORCED = "forced"
    UNKNOWN = "unknown"

    @property
    def description(self) -> str:
        """
        Get human-readable description of this rebuild reason.

        Returns:
            Descriptive string suitable for user display.
        """
        return {
            RebuildReason.CONTENT_CHANGED: "Content file was modified",
            RebuildReason.TEMPLATE_CHANGED: "Template file was modified",
            RebuildReason.PARTIAL_CHANGED: "Included partial was modified",
            RebuildReason.CONFIG_CHANGED: "Configuration changed",
            RebuildReason.DATA_CHANGED: "Data file was modified",
            RebuildReason.DEPENDENCY_CHANGED: "A dependency was modified",
            RebuildReason.NEW_FILE: "File is new (not in cache)",
            RebuildReason.CACHE_MISS: "Page not found in cache",
            RebuildReason.CACHE_INVALID: "Cache entry is invalid or corrupted",
            RebuildReason.FORCED: "Rebuild was explicitly forced",
            RebuildReason.UNKNOWN: "Unknown reason (investigate)",
        }[self]


@dataclass
class RebuildExplanation:
    """
    Detailed explanation of why a page was rebuilt.

    Provides comprehensive information about what triggered a rebuild,
    including the chain of dependencies that led to the rebuild.

    Attributes:
        page_path: Path to the page that was rebuilt
        reasons: List of reasons why the page was rebuilt
        changed_dependencies: Files that changed and caused the rebuild
        cache_status: Status of the page in the cache
        timestamps: Relevant timestamps (content mtime, cache time, etc.)
        dependency_chain: Chain of dependencies that triggered rebuild
        suggestions: Suggestions for optimization if applicable
    """

    page_path: str
    reasons: list[RebuildReason] = field(default_factory=list)
    changed_dependencies: list[str] = field(default_factory=list)
    cache_status: str = "unknown"
    timestamps: dict[str, str] = field(default_factory=dict)
    dependency_chain: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def primary_reason(self) -> RebuildReason:
        """Get the primary (first) reason for rebuild."""
        return self.reasons[0] if self.reasons else RebuildReason.UNKNOWN

    def format_summary(self) -> str:
        """
        Format as brief one-line summary.

        Returns:
            String like "path/to/page.md: Content file was modified"
        """
        reason = self.primary_reason
        return f"{self.page_path}: {reason.description}"

    def format_detailed(self) -> str:
        """
        Format with full details for verbose output.

        Includes cache status, all reasons, changed dependencies,
        dependency chain, and suggestions.

        Returns:
            Multi-line formatted string.
        """
        lines = [f"📄 {self.page_path}"]
        lines.append(f"   Cache Status: {self.cache_status}")
        lines.append("")
        lines.append("   Reasons:")
        for reason in self.reasons:
            lines.append(f"      • {reason.description}")

        if self.changed_dependencies:
            lines.append("")
            lines.append("   Changed Dependencies:")
            for dep in self.changed_dependencies[:5]:
                lines.append(f"      • {dep}")
            if len(self.changed_dependencies) > 5:
                lines.append(f"      ... and {len(self.changed_dependencies) - 5} more")

        if self.dependency_chain:
            lines.append("")
            lines.append("   Dependency Chain:")
            for i, dep in enumerate(self.dependency_chain):
                prefix = "      └─" if i == len(self.dependency_chain) - 1 else "      ├─"
                lines.append(f"{prefix} {dep}")

        if self.suggestions:
            lines.append("")
            lines.append("   💡 Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"      • {suggestion}")

        return "\n".join(lines)


@dataclass
class PhantomRebuild:
    """
    A page that rebuilds without apparent cause.

    Phantom rebuilds are pages that rebuild even though none of their
    known dependencies changed. These indicate missing dependency tracking,
    cache issues, or untracked global state affecting the build.

    Attributes:
        page_path: Path to the page experiencing phantom rebuilds.
        rebuild_count: Number of times this page has phantom rebuilt.
        last_rebuild: Timestamp of the most recent phantom rebuild.
        suspected_causes: Possible causes identified by analysis.
        investigation_notes: Additional notes from investigation.

    Example:
        >>> phantom = PhantomRebuild(
        ...     page_path="content/posts/my-post.md",
        ...     suspected_causes=["Missing template dependency tracking"],
        ... )
    """

    page_path: str
    rebuild_count: int = 1
    last_rebuild: datetime | None = None
    suspected_causes: list[str] = field(default_factory=list)
    investigation_notes: list[str] = field(default_factory=list)


@dataclass
class CacheConsistencyReport:
    """
    Report on cache consistency and integrity.

    Aggregates the results of cache validation, identifying orphaned
    entries, missing entries, and overall cache health.

    Attributes:
        total_entries: Total number of entries in the cache.
        valid_entries: Entries that pass validation (file exists, valid format).
        invalid_entries: Entries that fail validation.
        orphaned_entries: Cache entries for files that no longer exist on disk.
        missing_entries: Content files that exist but aren't in the cache.
        issues: Specific issues found during validation.

    Example:
        >>> report = CacheConsistencyReport(
        ...     total_entries=100,
        ...     valid_entries=95,
        ...     invalid_entries=5,
        ...     orphaned_entries=["content/deleted-post.md"],
        ... )
        >>> print(f"Cache health: {report.health_score:.1f}%")
        Cache health: 95.0%
    """

    total_entries: int = 0
    valid_entries: int = 0
    invalid_entries: int = 0
    orphaned_entries: list[str] = field(default_factory=list)
    missing_entries: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def health_score(self) -> float:
        """
        Calculate cache health as percentage.

        Returns:
            Percentage of valid entries (0-100). Returns 100.0 if cache is empty.
        """
        if self.total_entries == 0:
            return 100.0
        return (self.valid_entries / self.total_entries) * 100


@DebugRegistry.register
class IncrementalBuildDebugger(DebugTool):
    """
    Debug tool for incremental build issues.

    Helps diagnose why pages rebuild, find phantom rebuilds, and
    validate cache consistency.

    Creation:
        Direct instantiation or via DebugRegistry:
            debugger = IncrementalBuildDebugger(site=site, cache=cache)
            debugger = DebugRegistry.create("incremental", site=site, cache=cache)

    Example:
        >>> debugger = IncrementalBuildDebugger(site=site, cache=cache)
        >>> explanation = debugger.explain_rebuild("content/posts/my-post.md")
        >>> print(explanation.format_detailed())
    """

    name = "incremental"
    description = "Debug incremental build issues"

    def __init__(
        self,
        site: Site | None = None,
        cache: BuildCache | None = None,
        root_path: Path | None = None,
        rebuild_log: list[str] | None = None,
    ):
        """
        Initialize incremental build debugger.

        Args:
            site: Site instance for page access
            cache: BuildCache for cache inspection
            root_path: Root path of the project
            rebuild_log: Optional list of paths that were rebuilt (from last build)
        """
        super().__init__(site=site, cache=cache, root_path=root_path)
        self.rebuild_log = rebuild_log or []

    def analyze(self) -> DebugReport:
        """
        Perform comprehensive incremental build analysis.

        Analyzes cache consistency, identifies phantom rebuilds, and
        provides optimization recommendations.

        Returns:
            DebugReport with findings and recommendations
        """
        report = self.create_report()
        report.summary = "Incremental build analysis"

        # Check cache consistency
        consistency = self.validate_cache_consistency()
        report.statistics["cache_health"] = f"{consistency.health_score:.1f}%"
        report.statistics["cache_entries"] = consistency.total_entries
        report.statistics["valid_entries"] = consistency.valid_entries

        if consistency.orphaned_entries:
            report.add_finding(
                title=f"{len(consistency.orphaned_entries)} orphaned cache entries",
                description="Cache contains entries for files that no longer exist",
                severity=Severity.WARNING,
                category="cache",
                metadata={"orphaned": consistency.orphaned_entries[:10]},
                suggestion="Run 'bengal clean --cache' to clear orphaned entries",
            )

        if consistency.missing_entries:
            report.add_finding(
                title=f"{len(consistency.missing_entries)} files missing from cache",
                description="Content files exist but are not in cache",
                severity=Severity.INFO,
                category="cache",
                metadata={"missing": consistency.missing_entries[:10]},
                suggestion="These files will be processed on next build",
            )

        for issue in consistency.issues:
            report.add_finding(
                title="Cache issue detected",
                description=issue,
                severity=Severity.WARNING,
                category="cache",
            )

        # Find phantom rebuilds if we have rebuild log
        if self.rebuild_log:
            phantoms = self.find_phantom_rebuilds()
            if phantoms:
                report.add_finding(
                    title=f"{len(phantoms)} phantom rebuild(s) detected",
                    description="Pages rebuilt without apparent dependency changes",
                    severity=Severity.WARNING,
                    category="phantom",
                    metadata={"pages": [p.page_path for p in phantoms]},
                    suggestion="Check for missing dependency tracking or cache issues",
                )
            report.statistics["phantom_rebuilds"] = len(phantoms)

        # Analyze dependency health
        dep_health = self._analyze_dependency_health()
        for finding in dep_health:
            report.findings.append(finding)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def explain_rebuild(self, page_path: str) -> RebuildExplanation:
        """
        Explain why a specific page was rebuilt.

        Analyzes the page's dependencies, cache status, and file timestamps
        to determine why it was rebuilt (or would be rebuilt).

        Args:
            page_path: Path to the page (relative to content dir or absolute)

        Returns:
            RebuildExplanation with detailed analysis
        """
        explanation = RebuildExplanation(page_path=page_path)

        if not self.cache:
            explanation.reasons.append(RebuildReason.CACHE_MISS)
            explanation.cache_status = "no_cache"
            explanation.suggestions.append("Build cache not available - all pages rebuild")
            return explanation

        # Normalize path
        path_str = str(page_path)

        # Check if file is in cache
        if path_str not in self.cache.file_fingerprints:
            explanation.reasons.append(RebuildReason.NEW_FILE)
            explanation.cache_status = "not_in_cache"
            return explanation

        explanation.cache_status = "in_cache"

        # Check if content changed
        path = Path(page_path)
        if path.exists() and self.cache.is_changed(path):
            explanation.reasons.append(RebuildReason.CONTENT_CHANGED)
            # Get timestamps
            stat = path.stat()
            explanation.timestamps["file_mtime"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

        # Check dependencies
        deps = self.cache.dependencies.get(path_str, set())
        changed_deps = []

        for dep in deps:
            dep_path = Path(dep)
            if dep_path.exists() and self.cache.is_changed(dep_path):
                changed_deps.append(dep)

                # Categorize the dependency
                if "template" in dep.lower() or dep.endswith((".html", ".jinja2")):
                    if RebuildReason.TEMPLATE_CHANGED not in explanation.reasons:
                        explanation.reasons.append(RebuildReason.TEMPLATE_CHANGED)
                elif "partial" in dep.lower() or "include" in dep.lower():
                    if RebuildReason.PARTIAL_CHANGED not in explanation.reasons:
                        explanation.reasons.append(RebuildReason.PARTIAL_CHANGED)
                elif dep.endswith((".yaml", ".yml", ".toml", ".json")):
                    if "config" in dep.lower():
                        if RebuildReason.CONFIG_CHANGED not in explanation.reasons:
                            explanation.reasons.append(RebuildReason.CONFIG_CHANGED)
                    else:
                        if RebuildReason.DATA_CHANGED not in explanation.reasons:
                            explanation.reasons.append(RebuildReason.DATA_CHANGED)
                else:
                    if RebuildReason.DEPENDENCY_CHANGED not in explanation.reasons:
                        explanation.reasons.append(RebuildReason.DEPENDENCY_CHANGED)

        explanation.changed_dependencies = changed_deps

        # Build dependency chain for changed deps
        if changed_deps:
            explanation.dependency_chain = self._build_dependency_chain(page_path, changed_deps[0])

        # If no reasons found, it's unknown
        if not explanation.reasons:
            explanation.reasons.append(RebuildReason.UNKNOWN)
            explanation.suggestions.append(
                "No obvious reason found - check for missing dependency tracking"
            )

        return explanation

    def find_phantom_rebuilds(self) -> list[PhantomRebuild]:
        """
        Find pages that rebuilt without apparent dependency changes.

        Phantom rebuilds indicate missing dependency tracking or cache issues.

        Returns:
            List of PhantomRebuild instances
        """
        phantoms: list[PhantomRebuild] = []

        if not self.cache or not self.rebuild_log:
            return phantoms

        for page_path in self.rebuild_log:
            explanation = self.explain_rebuild(page_path)

            # If the only reason is UNKNOWN, it's a phantom rebuild
            if len(explanation.reasons) == 1 and explanation.reasons[0] == RebuildReason.UNKNOWN:
                phantom = PhantomRebuild(
                    page_path=page_path,
                    suspected_causes=["Missing dependency tracking"],
                )
                phantoms.append(phantom)

        return phantoms

    def validate_cache_consistency(self) -> CacheConsistencyReport:
        """
        Validate cache integrity and consistency.

        Checks for:
        - Orphaned entries (files no longer exist)
        - Missing entries (files should be cached but aren't)
        - Invalid entries (corrupted or malformed)

        Returns:
            CacheConsistencyReport with validation results
        """
        report = CacheConsistencyReport()

        if not self.cache:
            return report

        # Check file fingerprints
        all_cached = set(self.cache.file_fingerprints.keys())
        report.total_entries = len(all_cached)

        for path_str in all_cached:
            path = Path(path_str)

            # Check if file exists
            if not path.exists():
                # Try relative to root
                abs_path = self.root_path / path
                if not abs_path.exists():
                    report.orphaned_entries.append(path_str)
                    continue

            report.valid_entries += 1

        report.invalid_entries = len(report.orphaned_entries)

        # Check for content files not in cache
        if self.site:
            for page in self.site.pages:
                page_path = str(page.source_path)
                if page_path not in all_cached:
                    report.missing_entries.append(page_path)

        return report

    def simulate_change(self, file_path: str) -> list[str]:
        """
        Simulate what would rebuild if a file changed.

        Useful for understanding the blast radius of a change before making it.

        Args:
            file_path: Path to the file that would change

        Returns:
            List of page paths that would need to rebuild
        """
        would_rebuild: list[str] = []

        if not self.cache:
            return would_rebuild

        # If it's a content file, it would rebuild itself
        if file_path.endswith((".md", ".markdown", ".rst")):
            would_rebuild.append(file_path)

        # Find all pages that depend on this file
        for page_path, deps in self.cache.dependencies.items():
            if file_path in deps or str(file_path) in deps:
                would_rebuild.append(page_path)

        # Check taxonomy dependencies
        for _term, pages in self.cache.taxonomy_deps.items():
            for page in pages:
                if page not in would_rebuild:
                    # Check if this page's tags include pages affected
                    would_rebuild.append(page)

        return list(set(would_rebuild))

    def _build_dependency_chain(
        self, target: str, changed: str, visited: set[str] | None = None
    ) -> list[str]:
        """
        Build the chain of dependencies from changed file to target.

        Traces how a change in one file propagates to trigger a rebuild
        of the target page through intermediate dependencies.

        Args:
            target: Path of the page being rebuilt.
            changed: Path of the file that changed.
            visited: Set of already-visited paths (for recursion).

        Returns:
            List of paths showing the dependency chain.
        """
        if visited is None:
            visited = set()

        chain = [changed]

        if not self.cache:
            return chain

        # Find intermediate dependencies
        deps = self.cache.dependencies.get(target, set())
        for dep in deps:
            if dep != changed and dep not in visited:
                visited.add(dep)
                # Check if this dep depends on the changed file
                sub_deps = self.cache.dependencies.get(dep, set())
                if changed in sub_deps:
                    chain.extend(self._build_dependency_chain(dep, changed, visited))
                    break

        chain.append(target)
        return chain

    def _analyze_dependency_health(self) -> list[DebugFinding]:
        """
        Analyze the health of dependency tracking.

        Checks for suspicious patterns that may indicate problems:
        - Pages with no tracked dependencies (may be missing tracking)
        - Pages with very high dependency counts (performance risk)

        Returns:
            List of DebugFinding instances for any issues found.
        """
        findings: list[DebugFinding] = []

        if not self.cache:
            return findings

        # Check for pages with no dependencies (suspicious)
        pages_without_deps = []
        for path in self.cache.file_fingerprints:
            if path.endswith((".md", ".markdown")) and (
                path not in self.cache.dependencies or not self.cache.dependencies[path]
            ):
                pages_without_deps.append(path)

        if pages_without_deps:
            findings.append(
                DebugFinding(
                    title=f"{len(pages_without_deps)} pages have no tracked dependencies",
                    description="These pages don't track template dependencies",
                    severity=Severity.INFO,
                    category="dependency",
                    metadata={"pages": pages_without_deps[:10]},
                    suggestion="This is normal for simple pages, but may indicate missing tracking",
                )
            )

        # Check for very high dependency counts (potential performance issue)
        high_dep_pages = []
        for path, deps in self.cache.dependencies.items():
            if len(deps) > 50:
                high_dep_pages.append((path, len(deps)))

        if high_dep_pages:
            findings.append(
                DebugFinding(
                    title=f"{len(high_dep_pages)} pages have many dependencies (>50)",
                    description="Pages with many dependencies are more likely to rebuild",
                    severity=Severity.INFO,
                    category="dependency",
                    metadata={"pages": high_dep_pages[:5]},
                    suggestion="Consider restructuring templates to reduce dependencies",
                )
            )

        return findings

    def _generate_recommendations(self, report: DebugReport) -> list[str]:
        """
        Generate actionable recommendations based on analysis.

        Examines cache health, phantom rebuild count, and findings
        to suggest concrete actions.

        Args:
            report: Completed DebugReport with findings and statistics.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        # Based on cache health
        health = float(report.statistics.get("cache_health", "100").rstrip("%"))
        if health < 90:
            recommendations.append(
                "Cache health is below 90% - consider running 'bengal clean --cache'"
            )

        # Based on phantom rebuilds
        phantom_count = report.statistics.get("phantom_rebuilds", 0)
        if phantom_count > 0:
            recommendations.append(
                f"Found {phantom_count} phantom rebuild(s) - check dependency tracking"
            )

        # Based on findings
        for finding in report.findings:
            if finding.category == "dependency" and finding.severity == Severity.WARNING:
                recommendations.append("Review dependency tracking configuration")
                break

        if not recommendations:
            recommendations.append("Incremental build configuration looks healthy! ✅")

        return recommendations
