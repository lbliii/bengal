"""
Debug and introspection utilities for Bengal.

Provides comprehensive tools for understanding how pages are built,
diagnosing build issues, and safely restructuring content. All tools
follow a read-only introspection pattern with no side effects.

Architecture:
    This package follows the debug tool infrastructure pattern where all
    tools inherit from DebugTool and produce DebugReport instances. Tools
    can be discovered and instantiated via DebugRegistry.

Page Explanation:
    - PageExplainer: Generate complete build explanations for any page
    - ExplanationReporter: Rich terminal formatting for explanations
    - PageExplanation: Data model aggregating all explanation components
    - SourceInfo, TemplateInfo, DependencyInfo, CacheInfo, OutputInfo:
      Component models for different aspects of page building

Build Debugging:
    - IncrementalBuildDebugger: Diagnose why pages rebuild, find phantom
      rebuilds, validate cache consistency, simulate change impact
    - BuildDeltaAnalyzer: Compare build snapshots, track build history,
      explain what changed between builds
    - DependencyVisualizer: Generate Mermaid/DOT diagrams of dependency
      graphs, show blast radius of changes

Content Operations:
    - ContentMigrator: Safe content moves with link tracking, automatic
      redirect generation, preview before execution
    - ShortcodeSandbox: Test directives in isolation, validate syntax,
      render without full site context
    - ConfigInspector: Compare configs across environments, explain
      effective values with origin tracking

Debug Infrastructure:
    - DebugTool: Abstract base class for all debug tools
    - DebugReport: Structured output with findings and recommendations
    - DebugFinding: Individual finding with severity and metadata
    - DebugRegistry: Tool discovery, registration, and factory
    - Severity: Finding severity levels (ERROR, WARNING, INFO)

Example:
    Explain how a page is built:

    >>> from bengal.debug import PageExplainer, ExplanationReporter
    >>> explainer = PageExplainer(site)
    >>> explanation = explainer.explain("docs/guide.md")
    >>> reporter = ExplanationReporter()
    >>> reporter.print(explanation)

    Debug incremental build issues:

    >>> from bengal.debug import IncrementalBuildDebugger
    >>> debugger = IncrementalBuildDebugger(site=site, cache=cache)
    >>> explanation = debugger.explain_rebuild("content/posts/my-post.md")
    >>> print(explanation.format_detailed())

    Test a directive in isolation:

    >>> from bengal.debug import ShortcodeSandbox
    >>> sandbox = ShortcodeSandbox()
    >>> result = sandbox.render('```{note}\\nTest note.\\n```')
    >>> print(result.html)

Related Modules:
    - bengal.cli.commands.explain: CLI command for page explanation
    - bengal.cli.commands.debug: CLI commands for debug tools
    - bengal.core.page: Page model being explained
    - bengal.rendering.template_engine: Template resolution logic
    - bengal.cache.build_cache: Cache status introspection

See Also:
    - architecture/debug-tools.md: Debug tool architecture design
"""

from __future__ import annotations

from typing import Any

# Debug tool infrastructure
from bengal.debug.base import (
    DebugFinding,
    DebugRegistry,
    DebugReport,
    DebugTool,
    Severity,
)

# Configuration inspector
from bengal.debug.config_inspector import (
    ConfigComparisonResult,
    ConfigDiff,
    ConfigInspector,
    KeyExplanation,
)

# Content migration
from bengal.debug.content_migrator import (
    ContentMigrator,
    MoveOperation,
    MovePreview,
    PageDraft,
    Redirect,
)

# Build comparison
from bengal.debug.delta_analyzer import (
    BuildDelta,
    BuildDeltaAnalyzer,
    BuildHistory,
    BuildSnapshot,
)

# Dependency visualization
from bengal.debug.dependency_visualizer import (
    DependencyGraph,
    DependencyNode,
    DependencyVisualizer,
)

# Incremental build debugging
from bengal.debug.incremental_debugger import (
    IncrementalBuildDebugger,
    RebuildExplanation,
    RebuildReason,
)

# Page explanation tools
from bengal.debug.models import (
    CacheInfo,
    DependencyInfo,
    OutputInfo,
    PageExplanation,
    ShortcodeUsage,
    SourceInfo,
    TemplateInfo,
)

# Shortcode/directive sandbox
from bengal.debug.shortcode_sandbox import (
    RenderResult,
    ShortcodeSandbox,
    ValidationResult,
)


# Lazy imports for optional components
def __getattr__(name: str) -> Any:
    """
    Lazy import for optional components with heavier dependencies.

    PageExplainer and ExplanationReporter are loaded lazily because they
    have additional dependencies (Rich library, regex patterns) that may
    not be needed for basic debug tool usage.

    Args:
        name: Attribute name being accessed.

    Returns:
        The requested class if available.

    Raises:
        AttributeError: If the requested attribute does not exist.
    """
    if name == "PageExplainer":
        from bengal.debug.explainer import PageExplainer

        return PageExplainer
    if name == "ExplanationReporter":
        from bengal.debug.reporter import ExplanationReporter

        return ExplanationReporter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Page explanation
    "PageExplainer",
    "PageExplanation",
    "ExplanationReporter",
    "SourceInfo",
    "TemplateInfo",
    "DependencyInfo",
    "ShortcodeUsage",
    "CacheInfo",
    "OutputInfo",
    # Debug infrastructure
    "DebugTool",
    "DebugReport",
    "DebugFinding",
    "DebugRegistry",
    "Severity",
    # Incremental debugging
    "IncrementalBuildDebugger",
    "RebuildReason",
    "RebuildExplanation",
    # Build comparison
    "BuildDeltaAnalyzer",
    "BuildSnapshot",
    "BuildDelta",
    "BuildHistory",
    # Dependency visualization
    "DependencyVisualizer",
    "DependencyGraph",
    "DependencyNode",
    # Content migration
    "ContentMigrator",
    "MoveOperation",
    "MovePreview",
    "PageDraft",
    "Redirect",
    # Shortcode sandbox
    "ShortcodeSandbox",
    "RenderResult",
    "ValidationResult",
    # Config inspector
    "ConfigInspector",
    "ConfigDiff",
    "ConfigComparisonResult",
    "KeyExplanation",
]
