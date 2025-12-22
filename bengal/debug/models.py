"""
Data models for page explanation.

Defines dataclasses for representing the different aspects of how a page
is built: source file information, template inheritance chains, dependencies,
shortcode usage, cache status, output details, and performance metrics.

All models are:
    - Immutable data containers (dataclasses)
    - JSON-serializable for export and API usage
    - Display-friendly with human-readable formatting properties
    - Type-annotated for IDE support and documentation

Key Models:
    - SourceInfo: Source file metadata (path, size, modified time)
    - TemplateInfo: Single template in inheritance chain
    - DependencyInfo: Page dependencies by category
    - ShortcodeUsage: Directive/shortcode usage statistics
    - CacheInfo: Cache hit/miss/stale status with reasons
    - OutputInfo: Generated output path and URL
    - Issue: Detected problem with severity and suggestion
    - PerformanceInfo: Build timing breakdown
    - PageExplanation: Complete aggregation of all components

Related Modules:
    - bengal.debug.explainer: PageExplainer that produces these models
    - bengal.debug.reporter: Rich terminal formatting for display

See Also:
    - bengal/cli/commands/explain.py: CLI command using these models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SourceInfo:
    """
    Information about a page's source file.

    Contains metadata about the original content file including its
    location, size, modification time, and encoding.

    Attributes:
        path: Path to the source file (relative to content directory).
        size_bytes: File size in bytes.
        line_count: Number of lines in the file.
        modified: Last modification timestamp, or None for virtual pages.
        encoding: Character encoding (default UTF-8).

    Example:
        >>> source = SourceInfo(
        ...     path=Path("docs/guide.md"),
        ...     size_bytes=2048,
        ...     line_count=75,
        ...     modified=datetime.now(),
        ... )
        >>> source.size_human
        '2.0 KB'
    """

    path: Path
    size_bytes: int
    line_count: int
    modified: datetime | None
    encoding: str = "UTF-8"

    @property
    def size_human(self) -> str:
        """
        Human-readable file size.

        Returns:
            Formatted size string with appropriate unit (B, KB, or MB).
        """
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        else:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"


@dataclass
class TemplateInfo:
    """
    Information about a single template in the inheritance chain.

    Represents one template file and its relationships to other templates
    via Jinja2's extends and include directives.

    Attributes:
        name: Template filename (e.g., "page.html", "base.html").
        source_path: Absolute path to template file, or None if not resolved.
        theme: Theme name this template belongs to, or None for project templates.
        extends: Parent template name if this template extends another.
        includes: List of template names included via {% include %}.

    Example:
        >>> template = TemplateInfo(
        ...     name="post.html",
        ...     source_path=Path("/site/themes/default/templates/post.html"),
        ...     theme="default",
        ...     extends="base.html",
        ...     includes=["partials/meta.html", "partials/comments.html"],
        ... )
    """

    name: str
    source_path: Path | None
    theme: str | None
    extends: str | None = None
    includes: list[str] = field(default_factory=list)


@dataclass
class DependencyInfo:
    """
    All dependencies for a page, categorized by type.

    Tracks what files a page depends on, which determines when the page
    needs to be rebuilt during incremental builds. Dependencies are
    categorized for clarity and debugging.

    Attributes:
        content: Other content files this page depends on (e.g., section index).
        templates: Template files used to render this page.
        data: Data files (YAML, JSON, TOML) referenced by the page.
        assets: Static assets (images, CSS, JS) referenced in content.
        includes: Files included via shortcodes or directives.

    Example:
        >>> deps = DependencyInfo(
        ...     templates=["post.html", "base.html"],
        ...     data=["authors.yaml"],
        ...     assets=["images/hero.jpg"],
        ... )
    """

    content: list[str] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)
    data: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)


@dataclass
class ShortcodeUsage:
    """
    Information about shortcode/directive usage in a page.

    Tracks occurrences of a specific directive or shortcode, including
    where it appears and what arguments were used.

    Attributes:
        name: Directive/shortcode name (e.g., "note", "admonition", "include").
        count: Total number of times this directive appears in the page.
        lines: Line numbers where each occurrence appears.
        args: Arguments passed to the directive (for the first occurrence).

    Example:
        >>> usage = ShortcodeUsage(
        ...     name="note",
        ...     count=3,
        ...     lines=[12, 45, 89],
        ... )
    """

    name: str
    count: int
    lines: list[int] = field(default_factory=list)
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheInfo:
    """
    Cache status information for a page.

    Indicates whether the page can be served from cache or needs to be
    rebuilt, along with the reason for cache misses or staleness.

    Attributes:
        status: Cache status code: "HIT", "MISS", "STALE", or "UNKNOWN".
        reason: Explanation for MISS or STALE status (None for HIT).
        cache_key: Key used to identify this page in the cache.
        last_hit: When the cache was last accessed (if available).
        content_cached: Whether parsed content is in cache.
        rendered_cached: Whether rendered HTML is in cache.

    Status Meanings:
        - HIT: Page fully cached and up-to-date
        - MISS: Page not in cache, will be built from scratch
        - STALE: Page in cache but dependencies changed
        - UNKNOWN: Cache status could not be determined

    Example:
        >>> cache = CacheInfo(
        ...     status="STALE",
        ...     reason="Template changed: base.html",
        ...     cache_key="docs/guide.md",
        ...     content_cached=True,
        ...     rendered_cached=True,
        ... )
        >>> cache.status_emoji
        '⚠️'
    """

    status: str
    reason: str | None
    cache_key: str | None
    last_hit: datetime | None = None
    content_cached: bool = False
    rendered_cached: bool = False

    @property
    def status_emoji(self) -> str:
        """
        Get emoji indicator for cache status.

        Returns:
            ✅ for HIT, ⚠️ for STALE, ❌ for MISS or UNKNOWN.
        """
        if self.status == "HIT":
            return "✅"
        elif self.status == "STALE":
            return "⚠️"
        else:
            return "❌"


@dataclass
class OutputInfo:
    """
    Information about a page's generated output.

    Contains details about where the rendered HTML is written and how
    it can be accessed.

    Attributes:
        path: Output file path relative to output directory, or None if
            not yet rendered.
        url: Public URL path for this page (e.g., "/docs/guide/").
        size_bytes: Size of rendered output in bytes, or None if not
            yet written.

    Example:
        >>> output = OutputInfo(
        ...     path=Path("docs/guide/index.html"),
        ...     url="/docs/guide/",
        ...     size_bytes=8192,
        ... )
        >>> output.size_human
        '8.0 KB'
    """

    path: Path | None
    url: str
    size_bytes: int | None = None

    @property
    def size_human(self) -> str | None:
        """
        Human-readable output size.

        Returns:
            Formatted size string with appropriate unit (B, KB, or MB),
            or None if size_bytes is not set.
        """
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
    """
    A detected issue with a page.

    Represents a problem, warning, or informational note discovered
    during page diagnosis. Issues include actionable suggestions
    where possible.

    Attributes:
        severity: Issue severity level: "error", "warning", or "info".
        issue_type: Category identifier (e.g., "broken_link", "missing_asset").
        message: Human-readable description of the issue.
        details: Additional context-specific data about the issue.
        suggestion: Recommended action to resolve the issue.
        line: Source line number where issue was found (if applicable).

    Example:
        >>> issue = Issue(
        ...     severity="warning",
        ...     issue_type="broken_link",
        ...     message="Link to '/docs/old-page' may not exist",
        ...     details={"link_text": "Old Page", "line": 45},
        ...     suggestion="Check if page exists or update link",
        ...     line=45,
        ... )
        >>> issue.severity_emoji
        '⚠️'
    """

    severity: str
    issue_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    suggestion: str | None = None
    line: int | None = None

    @property
    def severity_emoji(self) -> str:
        """
        Get emoji indicator for severity level.

        Returns:
            ❌ for error, ⚠️ for warning, ℹ️ for info.
        """
        if self.severity == "error":
            return "❌"
        elif self.severity == "warning":
            return "⚠️"
        else:
            return "ℹ️"


@dataclass
class PerformanceInfo:
    """
    Performance timing breakdown for page building.

    Provides detailed timing measurements for different phases of
    page processing, useful for identifying performance bottlenecks.

    Attributes:
        total_ms: Total build time in milliseconds.
        parse_ms: Time spent parsing markdown content.
        shortcode_ms: Time spent processing directives/shortcodes.
        render_ms: Time spent rendering templates.
        breakdown: Additional phase timings by name.

    Example:
        >>> perf = PerformanceInfo(
        ...     total_ms=45.2,
        ...     parse_ms=12.5,
        ...     shortcode_ms=8.3,
        ...     render_ms=24.4,
        ... )
    """

    total_ms: float
    parse_ms: float | None = None
    shortcode_ms: float | None = None
    render_ms: float | None = None
    breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class PageExplanation:
    """
    Complete explanation of how a page is built.

    Aggregates all aspects of page building into a single comprehensive
    object. This is the primary output of PageExplainer and provides
    full traceability for any page.

    Attributes:
        source: Source file information (path, size, modified).
        frontmatter: Parsed frontmatter metadata dictionary.
        template_chain: Template inheritance chain (child to parent).
        dependencies: All page dependencies by category.
        shortcodes: Directive/shortcode usage statistics.
        cache: Cache status (HIT/MISS/STALE) with reasons.
        output: Output path and URL information.
        performance: Optional timing breakdown (if measured).
        issues: Optional list of detected issues (if diagnosed).

    Example:
        >>> from bengal.debug import PageExplainer, ExplanationReporter
        >>> explainer = PageExplainer(site)
        >>> explanation = explainer.explain("docs/guide.md", diagnose=True)
        >>> print(f"Template: {explanation.template_chain[0].name}")
        Template: page.html
        >>> print(f"Cache: {explanation.cache.status}")
        Cache: HIT
        >>> if explanation.issues:
        ...     for issue in explanation.issues:
        ...         print(f"{issue.severity_emoji} {issue.message}")

    See Also:
        - PageExplainer: Creates PageExplanation instances
        - ExplanationReporter: Formats for terminal display
    """

    source: SourceInfo
    frontmatter: dict[str, Any]
    template_chain: list[TemplateInfo]
    dependencies: DependencyInfo
    shortcodes: list[ShortcodeUsage]
    cache: CacheInfo
    output: OutputInfo
    performance: PerformanceInfo | None = None
    issues: list[Issue] | None = None
