"""
Build options for site builds.

Centralizes build configuration into a single dataclass, replacing the
11-parameter signature of BuildOrchestrator.build().

This improves:
- Type safety with explicit field types
- Documentation with field descriptions
- Extensibility (new options without breaking signatures)
- Call site clarity (named options instead of long parameter lists)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.utils.profile import BuildProfile


@dataclass
class BuildOptions:
    """
    Configuration options for site builds.

    Consolidates all build parameters into a single object, replacing
    the 11-parameter signature of BuildOrchestrator.build().

    Attributes:
        parallel: Whether to use parallel processing (default: True)
        incremental: Whether to perform incremental build. None = auto-detect
            based on cache presence. True = force incremental. False = force full.
        verbose: Whether to show verbose console logs during build
        quiet: Whether to suppress progress output (minimal output mode)
        profile: Build profile (WRITER, THEME_DEV, or DEV)
        memory_optimized: Use streaming build for memory efficiency (5K+ pages)
        strict: Whether to fail build on validation errors
        full_output: Show full traditional output instead of live progress
        profile_templates: Enable template profiling for performance analysis
        changed_sources: Set of paths to content files that changed (for dev server)
        nav_changed_sources: Set of paths to nav-affecting files that changed
        structural_changed: Whether structural changes occurred (file create/delete/move)

    Example:
        >>> from bengal.orchestration.build.options import BuildOptions
        >>> from bengal.utils.profile import BuildProfile
        >>>
        >>> # Default options (writer profile, parallel, auto-incremental)
        >>> options = BuildOptions()
        >>>
        >>> # Strict production build
        >>> options = BuildOptions(
        ...     profile=BuildProfile.WRITER,
        ...     strict=True,
        ...     incremental=False,
        ... )
        >>>
        >>> # Dev server rebuild with changed paths
        >>> options = BuildOptions(
        ...     incremental=True,
        ...     changed_sources={Path("content/blog/post.md")},
        ... )
    """

    # Build behavior
    parallel: bool = True
    incremental: bool | None = None
    verbose: bool = False
    quiet: bool = False
    memory_optimized: bool = False

    # Output behavior
    strict: bool = False
    full_output: bool = False

    # Profiling
    profile: BuildProfile | None = None
    profile_templates: bool = False

    # Incremental build hints (from dev server / file watcher)
    changed_sources: set[Path] = field(default_factory=set)
    nav_changed_sources: set[Path] = field(default_factory=set)
    structural_changed: bool = False
