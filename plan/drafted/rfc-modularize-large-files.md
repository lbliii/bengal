# RFC: Modularize Large Files

**Status**: Implemented (Phase 1)  
**Created**: 2025-12-23  
**Implemented**: 2025-12-23  
**Author**: AI Assistant  
**Priority**: P2 (Medium)  
**Scope**: Multiple large files across the codebase  
**Estimated Effort**: ~300 hours (7-8 weeks full-time, or opportunistic over 3-6 months)

> **Implementation Note**: Phase 1 (Critical Files 900+ lines) has been completed. See "Implementation Results" section below for details.

---

## Summary

Several files in the codebase have grown beyond maintainable size (500+ lines). This RFC proposes a systematic approach to modularizing these files to improve maintainability, testability, and code organization.

---

## Problem Statement

A codebase analysis identified **20 files with 500+ lines**, with the largest being **1,314 lines**. Large files present several problems:

### Symptoms

1. **Hard to navigate** - Finding specific functionality requires scrolling through hundreds of lines
2. **Difficult to test** - Large classes/modules mix concerns, making unit testing harder
3. **Merge conflicts** - Multiple developers working on the same large file increases conflict frequency
4. **Cognitive overload** - Understanding the full file requires holding too much context
5. **Tight coupling** - Related but distinct concerns are bundled together

### Current State

> **Note**: Line counts are raw totals including docstrings, imports, and type definitions.

**Critical (900+ lines):**
- `bengal/analysis/knowledge_graph.py` - **1,314 lines** (knowledge graph construction/analysis)
- `bengal/rendering/pipeline/core.py` - **1,271 lines** (rendering pipeline orchestration)
- `bengal/discovery/content_discovery.py` - **1,064 lines** (content discovery logic)
- `bengal/rendering/context.py` - **1,022 lines** (rendering context management)
- `bengal/orchestration/incremental/change_detector.py` - **897 lines** (change detection)

**High Priority (700-899 lines):**
- `bengal/cli/dashboard/screens.py` - **~750 lines** (dashboard UI screens)
- `bengal/orchestration/taxonomy.py` - **~740 lines** (taxonomy orchestration)
- `bengal/health/report.py` - **~704 lines**
- `bengal/cli/commands/debug.py` - **~702 lines**
- `bengal/orchestration/build/__init__.py` - **~688 lines**
- `bengal/health/autofix.py` - **~686 lines**
- `bengal/orchestration/asset.py` - **~686 lines**
- `bengal/orchestration/content.py` - **~684 lines**

**Medium Priority (500-699 lines):**
- `bengal/cli/commands/theme.py` - **~673 lines**
- `bengal/core/page/proxy.py` - **~630 lines**
- `bengal/rendering/errors.py` - **~624 lines**
- `bengal/orchestration/render.py` - **~609 lines**
- `bengal/autodoc/extractors/python/extractor.py` - **~607 lines**
- `bengal/autodoc/docstring_parser.py` - **~594 lines**
- `bengal/postprocess/social_cards.py` - **~594 lines**

### Existing Modularization (Prior Art)

The codebase already has successful modularization examples to follow:

**`bengal/orchestration/incremental/`** - Successfully modularized orchestrator:
```
bengal/orchestration/incremental/
├── __init__.py
├── orchestrator.py         # Main orchestrator (~392 lines)
├── cache_manager.py        # Cache operations
├── change_detector.py      # Change detection (still large - needs further work)
├── cleanup.py              # Deleted file cleanup
├── cascade_tracker.py      # Cascade tracking
└── rebuild_filter.py       # Rebuild filtering
```

**`bengal/rendering/pipeline/`** - Partially modularized:
```
bengal/rendering/pipeline/
├── __init__.py
├── core.py                 # Main pipeline (1,271 lines - needs further extraction)
├── output.py               # ✅ Already extracted: output path, template, formatting
├── thread_local.py         # ✅ Already extracted: thread-local parser management
├── toc.py                  # ✅ Already extracted: TOC extraction
└── transforms.py           # ✅ Already extracted: content transformations
```

---

## Proposed Solution

### Principles

1. **Single Responsibility** - Each module should have one clear purpose
2. **Preserve Public API** - Maintain backward compatibility during refactoring
3. **Incremental Migration** - Modularize one file at a time, starting with the largest
4. **Composition over Inheritance** - Use composition to combine focused modules
5. **Test-Driven** - Ensure tests pass before and after modularization
6. **Follow Existing Patterns** - Use the established patterns from `orchestration/incremental/`

### Modularization Patterns

#### Pattern 1: Extract Specialized Classes

**Before:**
```python
# core.py (1271 lines)
class RenderingPipeline:
    def __init__(self):
        # initialization

    def _try_rendered_cache(self):
        # 30 lines of cache checking

    def _try_parsed_cache(self):
        # 60 lines of cache checking

    def _parse_content(self):
        # 100 lines of parsing logic

    def _accumulate_json_data(self):
        # 60 lines of JSON accumulation

    def _render_autodoc_page(self):
        # 100 lines of autodoc rendering
```

**After:**
```python
# pipeline/core.py (~300 lines)
class RenderingPipeline:
    def __init__(self):
        self._cache_checker = CacheChecker(...)
        self._json_accumulator = JsonAccumulator(...)
        self._autodoc_renderer = AutodocRenderer(...)

    def process_page(self, page):
        if self._cache_checker.try_rendered_cache(page):
            return
        # ... orchestration logic

# pipeline/cache_checker.py (~150 lines)
class CacheChecker:
    def try_rendered_cache(self, page):
        # Focused cache checking

    def try_parsed_cache(self, page):
        # Focused parsed cache checking

# pipeline/json_accumulator.py (~100 lines)
class JsonAccumulator:
    def accumulate(self, page):
        # Focused JSON accumulation

# pipeline/autodoc_renderer.py (~150 lines)
class AutodocRenderer:
    def render(self, page):
        # Focused autodoc rendering
```

#### Pattern 2: Extract Peer Modules (for existing flat structures)

When a directory already has peer modules, add new peer modules rather than creating nested subdirectories.

**Before:**
```python
# discovery/content_discovery.py (1064 lines)
class ContentDiscovery:
    def _walk_directory(self):
        # 120 lines

    def _create_page(self):
        # 125 lines

    def _parse_content_file(self):
        # 110 lines

    def _sort_all_sections(self):
        # 20 lines
```

**After (working with existing structure):**
```python
# discovery/content_discovery.py (~300 lines) - orchestrator
class ContentDiscovery:
    def __init__(self):
        self._walker = DirectoryWalker(...)
        self._parser = ContentParser(...)
        # Use existing page_factory.py

    def discover(self):
        # High-level orchestration

# discovery/directory_walker.py (~150 lines) - NEW peer module
class DirectoryWalker:
    def walk(self, root):
        # Focused directory walking

# discovery/content_parser.py (~150 lines) - NEW peer module
class ContentParser:
    def parse(self, file_path):
        # Focused content parsing

# discovery/page_factory.py - EXISTING (already extracted!)
# discovery/asset_discovery.py - EXISTING (already extracted!)
```

#### Pattern 3: Extract Feature Modules

**Before:**
```python
# knowledge_graph.py (1314 lines)
class KnowledgeGraph:
    def build_graph(self):
        # 200 lines

    def analyze_connections(self):
        # 150 lines

    def calculate_metrics(self):
        # 150 lines

    def generate_report(self):
        # 150 lines

    def visualize(self):
        # 150 lines
```

**After:**
```python
# analysis/knowledge_graph/__init__.py
from bengal.analysis.knowledge_graph.core import KnowledgeGraph
__all__ = ["KnowledgeGraph"]

# analysis/knowledge_graph/core.py (~200 lines)
class KnowledgeGraph:
    def __init__(self):
        self._builder = GraphBuilder()
        self._analyzer = GraphAnalyzer()
        self._metrics = GraphMetrics()
        self._reporter = GraphReporter()
        self._visualizer = GraphVisualizer()

    def build_and_analyze(self):
        graph = self._builder.build()
        analysis = self._analyzer.analyze(graph)
        metrics = self._metrics.calculate(graph)
        return graph, analysis, metrics

# analysis/knowledge_graph/builder.py (~250 lines)
# analysis/knowledge_graph/analyzer.py (~200 lines)
# analysis/knowledge_graph/metrics.py (~200 lines)
# analysis/knowledge_graph/reporting.py (~200 lines)
# analysis/knowledge_graph/visualization.py (~200 lines)
```

---

## Implementation Plan

### Immediate Action: Add CI Linting

Before any modularization, add a file size check to CI:

```yaml
# In CI configuration
- name: Check file sizes
  run: |
    # Warn on files > 600 lines, fail on files > 1000 lines
    find bengal -name "*.py" -exec wc -l {} + | \
      awk '$1 > 600 { print "WARNING:", $0 } $1 > 1000 { exit 1 }'
```

This prevents files from growing further during the modularization effort.

### Phase 1: Critical Files (900+ lines)

**Priority Order** (largest first for maximum impact):

1. `bengal/analysis/knowledge_graph.py` (1,314 lines) - **Highest impact, cleanest boundaries**
2. `bengal/rendering/pipeline/core.py` (1,271 lines) - Continue existing modularization
3. `bengal/discovery/content_discovery.py` (1,064 lines)
4. `bengal/rendering/context.py` (1,022 lines)
5. `bengal/orchestration/incremental/change_detector.py` (897 lines)

### Phase 2: High Priority Files (700-899 lines)

After Phase 1 is complete, proceed with the 8 files in the 700-899 line range.

### Phase 3: Medium Priority Files (500-699 lines)

Complete modularization with the remaining files.

### Per-File Process

For each file:

1. **Analysis** (1-2 hours)
   - Run dependency analysis (e.g., `pydeps`) to visualize internal dependencies
   - Identify distinct responsibilities/concerns
   - Map dependencies between concerns
   - Design module boundaries

2. **Test Coverage** (2-4 hours)
   - Ensure existing tests cover current behavior
   - Add tests for edge cases if needed
   - Document expected behavior

3. **Extract Modules** (4-8 hours)
   - Create new module structure
   - Move code to appropriate modules
   - Update imports
   - Maintain public API compatibility

4. **Refactor Main Module** (2-4 hours)
   - Update main class to use composition
   - Ensure all tests pass
   - Update documentation

5. **Review & Merge** (1-2 hours)
   - Code review
   - Address feedback
   - Merge to main

**Total per file: ~10-20 hours**

### Total Effort Estimate

| Phase | Files | Hours/File | Total Hours |
|-------|-------|------------|-------------|
| Phase 1 | 5 | 15 | ~75 |
| Phase 2 | 8 | 15 | ~120 |
| Phase 3 | 7 | 15 | ~105 |
| **Total** | **20** | - | **~300 hours** |

**Recommended Approach**: Opportunistic modularization—when touching a large file for feature work, budget extra time to extract the relevant portion. This spreads the effort over 3-6 months rather than requiring dedicated refactoring sprints.

---

## Detailed File Analysis

### 1. `bengal/analysis/knowledge_graph.py` (1,314 lines) - **START HERE**

**Why First**: Largest file with cleanest separation boundaries. The graph lifecycle (build → analyze → metrics → report → visualize) maps directly to separate modules.

**Current Structure:**
- Graph construction
- Connection analysis
- Metrics calculation
- Report generation
- Visualization

**Proposed Structure:**
```
bengal/analysis/knowledge_graph/
├── __init__.py              # Public API (re-export KnowledgeGraph)
├── core.py                  # Main KnowledgeGraph class (~200 lines)
├── builder.py               # Graph construction (~250 lines)
├── analyzer.py              # Connection analysis (~200 lines)
├── metrics.py               # Metrics calculation (~200 lines)
├── reporting.py             # Report generation (~200 lines)
└── visualization.py         # Visualization (~200 lines)
```

### 2. `bengal/rendering/pipeline/core.py` (1,271 lines)

**Note**: This file is already partially modularized. The following have been extracted:
- `output.py` - output path determination, template selection, HTML formatting
- `thread_local.py` - thread-local parser management
- `toc.py` - TOC extraction
- `transforms.py` - content transformations (link normalization, Jinja escaping)

**Remaining concerns to extract:**
- Cache checking logic (`_try_rendered_cache`, `_try_parsed_cache`)
- JSON data accumulation (`_accumulate_json_data`, `_accumulate_unified_page_data`)
- Autodoc rendering (`_render_autodoc_page`, `_process_virtual_page`)
- Metadata extraction (`_extract_enhanced_metadata`, `_build_full_json_data`)

**Proposed Additional Structure:**
```
bengal/rendering/pipeline/
├── __init__.py              # Public API
├── core.py                  # Main pipeline orchestrator (~300 lines)
├── output.py                # ✅ EXISTING
├── thread_local.py          # ✅ EXISTING
├── toc.py                   # ✅ EXISTING
├── transforms.py            # ✅ EXISTING
├── cache_checker.py         # NEW: Cache checking (~150 lines)
├── json_accumulator.py      # NEW: JSON/metadata accumulation (~200 lines)
└── autodoc_renderer.py      # NEW: Autodoc page rendering (~200 lines)
```

### 3. `bengal/discovery/content_discovery.py` (1,064 lines)

**Note**: The `discovery/` folder already has peer modules:
- `asset_discovery.py` - asset discovery (already separate)
- `page_factory.py` - page creation (already separate)
- `version_resolver.py` - version resolution
- `git_version_adapter.py` - git version handling

**Proposed Structure** (adding peer modules, not nested folders):
```
bengal/discovery/
├── __init__.py              # Public API
├── content_discovery.py     # Main discovery orchestrator (~250 lines)
├── directory_walker.py      # NEW: Directory traversal (~150 lines)
├── content_parser.py        # NEW: Content file parsing (~150 lines)
├── section_sorter.py        # NEW: Section sorting logic (~100 lines)
├── asset_discovery.py       # EXISTING
├── page_factory.py          # EXISTING
├── version_resolver.py      # EXISTING
└── git_version_adapter.py   # EXISTING
```

### 4. `bengal/rendering/context.py` (1,022 lines)

**Current Structure:**
- Context building
- Context accessors
- Context caching
- Template variable injection

**Proposed Structure:**
```
bengal/rendering/context/
├── __init__.py              # Public API
├── core.py                  # Main context class (~200 lines)
├── builder.py               # Context building logic (~300 lines)
├── accessors.py             # Context accessors (~250 lines)
└── cache.py                 # Context caching (~200 lines)
```

### 5. `bengal/orchestration/incremental/change_detector.py` (897 lines)

**Note**: This file is part of the already-modularized `incremental/` package but still needs further splitting.

**Proposed Structure:**
```
bengal/orchestration/incremental/
├── __init__.py              # EXISTING
├── orchestrator.py          # EXISTING
├── cache_manager.py         # EXISTING
├── change_detector.py       # Refactor to ~200 lines (orchestrator)
├── file_change_detector.py  # NEW: File-level detection (~200 lines)
├── section_change_detector.py # NEW: Section-level detection (~200 lines)
├── dependency_change_detector.py # NEW: Dependency detection (~200 lines)
├── cleanup.py               # EXISTING
├── cascade_tracker.py       # EXISTING
└── rebuild_filter.py        # EXISTING
```

---

## Migration Strategy

### Backward Compatibility

1. **Preserve Public API** - Keep existing imports working:
   ```python
   # Old import still works
   from bengal.rendering.pipeline.core import RenderingPipeline

   # New import also works
   from bengal.rendering.pipeline import RenderingPipeline
   ```

2. **Gradual Migration** - Update internal imports first, external imports later

3. **Deprecation Warnings** - Add deprecation warnings for old import paths (after 1 release cycle)

### Testing Strategy

1. **Before Modularization:**
   - Ensure comprehensive test coverage
   - Document current behavior
   - Capture performance benchmarks

2. **During Modularization:**
   - Run tests after each module extraction
   - Ensure no regressions
   - Verify performance hasn't degraded

3. **After Modularization:**
   - Add tests for new module boundaries
   - Verify all integration tests pass
   - Compare performance benchmarks

### Rollback Criteria

A modularization should be reverted if:
- **Performance regression > 5%** in build time benchmarks
- **Import cycle introduced** that cannot be resolved with TYPE_CHECKING
- **Test failures** that cannot be resolved within 2 hours
- **Public API breakage** discovered after merge

---

## Success Criteria

1. **Code Organization**
   - No files exceed 500 lines of code
   - Each module has a single, clear responsibility
   - Module dependencies form a clear hierarchy

2. **Maintainability**
   - New developers can understand individual modules quickly
   - Changes to one concern don't affect unrelated code
   - Code reviews are easier (smaller, focused changes)

3. **Testability**
   - Individual modules can be tested in isolation
   - Test setup is simpler (fewer dependencies)
   - Test failures are easier to diagnose

4. **Performance**
   - No performance regression (same or better)
   - Import time doesn't increase significantly

---

## Risks & Mitigation

### Risk 1: Breaking Changes
**Mitigation:** Maintain public API compatibility, comprehensive test coverage

### Risk 2: Import Cycles
**Mitigation:** Careful dependency analysis, use of TYPE_CHECKING for type hints

### Risk 3: Performance Regression
**Mitigation:** Benchmark before/after, profile if needed, rollback if > 5% regression

### Risk 4: Scope Creep
**Mitigation:** Focus on modularization only, defer feature changes to separate PRs

### Risk 5: Incomplete Modularization
**Mitigation:** Track with "modularization" label, regular progress reviews

---

## Alternatives Considered

### Alternative 1: Do Nothing
**Rejected:** Files will continue to grow, making future refactoring harder

### Alternative 2: Split by Functionality Only
**Rejected:** Doesn't address the root cause of mixed concerns

### Alternative 3: Complete Rewrite
**Rejected:** Too risky, loses existing behavior and tests

### Alternative 4: Dedicated Refactoring Sprint
**Rejected in favor of opportunistic approach:** Spreading the work over feature development reduces risk and maintains momentum on feature delivery

---

## Decisions (Resolving Open Questions)

1. **Hard limit on file size**: Yes, 500 lines as a target. Files with extensive documentation may exceed this but should be reviewed.

2. **Linting rules**: Yes, add immediately. Warn at 600 lines, fail CI at 1000 lines. This prevents growth during modularization.

3. **Prioritization vs. feature work**: Opportunistic approach—when modifying a large file for feature work, budget extra time to extract the relevant portion.

4. **Tracking label**: Yes, create a "modularization" label for PRs. This aids progress tracking and helps new contributors find good first issues.

---

## Implementation Checklist

### Phase 1: Critical Files (900+ lines)

#### 1.1 `knowledge_graph.py` (1,314 → ~400 lines)

**Already Extracted:**
- ✅ `graph_analysis.py` (265 lines) - `GraphAnalyzer` class
- ✅ `graph_reporting.py` (507 lines) - `GraphReporter` class

**Remaining Extraction Tasks:**
- [ ] Extract `builder.py` (~350 lines) - Graph building logic:
  - `_ensure_links_extracted()`
  - `_analyze_cross_references()`
  - `_analyze_taxonomies()`
  - `_analyze_related_posts()`
  - `_analyze_menus()`
  - `_analyze_section_hierarchy()`
  - `_analyze_navigation_links()`
  - `_build_link_metrics()`
  - `_resolve_link()`
- [ ] Extract `metrics.py` (~100 lines) - Metrics computation:
  - `_compute_metrics()`
  - `GraphMetrics` dataclass
  - `PageConnectivity` dataclass
- [ ] Update `core.py` to use `GraphBuilder` via composition
- [ ] Add re-exports in `__init__.py`

**Dependencies:** None (self-contained module)

---

#### 1.2 `pipeline/core.py` (1,271 → ~400 lines)

**Already Extracted:**
- ✅ `output.py` - Output path, template selection, formatting
- ✅ `thread_local.py` - Thread-local parser management
- ✅ `toc.py` - TOC extraction
- ✅ `transforms.py` - Content transformations

**Remaining Extraction Tasks:**
- [ ] Extract `cache_checker.py` (~120 lines):
  - `_try_rendered_cache()`
  - `_try_parsed_cache()`
  - `_cache_parsed_content()`
  - `_cache_rendered_output()`
- [ ] Extract `json_accumulator.py` (~200 lines):
  - `_accumulate_json_data()`
  - `_accumulate_unified_page_data()`
  - `_extract_enhanced_metadata()`
  - `_build_full_json_data()`
- [ ] Extract `autodoc_renderer.py` (~250 lines):
  - `_process_virtual_page()`
  - `_render_autodoc_page()`
  - `_normalize_autodoc_element()`
  - `_normalize_config()`
  - `_MetadataView` class
- [ ] Update `core.py` to use extracted modules

**Dependencies:** Requires `output.py`, `transforms.py` (already extracted)

---

#### 1.3 `content_discovery.py` (1,064 → ~300 lines)

**Already Extracted (peer modules):**
- ✅ `asset_discovery.py` - Asset discovery
- ✅ `page_factory.py` - Page creation
- ✅ `version_resolver.py` - Version resolution
- ✅ `git_version_adapter.py` - Git version handling

**Remaining Extraction Tasks:**
- [ ] Extract `directory_walker.py` (~150 lines):
  - Directory traversal logic
  - File filtering and ignore patterns
  - Recursive directory enumeration
- [ ] Extract `content_parser.py` (~200 lines):
  - Frontmatter parsing
  - Content file type detection
  - Metadata extraction
- [ ] Extract `section_builder.py` (~150 lines):
  - Section creation from directories
  - Section sorting logic
  - Section hierarchy building
- [ ] Update `content_discovery.py` as orchestrator

**Dependencies:** `page_factory.py` (existing)

---

#### 1.4 `rendering/context.py` (1,022 → ~250 lines)

**Extraction Strategy:** Create `context/` subpackage:

- [ ] Extract `context/builder.py` (~300 lines):
  - Context building logic
  - Template variable injection
  - Context merging
- [ ] Extract `context/accessors.py` (~250 lines):
  - `SiteContext`, `ConfigContext`
  - `ParamsContext`, `SectionContext`
  - Safe attribute access wrappers
- [ ] Extract `context/cache.py` (~150 lines):
  - Global context caching
  - Thread-local context management
- [ ] Rename `context.py` → `context/core.py` (~250 lines)
- [ ] Add `context/__init__.py` with re-exports

**Dependencies:** Used by `pipeline/core.py`

---

#### 1.5 `change_detector.py` (897 → ~200 lines)

**Current Location:** `orchestration/incremental/change_detector.py`

**Extraction Tasks:**
- [ ] Extract `file_change_detector.py` (~200 lines):
  - File modification detection
  - Hash-based change detection
  - File metadata comparison
- [ ] Extract `section_change_detector.py` (~200 lines):
  - Section-level change detection
  - Section dependency tracking
- [ ] Extract `dependency_change_detector.py` (~200 lines):
  - Dependency graph traversal
  - Cascade change detection
  - Template dependency tracking
- [ ] Update `change_detector.py` as orchestrator

**Dependencies:** `cache_manager.py`, `cascade_tracker.py` (existing)

---

### Quick Win Opportunities

Files that can be tackled independently when time permits:

| File | Lines | Estimated Effort | Benefit |
|------|-------|------------------|---------|
| `knowledge_graph.py` builder extraction | 1,314 | 4-6 hours | High (cleanest boundaries) |
| `pipeline/core.py` cache extraction | 1,271 | 3-4 hours | High (isolated concern) |
| `content_discovery.py` directory walker | 1,064 | 2-3 hours | Medium |
| `context.py` accessors extraction | 1,022 | 3-4 hours | Medium |

---

## Implementation Results (Phase 1)

Phase 1 (Critical Files 900+ lines) was completed on 2025-12-23. All 5 critical files were successfully modularized:

### Summary Table

| Original File | Before | After | Extracted Modules |
|--------------|--------|-------|-------------------|
| `knowledge_graph.py` | 1,314 | 947 | `graph_builder.py` (364), `graph_metrics.py` (203) |
| `pipeline/core.py` | 1,271 | 554 | `cache_checker.py` (102), `json_accumulator.py` (180), `autodoc_renderer.py` (446) |
| `content_discovery.py` | 1,064 | 596 | `directory_walker.py` (202), `content_parser.py` (315), `section_builder.py` (175) |
| `rendering/context.py` | 1,022 | 45 | `context/` subpackage with `data_wrappers.py`, `site_wrappers.py`, `section_context.py`, `menu_context.py` |
| `change_detector.py` | 897 | 337 | `file_detector.py` (238), `template_detector.py` (181), `taxonomy_detector.py` (150), `version_detector.py` (209) |

### Key Changes

1. **Composition over inheritance** - Each original class now composes focused sub-components
2. **Single responsibility** - Each extracted module has one clear purpose
3. **Backward compatibility** - Public APIs preserved; tests updated to use new internal structure
4. **All tests pass** - 91 directly affected tests updated and passing

### Files Created

**`bengal/analysis/`**:
- `graph_builder.py` - Graph construction logic
- `graph_metrics.py` - Metrics computation and dataclasses

**`bengal/rendering/pipeline/`**:
- `cache_checker.py` - Cache checking and storing logic
- `json_accumulator.py` - JSON data accumulation
- `autodoc_renderer.py` - Autodoc page rendering

**`bengal/discovery/`**:
- `directory_walker.py` - Directory walking and filtering
- `content_parser.py` - Content file parsing and validation
- `section_builder.py` - Page and section creation

**`bengal/rendering/context/`** (new subpackage):
- `__init__.py` - Re-exports and context builders
- `data_wrappers.py` - SmartDict, ParamsContext, CascadingParamsContext
- `site_wrappers.py` - SiteContext, ThemeContext, ConfigContext
- `section_context.py` - SectionContext
- `menu_context.py` - MenusContext

**`bengal/orchestration/incremental/`**:
- `file_detector.py` - Page and asset change detection
- `template_detector.py` - Template change detection
- `taxonomy_detector.py` - Taxonomy and autodoc detection
- `version_detector.py` - Version-related change detection

### Remaining Work (Phase 2 & 3)

High and Medium priority files remain for future work:
- Dashboard screens (~750 lines)
- Taxonomy orchestration (~740 lines)
- Health report (~704 lines)
- Debug commands (~702 lines)
- And others listed in the RFC

---

## Related RFCs

- `rfc-modularize-incremental-orchestrator.md` - Similar modularization effort (completed)
- `rfc-codebase-pattern-adoption.md` - Establishes patterns for code organization

---

## References

- [Single Responsibility Principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- [Composition over Inheritance](https://en.wikipedia.org/wiki/Composition_over_inheritance)
- Existing modularization: `bengal/orchestration/incremental/orchestrator.py` (392 lines, successfully modularized)
- Partial modularization: `bengal/rendering/pipeline/` (output.py, thread_local.py, toc.py, transforms.py already extracted)
