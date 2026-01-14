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
from bengal.protocols.core import (
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
from bengal.protocols.analysis import (
    KnowledgeGraphProtocol,
)

__all__ = [
    # Build
    "BuildPhase",
    "PhaseStats",
    "PhaseTiming",
    "BuildContextDict",
    "BuildOptionsDict",
    "RenderContext",
    "RenderResult",
    "BuildStateProtocol",
    # Core
    "PageLike",
    "SectionLike",
    "SiteLike",
    "NavigableSection",
    "QueryableSection",
    # Rendering - Template
    "TemplateEnvironment",
    "EngineCapability",
    "TemplateRenderer",
    "TemplateIntrospector",
    "TemplateValidator",
    "TemplateEngine",
    "TemplateEngineProtocol",  # Backwards compatibility
    # Rendering - Highlighting
    "HighlightService",
    "HighlightBackend",  # Backwards compatibility
    # Rendering - Roles and Directives
    "RoleHandler",
    "DirectiveHandler",
    # Infrastructure
    "ProgressReporter",
    "Cacheable",
    "OutputCollector",
    "ContentSourceProtocol",
    "OutputTarget",
    # Analysis
    "KnowledgeGraphProtocol",
]
