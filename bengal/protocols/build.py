"""
Build-related protocols and shared types.

This module contains shared types for build orchestration that are used across
multiple packages (errors, orchestration, core). By consolidating these types
here, we reduce coupling between packages.

Types:
    BuildPhase: Enum of build pipeline phases
    PhaseStats: Statistics for a single build phase
    PhaseTiming: Timing record for a build phase
    RenderResult: Result of rendering a single page
    RenderContext: Context passed to template rendering
    BuildContextDict: Dict representation of build context
    BuildOptionsDict: Build options for serialization
    BuildStateProtocol: Protocol for build state access

Migration:
    Types were moved from:
    - bengal.errors.context.BuildPhase
    - bengal.orchestration.types.PhaseStats
    - bengal.orchestration.types.PhaseTiming
    - bengal.orchestration.types.RenderResult
    - bengal.orchestration.types.RenderContext
    - bengal.orchestration.types.BuildContextDict
    - bengal.orchestration.types.BuildOptionsDict

"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Literal, Protocol, TypedDict, runtime_checkable

if TYPE_CHECKING:
    pass


class BuildPhase(Enum):
    """
    Build phase where an error occurred.

    Helps narrow down which part of the codebase to investigate.
    Each phase maps to specific Bengal modules for targeted debugging.

    Phases follow the Bengal build pipeline order:

    1. **INITIALIZATION** - Config loading, CLI parsing
    2. **DISCOVERY** - Content and section discovery
    3. **PARSING** - Frontmatter and markdown parsing
    4. **RENDERING** - Template rendering
    5. **POSTPROCESSING** - Sitemap, RSS, search index
    6. **ASSET_PROCESSING** - Static asset copying/processing
    7. **CACHE** - Cache read/write operations
    8. **SERVER** - Dev server operations
    9. **OUTPUT** - Final output writing
    10. **ANALYSIS** - Knowledge graph and analysis operations

    Example:
        >>> phase = BuildPhase.RENDERING
        >>> phase.primary_modules
        ['bengal/rendering/', 'bengal/orchestration/render.py']

    """

    INITIALIZATION = "initialization"
    DISCOVERY = "discovery"
    PARSING = "parsing"
    RENDERING = "rendering"
    POSTPROCESSING = "postprocessing"
    ASSET_PROCESSING = "asset_processing"
    CACHE = "cache"
    SERVER = "server"
    OUTPUT = "output"
    ANALYSIS = "analysis"

    @property
    def primary_modules(self) -> list[str]:
        """
        Primary Bengal modules to investigate for errors in this phase.

        Returns:
            List of module paths relative to Bengal package root.
        """
        module_map = {
            BuildPhase.INITIALIZATION: ["bengal/config/", "bengal/cli/"],
            BuildPhase.DISCOVERY: ["bengal/content/discovery/", "bengal/content/sources/"],
            BuildPhase.PARSING: ["bengal/parsing/", "bengal/core/page/"],
            BuildPhase.RENDERING: ["bengal/rendering/", "bengal/orchestration/render.py"],
            BuildPhase.POSTPROCESSING: ["bengal/postprocess/"],
            BuildPhase.ASSET_PROCESSING: ["bengal/assets/", "bengal/orchestration/asset.py"],
            BuildPhase.CACHE: ["bengal/cache/"],
            BuildPhase.SERVER: ["bengal/server/"],
            BuildPhase.OUTPUT: ["bengal/output/"],
            BuildPhase.ANALYSIS: ["bengal/analysis/"],
        }
        return module_map.get(self, [])


# =============================================================================
# Phase Statistics (dict form for JSON serialization)
# =============================================================================


class PhaseStats(TypedDict, total=False):
    """Statistics for a single build phase."""

    name: str
    duration_ms: float
    items_processed: int
    errors: int
    warnings: int


class PhaseTiming(TypedDict):
    """Timing record for a build phase."""

    phase: str
    start_ms: float
    end_ms: float
    duration_ms: float


# =============================================================================
# Build Context Types
# =============================================================================


class BuildContextDict(TypedDict, total=False):
    """Dict representation of build context for serialization."""

    parallel: bool
    incremental: bool
    strict_mode: bool
    verbose: bool
    quiet: bool
    profile: str | None
    changed_sources: list[str]
    nav_changed_sources: list[str]
    structural_changed: bool


class BuildOptionsDict(TypedDict, total=False):
    """Dict form of build options for serialization."""

    parallel: bool
    incremental: bool
    verbose: bool
    quiet: bool
    strict: bool
    full_output: bool
    profile_templates: bool
    memory_optimized: bool
    profile: Literal["writer", "developer", "operator", "custom"] | None


# =============================================================================
# Render Context Types
# =============================================================================


class RenderContext(TypedDict, total=False):
    """Context passed to template rendering."""

    page: object  # Page instance
    site: object  # Site instance
    section: object  # Section instance
    baseurl: str
    now: str
    build_date: str
    is_production: bool


class RenderResult(TypedDict, total=False):
    """Result of rendering a single page."""

    page_path: str
    output_path: str
    success: bool
    duration_ms: float
    from_cache: bool
    error: str | None


# =============================================================================
# Build State Protocol
# =============================================================================


@runtime_checkable
class BuildStateProtocol(Protocol):
    """Protocol for build state access."""

    @property
    def phase(self) -> BuildPhase:
        """Current build phase."""
        ...

    @property
    def is_incremental(self) -> bool:
        """Whether this is an incremental build."""
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Build context
    "BuildContextDict",
    "BuildOptionsDict",
    # Build phase enum
    "BuildPhase",
    # Protocols
    "BuildStateProtocol",
    # Phase stats
    "PhaseStats",
    "PhaseTiming",
    # Render
    "RenderContext",
    "RenderResult",
]
