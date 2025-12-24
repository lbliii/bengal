# Implementation Plan: Codebase Pattern Adoption

**RFC**: `plan/drafted/rfc-codebase-pattern-adoption.md`  
**Status**: Ready for Implementation  
**Estimated Effort**: ~4 weeks (phased rollout)  
**Risk Level**: Low (additive changes, no API breaks)

---

## Summary

Systematically adopt Bengal's established architectural patterns across the codebase to eliminate pattern drift. This plan addresses 5 pattern categories: diagnostics sink, atomic writes, rich exceptions, query indexes, and output generator base class.

**Key insight**: All patterns already exist and are proven in production. This is wiring and consistency work, not new architecture.

---

## Prerequisites

- [ ] Read and understand the RFC: `plan/drafted/rfc-codebase-pattern-adoption.md`
- [ ] Verify existing patterns:
  - `bengal/core/diagnostics.py` — Diagnostics sink
  - `bengal/utils/atomic_write.py` — Atomic writes
  - `bengal/errors/` — Rich exceptions
  - `bengal/cache/query_index.py` — Query indexes
  - `bengal/utils/json_compat.py` — JSON utilities with atomic writes

---

## Phase 1: Critical Path (Week 1)

**Focus**: User-facing outputs and core model purity  
**Effort**: ~6 hours  
**Risk**: Low

---

### Task 1.1: ~~Atomic Writes in json_compat.py~~ ✅ Already Done

**File**: `bengal/utils/json_compat.py`  
**Status**: Already implemented - `dump()` uses `atomic_write_text()`

No changes needed.

---

### Task 1.2: Atomic Writes in postprocess/redirects.py

**File**: `bengal/postprocess/redirects.py`  
**Priority**: P0 (user-facing outputs)

**Changes**:

1. Add import at top of file:

```python
from bengal.utils.atomic_write import atomic_write_text
```

2. Update line ~226 (HTML redirect write):

```python
# BEFORE
output_path.write_text(html, encoding="utf-8")

# AFTER
atomic_write_text(output_path, html)
```

3. Update line ~302 (_redirects file write):

```python
# BEFORE
redirects_path.write_text("\n".join(lines), encoding="utf-8")

# AFTER
atomic_write_text(redirects_path, "\n".join(lines))
```

**Validation**:
- [ ] Build site with redirects enabled
- [ ] Verify `_redirects` file and HTML redirects exist

---

### Task 1.3: Atomic Writes in postprocess/special_pages.py

**File**: `bengal/postprocess/special_pages.py`  
**Priority**: P0 (user-facing outputs)

**Changes**:

1. Add import at top of file:

```python
from bengal.utils.atomic_write import atomic_write_text
```

2. Update line ~461 (graph HTML write):

```python
# BEFORE
output_path.write_text(html, encoding="utf-8")

# AFTER
atomic_write_text(output_path, html)
```

3. Update line ~469 (graph JSON write):

```python
# BEFORE
json_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")

# AFTER
from bengal.utils.json_compat import dump as json_dump
json_dump(graph_data, json_path, indent=2)  # Already atomic via Task 1.1
```

**Validation**:
- [ ] Build site with knowledge graph enabled
- [ ] Verify graph.html and graph.json exist in output

---

### Task 1.4: Atomic Writes in output_formats/lunr_index_generator.py

**File**: `bengal/postprocess/output_formats/lunr_index_generator.py`  
**Priority**: P0 (search index is critical)

**Changes**:

1. Add import:

```python
from bengal.utils.atomic_write import atomic_write_text
```

2. Update line ~168:

```python
# BEFORE
output_path.write_text(index_json, encoding="utf-8")

# AFTER
atomic_write_text(output_path, index_json)
```

**Validation**:
- [ ] Build site with search enabled
- [ ] Verify lunr index exists and is valid JSON

---

### Task 1.5: Diagnostics Sink in core/nav_tree.py

**File**: `bengal/core/nav_tree.py`  
**Priority**: High (core model purity)

**Changes**:

1. Add import:

```python
from bengal.core.diagnostics import emit
```

2. Update line ~198:

```python
# BEFORE
logger.warning(
    "NavTree URL collision detected: url=%s | existing_id=%s",
    url, existing_id
)

# AFTER
emit(
    self,
    "warning",
    "nav_url_collision",
    url=url,
    existing_id=existing_id,
    new_id=new_id,
)
```

**Validation**:
- [ ] Build site with URL collision scenario
- [ ] Verify warning appears in diagnostics output (not direct log)

---

### Task 1.6: Diagnostics Sink in core/theme/resolution.py

**File**: `bengal/core/theme/resolution.py`  
**Priority**: High (7 occurrences)

**Changes**:

1. Add import at top:

```python
from bengal.core.diagnostics import emit
```

2. Replace all 7 logger.debug() calls with emit():

| Line | Current | New Code |
|------|---------|----------|
| ~50 | `logger.debug("theme_manifest_read_failed", ...)` | `emit(self, "debug", "theme_manifest_read_failed", ...)` |
| ~70 | `logger.debug("theme_manifest_read_failed", ...)` | `emit(self, "debug", "theme_manifest_read_failed", ...)` |
| ~78 | `logger.debug("theme_package_resolve_failed", ...)` | `emit(self, "debug", "theme_package_resolve_failed", ...)` |
| ~94 | `logger.debug("theme_manifest_read_failed", ...)` | `emit(self, "debug", "theme_manifest_read_failed", ...)` |
| ~174 | `logger.debug("theme_templates_resolution_installed_failed", ...)` | `emit(self, "debug", "theme_templates_resolution_installed_failed", ...)` |
| ~213 | `logger.debug("installed_theme_assets_resolution_failed", ...)` | `emit(self, "debug", "installed_theme_assets_resolution_failed", ...)` |
| ~222 | `logger.debug("bundled_theme_assets_resolution_failed", ...)` | `emit(self, "debug", "bundled_theme_assets_resolution_failed", ...)` |

**Validation**:
- [ ] `uv run pytest tests/unit/core/theme/ -v`
- [ ] Verify no logger.* calls remain in file: `grep -n "logger\." bengal/core/theme/resolution.py`

---

### Task 1.7: Diagnostics Sink in core/theme/registry.py

**File**: `bengal/core/theme/registry.py`  
**Priority**: High (15 occurrences)

**Changes**:

1. Add import at top:

```python
from bengal.core.diagnostics import emit
```

2. Replace all 15 logger.debug() calls with emit() following the same pattern as Task 1.6.

**Note**: The emit() helper will resolve the sink via `obj._diagnostics` or `obj._site.diagnostics`.

**Validation**:
- [ ] `uv run pytest tests/unit/core/theme/ -v`
- [ ] Verify no logger.* calls remain: `grep -n "logger\." bengal/core/theme/registry.py`
- [ ] `grep -c "emit(" bengal/core/theme/registry.py` returns 15

---

### Task 1.8: Diagnostics Sink in core/output/collector.py

**File**: `bengal/core/output/collector.py`  
**Priority**: Medium (1 occurrence)

**Changes**:

1. Add import:

```python
from bengal.core.diagnostics import emit
```

2. Update line ~195:

```python
# BEFORE
logger.warning("output_tracking_empty", ...)

# AFTER
emit(self, "warning", "output_tracking_empty", ...)
```

**Validation**:
- [ ] `grep -n "logger\." bengal/core/output/collector.py` returns 0

---

### Phase 1 Completion Checklist

- [ ] All files in `public/` written atomically
- [ ] `grep -r "logger\." bengal/core/ --include="*.py" | grep -v diagnostics.py` returns 0
- [ ] All existing tests pass: `uv run pytest tests/ -v`
- [ ] Build Bengal docs site successfully

---

## Phase 2: Error Handling (Week 2)

**Focus**: Rich exceptions and error recovery  
**Effort**: ~10.5 hours  
**Risk**: Medium

---

### Task 2.1: Add Knowledge Graph Error Codes

**File**: `bengal/errors/codes.py`  
**Priority**: P0 (required for subsequent tasks)

**Changes**:

Add new error codes after existing definitions:

```python
# Knowledge Graph errors (G001-G005)
class GraphErrorCode:
    G001 = "graph_node_not_found"
    G002 = "graph_edge_invalid"
    G003 = "graph_cycle_detected"
    G004 = "graph_disconnected_component"
    G005 = "graph_analysis_failed"
```

**Validation**:
- [ ] Import successfully: `from bengal.errors.codes import GraphErrorCode`

---

### Task 2.2: Rich Exceptions in analysis/knowledge_graph.py

**File**: `bengal/analysis/knowledge_graph.py`  
**Priority**: High (8 occurrences)

**Changes**:

1. Add imports:

```python
from bengal.errors import BengalError, ErrorDebugPayload
from bengal.errors.codes import GraphErrorCode
```

2. Replace generic ValueError raises with rich exceptions:

```python
# BEFORE
raise ValueError(f"Node not found: {node}")

# AFTER
raise BengalError(
    f"Node not found in knowledge graph: {node}",
    code=GraphErrorCode.G001,
    suggestion="Check that the page exists and is not excluded from the graph",
    file_path=node.source_path if hasattr(node, 'source_path') else None,
    debug_payload=ErrorDebugPayload(
        context={"graph_size": len(self._nodes), "node_id": str(node)},
    ),
)
```

**Validation**:
- [ ] `grep -c "raise ValueError" bengal/analysis/knowledge_graph.py` returns 0
- [ ] `grep -c "BengalError" bengal/analysis/knowledge_graph.py` returns 8
- [ ] `uv run pytest tests/unit/analysis/ -v`

---

### Task 2.3: Rich Exceptions in analysis/graph_visualizer.py

**File**: `bengal/analysis/graph_visualizer.py`  
**Priority**: Medium (1 occurrence)

**Changes**:

Follow same pattern as Task 2.2. Replace ValueError with BengalError including:
- Appropriate GraphErrorCode
- Suggestion for resolution
- Debug payload with relevant context

**Validation**:
- [ ] `grep -c "raise ValueError" bengal/analysis/graph_visualizer.py` returns 0

---

### Task 2.4: Rich Exceptions in analysis/graph_reporting.py

**File**: `bengal/analysis/graph_reporting.py`  
**Priority**: Medium (1 occurrence)

**Validation**:
- [ ] `grep -c "raise ValueError" bengal/analysis/graph_reporting.py` returns 0

---

### Task 2.5: Rich Exceptions in analysis/graph_analysis.py

**File**: `bengal/analysis/graph_analysis.py`  
**Priority**: Medium (1 occurrence)

**Validation**:
- [ ] `grep -c "raise ValueError" bengal/analysis/graph_analysis.py` returns 0

---

### Task 2.6: Rich Exceptions in core/nav_tree.py

**File**: `bengal/core/nav_tree.py`  
**Priority**: Medium (1 RuntimeError)

**Changes**:

Replace RuntimeError with BengalError with navigation-specific error code.

**Validation**:
- [ ] `grep -c "raise RuntimeError" bengal/core/nav_tree.py` returns 0

---

### Task 2.7: Audit Bare Excepts in Rendering Pipeline

**File**: `bengal/rendering/` (multiple files)  
**Priority**: High (critical path)

**Discovery**:

```bash
grep -rn "except.*:" bengal/rendering/ | grep -v "except.*Error" | head -20
```

**Changes**:

For each bare `except:` or overly broad `except Exception:`:
1. Identify specific exception types that can occur
2. Add specific handlers for recoverable cases
3. Add logging/diagnostics for debugging

**Note**: Not all bare excepts need fixing. Focus on:
- Hot paths (rendering pipeline)
- User-facing operations
- Places where specific recovery is possible

**Validation**:
- [ ] Document which bare excepts were kept and why
- [ ] No bare `except:` (without type) in `bengal/rendering/pipeline/core.py`

---

### Phase 2 Completion Checklist

- [ ] `grep -r "raise ValueError" bengal/analysis/` returns 0
- [ ] All knowledge graph errors include investigation helpers
- [ ] `uv run pytest tests/unit/analysis/ -v` passes
- [ ] Build site with graph enabled—errors are actionable

---

## Phase 3: Performance (Week 3)

**Focus**: Query indexes and output generator consolidation  
**Effort**: ~8 hours  
**Risk**: Low-Medium

---

### Task 3.1: Query Indexes in health/validators/navigation.py

**File**: `bengal/health/validators/navigation.py`  
**Priority**: Medium (4 page iterations)

**Discovery**: Identify iteration patterns:

```bash
grep -n "for.*in.*site\.pages" bengal/health/validators/navigation.py
```

**Changes**:

Where iterations filter by section or other indexed criteria:

```python
# BEFORE
def validate(self, site):
    for page in site.pages:  # O(n)
        if page.section == "docs":
            self._check_page(page)

# AFTER
from bengal.cache.query_index import resolve_pages

def validate(self, site):
    docs_paths = site.indexes.section.get("docs")  # O(1)
    docs_pages = resolve_pages(docs_paths, site)   # O(k) where k << n
    for page in docs_pages:
        self._check_page(page)
```

**Note**: Some iterations are necessary (e.g., when checking all pages). Only optimize when filtering by indexed criteria.

**Validation**:
- [ ] `uv run pytest tests/unit/health/ -v`
- [ ] Benchmark: `time uv run bengal health check site/` before/after

---

### Task 3.2: Query Indexes in health/validators/links.py

**File**: `bengal/health/validators/links.py`  
**Priority**: Medium (3 page iterations)

Follow same pattern as Task 3.1.

---

### Task 3.3: Query Indexes in health/validators/url_collisions.py

**File**: `bengal/health/validators/url_collisions.py`  
**Priority**: Medium (2 page iterations)

Follow same pattern as Task 3.1.

---

### Task 3.4: Query Indexes in health/validators/tracks.py

**File**: `bengal/health/validators/tracks.py`  
**Priority**: Medium (2 page iterations)

Follow same pattern as Task 3.1.

---

### Task 3.5: Output Generator Base Class

**File**: `bengal/postprocess/output_formats/base.py` (new file)  
**Priority**: Medium

**Create**:

```python
"""Base class for output format generators."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.atomic_write import atomic_write_text, atomic_write_bytes
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class BaseOutputGenerator(ABC):
    """
    Base class for output format generators.

    Provides:
    - Atomic file writes (crash-safe)
    - Progress reporting integration
    - Error handling with recovery
    - BuildContext integration for accumulated data
    """

    def __init__(self, site: "Site", build_context: "BuildContext | None" = None):
        self.site = site
        self.build_context = build_context
        self.logger = get_logger(self.__class__.__module__)

    @abstractmethod
    def generate(self) -> int:
        """
        Generate output files.

        Returns:
            Number of files generated
        """
        ...

    def write_text(self, path: Path, content: str) -> None:
        """Write text file atomically."""
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, content)

    def write_bytes(self, path: Path, content: bytes) -> None:
        """Write binary file atomically."""
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(path, content)

    def get_accumulated_data(self) -> list | None:
        """Get accumulated page data from build context."""
        if self.build_context:
            return getattr(self.build_context, '_accumulated_page_json', None)
        return None
```

---

### Task 3.6: Refactor Generators to Use Base Class

**Files**:
- `bengal/postprocess/output_formats/txt_generator.py`
- `bengal/postprocess/output_formats/json_generator.py`
- `bengal/postprocess/output_formats/llm_txt_generator.py`
- `bengal/postprocess/output_formats/index_generator.py`
- `bengal/postprocess/output_formats/lunr_index_generator.py`

**Changes** (per generator):

```python
# BEFORE
class PageTxtGenerator:
    def __init__(self, site: Site):
        self.site = site

# AFTER
from bengal.postprocess.output_formats.base import BaseOutputGenerator

class PageTxtGenerator(BaseOutputGenerator):
    def __init__(self, site: Site, build_context: BuildContext | None = None):
        super().__init__(site, build_context)
```

**Validation**:
- [ ] All generators use base class
- [ ] All file writes use `self.write_text()` or `self.write_bytes()`
- [ ] `uv run pytest tests/ -k "generator" -v`

---

### Phase 3 Completion Checklist

- [ ] Health checks on 10k site < 2s (benchmark)
- [ ] All output generators use atomic writes via base class

---

## Phase 4: Cleanup (Week 4)

**Focus**: Remaining violations and documentation  
**Effort**: ~10 hours  
**Risk**: Low

---

### Task 4.1: Atomic Writes in CLI Commands

**Files**: `bengal/cli/commands/theme.py` (14), `bengal/cli/commands/config.py` (8)

**Changes**:

Add atomic writes for all user-facing file outputs:

```python
from bengal.utils.atomic_write import atomic_write_text

# Replace all .write_text() calls with atomic_write_text()
```

**Note**: CLI commands are lower priority since they're interactive and user can retry.

**Validation**:
- [ ] `grep -c "\.write_text\(" bengal/cli/commands/theme.py` returns 0
- [ ] `grep -c "\.write_text\(" bengal/cli/commands/config.py` returns 0

---

### Task 4.2: Atomic Writes in debug/dependency_visualizer.py

**File**: `bengal/debug/dependency_visualizer.py` (2 occurrences)

Follow same pattern as Task 4.1.

---

### Task 4.3: Atomic Writes in content_layer/manager.py

**File**: `bengal/content_layer/manager.py` (2 occurrences)

Follow same pattern as Task 4.1.

---

### Task 4.4: Atomic Writes in utils/swizzle.py

**File**: `bengal/utils/swizzle.py` (3 occurrences)

Follow same pattern as Task 4.1.

---

### Task 4.5: Audit Remaining Bare Excepts

**Discovery**:

```bash
grep -rn "except:" bengal/ --include="*.py" | wc -l
```

**Changes**:

Sample and fix the highest-impact bare excepts. Focus on:
1. `bengal/orchestration/` — Build pipeline
2. `bengal/cache/` — Cache operations
3. `bengal/rendering/` — Rendering (if not addressed in Phase 2)

**Validation**:
- [ ] Document decisions for each reviewed file
- [ ] Critical paths have specific exception handling

---

### Task 4.6: Update CONTRIBUTING.md

**File**: `CONTRIBUTING.md`

**Add section**:

```markdown
## Architectural Patterns

Bengal follows these patterns consistently. Please adopt them in new code:

### Pure Core Models

Core models in `bengal/core/` must not have side effects. Use the diagnostics sink:

```python
from bengal.core.diagnostics import emit

emit(self, "warning", "diagnostic_code", key=value)
```

### Atomic File Writes

All file writes must be crash-safe:

```python
from bengal.utils.atomic_write import atomic_write_text

atomic_write_text(path, content)
```

### Rich Exceptions

Exceptions must include context and suggestions:

```python
from bengal.errors import BengalError

raise BengalError(
    "Description of what went wrong",
    code=ErrorCode.X001,
    suggestion="How to fix it",
)
```

### Query Indexes

Use indexes for O(1) lookups instead of iterating all pages:

```python
paths = site.indexes.section.get("docs")
pages = resolve_pages(paths, site)
```

### JSON Serialization

Use json_compat for atomic file writes:

```python
from bengal.utils.json_compat import dump, load, dumps, loads
```

---

### Phase 4 Completion Checklist

- [ ] All CLI file writes are atomic
- [ ] Bare except audit documented
- [ ] CONTRIBUTING.md updated with pattern guidelines
- [ ] All tests pass: `uv run pytest tests/ -v`

---

## Testing Plan

### Unit Tests to Add

```
tests/unit/test_pattern_adoption.py
├── test_atomic_write_in_redirects
├── test_atomic_write_in_special_pages
├── test_atomic_write_in_lunr_generator
├── test_json_compat_uses_atomic_write
├── test_nav_tree_emits_diagnostics
├── test_theme_registry_emits_diagnostics
├── test_knowledge_graph_rich_exceptions
└── test_output_generator_base_class
```

### Integration Tests

```bash
# Full build with all patterns
uv run bengal build site/ --verbose

# Health checks on large site
uv run bengal health check site/

# Cache operations
rm -rf .bengal-cache && uv run bengal build site/
uv run bengal build site/  # Should use cache
```

### Benchmark Tests

```bash
# Before/after timing
time uv run bengal health check site/
time uv run bengal build site/ --no-cache
```

---

## Verification Steps

### Phase 1 Verification

```bash
# No direct logging in core/
grep -r "logger\." bengal/core/ --include="*.py" | grep -v diagnostics.py | wc -l
# Expected: 0

# Atomic writes in postprocess/
grep -r "\.write_text\(" bengal/postprocess/ --include="*.py" | wc -l
# Expected: 0 (all migrated to atomic_write_text)
```

### Phase 2 Verification

```bash
# No generic exceptions in analysis/
grep -r "raise ValueError" bengal/analysis/ --include="*.py" | wc -l
# Expected: 0

# Rich exceptions present
grep -r "BengalError" bengal/analysis/ --include="*.py" | wc -l
# Expected: 11+
```

### Phase 3 Verification

```bash
# All generators use base class
grep -r "BaseOutputGenerator" bengal/postprocess/output_formats/ --include="*.py" | wc -l
# Expected: 5+
```

---

## Rollback Plan

Each task is independently reversible:

1. **Atomic writes**: Revert to `.write_text()` (same behavior, just less safe)
2. **Diagnostics sink**: Revert to `logger.*()` (same output)
3. **Rich exceptions**: Revert to generic exceptions (same types)
4. **Query indexes**: Revert to iteration (same results, slower)
5. **Base class**: Revert inheritance (same functionality)

Feature flags are not needed—all changes are internal implementation details with identical external behavior.

---

## Commit Strategy

```
# Phase 1: Critical Path
feat(postprocess): atomic writes in redirects.py
feat(postprocess): atomic writes in special_pages.py
feat(postprocess): atomic writes in lunr_index_generator.py
refactor(core): diagnostics sink in nav_tree.py
refactor(core): diagnostics sink in theme/resolution.py
refactor(core): diagnostics sink in theme/registry.py
refactor(core): diagnostics sink in output/collector.py

# Phase 2: Error Handling
feat(errors): add knowledge graph error codes G001-G005
refactor(analysis): rich exceptions in knowledge_graph.py
refactor(analysis): rich exceptions in graph_visualizer.py
refactor(analysis): rich exceptions in graph_reporting.py
refactor(analysis): rich exceptions in graph_analysis.py
refactor(core): rich exception in nav_tree.py
refactor(rendering): audit and fix bare excepts in pipeline

# Phase 3: Performance
perf(health): query indexes in navigation validator
perf(health): query indexes in links validator
perf(health): query indexes in url_collisions validator
perf(health): query indexes in tracks validator
feat(postprocess): output generator base class
refactor(postprocess): generators extend base class

# Phase 4: Cleanup
feat(cli): atomic writes in theme commands
feat(cli): atomic writes in config commands
feat(debug): atomic writes in dependency_visualizer
feat(content_layer): atomic writes in manager
feat(utils): atomic writes in swizzle
docs: update CONTRIBUTING.md with pattern guidelines
```

---

## Success Metrics

| Metric | Before | After | Measurement |
|--------|--------|-------|-------------|
| Core model logger calls | 25 | 0 | `grep -r "logger\." bengal/core/` |
| Non-atomic writes in postprocess/ | 5 | 0 | Manual audit |
| Generic exceptions in analysis/ | 11 | 0 | `grep -r "raise ValueError" bengal/analysis/` |
| Health check time (10k site) | ~5s | <2s | Benchmark suite |
| Output generators with base class | 0 | 5 | Code inspection |

---

## Expected Outcomes

| Change | Impact |
|--------|--------|
| Atomic writes | No partial files on crash |
| Diagnostics sink | Testable core models, decoupled from CLI |
| Rich exceptions | Faster debugging, actionable errors |
| Query indexes | 2-3x faster health checks |
| Base class | Consistent generator behavior, less code |

---

## Files Changed Summary

| Phase | Files | Lines Changed |
|-------|-------|---------------|
| Phase 1 | 8 | ~100 |
| Phase 2 | 7 | ~200 |
| Phase 3 | 10 | ~300 |
| Phase 4 | 6 | ~150 |
| **Total** | **~31** | **~750** |

---

## Implementation Order

**Week 1 (Phase 1)**:
1. Task 1.1: ~~json_compat atomic writes~~ (already done)
2. Tasks 1.2-1.4: postprocess atomic writes (user-facing)
3. Tasks 1.5-1.8: diagnostics sink (core model purity)

**Week 2 (Phase 2)**:
1. Task 2.1: error codes (required for exceptions)
2. Tasks 2.2-2.6: rich exceptions (better debugging)
3. Task 2.7: bare except audit (critical path safety)

**Week 3 (Phase 3)**:
1. Tasks 3.1-3.4: query indexes (performance)
2. Tasks 3.5-3.6: base class (consistency)

**Week 4 (Phase 4)**:
1. Tasks 4.1-4.4: remaining atomic writes
2. Task 4.5: bare except audit
3. Task 4.6: documentation update
