# RFC: Mixin Composition for Large Classes

**Status**: Draft  
**Created**: 2025-12-23  
**Author**: AI Assistant  
**Priority**: P2 (Medium)  
**Scope**: Core dataclasses with many methods  
**Estimated Effort**: ~88 hours (includes 8h standardization + 80h new mixins)  
**Related**: [rfc-modularize-large-files.md](./rfc-modularize-large-files.md)

---

## Summary

Several core classes have accumulated many methods (40+) that handle distinct concerns. This RFC proposes using the **mixin composition pattern** (already proven with `Page` and `Site`) to split these classes into focused, testable components while preserving backward compatibility.

---

## Relationship to Modularization RFC

This RFC is **complementary** to `rfc-modularize-large-files.md`:

| RFC | Focus | Example |
|-----|-------|---------|
| Modularize Large Files | *Where* code lives (file/package structure) | Split `section.py` into `section/` package |
| **Mixin Composition** | *How* classes are composed (behavior grouping) | Split `Section` into `SectionHierarchyMixin` + `SectionQueryMixin` |

Both RFCs can be implemented together or independently. This RFC provides the **class architecture** that the modularization RFC's package structure would contain.

---

## Problem Statement

### Classes with Too Many Responsibilities

| Class | File | Methods | Properties | Total | Issue |
|-------|------|---------|------------|-------|-------|
| `Section` | `core/section.py` | 23 | 24 | **47** | Navigation, queries, sorting, ergonomics bundled |
| `KnowledgeGraph` | `analysis/knowledge_graph.py` | 26 | 0 | **26** | Connectivity, PageRank, communities, paths mixed |
| `AutoFixer` | `health/autofix.py` | 15 | 0 | **15** | Different fix strategies interleaved |
| `HealthReport` | `health/report.py` | 18 | 11 | **29** | Aggregation and formatting mixed |

### Symptoms

1. **Hard to test in isolation** - Testing one behavior requires instantiating the entire class
2. **Unclear boundaries** - New methods get added to the "nearest" class, growing it further
3. **Documentation sprawl** - Class docstrings become encyclopedic
4. **IDE noise** - Autocomplete shows 40+ methods when you need 3

### Prior Art: Successful Mixins

The codebase already has excellent mixin implementations:

**`Page` class** (11 focused mixins):
```
bengal/core/page/
├── __init__.py           # Page dataclass + mixin composition
├── metadata.py           # PageMetadataMixin (title, description, dates)
├── navigation.py         # PageNavigationMixin (prev/next, breadcrumbs)
├── computed.py           # PageComputedMixin (reading_time, word_count)
├── relationships.py      # PageRelationshipsMixin (related, translations)
├── operations.py         # PageOperationsMixin (render, invalidate)
└── content.py            # PageContentMixin (toc, excerpts)
```

**`Site` class** (7 mixins):
```
bengal/core/site/
├── core.py               # Site dataclass + mixin composition
├── properties.py         # SitePropertiesMixin
├── page_caches.py        # PageCachesMixin
├── factories.py          # SiteFactoriesMixin
├── discovery.py          # ContentDiscoveryMixin
├── theme.py              # ThemeIntegrationMixin
├── data.py               # DataLoadingMixin
└── section_registry.py   # SectionRegistryMixin
```

These patterns are well-tested, maintain backward compatibility, and improve code organization.

---

## Proposed Solution

### Principle: Group by Concern, Not by Data

Mixins should group **behaviors that change together**:
- ✅ "All version-aware navigation methods" → `SectionNavigationMixin`
- ❌ "All methods that use `self.pages`" → Too broad, changes for different reasons

### 1. Section Mixins

**Target**: `bengal/core/section.py` (1,170 lines, 47 methods)

**Proposed Structure**:
```
bengal/core/section/
├── __init__.py              # Section dataclass + mixin composition (~80 lines)
├── section_core.py          # Core dataclass fields only
├── hierarchy.py             # SectionHierarchyMixin (~150 lines)
├── navigation.py            # SectionNavigationMixin (~180 lines)
├── queries.py               # SectionQueryMixin (~150 lines)
├── ergonomics.py            # SectionErgonomicsMixin (~200 lines)
└── utils.py                 # Module-level helpers (resolve_page_section_path)
```

#### SectionHierarchyMixin

Tree traversal and parent-child relationships.

```python
class SectionHierarchyMixin:
    """Tree structure traversal and relationships."""

    # Properties
    @property
    def hierarchy(self) -> list[str]: ...

    @property
    def depth(self) -> int: ...

    @property
    def root(self) -> Section: ...

    @cached_property
    def sorted_subsections(self) -> list[Section]: ...

    # Methods
    def add_subsection(self, section: Section) -> None: ...

    def walk(self) -> list[Section]: ...

    # Identity
    def __hash__(self) -> int: ...
    def __eq__(self, other: Any) -> bool: ...
    def __repr__(self) -> str: ...
```

#### SectionNavigationMixin

URLs, hrefs, and version-aware filtering.

```python
class SectionNavigationMixin:
    """URL generation and version-aware navigation."""

    # URL properties
    @cached_property
    def href(self) -> str: ...

    @cached_property
    def _path(self) -> str: ...

    @property
    def absolute_href(self) -> str: ...

    @cached_property
    def subsection_index_urls(self) -> set[str]: ...

    @cached_property
    def has_nav_children(self) -> bool: ...

    # Version-aware methods
    def pages_for_version(self, version_id: str | None) -> list[Page]: ...

    def subsections_for_version(self, version_id: str | None) -> list[Section]: ...

    def has_content_for_version(self, version_id: str | None) -> bool: ...

    # Internal
    def _apply_version_path_transform(self, url: str) -> str: ...
```

#### SectionQueryMixin

Page retrieval and collection operations.

```python
class SectionQueryMixin:
    """Page collection and retrieval."""

    # Properties
    @property
    def regular_pages(self) -> list[Page]: ...

    @property
    def sections(self) -> list[Section]: ...

    @cached_property
    def sorted_pages(self) -> list[Page]: ...

    @property
    def regular_pages_recursive(self) -> list[Page]: ...

    # Methods
    def add_page(self, page: Page) -> None: ...

    def sort_children_by_weight(self) -> None: ...

    def get_all_pages(self, recursive: bool = True) -> list[Page]: ...

    def needs_auto_index(self) -> bool: ...

    def has_index(self) -> bool: ...
```

#### SectionErgonomicsMixin

Convenience methods for theme developers (blog-style queries).

```python
class SectionErgonomicsMixin:
    """Theme developer helpers for common patterns."""

    # Properties
    @cached_property
    def content_pages(self) -> list[Page]: ...

    @cached_property
    def post_count(self) -> int: ...

    @cached_property
    def post_count_recursive(self) -> int: ...

    @cached_property
    def word_count(self) -> int: ...

    @cached_property
    def total_reading_time(self) -> int: ...

    # Methods
    def recent_pages(self, limit: int = 10) -> list[Page]: ...

    def pages_with_tag(self, tag: str) -> list[Page]: ...

    def featured_posts(self, limit: int = 5) -> list[Page]: ...

    def aggregate_content(self) -> dict[str, Any]: ...

    def apply_section_template(self, template_engine: Any) -> str: ...
```

#### Final Composition

```python
# bengal/core/section/__init__.py
@dataclass
class Section(
    SectionHierarchyMixin,
    SectionNavigationMixin,
    SectionQueryMixin,
    SectionErgonomicsMixin,
):
    """Content directory with pages and subsections."""

    name: str = "root"
    path: Path | None = field(default_factory=lambda: Path("."))
    pages: list[Page] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    index_page: Page | None = None
    parent: Section | None = None
    _virtual: bool = False
    _relative_url_override: str | None = field(default=None, repr=False)
    _site: Any | None = field(default=None, repr=False)
    _diagnostics_sink: DiagnosticsSink | None = field(default=None, repr=False)
```

---

### 2. KnowledgeGraph Mixins

**Target**: `bengal/analysis/knowledge_graph.py` (946 lines, 26 methods)

The class already delegates to helper classes (`GraphBuilder`, `MetricsCalculator`, `GraphAnalyzer`, `GraphReporter`), but the main class still exposes 26 methods. Split the **access patterns**:

**Proposed Structure**:
```
bengal/analysis/knowledge_graph/
├── __init__.py              # KnowledgeGraph + mixin composition (~120 lines)
├── graph_core.py            # Core init/build (~80 lines)
├── connectivity.py          # ConnectivityMixin (~100 lines)
├── pagerank.py              # PageRankMixin (~80 lines)
├── community.py             # CommunityMixin (~60 lines)
├── paths.py                 # PathAnalysisMixin (~60 lines)
└── suggestions.py           # LinkSuggestionMixin (~50 lines)
```

#### ConnectivityMixin

```python
class ConnectivityMixin:
    """Basic graph connectivity queries."""

    def get_connectivity(self, page: Page) -> PageConnectivity: ...
    def get_hubs(self, threshold: int | None = None) -> list[Page]: ...
    def get_leaves(self, threshold: int | None = None) -> list[Page]: ...
    def get_orphans(self) -> list[Page]: ...
    def get_connectivity_report(self, ...) -> ConnectivityReport: ...
    def get_page_link_metrics(self, page: Page) -> LinkMetrics: ...
    def get_connectivity_score(self, page: Page) -> int: ...
```

#### PageRankMixin

```python
class PageRankMixin:
    """PageRank computation and queries."""

    def compute_pagerank(self, damping: float = 0.85, ...) -> PageRankResults: ...
    def compute_personalized_pagerank(self, ...) -> PageRankResults: ...
    def get_top_pages_by_pagerank(self, limit: int = 20) -> list[tuple[Page, float]]: ...
    def get_pagerank_score(self, page: Page) -> float: ...
```

#### CommunityMixin

```python
class CommunityMixin:
    """Community detection algorithms."""

    def detect_communities(self, algorithm: str = "louvain", ...) -> CommunityDetectionResults: ...
    def get_community_for_page(self, page: Page) -> int | None: ...
```

#### PathAnalysisMixin

```python
class PathAnalysisMixin:
    """Path analysis and centrality metrics."""

    def analyze_paths(self, sample_size: int = 100, ...) -> PathAnalysisResults: ...
    def get_betweenness_centrality(self, page: Page) -> float: ...
    def get_closeness_centrality(self, page: Page) -> float: ...
```

#### LinkSuggestionMixin

```python
class LinkSuggestionMixin:
    """Link suggestion algorithms."""

    def suggest_links(self, max_suggestions: int = 50, ...) -> LinkSuggestionResults: ...
    def get_suggestions_for_page(self, page: Page, limit: int = 5) -> list[...]: ...
```

---

### 3. AutoFixer Strategy Pattern

**Target**: `bengal/health/autofix.py` (940 lines, 15 methods)

Rather than mixins, `AutoFixer` benefits from a **strategy pattern** because fix types are **independent and extensible**:

**Proposed Structure**:
```
bengal/health/autofix/
├── __init__.py              # AutoFixer coordinator (~100 lines)
├── base.py                  # FixAction, FixSafety, FixStrategy protocol (~80 lines)
├── directive_fixer.py       # DirectiveFixStrategy (~300 lines)
├── link_fixer.py            # LinkFixStrategy (future)
└── frontmatter_fixer.py     # FrontmatterFixStrategy (future)
```

#### Protocol Definition

```python
# base.py
from typing import Protocol

class FixStrategy(Protocol):
    """Protocol for fix strategy implementations."""

    def suggest_fixes(self, report: ValidatorReport) -> list[FixAction]:
        """Analyze report and suggest fixes."""
        ...

    def can_handle(self, result: CheckResult) -> bool:
        """Check if this strategy handles this result type."""
        ...
```

#### Coordinator

```python
# __init__.py
class AutoFixer:
    """Coordinates fix strategies."""

    def __init__(self, report: HealthReport, site_root: Path):
        self.report = report
        self.site_root = site_root
        self.strategies: list[FixStrategy] = [
            DirectiveFixStrategy(site_root),
            # Future: LinkFixStrategy(site_root),
        ]

    def suggest_fixes(self) -> list[FixAction]:
        """Collect fixes from all strategies."""
        fixes = []
        for strategy in self.strategies:
            fixes.extend(strategy.suggest_fixes(self.report))
        return fixes

    def apply_fixes(self, fixes: list[FixAction] | None = None) -> dict[str, Any]:
        """Apply fixes and return results."""
        ...
```

---

### 4. BuildOrchestrator Setup Mixins

**Target**: `bengal/orchestration/build/__init__.py` (781 lines, 443-line `build()` method)

The `build()` method has ~120 lines of setup before phases start. Extract into mixins:

**Proposed Structure**:
```
bengal/orchestration/build/
├── __init__.py              # BuildOrchestrator + mixin composition
├── orchestrator.py          # Core build loop (~200 lines)
├── setup.py                 # BuildSetupMixin (~100 lines)
├── incremental_init.py      # IncrementalResolutionMixin (~80 lines)
├── initialization.py        # ✅ Already exists (phase functions)
├── content.py               # ✅ Already exists
├── rendering.py             # ✅ Already exists
└── finalization.py          # ✅ Already exists
```

#### BuildSetupMixin

```python
class BuildSetupMixin:
    """Build initialization and options extraction."""

    def _extract_options(self, options: BuildOptions) -> dict[str, Any]:
        """Extract and normalize build options."""
        ...

    def _init_cli_output(self, profile, quiet, verbose) -> CLIOutput:
        """Initialize CLI output system."""
        ...

    def _init_performance_collector(self, profile_config) -> PerformanceCollector | None:
        """Initialize performance collection if enabled."""
        ...

    def _create_phase_callbacks(self, on_start, on_complete) -> tuple[Callable, Callable]:
        """Create safe phase notification callbacks."""
        ...
```

#### IncrementalResolutionMixin

```python
class IncrementalResolutionMixin:
    """Auto-detect incremental mode and cache initialization."""

    def _resolve_incremental_mode(
        self,
        incremental: bool | None,
        cache: BuildCache
    ) -> tuple[bool, str | None]:
        """Resolve auto incremental mode. Returns (is_incremental, reason)."""
        ...

    def _initialize_cache_and_tracker(self) -> tuple[BuildCache, CascadeTracker]:
        """Initialize build cache and cascade tracker."""
        ...
```

---

### 5. HealthReport Mixins

**Target**: `bengal/health/report.py` (900 lines, 29 methods)

Split aggregation from formatting:

**Proposed Structure**:
```
bengal/health/report/
├── __init__.py              # HealthReport + mixin composition
├── check_result.py          # CheckResult dataclass (already clean)
├── validator_report.py      # ValidatorReport + ValidatorReportStats
├── aggregation.py           # ReportAggregationMixin
└── formatting.py            # ReportFormattingMixin
```

#### ReportAggregationMixin

```python
class ReportAggregationMixin:
    """Count aggregation across validators."""

    @property
    def total_passed(self) -> int: ...

    @property
    def total_warnings(self) -> int: ...

    @property
    def total_errors(self) -> int: ...

    @property
    def total_suggestions(self) -> int: ...

    @property
    def total_checks(self) -> int: ...

    @property
    def has_problems(self) -> bool: ...

    @property
    def has_errors(self) -> bool: ...

    @property
    def cache_hit_rate(self) -> float: ...

    @property
    def skip_rate(self) -> float: ...
```

#### ReportFormattingMixin

```python
class ReportFormattingMixin:
    """Output formatting helpers."""

    @property
    def status_emoji(self) -> str: ...

    def format_summary(self) -> str: ...

    def to_log_context(self) -> dict[str, int | float | str]: ...
```

---

## Implementation Plan

### Phase 0: Standardize Existing Mixins (High Priority)

**Week 0** (~8 hours) - Do this first to establish patterns for new mixins.

1. **Define Protocols** (~2 hours)
   - Create `bengal/core/page/protocols.py` with `PageMixinHost`
   - Create `bengal/core/site/protocols.py` with `SiteMixinHost`
   - Add Protocol type hints to existing mixins (optional, for validation)

2. **Standardize Caching in Page Mixins** (~3 hours)
   - Audit all caching in `PageMetadataMixin`, `PageContentMixin`, etc.
   - Convert to tiered caching strategy (see Appendix A)
   - Add `invalidate_caches()` method to Page class

3. **Split `PageMetadataMixin`** (~3 hours)
   - Extract `PageVisibilityMixin` (lines 510-687)
   - Update Page class composition
   - Verify tests pass

### Phase 1: Section Mixins (High Priority)

**Week 1-2** (~40 hours)

1. Create `bengal/core/section/` package structure
2. Extract `SectionHierarchyMixin` with tests
3. Extract `SectionNavigationMixin` with tests
4. Extract `SectionQueryMixin` with tests
5. Extract `SectionErgonomicsMixin` with tests
6. Update imports across codebase
7. Verify all existing tests pass

### Phase 2: KnowledgeGraph Mixins (Medium Priority)

**Week 3** (~20 hours)

1. Create `bengal/analysis/knowledge_graph/` package structure
2. Extract connectivity, pagerank, community, paths, suggestions mixins
3. Update imports
4. Verify tests

### Phase 3: AutoFixer Strategy (Medium Priority)

**Week 4** (~15 hours)

1. Create `bengal/health/autofix/` package structure
2. Define `FixStrategy` protocol
3. Extract `DirectiveFixStrategy`
4. Refactor coordinator

### Phase 4: BuildOrchestrator + HealthReport (Low Priority)

**Opportunistic** (~5-10 hours)

1. Extract setup mixins as build() is touched
2. Extract report mixins as report.py is touched

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking changes to public API | Low | High | Re-export all symbols from `__init__.py` |
| Mixin method resolution order issues | Low | Medium | Follow existing `Page`/`Site` patterns exactly |
| Test coverage gaps | Medium | Medium | Run full test suite after each mixin extraction |
| Import cycle introduction | Low | High | Use TYPE_CHECKING guards consistently |
| Cache invalidation bugs | Medium | Medium | Add `invalidate_caches()` methods; test hot reload |
| Protocol over-specification | Low | Low | Keep Protocols minimal; only required attributes |

---

## Success Criteria

1. **Section class**: Split into 4 mixins, core file < 100 lines
2. **KnowledgeGraph class**: Split into 5 mixins, core file < 150 lines
3. **AutoFixer**: Converted to strategy pattern, easy to add new fix types
4. **All existing tests pass** without modification (backward compatibility)
5. **No new import cycles** introduced
6. **Existing mixins standardized**: Consistent caching patterns across Page/Site/BuildCache mixins
7. **Protocols defined**: `PageMixinHost` and `SiteMixinHost` protocols in place
8. **Large mixins split**: `PageMetadataMixin` split to extract `PageVisibilityMixin`

---

## Appendix A: Existing Mixin Audit & Standardization

An audit of existing mixins (`Page`, `Site`, `BuildCache`) found them to be **high quality (B+/A-)** but identified opportunities for standardization.

### What Existing Mixins Do Well ✅

1. **Excellent documentation** - Thorough docstrings with template examples
2. **Clear attribute declarations** - Each mixin declares expected host attributes
3. **Proper TYPE_CHECKING guards** - Consistent use of `from __future__ import annotations`
4. **Single responsibility** - Each mixin focuses on one concern
5. **Smart caching** - Lazy evaluation with proper invalidation

### Areas to Standardize ⚠️

#### 1. Inconsistent Caching Patterns

**Current state**: Mixins use multiple caching approaches:
- Manual `__dict__` assignment (`self.__dict__["_cache"] = value`)
- Private attribute caching (`self._cache = value`)
- `@cached_property` decorator (less common)

**Standard**: Use tiered caching based on invalidation needs:

```python
# Tier 1: Immutable computed values → @cached_property
@cached_property
def depth(self) -> int:
    """Depth never changes after construction."""
    return self._compute_depth()

# Tier 2: Session-stable values → private attribute with None sentinel
@property
def href(self) -> str:
    """URL is stable within a build but may change on config reload."""
    if self._href_cache is not None:
        return self._href_cache
    self._href_cache = self._compute_href()
    return self._href_cache

# Tier 3: Conditionally-cached values → __dict__ with explicit check
@property
def toc_items(self) -> list[dict]:
    """Only cache non-empty results (toc may be set later during parsing)."""
    cached = self.__dict__.get("_toc_items_cache")
    if cached is not None:
        return cached
    items = self._extract_toc()
    if items:  # Only cache if non-empty
        self.__dict__["_toc_items_cache"] = items
    return items
```

#### 2. Missing Protocol Definitions

**Current state**: Mixins declare expected attributes as class-level type hints, but no formal Protocol enforces the contract.

**Standard**: Define a Protocol for complex mixins (optional but recommended for core mixins):

```python
# bengal/core/page/protocols.py
from typing import Protocol, Any
from pathlib import Path

class PageMixinHost(Protocol):
    """Protocol defining attributes required by Page mixins."""

    metadata: dict[str, Any]
    source_path: Path
    output_path: Path | None
    content: str
    toc: str | None
    _site: Any  # Site | None (avoid import)

    # Cache attributes (initialized by dataclass __post_init__)
    _toc_items_cache: list[dict[str, Any]] | None
    _html_cache: str | None
```

This makes mixin contracts machine-checkable and improves IDE support.

#### 3. Large Mixins Need Splitting

**Guideline**: Split mixins exceeding ~400 lines or containing distinct sub-concerns.

**Example**: `PageMetadataMixin` (640 lines) contains:
- Core metadata (title, date, slug) - ~150 lines
- URL generation (href, _path) - ~100 lines
- Component Model (type, variant, props) - ~80 lines
- Visibility system (hidden, in_listings, in_sitemap) - ~180 lines

**Recommendation**: Extract `PageVisibilityMixin` when touching this code.

---

## Appendix B: Mixin Pattern Guidelines

### Do

- Group methods that **change together** for the same reason
- Use `TYPE_CHECKING` for circular import prevention
- Keep mixin files < 200 lines (split if >400)
- Document which attributes the mixin expects from the host class
- Re-export everything from package `__init__.py`
- **Use consistent caching patterns** (see Appendix A)
- **Define Protocols for complex mixin contracts** (optional)
- **Include template usage examples in docstrings**

### Don't

- Create mixins with only 1-2 methods (not worth the indirection)
- Mix data fields into mixins (keep fields in the dataclass)
- Create deep mixin hierarchies (prefer flat composition)
- Break existing public APIs
- **Cache empty results that may be populated later**
- **Mix caching strategies within the same mixin**

### Template

```python
# bengal/core/section/hierarchy.py
"""
Section hierarchy mixin.

Provides tree traversal and parent-child relationship methods.

Required Host Attributes:
    - name: str
    - path: Path | None
    - parent: Section | None
    - subsections: list[Section]
    - metadata: dict[str, Any]

Cache Attributes (initialized by host __post_init__):
    - _depth_cache: int | None

Related Modules:
    - bengal.core.section: Section dataclass using this mixin
    - bengal.core.section.navigation: URL generation for sections

Example:
    >>> section = site.get_section("blog/2024")
    >>> section.depth
    2
    >>> section.root.name
    'content'
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path
    from bengal.core.section import Section


class SectionHierarchyMixin:
    """
    Tree structure traversal and relationships.

    This mixin handles:
    - Parent/child navigation (parent, root, subsections)
    - Depth calculation
    - Tree walking (walk, walk_pages)
    - Identity operations (__hash__, __eq__)
    """

    # =========================================================================
    # HOST CLASS ATTRIBUTES
    # =========================================================================
    # Type hints for attributes provided by the host dataclass.
    # These are NOT defined here - they're declared for type checking only.

    name: str
    path: Path | None
    parent: Section | None
    subsections: list[Section]
    metadata: dict[str, Any]

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @cached_property
    def depth(self) -> int:
        """
        Return nesting depth (0 for root).

        Uses @cached_property since depth is immutable after construction.

        Example:
            >>> site.root_section.depth
            0
            >>> site.get_section("blog/2024").depth
            2
        """
        count = 0
        current = self.parent
        while current is not None:
            count += 1
            current = current.parent
        return count

    @property
    def root(self) -> Section:
        """
        Get the root section of the tree.

        Returns:
            Root Section (may be self if this is root)
        """
        current: Section = self  # type: ignore[assignment]
        while current.parent is not None:
            current = current.parent
        return current

    @cached_property
    def sorted_subsections(self) -> list[Section]:
        """
        Subsections sorted by weight, then alphabetically.

        Uses @cached_property since sort order is stable within a build.
        """
        return sorted(
            self.subsections,
            key=lambda s: (s.metadata.get("weight", 0), s.name)
        )

    # =========================================================================
    # METHODS
    # =========================================================================

    def walk(self) -> list[Section]:
        """
        Walk all subsections recursively (depth-first).

        Returns:
            List of all descendant sections (not including self)
        """
        result: list[Section] = []
        for sub in self.subsections:
            result.append(sub)
            result.extend(sub.walk())
        return result

    # =========================================================================
    # IDENTITY
    # =========================================================================

    def __hash__(self) -> int:
        """Hash by path for set/dict membership."""
        return hash(self.path)

    def __eq__(self, other: Any) -> bool:
        """Equality by path."""
        if not isinstance(other, SectionHierarchyMixin):
            return NotImplemented
        return self.path == other.path
```

---

## Appendix C: Caching Decision Matrix

Use this matrix to choose the right caching strategy:

| Scenario | Strategy | Example |
|----------|----------|---------|
| Value never changes after init | `@cached_property` | `depth`, `hierarchy` |
| Value stable within build session | Private attr + None sentinel | `href`, `_path` |
| Value may be set later (lazy init) | `__dict__` + conditional cache | `toc_items` |
| Value depends on external state | No cache (recompute) | `is_changed()` |
| Value expensive + rarely accessed | `@cached_property` | `word_count` |
| Value cheap to compute | No cache | `is_home`, `kind` |

### Cache Invalidation

For session-stable caches, provide an invalidation method:

```python
def invalidate_caches(self) -> None:
    """Clear cached values (call on config reload)."""
    for attr in ("_href_cache", "_path_cache", "_sorted_pages_cache"):
        if attr in self.__dict__:
            del self.__dict__[attr]
    # Also clear @cached_property values
    for attr in ("sorted_subsections", "content_pages"):
        if attr in self.__dict__:
            del self.__dict__[attr]
```
