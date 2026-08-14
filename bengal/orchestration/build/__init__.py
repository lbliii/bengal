"""
Build orchestration for Bengal SSG.

Main coordinator that sequences the entire build pipeline, delegating to
specialized orchestrators for each phase. This is the primary entry point
for building a Bengal site.

Package Structure:
__init__.py (this file)
    BuildOrchestrator class - public coordinator
runner.py
    build() sequencing: plugin lifecycle and phase-group dispatch
session.py
    Per-build runtime state and CLI/cache/plugin setup
mid_flow.py
    Phases 1–snapshot (discovery, content, parsing)
output_flow.py
    Phases 13–16 (assets, render)
finalize_flow.py
    Phases 17–21 (postprocess, cache, health, finalize)
initialization.py
    Phases 1-5: fonts, discovery, cache, config, filtering
content.py
    Phases 6-11: sections, taxonomies, menus, related posts, indexes
rendering.py
    Phases 13-16: assets, render, update pages, track dependencies
finalization.py
    Phases 17-21: postprocess, cache save, stats, health, finalize
options.py
    BuildOptions dataclass for build configuration
results.py
    Result types for phase outputs

Build Phases:
The build executes 21 phases in sequence. Key phases include:
- Phase 2: Content discovery (pages, sections, assets)
- Phase 6: Section finalization (ensure indexes exist)
- Phase 7: Taxonomy collection and page generation
- Phase 9: Menu building
- Phase 13: Asset processing
- Phase 14: PageLike rendering (parallel or sequential)
- Phase 17: Post-processing (sitemap, RSS, output formats)
- Phase 20: Health checks and validation

Usage:
from bengal.orchestration.build import BuildOrchestrator, BuildOptions

    orchestrator = BuildOrchestrator(site)
    stats = orchestrator.build(BuildOptions(incremental=True))

See Also:
bengal.orchestration: All specialized orchestrators
bengal.core.site: Site data model
bengal.cache: Build caching infrastructure

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.orchestration.asset import AssetOrchestrator
from bengal.orchestration.content import ContentOrchestrator
from bengal.orchestration.menu import MenuOrchestrator
from bengal.orchestration.postprocess import PostprocessOrchestrator
from bengal.orchestration.render import RenderOrchestrator
from bengal.orchestration.section import SectionOrchestrator
from bengal.orchestration.stats import BuildStats
from bengal.orchestration.taxonomy import TaxonomyOrchestrator
from bengal.protocols.capabilities import HasErrors
from bengal.utils.observability.logger import get_logger

from .inputs import BuildInput as BuildInput  # noqa: TC001
from .options import BuildCompletionPolicy as BuildCompletionPolicy
from .options import BuildOptions as BuildOptions  # noqa: TC001

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site


def __getattr__(name: str) -> Any:
    """
    Lazily expose optional orchestration types without creating import cycles.

    Some tests and callers patch/inspect `bengal.orchestration.build.IncrementalOrchestrator`.
    We keep that surface stable while avoiding eager imports at module import time.

    """
    if name == "IncrementalOrchestrator":
        from bengal.orchestration.incremental import IncrementalOrchestrator

        return IncrementalOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class BuildOrchestrator:
    """
    Main build coordinator that orchestrates the entire build process.

    Delegates to specialized orchestrators for each phase:
        - ContentOrchestrator: Discovery and setup
        - TaxonomyOrchestrator: Taxonomies and dynamic pages
        - MenuOrchestrator: Navigation menus
        - RenderOrchestrator: PageLike rendering
        - AssetOrchestrator: Asset processing
        - PostprocessOrchestrator: Sitemap, RSS, validation
        - IncrementalOrchestrator: Change detection and caching

    Sequencing lives in `runner.py`; this class remains the public coordinator.

    """

    _provenance_filter: Any = None

    def __init__(self, site: Site):
        """
        Initialize build orchestrator.

        Args:
            site: Site instance to build
        """
        self.site = site
        self.stats = BuildStats()
        self.logger = get_logger(__name__)
        self.options: BuildOptions | None = None  # Set during build() call

        # Import directly to avoid self-import through __getattr__
        from bengal.orchestration.incremental import IncrementalOrchestrator

        # Initialize orchestrators
        self.content = ContentOrchestrator(site)
        self.sections = SectionOrchestrator(site)
        self.taxonomy = TaxonomyOrchestrator(site)
        self.menu = MenuOrchestrator(site)
        self.render = RenderOrchestrator(site)
        self.assets = AssetOrchestrator(site)
        self.postprocess = PostprocessOrchestrator(site)
        self.incremental = IncrementalOrchestrator(site)

    def build(
        self,
        options: BuildOptions | BuildInput,
    ) -> BuildStats:
        """
        Execute full build pipeline.

        Args:
            options: BuildOptions or BuildInput with all build configuration.
                BuildInput provides a complete serializable record for debugging.

        Returns:
            BuildStats object with build statistics

        Example:
            >>> from bengal.orchestration.build.options import BuildOptions
            >>> options = BuildOptions(strict=True)
            >>> stats = orchestrator.build(options)
        """
        from .runner import run_build

        return run_build(self, options)

    def _filter_sections_by_variant(self, sections: list[Any], variant: str) -> None:
        """Filter section pages by variant; invalidate cached properties."""
        for section in sections:
            section.pages = [p for p in section.pages if p.in_variant(variant)]
            section.__dict__.pop("regular_pages", None)
            section.__dict__.pop("sorted_pages", None)
            section.__dict__.pop("regular_pages_recursive", None)
            self._filter_sections_by_variant(section.subsections, variant)

    def _print_rendering_summary(self) -> None:
        """Print summary of rendered pages (quiet mode)."""
        from bengal.output import get_cli_output

        cli = get_cli_output()

        # Count page types in a single pass
        tag_pages = 0
        archive_pages = 0
        pagination_pages = 0
        for p in self.site.pages:
            meta = p.metadata
            if meta is not None and meta.get("_generated"):
                if p.output_path is not None and "tag" in p.output_path.parts:
                    tag_pages += 1
                if meta.get("template") == "archive.html":
                    archive_pages += 1
                if p.output_path is not None and "/page/" in str(p.output_path):
                    pagination_pages += 1
        regular_pages = len(self.site.regular_pages)

        cli.detail(f"Regular pages:    {regular_pages}", indent=1, icon="├─")
        if tag_pages:
            cli.detail(f"Tag pages:        {tag_pages}", indent=1, icon="├─")
        if archive_pages:
            cli.detail(f"Archive pages:    {archive_pages}", indent=1, icon="├─")
        if pagination_pages:
            cli.detail(f"Pagination:       {pagination_pages}", indent=1, icon="├─")
        cli.detail(f"Total:            {len(self.site.pages)} ✓", indent=1, icon="└─")

    def _finalize_error_session(self) -> None:
        """
        Record build errors in session for pattern detection and summary.

        Tracks orchestration errors in the error session to enable:
        - Build summaries including orchestration failures
        - Pattern detection for recurring build issues
        - Error aggregation across build phases
        """
        try:
            from bengal.errors import get_session, record_error

            session = get_session()

            # Record any errors collected during build phases
            if isinstance(self.stats, HasErrors) and self.stats.errors:
                for error in self.stats.errors:
                    if hasattr(error, "phase"):
                        record_error(
                            error,
                            file_path=f"build:{error.phase}",
                            build_phase=error.phase,
                        )
                    else:
                        record_error(error, file_path="build:unknown")

            # Log session summary if errors occurred
            summary = session.get_summary()
            if summary["total_errors"] > 0:
                logger.info(
                    "build_error_session_summary",
                    total_errors=summary["total_errors"],
                    by_phase=summary["errors_by_phase"],
                    recurring_patterns=summary["recurring_errors"],
                )
        except Exception as e:
            # Don't fail build on session tracking errors
            logger.debug(
                "error_session_finalize_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
