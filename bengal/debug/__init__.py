"""
Debug and introspection utilities for Bengal.

Provides tools for understanding how pages are built, including template
resolution, dependency tracking, cache status, and performance analysis.

Key Components:
    - PageExplainer: Generate explanations for how pages are built
    - ExplanationReporter: Format and display explanations in terminal
    - IncrementalBuildDebugger: Debug incremental build issues
    - BuildDeltaAnalyzer: Compare builds and explain changes
    - DependencyVisualizer: Visualize build dependencies

Debug Tool Infrastructure:
    - DebugTool: Base class for debug tools
    - DebugReport: Structured output from debug tools
    - DebugRegistry: Tool discovery and registration

Related Modules:
    - bengal.cli.commands.explain: CLI command for page explanation
    - bengal.cli.commands.debug: CLI commands for debug tools
    - bengal.core.page: Page model being explained
    - bengal.rendering.template_engine: Template resolution
    - bengal.cache.build_cache: Cache status introspection

See Also:
    - plan/active/rfc-explain-page.md: Design RFC for this feature
"""

from __future__ import annotations

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

# Debug tool infrastructure
from bengal.debug.base import (
    DebugFinding,
    DebugRegistry,
    DebugReport,
    DebugTool,
    Severity,
)

# Incremental build debugging
from bengal.debug.incremental_debugger import (
    IncrementalBuildDebugger,
    RebuildExplanation,
    RebuildReason,
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

# Content migration
from bengal.debug.content_migrator import (
    ContentMigrator,
    MoveOperation,
    MovePreview,
    PageDraft,
    Redirect,
)

# Lazy imports for optional components
def __getattr__(name: str):
    """Lazy import for optional components."""
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
]

