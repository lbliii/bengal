# RFC: Large File Refactoring - Modularize Monolithic Classes

**Author**: AI Assistant  
**Date**: 2025-01-27  
**Status**: Draft (Validated)  
**Confidence**: 90% 🟢

---

## Executive Summary

**Context**: Three core modules have grown to 1,000+ lines with multiple responsibilities:
- `knowledge_graph.py`: 1,331 lines, 33 methods (graph building + basic analysis + reporting)
  - Note: Advanced analysis (PageRank, communities, paths) **already extracted** to 4 modules (1,399 lines)
- `output_formats.py`: 1,146 lines, 19 methods (4 different output formats in one class)
- `site.py`: 1,015 lines, 30 methods (data model + discovery + caching + validation)

**Question**: Should we refactor these large files into focused modules to improve maintainability, testability, and contributor experience?

**Answer**: **Yes** - Continue the modularization pattern already proven in `bengal/core/page/` and `bengal/analysis/`. Split remaining concerns into focused modules.

**Impact**:
- ✅ Reduced cognitive load (1,000+ line files → 200-400 line modules)
- ✅ Improved testability (can test individual concerns independently)
- ✅ Better maintainability (clear module boundaries)
- ✅ **Contributor-friendly codebase** (easier to find and modify code)
- ✅ Builds on existing successful patterns (Page package, analysis modules)
- ⚠️ Requires careful migration to maintain backward compatibility

**Confidence**: 90% (strong evidence, proven patterns in codebase, reduced scope for knowledge_graph.py)

---

## 0. Strategic Context

### Why This Matters for Bengal

Bengal is positioning as **the modern Python SSG**. For open source success, we need:

```
Adoption = (Ease of Getting Started × Visible Quality × Community) / Friction
```

**This refactoring directly impacts "Visible Quality" and "Community":**

1. **Contributor Velocity**: 1,000+ line files are contributor deterrents
   - New contributors open `knowledge_graph.py` → see 1,331 lines → feel overwhelmed
   - Clean, focused modules → contributors can find relevant code quickly

2. **Code Review Quality**: Smaller modules enable better reviews
   - Reviewers can understand changes in context
   - Easier to spot bugs and suggest improvements

3. **Long-term Maintainability**: Technical debt compounds
   - Current: Every feature adds to monolithic files
   - After: New features go in focused modules, easier to reason about

**Strategic recommendation**: Refactor incrementally, one module at a time, starting with `knowledge_graph.py` (highest impact, clearest boundaries).

> **Precedent**: Bengal has successfully applied this pattern before:
> - `bengal/core/page/` converted from single file to focused package (mixin pattern)
> - `bengal/analysis/` already has 4 modules extracted from `knowledge_graph.py` (1,399 lines total)

---

## 1. Problem Statement

### Current State

#### 1.1 `knowledge_graph.py` (1,331 lines)

**Location**: `bengal/analysis/knowledge_graph.py`

**Current State** (partially modularized):
- Graph building (in class) ✅
- Basic analysis (in class) - hubs, leaves, orphans, connectivity
- **Advanced analysis (ALREADY EXTRACTED)** - Delegates to separate modules:
  - `page_rank.py` (281 lines) - PageRankCalculator
  - `community_detection.py` (397 lines) - LouvainCommunityDetector
  - `path_analysis.py` (374 lines) - PathAnalyzer
  - `link_suggestions.py` (347 lines) - LinkSuggestionEngine
- Reporting (in class) - format_stats, recommendations, SEO insights ❌ needs extraction

**Evidence from codebase**:
```python
# bengal/analysis/knowledge_graph.py:73-1331
class KnowledgeGraph:
    # Graph building (lines 133-186)
    def build(self) -> None: ...

    # Basic analysis (lines 421-565) - STILL IN CLASS
    def get_hubs(self) -> list[Page]: ...
    def get_leaves(self) -> list[Page]: ...
    def get_orphans(self) -> list[Page]: ...

    # Advanced analysis (lines 1005-1263) - THIN DELEGATION WRAPPERS
    # These are 10-20 line methods that delegate to external modules
    def compute_pagerank(self) -> PageRankResults: ...  # delegates to page_rank.py
    def detect_communities(self) -> CommunityDetectionResults: ...  # delegates to community_detection.py
    def analyze_paths(self) -> PathAnalysisResults: ...  # delegates to path_analysis.py

    # Reporting (lines 616-1003) - STILL IN CLASS, NEEDS EXTRACTION
    def format_stats(self) -> str: ...  # 100+ lines
    def get_actionable_recommendations(self) -> list[str]: ...  # 100+ lines
    def get_seo_insights(self) -> list[str]: ...  # 100+ lines
    def get_content_gaps(self) -> list[str]: ...  # 80+ lines
```

**Already Modularized** (1,399 lines total):
| Module | Lines | Purpose |
|--------|-------|---------|
| `page_rank.py` | 281 | PageRank calculation |
| `community_detection.py` | 397 | Louvain community detection |
| `path_analysis.py` | 374 | Betweenness/closeness centrality |
| `link_suggestions.py` | 347 | Smart link suggestions |

**Remaining Issues**:
- Still 33 methods in the class (basic analysis + reporting + delegation wrappers)
- Long reporting methods (`format_stats()` ~100 lines, `get_actionable_recommendations()` ~100 lines)
- Basic analysis methods (hubs, leaves, orphans) could be extracted
- High cognitive load when working on reporting features

---

#### 1.2 `output_formats.py` (1,146 lines)

**Location**: `bengal/postprocess/output_formats.py`

**Responsibilities** (mixed in single class):
- Configuration normalization
- Page filtering
- Per-page JSON generation
- Per-page LLM text generation
- Site-wide index.json generation
- Site-wide llm-full.txt generation

**Evidence from codebase**:
```python
# bengal/postprocess/output_formats.py:23-1146
class OutputFormatsGenerator:
    # Configuration (lines 63-147)
    def _normalize_config(self) -> dict: ...
    def _default_config(self) -> dict: ...

    # Filtering (lines 202-262)
    def _filter_pages(self) -> list[Page]: ...

    # Per-page formats (lines 264-342)
    def _generate_page_json(self) -> int: ...
    def _generate_page_txt(self) -> int: ...
    def _page_to_json(self) -> dict: ...  # 150+ lines

    # Site-wide formats (lines 344-547)
    def _generate_site_index_json(self) -> None: ...  # 100+ lines
    def _generate_site_llm_txt(self) -> None: ...  # 100+ lines
```

**Issues**:
- Single class handling 4 different output formats
- Long methods (`_page_to_json()` ~150 lines, `_generate_site_index_json()` ~100 lines)
- Mixed concerns: serialization, filtering, file I/O
- Hard to add new formats without touching existing code

---

#### 1.3 `site.py` (1,015 lines)

**Location**: `bengal/core/site.py`

**Responsibilities** (mixed in single class):
- Data model (Site container)
- Content discovery
- Asset discovery
- Cache management
- Reference setup
- Factory methods

**Evidence from codebase**:
```python
# bengal/core/site.py:37-1015
@dataclass
class Site:
    # Data model (lines 79-106)
    root_path: Path
    pages: list[Page] = ...
    sections: list[Section] = ...

    # Discovery (lines 406-485)
    def discover_content(self) -> None: ...
    def discover_assets(self) -> None: ...

    # Caching (lines 246-270)
    def invalidate_page_caches(self) -> None: ...
    def invalidate_regular_pages_cache(self) -> None: ...

    # References (lines 486-553)
    def _setup_page_references(self) -> None: ...
    def _setup_section_references(self) -> None: ...

    # Factory (lines 271-405)
    @classmethod
    def from_config(cls) -> Site: ...  # 160+ lines
    @classmethod
    def for_testing(cls) -> Site: ...
```

**Issues**:
- Core class mixing data model with operations
- Long factory method (`from_config()` ~160 lines)
- Hard to test discovery/caching independently
- Violates single responsibility principle

---

### Pain Points

1. **Maintainability**: Adding features requires understanding 1,000+ lines
2. **Testability**: Cannot test individual concerns in isolation
3. **Readability**: Hard to find relevant code (buried in large files)
4. **Code Review**: Reviewers struggle with large diffs
5. **Contributor Onboarding**: New contributors feel overwhelmed
6. **Code Duplication**: Similar patterns repeated across long methods

### User Impact

**End Users**: No impact (internal refactoring only, public APIs unchanged)

**Contributors** (Strategic Priority):
- ❌ Current: Open `knowledge_graph.py` → 1,331 lines → "where do I start?" → close PR
- ✅ After: Open `graph_analysis.py` → 200 lines → find relevant code → submit PR

**Maintainers**:
- Hard to understand module boundaries
- High cognitive load when debugging
- Difficult to test individual concerns
- Hard to reason about dependencies

**Open Source Growth**:
- Clean codebase → more contributors → more features → more users
- 1,000+ line files deter contributions (proven pattern in OSS)

---

## 2. Goals & Non-Goals

### Goals

1. **Split Large Files**: Break 1,000+ line files into focused modules (200-400 lines each)
2. **Improve Contributor Experience**: Make codebase approachable for new contributors
3. **Reduce Cognitive Load**: Lower complexity per module
4. **Improve Testability**: Enable independent testing of concerns
5. **Maintain Backward Compatibility**: No breaking changes to public APIs
6. **Preserve Functionality**: All existing behavior unchanged

### Non-Goals

- **Not changing public APIs** (only internal reorganization)
- **Not optimizing performance** (focus on code structure)
- **Not adding new features** (pure refactoring)
- **Not changing module interfaces** (only internal refactoring)
- **Not adding abstractions prematurely** (YAGNI principle)

---

## 3. Architecture Impact

**Affected Subsystems**:

- **Analysis** (`bengal/analysis/`): **Primary impact** (knowledge_graph.py)
- **Postprocess** (`bengal/postprocess/`): **Primary impact** (output_formats.py)
- **Core** (`bengal/core/`): **Primary impact** (site.py)

**Dependencies**:
- No external API changes
- Internal imports may change (but public APIs remain)
- Tests may need import updates (but test logic unchanged)

**Risk Assessment**:
- **Low Risk**: Pure refactoring, no behavior changes
- **Low Risk**: Public APIs preserved via `__init__.py` re-exports
- **Medium Risk**: Need to update internal imports across codebase

---

## 4. Design Options

### Option A: Incremental Module Extraction (Recommended)

**Approach**: Extract concerns into separate modules, keep main class as orchestrator.

**Structure**:

#### 4.1 `knowledge_graph.py` → Focused Modules

> **Note**: Advanced analysis (PageRank, communities, paths, link suggestions) is **already extracted**
> into separate modules. This refactoring focuses on extracting the remaining concerns.

```
bengal/analysis/
  │
  │ # ALREADY EXIST - NO CHANGES NEEDED ✅
  ├── page_rank.py              # 281 lines - PageRankCalculator
  ├── community_detection.py    # 397 lines - LouvainCommunityDetector
  ├── path_analysis.py          # 374 lines - PathAnalyzer
  ├── link_suggestions.py       # 347 lines - LinkSuggestionEngine
  │
  │ # REFACTORED STRUCTURE
  ├── knowledge_graph.py        # Core graph building (300-400 lines)
  │   └── class KnowledgeGraph:
  │       - build()
  │       - get_analysis_pages()
  │       - _analyze_*() methods
  │       - (delegation wrappers to other modules)
  │
  ├── graph_analysis.py         # Basic analysis - NEW (200-300 lines)
  │   └── class GraphAnalyzer:
  │       - get_hubs()
  │       - get_leaves()
  │       - get_orphans()
  │       - get_connectivity()
  │       - get_connectivity_score()
  │       - get_layers()
  │
  └── graph_reporting.py        # Reporting & formatting - NEW (300-400 lines)
      └── class GraphReporter:
          - format_stats()
          - get_actionable_recommendations()
          - get_seo_insights()
          - get_content_gaps()
```

**Public API** (preserved):
```python
# bengal/analysis/__init__.py
from .knowledge_graph import KnowledgeGraph  # Main class unchanged
from .graph_analysis import GraphAnalyzer      # NEW
from .graph_reporting import GraphReporter     # NEW
# Advanced analysis modules already exist and are re-exported
from .page_rank import PageRankCalculator, PageRankResults
from .community_detection import LouvainCommunityDetector, CommunityDetectionResults
from .path_analysis import PathAnalyzer, PathAnalysisResults
from .link_suggestions import LinkSuggestionEngine, LinkSuggestionResults

# Backward compatibility: KnowledgeGraph delegates to analyzers
class KnowledgeGraph:
    def __init__(self):
        self._basic_analyzer = GraphAnalyzer(self)   # NEW
        self._reporter = GraphReporter(self)          # NEW
        # Advanced analysis already delegates via lazy imports

    def get_hubs(self):  # Delegates to _basic_analyzer
        return self._basic_analyzer.get_hubs()
```

**Pros**:
- ✅ Builds on existing modular structure (advanced analysis already extracted)
- ✅ Each module independently testable
- ✅ Public API unchanged (backward compatible)
- ✅ Lower risk - advanced analysis patterns proven to work

**Cons**:
- ⚠️ Need to update internal imports
- ⚠️ Reporting methods tightly coupled to graph state

**Complexity**: Low-Medium (1-2 days) - Advanced analysis already done!

---

#### 4.2 `output_formats.py` → Package

```
bengal/postprocess/output_formats/
  ├── __init__.py                 # Main generator (orchestrator, 200 lines)
  │   └── class OutputFormatsGenerator:
  │       - generate()
  │       - _filter_pages()
  │
  ├── base.py                     # Base classes, filtering, config (200 lines)
  │   └── class BaseFormatGenerator:
  │       - _normalize_config()
  │       - _default_config()
  │       - _filter_pages()
  │
  ├── page_json.py               # Per-page JSON (250 lines)
  │   └── class PageJSONGenerator:
  │       - generate()
  │       - _page_to_json()
  │
  ├── page_txt.py                # Per-page LLM text (200 lines)
  │   └── class PageTxtGenerator:
  │       - generate()
  │       - _page_to_llm_text()
  │
  ├── site_index.py              # Site-wide index.json (250 lines)
  │   └── class SiteIndexGenerator:
  │       - generate()
  │       - _generate_site_index_json()
  │
  └── site_llm_txt.py           # Site-wide llm-full.txt (200 lines)
      └── class SiteLlmTxtGenerator:
          - generate()
          - _generate_site_llm_txt()
```

**Public API** (preserved):
```python
# bengal/postprocess/output_formats/__init__.py
from . import OutputFormatsGenerator  # Main class unchanged

# Backward compatibility: Main class orchestrates generators
class OutputFormatsGenerator:
    def __init__(self):
        self._page_json = PageJSONGenerator(self)
        self._page_txt = PageTxtGenerator(self)
        self._site_index = SiteIndexGenerator(self)
        self._site_llm_txt = SiteLlmTxtGenerator(self)

    def generate(self):
        # Orchestrates all generators
        self._page_json.generate()
        self._page_txt.generate()
        # ...
```

**Pros**:
- ✅ Each format independently testable
- ✅ Easy to add new formats
- ✅ Clear code organization
- ✅ Public API unchanged

**Cons**:
- ⚠️ Requires orchestration layer
- ⚠️ Need to update imports

**Complexity**: Medium (2-3 days)

---

#### 4.3 `site.py` → Package (Optional)

> **Template**: Follow the successful `bengal/core/page/` pattern which uses mixins
> to separate concerns while maintaining a single public `Page` class.

```
bengal/core/site/
  ├── __init__.py                # Site class (maintains API, 300 lines)
  │   └── @dataclass
  │   class Site(
  │       SiteDiscoveryMixin,
  │       SiteCachingMixin,
  │       SiteReferencesMixin,
  │   ):
  │       # Core data model only
  │       # Methods delegated via mixins
  │
  ├── discovery.py               # Content/asset discovery (200 lines)
  │   └── class SiteDiscoveryMixin:
  │       - discover_content()
  │       - discover_assets()
  │       - _get_theme_assets_dir()
  │       - _get_theme_assets_chain()
  │
  ├── caching.py                # Cache management (150 lines)
  │   └── class SiteCachingMixin:
  │       - invalidate_page_caches()
  │       - invalidate_regular_pages_cache()
  │       - regular_pages property
  │       - generated_pages property
  │
  ├── references.py             # Reference setup (200 lines)
  │   └── class SiteReferencesMixin:
  │       - _setup_page_references()
  │       - _setup_section_references()
  │       - _apply_cascades()
  │       - register_sections()
  │
  └── factory.py                # Factory methods (200 lines)
      └── class SiteFactory:
          - from_config()
          - for_testing()
```

**Public API** (preserved):
```python
# bengal/core/site/__init__.py
from . import Site  # Main class unchanged

# Site delegates to helpers internally
@dataclass
class Site:
    def discover_content(self):
        return SiteDiscovery(self).discover_content()
```

**Pros**:
- ✅ Clear separation of concerns
- ✅ Easier to test individual operations
- ✅ Public API unchanged

**Cons**:
- ⚠️ More complex (Site is core class)
- ⚠️ Higher risk (touches many dependencies)
- ⚠️ May be acceptable as-is (1,015 lines is borderline)

**Complexity**: Medium-High (4-5 days)

**Recommendation**: Defer until after `knowledge_graph.py` and `output_formats.py` are refactored. Re-evaluate based on pain points.

---

### Option B: Keep As-Is (Not Recommended)

**Approach**: Leave files as monolithic classes.

**Pros**:
- ✅ No refactoring effort
- ✅ No risk of breaking changes

**Cons**:
- ❌ Continues to deter contributors
- ❌ Hard to maintain and test
- ❌ Technical debt compounds

**Complexity**: None (but technical debt increases)

---

### Recommended: Option A (Incremental Module Extraction)

**Strategic Reasoning**:
- **Contributor experience**: Focused modules attract contributors; 1,000+ line files repel them
- **Low risk**: Pure refactoring, public APIs preserved
- **Immediate value**: 80% of the benefit with 20% of the complexity
- **Incremental**: Can refactor one module at a time
- **Reversible**: Can always consolidate later if needed

**Implementation approach**:
1. **Phase 1**: Refactor `knowledge_graph.py` (highest impact, clearest boundaries)
2. **Phase 2**: Refactor `output_formats.py` (similar pattern, easier to validate)
3. **Phase 3**: Re-evaluate `site.py` (may be acceptable as-is after other refactors)

---

## 5. Detailed Design (Option A)

### 5.1 `knowledge_graph.py` Refactoring

> **Key Insight**: Advanced analysis (PageRank, communities, paths) is **already extracted**.
> This refactoring extracts the remaining basic analysis and reporting concerns.

**Current State**:
- `knowledge_graph.py` - 1,331 lines (graph building + basic analysis + reporting + delegation wrappers)
- `page_rank.py` - 281 lines (PageRankCalculator) ✅ DONE
- `community_detection.py` - 397 lines (LouvainCommunityDetector) ✅ DONE
- `path_analysis.py` - 374 lines (PathAnalyzer) ✅ DONE
- `link_suggestions.py` - 347 lines (LinkSuggestionEngine) ✅ DONE

**Target Structure** (only NEW extractions shown):

```python
# bengal/analysis/knowledge_graph.py (Core - 300-400 lines, down from 1,331)
class KnowledgeGraph:
    """Main graph builder - orchestrates analysis."""

    def __init__(self, site, hub_threshold=10, leaf_threshold=2):
        self.site = site
        self._basic_analyzer = GraphAnalyzer(self)  # NEW
        self._reporter = GraphReporter(self)         # NEW
        # Advanced analysis already uses lazy imports to separate modules
        # ... graph data structures ...

    def build(self) -> None:
        """Build graph by analyzing connections."""
        # Core graph building logic (stays here)
        self._analyze_cross_references()
        self._analyze_taxonomies()
        # ...

    # Delegation methods (backward compatibility)
    def get_hubs(self, threshold=None):
        return self._basic_analyzer.get_hubs(threshold)

    def format_stats(self):
        return self._reporter.format_stats()

    # Advanced analysis - already delegates via lazy imports (no change needed)
    def compute_pagerank(self, **kwargs):
        from bengal.analysis.page_rank import PageRankCalculator  # existing
        # ...

# bengal/analysis/graph_analysis.py (Basic Analysis - NEW, 200-300 lines)
class GraphAnalyzer:
    """Basic graph analysis: hubs, leaves, orphans, connectivity."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def get_hubs(self, threshold=None) -> list[Page]:
        """Get hub pages (highly connected)."""
        # MOVED from knowledge_graph.py lines 451-479

    def get_leaves(self, threshold=None) -> list[Page]:
        """Get leaf pages (low connectivity)."""
        # MOVED from knowledge_graph.py lines 481-511

    def get_orphans(self) -> list[Page]:
        """Get orphaned pages (no connections)."""
        # MOVED from knowledge_graph.py lines 513-544

    def get_connectivity(self, page: Page) -> PageConnectivity:
        """Get connectivity information for a page."""
        # MOVED from knowledge_graph.py lines 421-449

    def get_connectivity_score(self, page: Page) -> int:
        """Get total connectivity score for a page."""
        # MOVED from knowledge_graph.py lines 546-564

    def get_layers(self) -> tuple[list[Page], list[Page], list[Page]]:
        """Partition pages into hub/mid-tier/leaf layers."""
        # MOVED from knowledge_graph.py lines 566-599

# bengal/analysis/graph_reporting.py (Reporting - NEW, 300-400 lines)
class GraphReporter:
    """Graph reporting: formatting, recommendations, insights."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def format_stats(self) -> str:
        """Format graph statistics as string."""
        # MOVED from knowledge_graph.py lines 616-712 (~100 lines)

    def get_actionable_recommendations(self) -> list[str]:
        """Generate actionable recommendations."""
        # MOVED from knowledge_graph.py lines 714-816 (~100 lines)

    def get_seo_insights(self) -> list[str]:
        """Generate SEO insights."""
        # MOVED from knowledge_graph.py lines 818-922 (~100 lines)

    def get_content_gaps(self) -> list[str]:
        """Identify content gaps based on link structure."""
        # MOVED from knowledge_graph.py lines 924-1003 (~80 lines)

# ALREADY EXIST - NO CHANGES NEEDED:
# - bengal/analysis/page_rank.py (PageRankCalculator)
# - bengal/analysis/community_detection.py (LouvainCommunityDetector)
# - bengal/analysis/path_analysis.py (PathAnalyzer)
# - bengal/analysis/link_suggestions.py (LinkSuggestionEngine)
```

**Migration Strategy**:
1. Create new modules alongside existing file
2. Extract methods to new classes
3. Update `KnowledgeGraph` to delegate to new classes
4. Run tests to verify behavior unchanged
5. Update internal imports
6. Remove old code

**Backward Compatibility**:
- Public API unchanged (`KnowledgeGraph` class interface preserved)
- All methods delegate to new classes internally
- No breaking changes for users

---

### 5.2 `output_formats.py` Refactoring

**Target Structure**:

```python
# bengal/postprocess/output_formats/__init__.py (Orchestrator - 200 lines)
class OutputFormatsGenerator:
    """Main generator - orchestrates all format generators."""

    def __init__(self, site, config=None, graph_data=None):
        self.site = site
        self.config = self._normalize_config(config or {})

        # Initialize format generators
        self._page_json = PageJSONGenerator(self)
        self._page_txt = PageTxtGenerator(self)
        self._site_index = SiteIndexGenerator(self)
        self._site_llm_txt = SiteLlmTxtGenerator(self)

    def generate(self) -> None:
        """Generate all enabled output formats."""
        pages = self._filter_pages()

        if "json" in self.config.get("per_page", []):
            self._page_json.generate(pages)
        if "llm_txt" in self.config.get("per_page", []):
            self._page_txt.generate(pages)
        # ...

# bengal/postprocess/output_formats/page_json.py (250 lines)
class PageJSONGenerator:
    """Generate per-page JSON files."""

    def __init__(self, generator: OutputFormatsGenerator):
        self.generator = generator
        self.site = generator.site
        self.config = generator.config

    def generate(self, pages: list[Page]) -> int:
        """Generate JSON for each page."""
        # ... generation logic ...

    def _page_to_json(self, page: Page) -> dict:
        """Convert page to JSON dict."""
        # ... serialization logic ...

# Similar structure for page_txt.py, site_index.py, site_llm_txt.py
```

**Migration Strategy**:
1. Create package structure
2. Extract each format to separate module
3. Update main class to orchestrate
4. Run tests to verify behavior
5. Update imports
6. Remove old code

**Backward Compatibility**:
- Public API unchanged (`OutputFormatsGenerator` class interface preserved)
- All methods delegate to format generators internally
- No breaking changes for users

---

## 6. Implementation Plan

### Phase 1: `knowledge_graph.py` (3-4 days)

> **Reduced Scope**: Advanced analysis already extracted to separate modules.
> Only basic analysis and reporting remain to be extracted.

**Tasks**:
1. Create `graph_analysis.py` module
2. Extract basic analysis methods (`get_hubs`, `get_leaves`, `get_orphans`, `get_connectivity`, `get_connectivity_score`, `get_layers`)
3. Update `KnowledgeGraph` to delegate to `GraphAnalyzer`
4. Run tests, verify behavior unchanged
5. Create `graph_reporting.py` module
6. Extract reporting methods (`format_stats`, `get_actionable_recommendations`, `get_seo_insights`, `get_content_gaps`)
7. Update `KnowledgeGraph` to delegate to `GraphReporter`
8. Run tests, verify behavior unchanged
9. Update internal imports across codebase
10. Clean up delegation wrappers in `KnowledgeGraph`

**Already Done** (no work needed):
- ✅ `page_rank.py` - PageRank computation (281 lines)
- ✅ `community_detection.py` - Community detection (397 lines)
- ✅ `path_analysis.py` - Path analysis (374 lines)
- ✅ `link_suggestions.py` - Link suggestions (347 lines)

**Success Criteria**:
- [ ] `knowledge_graph.py` reduced to <500 lines (from 1,331)
- [ ] 2 new focused modules created:
  - [ ] `graph_analysis.py` (200-300 lines)
  - [ ] `graph_reporting.py` (300-400 lines)
- [ ] All existing tests pass
- [ ] Public API unchanged
- [ ] No performance regression

---

### Phase 2: `output_formats.py` (Week 2)

**Tasks**:
1. Create `output_formats/` package
2. Extract `PageJSONGenerator` to `page_json.py`
3. Extract `PageTxtGenerator` to `page_txt.py`
4. Extract `SiteIndexGenerator` to `site_index.py`
5. Extract `SiteLlmTxtGenerator` to `site_llm_txt.py`
6. Update `OutputFormatsGenerator` to orchestrate generators
7. Run tests, verify behavior
8. Update internal imports
9. Remove old code

**Success Criteria**:
- [ ] `output_formats.py` reduced to <300 lines (orchestrator only)
- [ ] 4 new focused modules (200-250 lines each)
- [ ] All existing tests pass
- [ ] Public API unchanged
- [ ] No performance regression

---

### Phase 3: `site.py` (Deferred - Re-evaluate)

**Decision Point**: After Phases 1-2, re-evaluate if `site.py` refactoring is needed.

**Criteria for proceeding**:
- Pain points remain after other refactors
- Contributors report difficulty working with `site.py`
- Clear boundaries identified

**If proceeding**:
- Follow same pattern as Phases 1-2
- Extract discovery, caching, references, factory to separate modules
- Preserve public API

---

## 7. Testing Strategy

### Test Coverage

**Before Refactoring**:
- Run full test suite: `pytest tests/`
- Document test coverage for each module
- Identify integration tests that depend on internal structure

**During Refactoring**:
- Run tests after each extraction step
- Verify behavior unchanged (no regressions)
- Add tests for new module boundaries if needed

**After Refactoring**:
- Run full test suite: `pytest tests/`
- Verify coverage maintained or improved
- Run integration tests
- Manual smoke testing

### Test Updates Required

**Minimal Changes**:
- Update imports in test files (if testing internal modules)
- Test public API remains unchanged
- No test logic changes needed

---

## 8. Risks & Mitigations

### Risk 1: Breaking Changes

**Risk**: Accidentally change public API during refactoring

**Mitigation**:
- Preserve all public methods via delegation
- Run tests after each step
- Type check with mypy
- Document public API explicitly

### Risk 2: Import Updates

**Risk**: Many files import from refactored modules

**Mitigation**:
- Use `__init__.py` re-exports for backward compatibility
- Update imports incrementally
- Use grep to find all import sites
- Test after each import update

### Risk 3: Performance Regression

**Risk**: Delegation adds overhead

**Mitigation**:
- Measure performance before/after
- Use delegation (minimal overhead)
- Profile if needed
- Optimize hot paths if regression found

### Risk 4: Incomplete Migration

**Risk**: Some code paths not updated

**Mitigation**:
- Comprehensive test coverage
- Code review for all changes
- Incremental migration (one module at a time)
- Rollback plan if issues found

---

## 9. Success Metrics

### Code Quality Metrics

- **File Size**: Reduce 1,000+ line files to <500 lines
- **Module Count**: Increase focused modules (3-4 per refactored file)
- **Cyclomatic Complexity**: Reduce complexity per module
- **Test Coverage**: Maintain or improve coverage

### Contributor Experience Metrics

- **Time to Find Code**: Measure time to locate relevant code (before/after)
- **PR Review Time**: Measure code review time (should decrease)
- **Contributor Feedback**: Survey contributors on codebase clarity

### Technical Metrics

- **Build Time**: No regression (should be unchanged)
- **Test Time**: No regression (should be unchanged)
- **Memory Usage**: No regression (should be unchanged)

---

## 10. Alternatives Considered

### Alternative 1: Keep As-Is

**Rejected**: Continues technical debt, deters contributors

### Alternative 2: Full Rewrite

**Rejected**: Too risky, unnecessary (code works, just needs organization)

### Alternative 3: Only Extract Long Methods

**Rejected**: Doesn't address root cause (mixed responsibilities)

---

## 11. Open Questions

1. **Should we refactor `site.py` immediately or defer?**
   - **Recommendation**: Defer until after `knowledge_graph.py` and `output_formats.py` are done
   - **Rationale**: Lower priority, higher risk, may be acceptable as-is
   - **Template**: Follow `bengal/core/page/` mixin pattern if proceeding

2. **Should we extract to separate packages or keep in same package?**
   - **Recommendation**: Keep in same package (e.g., `bengal/analysis/` stays as package)
   - **Rationale**: Maintains logical grouping, easier imports
   - **Precedent**: `bengal/analysis/` already has 5 related modules working well together

3. **Should we add new abstractions (interfaces, base classes)?**
   - **Recommendation**: No, keep simple (YAGNI principle)
   - **Rationale**: Current design sufficient, avoid premature abstraction
   - **Evidence**: `page_rank.py`, `community_detection.py` etc. work fine without base classes

4. **Should reporting methods access graph state directly or through accessor methods?**
   - **Recommendation**: Use accessor methods for better testability
   - **Rationale**: Allows mocking graph state in tests for GraphReporter

---

## 12. References

**Existing Successful Refactoring Examples**:
- **[bengal/core/page/](mdc:bengal/core/page/)** - Page object successfully refactored using this exact pattern:
  - `__init__.py` - Main Page class
  - `page_core.py` - Cacheable core data (PageCore)
  - `metadata.py` - PageMetadataMixin
  - `navigation.py` - PageNavigationMixin
  - `computed.py` - PageComputedMixin
  - `relationships.py` - PageRelationshipsMixin
  - `operations.py` - PageOperationsMixin
  - `proxy.py` - PageProxy for lazy loading

**Existing Modular Analysis** (already extracted from knowledge_graph.py):
- `bengal/analysis/page_rank.py` (281 lines) - PageRank algorithm
- `bengal/analysis/community_detection.py` (397 lines) - Louvain method
- `bengal/analysis/path_analysis.py` (374 lines) - Centrality metrics
- `bengal/analysis/link_suggestions.py` (347 lines) - Link suggestion engine

**Related Documentation**:
- [BuildOrchestrator RFC](rfc-build-orchestrator-refactoring.md) - Similar refactoring pattern
- [File Organization Rules](.cursor/rules/file-organization.mdc) - Bengal's file organization standards
- [Architecture Patterns](.cursor/rules/architecture-patterns.mdc) - Bengal's architectural principles

---

## 13. Decision

**Status**: Draft - Pending Review

**Next Steps**:
1. Review RFC with team
2. Get approval for Phase 1 (`knowledge_graph.py`)
3. Create implementation plan
4. Begin Phase 1 refactoring

**Estimated Timeline** (Revised):
- Phase 1 (`knowledge_graph.py`): **3-4 days** (reduced - advanced analysis already extracted)
- Phase 2 (`output_formats.py`): **1 week**
- Phase 3 (`site.py`): Deferred, re-evaluate

**Total Effort**: ~1.5 weeks (Phases 1-2), ~2.5 weeks if Phase 3 proceeds

---

**Confidence**: 90% 🟢

**Rationale**:
- ✅ Strong evidence from code analysis (verified line counts and method counts)
- ✅ Proven pattern already working in codebase (`bengal/core/page/` package)
- ✅ Advanced analysis already extracted from `knowledge_graph.py` (1,399 lines in 4 modules)
- ✅ Low risk (pure refactoring, public APIs preserved)
- ✅ Reduced scope for Phase 1 (only basic analysis + reporting remain)
- ✅ High value (improved contributor experience, clearer boundaries)

---

## Appendix: Validation Results

**Validation Date**: 2025-12-01  
**Method**: Code analysis against actual codebase

### Line Count Verification

| File | RFC Claim | Actual (`wc -l`) | Status |
|------|-----------|------------------|--------|
| `knowledge_graph.py` | 1,331 | 1,331 | ✅ Exact |
| `output_formats.py` | 1,146 | 1,146 | ✅ Exact |
| `site.py` | 1,015 | 1,015 | ✅ Exact |

### Method Count Verification

| File | RFC Claim | Actual (`grep def`) | Status |
|------|-----------|---------------------|--------|
| `knowledge_graph.py` | 36 | 33 | ⚠️ Corrected |
| `output_formats.py` | 19 | 19 | ✅ Exact |
| `site.py` | 31 | 30 | ⚠️ Corrected |

### Key Finding: Existing Modularization

**Discovery**: Advanced analysis in `knowledge_graph.py` is **already extracted**:

```
bengal/analysis/
├── knowledge_graph.py      # 1,331 lines (core + basic analysis + reporting)
├── page_rank.py            # 281 lines ← ALREADY EXTRACTED
├── community_detection.py  # 397 lines ← ALREADY EXTRACTED
├── path_analysis.py        # 374 lines ← ALREADY EXTRACTED
├── link_suggestions.py     # 347 lines ← ALREADY EXTRACTED
├── graph_visualizer.py     # 671 lines
└── performance_advisor.py
```

**Impact**: Phase 1 scope reduced from 3-4 days to 1-2 days (only basic analysis + reporting need extraction).
