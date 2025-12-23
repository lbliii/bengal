# RFC: Codebase Pattern Adoption

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Subsystems**: core/, postprocess/, analysis/, health/, errors/

---

## Executive Summary

Adopt Bengal's established architectural patterns consistently across the codebase. This RFC addresses pattern drift where newer code doesn't follow the patterns established in core modules, leading to maintenance burden, subtle bugs, and performance issues.

**Impact**: Improved code consistency, better error handling, crash-safe file operations, and maintained architectural integrity.

**Scope**: 8 pattern categories across ~100 files, prioritized by risk and effort.

---

## Problem Statement

### Current State

Bengal has excellent architectural patterns established in core modules:

| Pattern | Where Established | Purpose |
|---------|-------------------|---------|
| Diagnostics Sink | `bengal/core/diagnostics.py` | Pure core models without logging side effects |
| Atomic Writes | `bengal/utils/atomic_write.py` | Crash-safe file operations |
| Rich Exceptions | `bengal/errors/` | Contextual, actionable error messages |
| Query Indexes | `bengal/cache/query_index.py` | O(1) page lookups |
| Cacheable Protocol | `bengal/cache/cacheable.py` | Type-safe serialization |
| Error Recovery | `bengal/errors/recovery.py` | Graceful degradation |
| Thread-Local Cache | `bengal/utils/thread_local.py` | Per-thread expensive object reuse |
| Orchestrator Pattern | `bengal/orchestration/` | Separation of coordination from implementation |

### The Problem

**Pattern drift** has occurred where:

1. **Core models log directly** — 25 `logger.*()` calls in `bengal/core/` violate the "pure core" principle
2. **File writes aren't atomic** — 65 direct `.write_text()` calls risk partial writes on crash
3. **Exceptions lack context** — 16 generic `ValueError`/`TypeError` raises without suggestions
4. **O(n) iterations abound** — 37 files iterate `for page in site.pages` when indexes exist
5. **Bare excepts everywhere** — 772 `except ...:` clauses without specific handling

### Impact

| Issue | Risk | Frequency |
|-------|------|-----------|
| Non-atomic writes | Output corruption on crash | 65 occurrences |
| Direct logging in core | Untestable models, tight coupling | 25 occurrences |
| Generic exceptions | Poor debugging experience | 16 occurrences |
| O(n) page scans | Performance degradation at scale | 37 files |
| Bare except clauses | Swallowed errors, hidden bugs | 772 occurrences |

---

## Goals

### Must Have

1. **Atomic writes for user-facing outputs** — All files in `public/` must use atomic writes
2. **Diagnostics sink in core/** — All logging in core models migrates to diagnostics
3. **Rich exceptions in analysis/** — Knowledge graph errors include investigation helpers
4. **Audit bare excepts in rendering/** — Critical path must have specific error handling

### Should Have

1. **Query indexes in health validators** — Reduce validation time on large sites
2. **Output generator base class** — Shared patterns for all output format generators

### Non-Goals

- Rewriting working code that follows different but valid patterns
- 100% adoption immediately (phased rollout)
- Adding new patterns (only adopting existing ones)

---

## Design

### Pattern 1: Diagnostics Sink for Core Models

**Purpose**: Core models (`bengal/core/`) must remain pure data containers. Side effects like logging or terminal output make them difficult to test and couple them to the CLI.

**Diagnostics vs. Exceptions**:
- **Diagnostics**: Use `emit(self, level, code, **data)` for observability of internal state, non-fatal warnings, or progress events. These are collected by the orchestrator.
- **Exceptions**: Use `raise BengalError(...)` for fatal failures that must stop the build or trigger recovery logic.

**Resolution Order**: The `emit()` helper resolves the sink in this order:
1. `obj._diagnostics` (explicitly injected)
2. `obj.diagnostics` (e.g., `Site.diagnostics`)
3. `obj._site.diagnostics` (common for page/section objects)

**Current violation example** (`bengal/core/nav_tree.py`):

```python
# BEFORE: Direct logging in core model
logger.warning(
    "NavTree URL collision detected: url=%s | existing_id=%s",
    url, existing_id
)
```

**After adoption**:

```python
# AFTER: Pure core model with diagnostics emission
from bengal.core.diagnostics import emit

emit(
    self,
    "warning",
    "nav_url_collision",
    url=url,
    existing_id=existing_id,
    new_id=new_id,
)
```

**Files to migrate**:

| File | Occurrences | Priority |
|------|-------------|----------|
| `bengal/core/theme/resolution.py` | 7 | High |
| `bengal/core/theme/registry.py` | 15 | High |
| `bengal/core/nav_tree.py` | 1 | High |
| `bengal/core/output/collector.py` | 1 | Medium |

**Diagnostic codes to add**:

```python
# bengal/core/theme/resolution.py
"theme_manifest_read_failed"     # Debug: Theme manifest couldn't be read
"theme_package_resolve_failed"   # Debug: Installed theme package not found
"theme_templates_resolution_installed_failed"  # Debug: Template resolution failed

# bengal/core/theme/registry.py
"theme_templates_dir_check_failed"   # Debug: Templates dir check failed
"theme_assets_dir_check_failed"      # Debug: Assets dir check failed
"theme_manifest_check_failed"        # Debug: Manifest check failed
"theme_resource_path_resolve_failed" # Debug: Resource path resolution failed
"installed_themes_discovered"        # Info: Theme discovery complete

# bengal/core/nav_tree.py
"nav_url_collision"  # Warning: URL collision in navigation tree
```

---

### Pattern 2: Atomic File Writes

**Current violation example** (`bengal/postprocess/redirects.py`):

```python
# BEFORE: Non-atomic write
output_path.write_text(html, encoding="utf-8")
```

**After adoption**:

```python
# AFTER: Atomic write with crash safety
from bengal.utils.atomic_write import atomic_write_text

atomic_write_text(output_path, html)
```

**Already correct** ✅: `bengal/utils/json_compat.py`
The `dump()` function already uses `atomic_write_text()` for crash-safe JSON serialization.

**Files to migrate** (by priority):

**P0 - User-facing outputs (must fix)**:

| File | Occurrences | Output Type |
|------|-------------|-------------|
| `bengal/postprocess/redirects.py` | 2 | Redirect HTML, `_redirects` |
| `bengal/postprocess/special_pages.py` | 2 | Graph HTML/JSON |
| `bengal/postprocess/output_formats/lunr_index_generator.py` | 1 | Search index |

**P1 - CLI outputs (should fix)**:

| File | Occurrences | Output Type |
|------|-------------|-------------|
| `bengal/cli/commands/theme.py` | 14 | Theme files |
| `bengal/cli/commands/config.py` | 8 | Config files |
| `bengal/debug/dependency_visualizer.py` | 2 | Debug output |

**P2 - Internal (nice to fix)**:

| File | Occurrences | Output Type |
|------|-------------|-------------|
| `bengal/content_layer/manager.py` | 2 | Cache files |
| `bengal/utils/swizzle.py` | 3 | Swizzled templates |

**Already correct** ✅:

- `bengal/postprocess/output_formats/txt_generator.py` — Uses `AtomicFile`
- `bengal/cache/cache_store.py` — Uses compression utilities with atomic semantics

---

### Pattern 3: Rich Exceptions with Context

**Current violation example** (`bengal/analysis/knowledge_graph.py`):

```python
# BEFORE: Generic exception without context
raise ValueError(f"Node not found: {node}")
```

**After adoption**:

```python
# AFTER: Rich exception with investigation helpers
from bengal.errors import BengalError, ErrorCode

raise BengalError(
    f"Node not found in knowledge graph: {node}",
    code=ErrorCode.D003,  # Discovery error: node not found
    suggestion="Check that the page exists and is not excluded from the graph",
    file_path=node.source_path if hasattr(node, 'source_path') else None,
    debug_payload=ErrorDebugPayload(
        context={"graph_size": len(self._nodes), "node_id": str(node)},
    ),
)
```

**New error codes to add** (`bengal/errors/codes.py`):

```python
# Knowledge Graph errors (G001-G010)
G001 = "graph_node_not_found"
G002 = "graph_edge_invalid"
G003 = "graph_cycle_detected"
G004 = "graph_disconnected_component"
G005 = "graph_analysis_failed"
```

**Files to migrate**:

| File | Count | Current Exception |
|------|-------|-------------------|
| `bengal/analysis/knowledge_graph.py` | 8 | `ValueError` |
| `bengal/analysis/graph_visualizer.py` | 1 | `ValueError` |
| `bengal/analysis/graph_reporting.py` | 1 | `ValueError` |
| `bengal/analysis/graph_analysis.py` | 1 | `ValueError` |
| `bengal/core/nav_tree.py` | 1 | `RuntimeError` |

---

### Pattern 4: Query Indexes for O(1) Lookups

**Current pattern** (O(n) scan):

```python
# BEFORE: O(n) iteration in health validator
def validate(self, site):
    for page in site.pages:  # O(n)
        if page.section == "docs":
            self._check_page(page)
```

**After adoption** (O(1) lookup):

```python
# AFTER: O(1) index lookup
def validate(self, site):
    docs_paths = site.indexes.section.get("docs")  # O(1)
    docs_pages = resolve_pages(docs_paths, site)   # O(k) where k << n
    for page in docs_pages:
        self._check_page(page)
```

**Candidates for optimization**:

| File | Pattern | Potential Speedup |
|------|---------|-------------------|
| `bengal/health/validators/navigation.py` | 4 page iterations | 2-3x |
| `bengal/health/validators/links.py` | 3 page iterations | 2-3x |
| `bengal/health/validators/url_collisions.py` | 2 page iterations | 2x |
| `bengal/health/validators/tracks.py` | 2 page iterations | 2x |

**Note**: Some iterations are necessary (e.g., building indexes). Focus on repeated lookups in inner loops.

---

### Pattern 5: Output Generator Base Class

**Current state**: 6 independent generators without shared abstraction.

**Proposed base class**:

```python
# bengal/postprocess/output_formats/base.py

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

    def __init__(self, site: Site, build_context: BuildContext | None = None):
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

**Generators to refactor**:

| Generator | Changes Required |
|-----------|------------------|
| `PageTxtGenerator` | Already uses `AtomicFile`, add base class |
| `PageJSONGenerator` | Add atomic writes, base class |
| `SiteLlmTxtGenerator` | Add atomic writes, base class |
| `SiteIndexGenerator` | Add atomic writes, base class |
| `LunrIndexGenerator` | Add atomic writes, base class |

---

## Implementation Plan

### Phase 1: Critical Path (Week 1)

**Focus**: User-facing outputs and core model purity.

| Task | Files | Effort | Risk |
|------|-------|--------|------|
| Atomic writes in postprocess/ | 5 files | 2h | Low |
| Diagnostics sink in core/theme/ | 2 files | 3h | Medium |
| Diagnostics sink in core/nav_tree.py | 1 file | 1h | Low |

**Acceptance criteria**:
- All files in `public/` written atomically
- No `logger.*()` calls in `bengal/core/` except diagnostics.py

### Phase 2: Error Handling (Week 2)

**Focus**: Rich exceptions and error recovery.

| Task | Files | Effort | Risk |
|------|-------|--------|------|
| Add G001-G005 error codes | 1 file | 0.5h | Low |
| Rich exceptions in analysis/ | 4 files | 4h | Medium |
| Audit bare excepts in rendering/ | 5 files | 6h | Medium |

**Acceptance criteria**:
- Knowledge graph errors include investigation commands
- No bare `except:` in rendering pipeline hot path

### Phase 3: Performance (Week 3)

**Focus**: Query indexes and output generator consolidation.

| Task | Files | Effort | Risk |
|------|-------|--------|------|
| Query indexes in health validators | 4 files | 4h | Low |
| Output generator base class | 6 files | 4h | Medium |

**Acceptance criteria**:
- Health checks on 10k site < 2s (vs current ~5s)
- All output generators use atomic writes

### Phase 4: Cleanup (Week 4)

**Focus**: Remaining violations, documentation.

| Task | Files | Effort | Risk |
|------|-------|--------|------|
| Atomic writes in CLI commands | 22 files | 4h | Low |
| Audit remaining bare excepts | Sample | 4h | Low |
| Update CONTRIBUTING.md | 1 file | 2h | Low |

---

## Migration Strategy

### Backward Compatibility

All changes are internal implementation details. No API changes.

| Change | Compatibility |
|--------|---------------|
| Atomic writes | Same output, just crash-safe |
| Diagnostics sink | No behavior change (events still logged) |
| Rich exceptions | Same exception types, just richer context |
| Query indexes | Same results, just faster |

### Rollback Plan

Each phase is independently deployable. If issues arise:

1. Revert specific file changes
2. Pattern adoption is additive, not breaking
3. Feature flags not needed (internal changes only)

### Testing Strategy

**Unit tests**:
- Atomic write: Test crash-recovery scenarios
- Diagnostics: Test event emission and collection
- Rich exceptions: Test context preservation

**Integration tests**:
- Build same site before/after, diff outputs
- Verify no regression in build time

**Benchmark tests**:
- Health check timing on 10k site
- Cache serialization timing

---

## Testing

### New Test Cases

```python
# tests/unit/test_atomic_write_adoption.py

def test_redirect_files_atomic():
    """Verify redirect files are written atomically."""
    # Simulate crash during write
    # Verify original file intact OR new file complete

def test_graph_output_atomic():
    """Verify graph HTML/JSON written atomically."""
    pass


# tests/unit/test_diagnostics_adoption.py

def test_theme_registry_uses_diagnostics():
    """Verify theme registry emits diagnostics, not logs."""
    collector = DiagnosticsCollector()
    registry = ThemeRegistry()
    registry._diagnostics = collector

    registry.discover_themes()

    events = collector.drain()
    assert any(e.code == "installed_themes_discovered" for e in events)


# tests/unit/test_rich_exceptions.py

def test_knowledge_graph_exception_context():
    """Verify knowledge graph errors include investigation helpers."""
    graph = KnowledgeGraph(site)

    with pytest.raises(BengalError) as exc_info:
        graph.get_node("nonexistent")

    assert exc_info.value.code == ErrorCode.G001
    assert exc_info.value.suggestion is not None
    assert "get_investigation_commands" in dir(exc_info.value)
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Atomic write performance | Low | Low | Already proven in txt_generator |
| Diagnostics breaking tests | Medium | Low | Provide mock collector for tests |
| Rich exceptions breaking error handling | Low | Medium | Same exception types, just richer |
| Query index cache invalidation | Medium | Medium | Reuse existing cache invalidation |

---

## Success Metrics

| Metric | Before | After | Measurement |
|--------|--------|-------|-------------|
| Core model logger calls | 25 | 0 | `grep -r "logger\." bengal/core/` |
| Non-atomic writes in postprocess/ | 5 | 0 | Manual audit |
| Generic exceptions in analysis/ | 11 | 0 | `grep -r "raise ValueError"` |
| Health check time (10k site) | ~5s | <2s | Benchmark suite |

---

## Appendix

### A. Full Violation Inventory

<details>
<summary>Direct logging in core/ (25 occurrences)</summary>

```
bengal/core/theme/resolution.py:50:  logger.debug("theme_manifest_read_failed", ...)
bengal/core/theme/resolution.py:70:  logger.debug("theme_manifest_read_failed", ...)
bengal/core/theme/resolution.py:78:  logger.debug("theme_package_resolve_failed", ...)
bengal/core/theme/resolution.py:94:  logger.debug("theme_manifest_read_failed", ...)
bengal/core/theme/resolution.py:174: logger.debug("theme_templates_resolution_installed_failed", ...)
bengal/core/theme/resolution.py:213: logger.debug("installed_theme_assets_resolution_failed", ...)
bengal/core/theme/resolution.py:222: logger.debug("bundled_theme_assets_resolution_failed", ...)
bengal/core/theme/registry.py:61:   logger.debug("theme_templates_dir_check_failed", ...)
bengal/core/theme/registry.py:76:   logger.debug("theme_templates_dir_check_failed", ...)
bengal/core/theme/registry.py:100:  logger.debug("theme_assets_dir_check_failed", ...)
bengal/core/theme/registry.py:115:  logger.debug("theme_assets_dir_check_failed", ...)
bengal/core/theme/registry.py:138:  logger.debug("theme_manifest_check_failed", ...)
bengal/core/theme/registry.py:152:  logger.debug("theme_manifest_check_failed", ...)
bengal/core/theme/registry.py:178:  logger.debug("theme_resource_path_import_failed", ...)
bengal/core/theme/registry.py:198:  logger.debug("theme_resource_path_fspath_failed", ...)
bengal/core/theme/registry.py:213:  logger.debug("theme_resource_path_as_file_failed", ...)
bengal/core/theme/registry.py:222:  logger.debug("theme_resource_path_resolve_failed", ...)
bengal/core/theme/registry.py:231:  logger.debug("theme_resource_resolve_failed", ...)
bengal/core/theme/registry.py:247:  logger.debug("entry_point_discovery_failed", ...)
bengal/core/theme/registry.py:269:  logger.debug("theme_version_lookup_failed", ...)
bengal/core/theme/registry.py:277:  logger.debug("theme_distribution_lookup_failed", ...)
bengal/core/theme/registry.py:289:  logger.debug("installed_themes_discovered", ...)
bengal/core/output/collector.py:195: logger.warning("output_tracking_empty", ...)
bengal/core/nav_tree.py:198:        logger.warning("NavTree URL collision detected", ...)
```

</details>

<details>
<summary>Non-atomic writes in postprocess/ (5 occurrences)</summary>

```
bengal/postprocess/special_pages.py:461:   output_path.write_text(html, ...)
bengal/postprocess/special_pages.py:469:   json_path.write_text(json.dumps(...), ...)
bengal/postprocess/redirects.py:226:       output_path.write_text(html, ...)
bengal/postprocess/redirects.py:302:       redirects_path.write_text("\n".join(lines), ...)
bengal/postprocess/output_formats/lunr_index_generator.py:168: output_path.write_text(...)
```

</details>

<details>
<summary>Generic exceptions in analysis/ (11 occurrences)</summary>

```
bengal/analysis/knowledge_graph.py: 8 ValueError raises
bengal/analysis/graph_visualizer.py: 1 ValueError raise
bengal/analysis/graph_reporting.py: 1 ValueError raise
bengal/analysis/graph_analysis.py: 1 ValueError raise
```

</details>

### B. Related RFCs

- [RFC: Unified Page Data Accumulation](rfc-unified-page-data-accumulation.md) — Uses accumulated data pattern
- [RFC: Template Context Redesign](rfc-template-context-redesign.md) — Uses wrapper pattern
- Inline Asset Extraction (Implemented) — Uses BuildContext accumulation (see changelog.md)

### C. References

- `bengal/core/diagnostics.py` — Diagnostics sink implementation
- `bengal/utils/atomic_write.py` — Atomic write implementation
- `bengal/errors/` — Rich exception implementation
- `bengal/cache/query_index.py` — Query index implementation
