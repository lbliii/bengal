# RFC: Modularize Large Files

**Status**: Draft  
**Created**: 2025-01-23  
**Author**: AI Assistant  
**Priority**: P2 (Medium)  
**Scope**: Multiple large files across the codebase

---

## Summary

Several files in the codebase have grown beyond maintainable size (500+ lines of code, excluding docstrings). This RFC proposes a systematic approach to modularizing these files to improve maintainability, testability, and code organization.

---

## Problem Statement

A codebase analysis identified **20 files with 500+ lines of code** (excluding docstrings), with the largest being **1,116 lines**. Large files present several problems:

### Symptoms

1. **Hard to navigate** - Finding specific functionality requires scrolling through hundreds of lines
2. **Difficult to test** - Large classes/modules mix concerns, making unit testing harder
3. **Merge conflicts** - Multiple developers working on the same large file increases conflict frequency
4. **Cognitive overload** - Understanding the full file requires holding too much context
5. **Tight coupling** - Related but distinct concerns are bundled together

### Current State

**Critical (700+ lines):**
- `bengal/rendering/pipeline/core.py` - **1,116 lines** (rendering pipeline orchestration)
- `bengal/discovery/content_discovery.py` - **826 lines** (content discovery logic)
- `bengal/analysis/knowledge_graph.py` - **797 lines** (knowledge graph construction/analysis)
- `bengal/rendering/context.py` - **769 lines** (rendering context management)
- `bengal/orchestration/incremental/change_detector.py` - **766 lines** (change detection)
- `bengal/cli/dashboard/screens.py` - **749 lines** (dashboard UI screens)
- `bengal/orchestration/taxonomy.py` - **739 lines** (taxonomy orchestration)

**High Priority (600-699 lines):**
- `bengal/health/report.py` - **704 lines**
- `bengal/cli/commands/debug.py` - **702 lines**
- `bengal/orchestration/build/__init__.py` - **688 lines**
- `bengal/health/autofix.py` - **686 lines**
- `bengal/orchestration/asset.py` - **686 lines**
- `bengal/orchestration/content.py` - **684 lines**
- `bengal/cli/commands/theme.py` - **673 lines**
- `bengal/core/page/proxy.py` - **630 lines**
- `bengal/rendering/errors.py` - **624 lines**
- `bengal/orchestration/render.py` - **609 lines**
- `bengal/autodoc/extractors/python/extractor.py` - **607 lines**

**Medium Priority (500-599 lines):**
- `bengal/autodoc/docstring_parser.py` - **594 lines**
- `bengal/postprocess/social_cards.py` - **594 lines**

---

## Proposed Solution

### Principles

1. **Single Responsibility** - Each module should have one clear purpose
2. **Preserve Public API** - Maintain backward compatibility during refactoring
3. **Incremental Migration** - Modularize one file at a time, starting with the largest
4. **Composition over Inheritance** - Use composition to combine focused modules
5. **Test-Driven** - Ensure tests pass before and after modularization

### Modularization Patterns

#### Pattern 1: Extract Specialized Classes

**Before:**
```python
# core.py (1116 lines)
class RenderingPipeline:
    def __init__(self):
        # 50 lines of initialization

    def stage_parse(self):
        # 200 lines of parsing logic

    def stage_transform(self):
        # 300 lines of transformation logic

    def stage_render(self):
        # 400 lines of rendering logic

    def stage_postprocess(self):
        # 166 lines of post-processing
```

**After:**
```python
# pipeline/__init__.py
from bengal.rendering.pipeline.core import RenderingPipeline
__all__ = ["RenderingPipeline"]

# pipeline/core.py (~150 lines)
class RenderingPipeline:
    def __init__(self):
        self._parser = ParseStage()
        self._transformer = TransformStage()
        self._renderer = RenderStage()
        self._postprocessor = PostprocessStage()

    def execute(self, page):
        parsed = self._parser.process(page)
        transformed = self._transformer.process(parsed)
        rendered = self._renderer.process(transformed)
        return self._postprocessor.process(rendered)

# pipeline/stages/parse.py (~200 lines)
class ParseStage:
    def process(self, page):
        # Focused parsing logic

# pipeline/stages/transform.py (~300 lines)
class TransformStage:
    def process(self, parsed):
        # Focused transformation logic

# pipeline/stages/render.py (~400 lines)
class RenderStage:
    def process(self, transformed):
        # Focused rendering logic

# pipeline/stages/postprocess.py (~166 lines)
class PostprocessStage:
    def process(self, rendered):
        # Focused post-processing logic
```

#### Pattern 2: Extract Utility Modules

**Before:**
```python
# content_discovery.py (826 lines)
class ContentDiscovery:
    def discover_markdown(self):
        # 200 lines

    def discover_assets(self):
        # 150 lines

    def discover_templates(self):
        # 100 lines

    def discover_config(self):
        # 100 lines

    def _normalize_path(self):
        # 50 lines

    def _validate_content(self):
        # 50 lines

    def _build_index(self):
        # 176 lines
```

**After:**
```python
# discovery/__init__.py
from bengal.discovery.content_discovery import ContentDiscovery
__all__ = ["ContentDiscovery"]

# discovery/content_discovery.py (~200 lines)
class ContentDiscovery:
    def __init__(self):
        self._markdown_discoverer = MarkdownDiscoverer()
        self._asset_discoverer = AssetDiscoverer()
        self._template_discoverer = TemplateDiscoverer()
        self._config_discoverer = ConfigDiscoverer()

    def discover_all(self):
        return {
            "markdown": self._markdown_discoverer.discover(),
            "assets": self._asset_discoverer.discover(),
            "templates": self._template_discoverer.discover(),
            "config": self._config_discoverer.discover(),
        }

# discovery/markdown.py (~200 lines)
class MarkdownDiscoverer:
    def discover(self):
        # Focused markdown discovery

# discovery/assets.py (~150 lines)
class AssetDiscoverer:
    def discover(self):
        # Focused asset discovery

# discovery/utils.py (~100 lines)
def normalize_path(path):
    # Shared utilities

def validate_content(content):
    # Shared utilities

def build_index(items):
    # Shared utilities
```

#### Pattern 3: Extract Feature Modules

**Before:**
```python
# knowledge_graph.py (797 lines)
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
        # 147 lines
```

**After:**
```python
# analysis/knowledge_graph/__init__.py
from bengal.analysis.knowledge_graph.core import KnowledgeGraph
__all__ = ["KnowledgeGraph"]

# analysis/knowledge_graph/core.py (~150 lines)
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

# analysis/knowledge_graph/builder.py (~200 lines)
class GraphBuilder:
    def build(self):
        # Graph construction logic

# analysis/knowledge_graph/analyzer.py (~150 lines)
class GraphAnalyzer:
    def analyze(self, graph):
        # Analysis logic

# analysis/knowledge_graph/metrics.py (~150 lines)
class GraphMetrics:
    def calculate(self, graph):
        # Metrics calculation

# analysis/knowledge_graph/reporting.py (~150 lines)
class GraphReporter:
    def generate_report(self, graph, analysis, metrics):
        # Report generation

# analysis/knowledge_graph/visualization.py (~147 lines)
class GraphVisualizer:
    def visualize(self, graph):
        # Visualization logic
```

---

## Implementation Plan

### Phase 1: Critical Files (700+ lines)

**Priority Order:**
1. `bengal/rendering/pipeline/core.py` (1,116 lines) - **Highest impact**
2. `bengal/discovery/content_discovery.py` (826 lines)
3. `bengal/analysis/knowledge_graph.py` (797 lines)
4. `bengal/rendering/context.py` (769 lines)
5. `bengal/orchestration/incremental/change_detector.py` (766 lines)
6. `bengal/cli/dashboard/screens.py` (749 lines)
7. `bengal/orchestration/taxonomy.py` (739 lines)

### Phase 2: High Priority Files (600-699 lines)

After Phase 1 is complete, proceed with the 11 files in the 600-699 line range.

### Phase 3: Medium Priority Files (500-599 lines)

Complete modularization with the remaining files.

### Per-File Process

For each file:

1. **Analysis** (1-2 hours)
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

---

## Detailed File Analysis

### 1. `bengal/rendering/pipeline/core.py` (1,116 lines)

**Current Structure:**
- Pipeline orchestration
- Multiple rendering stages
- Error handling
- Caching logic

**Proposed Structure:**
```
bengal/rendering/pipeline/
├── __init__.py              # Public API
├── core.py                  # Main pipeline orchestrator (~150 lines)
├── stages/
│   ├── __init__.py
│   ├── base.py              # Base stage class
│   ├── parse.py             # Parse stage (~200 lines)
│   ├── transform.py         # Transform stage (~300 lines)
│   ├── render.py            # Render stage (~400 lines)
│   └── postprocess.py       # Postprocess stage (~166 lines)
└── errors.py                # Pipeline-specific errors
```

### 2. `bengal/discovery/content_discovery.py` (826 lines)

**Current Structure:**
- Markdown file discovery
- Asset discovery
- Template discovery
- Config discovery
- Path normalization utilities
- Content validation

**Proposed Structure:**
```
bengal/discovery/
├── __init__.py              # Public API
├── content_discovery.py     # Main discovery orchestrator (~200 lines)
├── discoverers/
│   ├── __init__.py
│   ├── markdown.py          # Markdown discovery (~200 lines)
│   ├── assets.py            # Asset discovery (~150 lines)
│   ├── templates.py         # Template discovery (~100 lines)
│   └── config.py            # Config discovery (~100 lines)
└── utils.py                 # Shared utilities (~76 lines)
```

### 3. `bengal/analysis/knowledge_graph.py` (797 lines)

**Current Structure:**
- Graph construction
- Connection analysis
- Metrics calculation
- Report generation
- Visualization

**Proposed Structure:**
```
bengal/analysis/knowledge_graph/
├── __init__.py              # Public API
├── core.py                  # Main KnowledgeGraph class (~150 lines)
├── builder.py               # Graph construction (~200 lines)
├── analyzer.py              # Connection analysis (~150 lines)
├── metrics.py               # Metrics calculation (~150 lines)
├── reporting.py             # Report generation (~150 lines)
└── visualization.py         # Visualization (~147 lines)
```

### 4. `bengal/rendering/context.py` (769 lines)

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
├── builder.py               # Context building logic (~250 lines)
├── accessors.py             # Context accessors (~200 lines)
└── cache.py                 # Context caching (~119 lines)
```

### 5. `bengal/orchestration/incremental/change_detector.py` (766 lines)

**Current Structure:**
- File change detection
- Section change detection
- Dependency change detection
- Cache comparison logic

**Proposed Structure:**
```
bengal/orchestration/incremental/change_detection/
├── __init__.py              # Public API
├── detector.py              # Main change detector (~200 lines)
├── file_detector.py         # File-level detection (~200 lines)
├── section_detector.py      # Section-level detection (~200 lines)
├── dependency_detector.py   # Dependency detection (~166 lines)
└── cache_comparator.py      # Cache comparison utilities
```

### 6. `bengal/cli/dashboard/screens.py` (749 lines)

**Current Structure:**
- Multiple dashboard screens
- Screen navigation
- Screen state management

**Proposed Structure:**
```
bengal/cli/dashboard/screens/
├── __init__.py              # Public API
├── base.py                  # Base screen class (~100 lines)
├── home.py                  # Home screen (~150 lines)
├── build.py                 # Build screen (~150 lines)
├── health.py                # Health screen (~150 lines)
├── serve.py                 # Serve screen (~100 lines)
└── navigation.py            # Screen navigation (~99 lines)
```

### 7. `bengal/orchestration/taxonomy.py` (739 lines)

**Current Structure:**
- Taxonomy building
- Taxonomy processing
- Taxonomy indexing
- Taxonomy queries

**Proposed Structure:**
```
bengal/orchestration/taxonomy/
├── __init__.py              # Public API
├── core.py                  # Main taxonomy orchestrator (~200 lines)
├── builder.py               # Taxonomy building (~200 lines)
├── processor.py             # Taxonomy processing (~200 lines)
└── index.py                 # Taxonomy indexing/queries (~139 lines)
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

---

## Success Criteria

1. **Code Organization**
   - No files exceed 500 lines of code (excluding docstrings)
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
**Mitigation:** Benchmark before/after, profile if needed

### Risk 4: Scope Creep
**Mitigation:** Focus on modularization only, defer feature changes to separate PRs

---

## Alternatives Considered

### Alternative 1: Do Nothing
**Rejected:** Files will continue to grow, making future refactoring harder

### Alternative 2: Split by Functionality Only
**Rejected:** Doesn't address the root cause of mixed concerns

### Alternative 3: Complete Rewrite
**Rejected:** Too risky, loses existing behavior and tests

---

## Related RFCs

- `rfc-modularize-incremental-orchestrator.md` - Similar modularization effort
- `rfc-codebase-pattern-adoption.md` - Establishes patterns for code organization

---

## Open Questions

1. Should we set a hard limit on file size (e.g., 500 lines) going forward?
2. Should we add linting rules to prevent files from growing too large?
3. How should we prioritize modularization vs. feature work?
4. Should we create a "modularization" label for tracking these PRs?

---

## References

- [Single Responsibility Principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- [Composition over Inheritance](https://en.wikipedia.org/wiki/Composition_over_inheritance)
- Existing modularization: `bengal/orchestration/incremental/orchestrator.py` (392 lines, successfully modularized)
