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
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.analysis.knowledge_graph import KnowledgeGraph
    from bengal.cache.build_cache import BuildCache
    from bengal.cache.dependency_tracker import DependencyTracker
    from bengal.cli.progress import LiveProgressManager
    from bengal.core.asset import Asset
    from bengal.core.output import OutputCollector
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.stats import BuildStats
    from bengal.output import CLIOutput
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

    # Output collector for hot reload tracking
    output_collector: OutputCollector | None = None

    # Timing (build start time for duration calculation)
    build_start: float = 0.0

    # Lazy-computed artifacts (built once on first access)
    # These eliminate redundant expensive computations across build phases
    _knowledge_graph: Any = field(default=None, repr=False)
    _knowledge_graph_enabled: bool = field(default=True, repr=False)

    # Content cache - populated during discovery, shared by validators
    # Eliminates redundant disk I/O during health checks (4s+ → <100ms)
    # See: plan/active/rfc-build-integrated-validation.md
    _page_contents: dict[str, str] = field(default_factory=dict, repr=False)
    _content_cache_lock: Lock = field(default_factory=Lock, repr=False)

    # Accumulated JSON data - populated during rendering, consumed in post-processing
    # Eliminates double iteration of pages (saves ~500-700ms on large sites)
    # See: plan/active/rfc-postprocess-optimization.md
    _accumulated_page_json: list[tuple[Any, dict[str, Any]]] = field(
        default_factory=list, repr=False
    )
    _accumulated_json_lock: Lock = field(default_factory=Lock, repr=False)

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
        cached artifacts like the knowledge graph and content cache.
        """
        self._knowledge_graph = None
        self.clear_content_cache()

    # =========================================================================
    # Content Cache Methods (Build-Integrated Validation)
    # =========================================================================
    # These methods enable validators to use cached content instead of re-reading
    # files from disk, reducing health check time from ~4.6s to <100ms.
    # See: plan/active/rfc-build-integrated-validation.md

    def cache_content(self, source_path: Path, content: str) -> None:
        """
        Cache raw content during discovery phase (thread-safe).

        Call this during content discovery to store file content for later
        use by validators. This eliminates redundant disk I/O during health
        checks.

        Args:
            source_path: Path to source file (used as cache key)
            content: Raw file content to cache

        Example:
            # During content discovery
            content = file_path.read_text()
            if build_context:
                build_context.cache_content(file_path, content)
        """
        with self._content_cache_lock:
            self._page_contents[str(source_path)] = content

    def get_content(self, source_path: Path) -> str | None:
        """
        Get cached content without disk I/O.

        Args:
            source_path: Path to source file

        Returns:
            Cached content string, or None if not cached

        Example:
            # In validator
            content = build_context.get_content(page.source_path)
            if content is None:
                content = page.source_path.read_text()  # Fallback
        """
        with self._content_cache_lock:
            return self._page_contents.get(str(source_path))

    def get_all_cached_contents(self) -> dict[str, str]:
        """
        Get a copy of all cached contents for batch processing.

        Returns a copy to avoid thread safety issues when iterating.

        Returns:
            Dictionary mapping source path strings to content

        Example:
            # In DirectiveAnalyzer
            all_contents = build_context.get_all_cached_contents()
            for path, content in all_contents.items():
                directives = self._extract_directives(content, Path(path))
        """
        with self._content_cache_lock:
            return dict(self._page_contents)

    def clear_content_cache(self) -> None:
        """
        Clear content cache to free memory.

        Call this after validation phase completes to release memory
        used by cached file contents.
        """
        with self._content_cache_lock:
            self._page_contents.clear()

    @property
    def content_cache_size(self) -> int:
        """
        Get number of cached content entries.

        Returns:
            Number of files with cached content
        """
        with self._content_cache_lock:
            return len(self._page_contents)

    @property
    def has_cached_content(self) -> bool:
        """
        Check if content cache has any entries.

        Validators can use this to decide whether to use cache or fallback.

        Returns:
            True if cache has content
        """
        with self._content_cache_lock:
            return len(self._page_contents) > 0

    # =========================================================================
    # Accumulated JSON Data Methods (Post-Processing Optimization)
    # =========================================================================
    # These methods enable JSON data to be accumulated during rendering
    # instead of being computed again in post-processing, eliminating
    # double iteration and saving ~500-700ms on large sites.
    # See: plan/active/rfc-postprocess-optimization.md

    def accumulate_page_json(self, json_path: Any, page_data: dict[str, Any]) -> None:
        """
        Accumulate JSON data for a page during rendering (thread-safe).

        Call this during rendering phase to store JSON data for later
        use in post-processing. This eliminates redundant computation
        and double iteration of pages.

        Args:
            json_path: Path where JSON file should be written
            page_data: Pre-computed JSON data dictionary

        Example:
            # During rendering phase
            json_path = get_page_json_path(page)
            page_data = build_page_json_data(page)
            if build_context:
                build_context.accumulate_page_json(json_path, page_data)
        """
        with self._accumulated_json_lock:
            self._accumulated_page_json.append((json_path, page_data))

    def get_accumulated_json(self) -> list[tuple[Any, dict[str, Any]]]:
        """
        Get all accumulated JSON data for post-processing.

        Returns a copy to avoid thread safety issues when iterating.

        Returns:
            List of (json_path, page_data) tuples

        Example:
            # In post-processing phase
            accumulated = build_context.get_accumulated_json()
            for json_path, page_data in accumulated:
                write_json(json_path, page_data)
        """
        with self._accumulated_json_lock:
            return list(self._accumulated_page_json)

    def clear_accumulated_json(self) -> None:
        """
        Clear accumulated JSON data to free memory.

        Call this after post-processing phase completes to release memory
        used by accumulated JSON data.
        """
        with self._accumulated_json_lock:
            self._accumulated_page_json.clear()

    @property
    def has_accumulated_json(self) -> bool:
        """
        Check if accumulated JSON data exists.

        Post-processing can use this to decide whether to use accumulated
        data or fall back to computing from pages.

        Returns:
            True if accumulated JSON data exists
        """
        with self._accumulated_json_lock:
            return len(self._accumulated_page_json) > 0
