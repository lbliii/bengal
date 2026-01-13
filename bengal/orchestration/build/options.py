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

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.utils.profile import BuildProfile

# Type aliases for phase callbacks (RFC: rfc-dashboard-api-integration)
# on_phase_start receives: (phase_name)
# on_phase_complete receives: (phase_name, duration_ms, details)
type PhaseStartCallback = Callable[[str], None]
type PhaseCompleteCallback = Callable[[str, float, str], None]


@dataclass
class BuildOptions:
    """
    Configuration options for site builds.
    
    Consolidates all build parameters into a single object, replacing
    the 11-parameter signature of BuildOrchestrator.build().
    
    **Preferred Usage**: Use :func:`bengal.config.build_options_resolver.resolve_build_options`
    to create BuildOptions with proper precedence (CLI > config > DEFAULTS).
    Direct instantiation is supported for backward compatibility and testing.
    
    Attributes:
        force_sequential: If True, force sequential processing (bypasses auto-detection).
            Use --no-parallel CLI flag to set this. Default: False (auto-detect via should_parallelize).
        incremental: Whether to perform incremental build. None = auto-detect
            based on cache presence. True = force incremental. False = force full.
        verbose: Whether to show verbose console logs during build
        quiet: Whether to suppress progress output (minimal output mode)
        profile: Build profile (WRITER, THEME_DEV, or DEV)
        memory_optimized: Use streaming build for memory efficiency (5K+ pages)
        strict: Whether to fail build on validation errors
        full_output: Show full traditional output instead of live progress
        profile_templates: Enable template profiling for performance analysis
        explain: Show detailed incremental build decisions (RFC: rfc-incremental-build-observability)
        dry_run: Preview build without writing files (shows what WOULD happen)
        explain_json: Output explain results as JSON (for tooling integration)
        changed_sources: Set of paths to content files that changed (for dev server)
        nav_changed_sources: Set of paths to nav-affecting files that changed
        structural_changed: Whether structural changes occurred (file create/delete/move)
    
    Example:
            >>> # Preferred: Use resolver for proper precedence
            >>> from bengal.config.build_options_resolver import resolve_build_options, CLIFlags
            >>> options = resolve_build_options(site.config, CLIFlags(force_sequential=True))
            >>>
            >>> # Direct instantiation (for testing/backward compatibility)
            >>> from bengal.orchestration.build.options import BuildOptions
            >>> from bengal.utils.profile import BuildProfile
            >>> options = BuildOptions(
            ...     profile=BuildProfile.WRITER,
            ...     strict=True,
            ...     incremental=False,
            ... )
        
    """

    # Build behavior
    force_sequential: bool = False
    incremental: bool | None = None
    verbose: bool = False
    quiet: bool = False
    memory_optimized: bool = False

    # Output behavior
    strict: bool = False
    full_output: bool = False

    # Explain mode (RFC: rfc-incremental-build-observability Phase 2)
    explain: bool = False
    dry_run: bool = False
    explain_json: bool = False

    # Profiling
    profile: BuildProfile | None = None
    profile_templates: bool = False

    # Incremental build hints (from dev server / file watcher)
    changed_sources: set[Path] = field(default_factory=set)
    nav_changed_sources: set[Path] = field(default_factory=set)
    structural_changed: bool = False

    # Phase streaming callbacks (RFC: rfc-dashboard-api-integration)
    # These enable real-time build progress updates in the dashboard.
    # Callbacks are optional (None = no streaming).
    on_phase_start: PhaseStartCallback | None = None
    on_phase_complete: PhaseCompleteCallback | None = None
