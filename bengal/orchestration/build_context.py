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

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.analysis.graph.knowledge_graph import KnowledgeGraph
    from bengal.cache.build_cache import BuildCache
    from bengal.core.asset import Asset
    from bengal.core.output import OutputCollector
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.stats import BuildStats
    from bengal.output import CLIOutput
    from bengal.protocols import ProgressReporter
    from bengal.utils.observability.cli_progress import LiveProgressManager
    from bengal.utils.observability.profile import BuildProfile


@dataclass
class AccumulatedPageData:
    """
    Unified per-page data accumulated during rendering.

    Contains all fields needed by:
    - PageJSONGenerator (per-page JSON files)
    - SiteIndexGenerator (index.json for search)

    Computed once during render phase, consumed by multiple post-processing
    generators. Eliminates redundant computation and double page iteration.

    See: plan/drafted/rfc-unified-page-data-accumulation.md

    """

    # =========================================================================
    # Identity (required by all consumers)
    # =========================================================================
    source_path: Path
    url: str  # Full URL with baseurl (for PageJSONGenerator)
    uri: str  # Relative path without baseurl (for SiteIndexGenerator)

    # =========================================================================
    # Core Metadata (required by all consumers)
    # =========================================================================
    title: str
    description: str
    date: str | None  # ISO format (YYYY-MM-DD for index)
    date_iso: str | None  # Full ISO format for PageJSONGenerator

    # =========================================================================
    # Content Derivatives (computed once, used by many)
    # =========================================================================
    plain_text: str
    excerpt: str  # Short excerpt (excerpt_length chars)
    content_preview: str  # Longer preview for search (excerpt_length * 3)
    word_count: int
    reading_time: int

    # =========================================================================
    # Classification (for search/filtering)
    # =========================================================================
    section: str
    tags: list[str]

    # =========================================================================
    # Navigation/Structure (for SiteIndexGenerator)
    # =========================================================================
    dir: str  # Directory path (e.g., "/docs/getting-started/")

    # =========================================================================
    # Enhanced Metadata (for SiteIndexGenerator)
    # These are extracted from page.metadata during accumulation
    # =========================================================================
    enhanced_metadata: dict[str, Any] = field(default_factory=dict)
    # Contains: type, layout, author, authors, category, categories, weight,
    #           draft, featured, search_keywords, search_exclude, cli_name,
    #           api_module, difficulty, level, related, lastmod, source_file,
    #           version, isAutodoc

    # =========================================================================
    # Extended Data for PageJSONGenerator
    # Only populated if per-page JSON is enabled
    # =========================================================================
    full_json_data: dict[str, Any] | None = None
    json_output_path: Path | None = None

    # =========================================================================
    # Raw Metadata (fallback for fields we didn't anticipate)
    # =========================================================================
    raw_metadata: dict[str, Any] = field(default_factory=dict)


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
        4. (Optional) Can be used as context manager for automatic cleanup

    Categories:
        - Core: site, stats, profile (required)
        - Cache: cache, tracker (initialized in Phase 0)
        - Build mode: incremental, verbose, quiet, strict, parallel
        - Work items: pages_to_build, assets_to_process (determined in Phase 2)
        - Incremental state: affected_tags, affected_sections, changed_page_paths
        - Output: cli, progress_manager, reporter
        - Build-scoped: build_id, _build_scoped_cache (for cross-build isolation)

    Build-Scoped Caching (RFC: Cache Lifecycle Hardening):
        Values cached via get_cached() are scoped to this build instance.
        When used as a context manager, BUILD_START is signaled on entry
        and BUILD_END + cache cleanup on exit. This prevents cross-build
        contamination when Site objects are reused.

    Example:
        # As context manager (recommended for new code)
        with BuildContext(site=site) as ctx:
            contexts = ctx.get_cached("global_contexts", lambda: build_contexts(site))
            # ... build operations ...
        # Automatic cleanup on exit

        # Traditional usage (backward compatible)
        ctx = BuildContext(site=site)
        # ... build operations ...
        ctx.clear_lazy_artifacts()  # Manual cleanup

    """

    # Core (required)
    site: Site | None = None
    stats: BuildStats | None = None
    profile: BuildProfile | None = None

    # Cache
    cache: BuildCache | None = None

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

    # Write-behind collector for async I/O (RFC: rfc-path-to-200-pgs Phase III)
    # Created by BuildOrchestrator when build.write_behind=True
    write_behind: Any = None  # WriteBehindCollector (lazy import to avoid circular)

    # Snapshot for lock-free parallel rendering (RFC: rfc-bengal-snapshot-engine)
    snapshot: Any = None  # SiteSnapshot (lazy import to avoid circular)

    # Services — instantiated from snapshot after creation (RFC: bengal-v2-architecture)
    # These provide O(1) lookups on immutable data for thread-safe rendering.
    query_service: Any = None  # QueryService (lazy import to avoid circular)
    data_service: Any = None  # DataService (lazy import to avoid circular)

    # Timing (build start time for duration calculation)
    build_start: float = 0.0

    # =========================================================================
    # Pipeline Integration (data-driven build pipeline)
    # =========================================================================
    # These fields are populated by build() before execute_pipeline() runs.
    # Tasks access them as ctx._orchestrator, ctx._build_options, etc.

    # Reference to the BuildOrchestrator instance (tasks delegate to sub-orchestrators)
    _orchestrator: Any = field(default=None, repr=False)

    # The original BuildOptions object (tasks read flags like force_sequential, dry_run)
    _build_options: Any = field(default=None, repr=False)

    # Result of the incremental filtering phase (set by filter_pages task)
    filter_result: Any = field(default=None, repr=False)

    # GeneratedPageCache for tag page incremental skipping
    _generated_page_cache: Any = field(default=None, repr=False)

    # =========================================================================
    # Build-Scoped Caching (RFC: Cache Lifecycle Hardening)
    # =========================================================================
    # Unique build identifier and build-scoped cache prevent cross-build
    # contamination when Site objects are reused across builds.

    # Unique identifier for this build (8 hex chars from uuid4)
    build_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    # Build-scoped cache: values here are automatically cleared when build ends
    # Use get_cached() to access - don't access directly
    _build_scoped_cache: dict[str, Any] = field(default_factory=dict, repr=False)
    _build_scoped_cache_lock: Lock = field(default_factory=Lock, repr=False)

    # Lazy-computed artifacts (built once on first access)
    # These eliminate redundant expensive computations across build phases
    _knowledge_graph: Any = field(default=None, repr=False)
    _knowledge_graph_enabled: bool = field(default=True, repr=False)

    # Content cache - populated during discovery, shared by validators
    # Eliminates redundant disk I/O during health checks (4s+ → <100ms)
    # See: plan/active/rfc-build-integrated-validation.md
    _page_contents: dict[str, str] = field(default_factory=dict, repr=False)
    _content_cache_lock: Lock = field(default_factory=Lock, repr=False)

    # Accumulated Asset Dependencies (Inline Asset Extraction)
    # Eliminates double iteration in phase_track_assets (saves ~5-6s on large sites)
    # See: changelog.md (Inline Asset Extraction)
    _accumulated_assets: list[tuple[Path, set[str]]] = field(default_factory=list, repr=False)
    _accumulated_assets_lock: Lock = field(default_factory=Lock, repr=False)

    # Unified Page Data Accumulation
    # Populated during rendering, consumed by PageJSONGenerator and SiteIndexGenerator
    # Eliminates redundant computation and double page iteration (~350ms savings)
    # See: plan/drafted/rfc-unified-page-data-accumulation.md
    _accumulated_page_data: list[AccumulatedPageData] = field(default_factory=list, repr=False)
    _accumulated_page_data_lock: Lock = field(default_factory=Lock, repr=False)
    # Index for O(1) lookup by source_path during hybrid mode (incremental builds)
    _accumulated_page_index: dict[Path, AccumulatedPageData] = field(
        default_factory=dict, repr=False
    )

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
            from bengal.analysis.graph.knowledge_graph import KnowledgeGraph
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
        self.clear_accumulated_assets()
        self.clear_accumulated_page_data()
        self.clear_build_scoped_cache()

    # =========================================================================
    # Build-Scoped Cache Methods (RFC: Cache Lifecycle Hardening)
    # =========================================================================
    # These methods enable caching values that are scoped to a specific build,
    # preventing cross-build contamination when Site objects are reused.

    def get_cached(self, key: str, factory: Callable[[], Any]) -> Any:
        """
        Get or create cached value scoped to this build.

        Values cached here are automatically cleared when build completes
        (via __exit__ or clear_build_scoped_cache), preventing cross-build
        contamination.

        Thread-safe: Uses lock for concurrent access.

        Args:
            key: Cache key (should be descriptive, e.g., "global_contexts")
            factory: Callable that creates the value if not cached

        Returns:
            Cached value (created on first access)

        Example:
            # Cache expensive computation for this build only
            contexts = build_context.get_cached(
                "global_contexts",
                lambda: _create_contexts(site)
            )
        """
        with self._build_scoped_cache_lock:
            if key not in self._build_scoped_cache:
                self._build_scoped_cache[key] = factory()
            return self._build_scoped_cache[key]

    def clear_build_scoped_cache(self) -> None:
        """
        Clear build-scoped cache to free memory.

        Called automatically by __exit__ when used as context manager,
        or manually at end of build.
        """
        with self._build_scoped_cache_lock:
            self._build_scoped_cache.clear()

    @property
    def build_scoped_cache_size(self) -> int:
        """Get number of entries in build-scoped cache."""
        with self._build_scoped_cache_lock:
            return len(self._build_scoped_cache)

    def __enter__(self) -> BuildContext:
        """
        Enter build scope - signal BUILD_START event.

        Enables context manager usage for automatic lifecycle management:

            with BuildContext(site=site) as ctx:
                # Build operations
            # Automatic cleanup on exit

        Returns:
            Self for use in with statement
        """
        from bengal.utils.cache_registry import InvalidationReason, invalidate_for_reason

        invalidate_for_reason(InvalidationReason.BUILD_START)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """
        Exit build scope - signal BUILD_END event and clear build-scoped caches.

        Automatically clears _build_scoped_cache to free memory and prevent
        cross-build contamination.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Traceback if an exception was raised
        """
        from bengal.utils.cache_registry import InvalidationReason, invalidate_for_reason

        invalidate_for_reason(InvalidationReason.BUILD_END)
        self.clear_build_scoped_cache()

    # =========================================================================
    # Section Snapshot Lookup (PERF: O(1) instead of O(S))
    # =========================================================================
    # Section lookup by path/name is called per page during rendering.
    # Without caching, this is O(S) per page = O(S*P) total.
    # With cached maps, it's O(1) per page = O(P) total.

    def get_section_snapshot(self, section: Any) -> Any:
        """
        Get SectionSnapshot for a section using O(1) cached lookup.

        PERF: Builds lookup maps once per build, then uses dict lookups.
        Replaces O(S) iteration over snapshot.sections with O(1) dict access.

        Args:
            section: Section object with path or name attribute, or None

        Returns:
            SectionSnapshot if found, NO_SECTION sentinel otherwise
        """
        from bengal.snapshots.types import NO_SECTION, SectionSnapshot

        if section is None:
            return NO_SECTION

        # Already a SectionSnapshot - return as-is
        if isinstance(section, SectionSnapshot):
            return section

        # No snapshot available - return sentinel
        if self.snapshot is None:
            return NO_SECTION

        # Get or build cached lookup maps
        section_maps = self.get_cached(
            "section_snapshot_maps",
            lambda: self._build_section_maps(),
        )

        # Try path lookup first (more specific)
        section_path = getattr(section, "path", None)
        if section_path and section_path in section_maps["by_path"]:
            return section_maps["by_path"][section_path]

        # Fall back to name lookup
        section_name = getattr(section, "name", "")
        if section_name and section_name in section_maps["by_name"]:
            return section_maps["by_name"][section_name]

        return NO_SECTION

    def _build_section_maps(self) -> dict[str, dict[Any, Any]]:
        """Build section lookup maps from snapshot (called once per build)."""
        by_path: dict[Any, Any] = {}
        by_name: dict[str, Any] = {}

        if self.snapshot:
            for sec_snap in self.snapshot.sections:
                if sec_snap.path:
                    by_path[sec_snap.path] = sec_snap
                if sec_snap.name:
                    by_name[sec_snap.name] = sec_snap

        return {"by_path": by_path, "by_name": by_name}

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
    # Accumulated Asset Dependencies (Inline Asset Extraction)
    # =========================================================================
    # These methods enable asset dependencies to be accumulated during rendering
    # instead of being extracted in a separate phase, eliminating double iteration
    # and saving ~5-6s on large sites.
    # See: changelog.md (Inline Asset Extraction)

    def accumulate_page_assets(self, source_path: Path, assets: set[str]) -> None:
        """
        Accumulate asset dependencies during rendering (thread-safe).

        Call this during rendering phase to store asset deps for later
        persistence. Eliminates redundant iteration in phase_track_assets.

        Args:
            source_path: Page source path (key for asset map)
            assets: Set of asset URLs/paths referenced by the page
        """
        with self._accumulated_assets_lock:
            self._accumulated_assets.append((source_path, assets))

    def get_accumulated_assets(self) -> list[tuple[Path, set[str]]]:
        """
        Get accumulated asset dependencies for persistence.

        Returns a copy to avoid thread safety issues when iterating.
        """
        with self._accumulated_assets_lock:
            return list(self._accumulated_assets)

    @property
    def has_accumulated_assets(self) -> bool:
        """Check if asset dependencies were accumulated during render."""
        with self._accumulated_assets_lock:
            return len(self._accumulated_assets) > 0

    @property
    def accumulated_asset_count(self) -> int:
        """Get count of pages with accumulated assets."""
        with self._accumulated_assets_lock:
            return len(self._accumulated_assets)

    def clear_accumulated_assets(self) -> None:
        """Clear accumulated asset data to free memory."""
        with self._accumulated_assets_lock:
            self._accumulated_assets.clear()

    # =========================================================================
    # Unified Page Data Accumulation (JSON + Index)
    # =========================================================================
    # These methods enable unified page data to be accumulated during rendering
    # for consumption by multiple post-processing generators (PageJSONGenerator,
    # SiteIndexGenerator). Eliminates redundant computation and double iteration.
    # See: plan/drafted/rfc-unified-page-data-accumulation.md

    def accumulate_page_data(self, data: AccumulatedPageData) -> None:
        """
        Accumulate unified page data during rendering (thread-safe).

        Called once per page during render phase. Data is consumed by
        multiple post-processing generators.

        Args:
            data: Unified page data containing all fields needed by consumers

        Example:
            # During rendering phase
            data = AccumulatedPageData(
                source_path=page.source_path,
                url=get_page_url(page, site),
                uri=get_page_relative_url(page, site),
                ...
            )
            build_context.accumulate_page_data(data)
        """
        with self._accumulated_page_data_lock:
            self._accumulated_page_data.append(data)
            self._accumulated_page_index[data.source_path] = data

    def get_accumulated_page_data(self) -> list[AccumulatedPageData]:
        """
        Get accumulated page data for post-processing.

        Returns a copy to avoid thread safety issues when iterating.

        Returns:
            List of AccumulatedPageData for all rendered pages

        Example:
            # In post-processing phase
            accumulated = build_context.get_accumulated_page_data()
            for data in accumulated:
                process_page_data(data)
        """
        with self._accumulated_page_data_lock:
            return list(self._accumulated_page_data)

    def get_accumulated_for_page(self, source_path: Path) -> AccumulatedPageData | None:
        """
        Get accumulated data for a specific page (O(1) lookup).

        Used by SiteIndexGenerator in hybrid mode during incremental builds.
        Returns None if the page was not rendered (not in accumulated data).

        Args:
            source_path: Path to source file

        Returns:
            AccumulatedPageData for the page, or None if not found

        Example:
            # In SiteIndexGenerator hybrid mode
            for page in all_pages:
                if acc_data := ctx.get_accumulated_for_page(page.source_path):
                    summary = accumulated_to_summary(acc_data)
                else:
                    summary = page_to_summary(page)  # Fallback
        """
        with self._accumulated_page_data_lock:
            return self._accumulated_page_index.get(source_path)

    @property
    def has_accumulated_page_data(self) -> bool:
        """
        Check if page data was accumulated during render.

        Post-processing can use this to decide whether to use accumulated
        data or fall back to computing from pages.

        Returns:
            True if accumulated page data exists
        """
        with self._accumulated_page_data_lock:
            return len(self._accumulated_page_data) > 0

    @property
    def accumulated_page_count(self) -> int:
        """
        Get count of accumulated pages (for hybrid mode detection).

        Compare this to total page count to determine if full or hybrid
        mode should be used in post-processing.

        Returns:
            Number of pages with accumulated data
        """
        with self._accumulated_page_data_lock:
            return len(self._accumulated_page_data)

    def clear_accumulated_page_data(self) -> None:
        """
        Clear accumulated page data to free memory.

        Call this after post-processing phase completes to release memory
        used by accumulated page data.
        """
        with self._accumulated_page_data_lock:
            self._accumulated_page_data.clear()
            self._accumulated_page_index.clear()
