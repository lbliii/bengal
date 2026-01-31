"""
Canonical protocol definitions for Bengal.

All protocols should be imported from this module. This ensures a single
source of truth for interface contracts across the codebase.

Internal modules may define implementation-specific protocols, but
cross-module contracts belong here.

Organization:
- core: PageLike, SectionLike, SiteLike, NavigableSection, QueryableSection
- rendering: TemplateRenderer, TemplateIntrospector, TemplateEngine, HighlightService
- infrastructure: ProgressReporter, Cacheable, OutputCollector, ContentSourceProtocol

Thread Safety:
    All protocols are designed for use in multi-threaded contexts.
    Implementations should be thread-safe for concurrent builds.

Example:
        >>> from bengal.protocols import SectionLike, HighlightService
        >>>
        >>> def build_nav(section: SectionLike) -> list[dict]:
        ...     return [{"title": p.title, "href": p.href} for p in section.pages]

Migration:
    Old import paths emit deprecation warnings and re-export from here.
    Update imports to use bengal.protocols directly:

    # Old (deprecated)
    from bengal.core.section.protocols import SectionLike

    # New (preferred)
    from bengal.protocols import SectionLike

"""

from bengal.protocols.analysis import (
    KnowledgeGraphProtocol,
)
from bengal.protocols.build import (
    BuildContextDict,
    BuildOptionsDict,
    BuildPhase,
    BuildStateProtocol,
    PhaseStats,
    PhaseTiming,
    RenderContext,
    RenderResult,
)
from bengal.protocols.capabilities import (
    HasActionRebuild,
    HasClearTemplateCache,
    HasConfigChangedSignal,
    HasErrors,
    HasWalk,
    has_action_rebuild,
    has_clear_template_cache,
    has_config_changed_signal,
    has_errors,
    has_walk,
)
from bengal.protocols.core import (
    ConfigLike,
    NavigableSection,
    PageLike,
    QueryableSection,
    SectionLike,
    SiteLike,
)
from bengal.protocols.infrastructure import (
    Cacheable,
    ContentSourceProtocol,
    OutputCollector,
    OutputTarget,
    ProgressReporter,
)
from bengal.protocols.rendering import (
    DirectiveHandler,
    EngineCapability,
    HighlightBackend,
    HighlightService,
    RoleHandler,
    TemplateEngine,
    TemplateEngineProtocol,
    TemplateEnvironment,
    TemplateIntrospector,
    TemplateRenderer,
    TemplateValidator,
)
from bengal.protocols.stats import (
    BuildStatsProtocol,
)

__all__ = [
    "BuildContextDict",
    "BuildOptionsDict",
    # Build
    "BuildPhase",
    "BuildStateProtocol",
    # Stats
    "BuildStatsProtocol",
    "Cacheable",
    "ConfigLike",
    "ContentSourceProtocol",
    "DirectiveHandler",
    "EngineCapability",
    "HasActionRebuild",
    # Capabilities (TypeGuard protocols)
    "HasClearTemplateCache",
    "HasConfigChangedSignal",
    "HasErrors",
    "HasWalk",
    "HighlightBackend",  # Backwards compatibility
    # Rendering - Highlighting
    "HighlightService",
    # Analysis
    "KnowledgeGraphProtocol",
    "NavigableSection",
    "OutputCollector",
    "OutputTarget",
    # Core
    "PageLike",
    "PhaseStats",
    "PhaseTiming",
    # Infrastructure
    "ProgressReporter",
    "QueryableSection",
    "RenderContext",
    "RenderResult",
    # Rendering - Roles and Directives
    "RoleHandler",
    "SectionLike",
    "SiteLike",
    "TemplateEngine",
    "TemplateEngineProtocol",  # Backwards compatibility
    # Rendering - Template
    "TemplateEnvironment",
    "TemplateIntrospector",
    "TemplateRenderer",
    "TemplateValidator",
    "has_action_rebuild",
    "has_clear_template_cache",
    "has_config_changed_signal",
    "has_errors",
    "has_walk",
]
