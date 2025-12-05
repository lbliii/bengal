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
    - Lazy artifacts: Expensive computations cached on first access

Related Modules:
    - bengal.orchestration.build: Build orchestration using BuildContext
    - bengal.utils.build_stats: Build statistics collection
    - bengal.utils.progress: Progress reporting

See Also:
    - bengal/utils/build_context.py:BuildContext for context structure
    - plan/active/rfc-build-pipeline.md: Build pipeline design
    - plan/active/rfc-lazy-build-artifacts.md: Lazy artifact design
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
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

    # Lazy-computed artifacts (built once on first access)
    # These eliminate redundant expensive computations across build phases
    _knowledge_graph: Any = field(default=None, repr=False)
    _knowledge_graph_enabled: bool = field(default=True, repr=False)

    @property
    def knowledge_graph(self) -> KnowledgeGraph | None:
        """
        Get knowledge graph (built lazily, cached for build duration).

        The knowledge graph is expensive to build (~200-500ms for 773 pages).
        By caching it here, we avoid rebuilding it 3 times per build
        (post-processing, special pages, health check).

        Returns:
            Built KnowledgeGraph instance, or None if disabled/unavailable

        Example:
            # First access builds the graph
            graph = ctx.knowledge_graph

            # Subsequent accesses reuse cached instance
            graph2 = ctx.knowledge_graph  # Same instance, no rebuild
        """
        if not self._knowledge_graph_enabled:
            return None

        if self._knowledge_graph is None:
            self._knowledge_graph = self._build_knowledge_graph()
        return self._knowledge_graph

    def _build_knowledge_graph(self) -> KnowledgeGraph | None:
        """
        Build and cache knowledge graph.

        Returns:
            Built KnowledgeGraph instance, or None if disabled/unavailable
        """
        if self.site is None:
            return None

        try:
            from bengal.analysis.knowledge_graph import KnowledgeGraph
            from bengal.config.defaults import is_feature_enabled

            # Check if graph feature is enabled
            if not is_feature_enabled(self.site.config, "graph"):
                self._knowledge_graph_enabled = False
                return None

            graph = KnowledgeGraph(self.site)
            graph.build()
            return graph
        except ImportError:
            self._knowledge_graph_enabled = False
            return None

    def clear_lazy_artifacts(self) -> None:
        """
        Clear lazy-computed artifacts to free memory.

        Call this at the end of a build to release memory used by
        cached artifacts like the knowledge graph.
        """
        self._knowledge_graph = None
