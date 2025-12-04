"""
Build context for sharing state across build phases.

Provides BuildContext dataclass for passing shared state between build phases,
replacing scattered local variables. Created at build start and populated
incrementally as phases execute.

Key Concepts:
    - Shared context: Single context object passed to all build phases
    - Phase coordination: Enables phase-to-phase communication
    - State management: Centralized build state management
    - Lifecycle: Created at build start, populated during phases

Related Modules:
    - bengal.orchestration.build: Build orchestration using BuildContext
    - bengal.utils.build_stats: Build statistics collection
    - bengal.utils.progress: Progress reporting

See Also:
    - bengal/utils/build_context.py:BuildContext for context structure
    - plan/active/rfc-build-pipeline.md: Build pipeline design
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.cache.dependency_tracker import DependencyTracker
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.utils.build_stats import BuildStats
    from bengal.utils.cli_output import CLIOutput
    from bengal.utils.live_progress import LiveProgressManager
    from bengal.utils.profile import BuildProfile
    from bengal.utils.progress import ProgressReporter


@dataclass
class BuildContext:
    """
    Shared build context passed across build phases.

    This context is created at the start of build() and passed to all _phase_* methods.
    It replaces local variables that were scattered throughout the 894-line build() method.

    Lifecycle:
        1. Created in _setup_build_context() at build start
        2. Populated incrementally as phases execute
        3. Used by all _phase_* methods for shared state

    Categories:
        - Core: site, stats, profile (required)
        - Cache: cache, tracker (initialized in Phase 0)
        - Build mode: incremental, verbose, quiet, strict, parallel
        - Work items: pages_to_build, assets_to_process (determined in Phase 2)
        - Incremental state: affected_tags, affected_sections, changed_page_paths
        - Output: cli, progress_manager, reporter
    """

    # Core (required)
    site: Site | None = None
    stats: BuildStats | None = None
    profile: BuildProfile | None = None

    # Cache and tracking
    cache: BuildCache | None = None
    tracker: DependencyTracker | None = None

    # Build mode flags
    incremental: bool = False
    verbose: bool = False
    quiet: bool = False
    strict: bool = False
    parallel: bool = True
    memory_optimized: bool = False
    full_output: bool = False
    profile_templates: bool = False  # Enable template profiling for performance analysis

    # Work items (determined during incremental filtering)
    pages: list[Page] | None = None  # All discovered pages
    pages_to_build: list[Page] | None = None  # Pages that need rendering
    assets: list[Asset] | None = None  # All discovered assets
    assets_to_process: list[Asset] | None = None  # Assets that need processing

    # Incremental build state
    affected_tags: set[str] = field(default_factory=set)
    affected_sections: set[str] | None = None
    changed_page_paths: set[Path] = field(default_factory=set)
    config_changed: bool = False

    # Output/progress
    cli: CLIOutput | None = None
    progress_manager: LiveProgressManager | None = None
    reporter: ProgressReporter | None = None

    # Timing (build start time for duration calculation)
    build_start: float = 0.0
