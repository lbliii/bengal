# Implementation Plan: Large File Refactoring

**Source RFC**: `rfc-large-file-refactoring.md`  
**Created**: 2025-12-01  
**Status**: Ready for Implementation  
**Confidence**: 90% 🟢

---

## Executive Summary

Refactor three 1,000+ line files into focused modules to improve maintainability and contributor experience. Builds on existing successful patterns (`bengal/core/page/`, analysis modules).

**Phases**:
1. `knowledge_graph.py` → Extract basic analysis + reporting (3-4 days)
2. `output_formats.py` → Convert to package with format-specific modules (1 week)
3. `site.py` → Deferred pending re-evaluation

---

## Phase 1: Knowledge Graph Modularization

**Goal**: Reduce `knowledge_graph.py` from 1,331 → ~400 lines  
**Duration**: 3-4 days  
**Risk**: Low (advanced analysis already extracted, proven patterns)

### Subsystem: Analysis (`bengal/analysis/`)

#### 1.1 Create `graph_analysis.py` - Basic Analysis Module

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 1.1.1 Create `bengal/analysis/graph_analysis.py` with `GraphAnalyzer` class
- [ ] 1.1.2 Move `get_connectivity()` (lines 421-449) → `GraphAnalyzer.get_connectivity()`
- [ ] 1.1.3 Move `get_hubs()` (lines 451-479) → `GraphAnalyzer.get_hubs()`
- [ ] 1.1.4 Move `get_leaves()` (lines 481-511) → `GraphAnalyzer.get_leaves()`
- [ ] 1.1.5 Move `get_orphans()` (lines 513-544) → `GraphAnalyzer.get_orphans()`
- [ ] 1.1.6 Move `get_connectivity_score()` (lines 546-564) → `GraphAnalyzer.get_connectivity_score()`
- [ ] 1.1.7 Move `get_layers()` (lines 566-599) → `GraphAnalyzer.get_layers()`
- [ ] 1.1.8 Add delegation wrappers in `KnowledgeGraph` for backward compatibility
- [ ] 1.1.9 Run tests: `pytest tests/unit/test_knowledge_graph.py -v`

**Commit**:
```bash
git add -A && git commit -m "analysis: extract GraphAnalyzer from knowledge_graph.py; move basic analysis methods (hubs, leaves, orphans, connectivity)"
```

**Verification**:
```bash
# All tests pass
pytest tests/unit/test_knowledge_graph.py tests/integration/ -v -k graph

# Line count check
wc -l bengal/analysis/graph_analysis.py  # Expected: 200-300 lines
```

---

#### 1.2 Create `graph_reporting.py` - Reporting Module

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 1.2.1 Create `bengal/analysis/graph_reporting.py` with `GraphReporter` class
- [ ] 1.2.2 Move `format_stats()` (lines 616-712, ~100 lines) → `GraphReporter.format_stats()`
- [ ] 1.2.3 Move `get_actionable_recommendations()` (lines 714-816, ~100 lines) → `GraphReporter.get_actionable_recommendations()`
- [ ] 1.2.4 Move `get_seo_insights()` (lines 818-922, ~100 lines) → `GraphReporter.get_seo_insights()`
- [ ] 1.2.5 Move `get_content_gaps()` (lines 924-1003, ~80 lines) → `GraphReporter.get_content_gaps()`
- [ ] 1.2.6 Add delegation wrappers in `KnowledgeGraph` for backward compatibility
- [ ] 1.2.7 Run tests: `pytest tests/unit/test_knowledge_graph.py -v`

**Commit**:
```bash
git add -A && git commit -m "analysis: extract GraphReporter from knowledge_graph.py; move format_stats, recommendations, SEO insights, content gaps"
```

**Verification**:
```bash
# All tests pass
pytest tests/unit/test_knowledge_graph.py tests/integration/ -v -k graph

# Line count check
wc -l bengal/analysis/graph_reporting.py  # Expected: 300-400 lines
```

---

#### 1.3 Update `__init__.py` and Clean Up

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 1.3.1 Update `bengal/analysis/__init__.py` to export new classes
- [ ] 1.3.2 Clean up `KnowledgeGraph` - verify all delegation wrappers work
- [ ] 1.3.3 Update any internal imports across codebase
- [ ] 1.3.4 Run full test suite
- [ ] 1.3.5 Verify `knowledge_graph.py` is now <500 lines

**Commit**:
```bash
git add -A && git commit -m "analysis: update __init__.py exports; complete knowledge_graph.py modularization (1,331 → ~400 lines)"
```

**Verification**:
```bash
# Full test suite
pytest tests/ -v

# Final line count
wc -l bengal/analysis/knowledge_graph.py  # Expected: <500 lines

# Verify public API unchanged
python -c "from bengal.analysis import KnowledgeGraph; print('API OK')"
```

---

### Phase 1 Success Criteria

- [ ] `knowledge_graph.py` reduced from 1,331 → <500 lines
- [ ] `graph_analysis.py` created (200-300 lines)
- [ ] `graph_reporting.py` created (300-400 lines)
- [ ] All existing tests pass
- [ ] Public API unchanged (`KnowledgeGraph` interface preserved)
- [ ] No performance regression

---

## Phase 2: Output Formats Modularization

**Goal**: Convert `output_formats.py` (1,146 lines) to package with focused modules  
**Duration**: 1 week  
**Risk**: Low (follows same pattern as Phase 1)

### Subsystem: Postprocess (`bengal/postprocess/`)

#### 2.1 Create Package Structure

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 2.1.1 Create `bengal/postprocess/output_formats/` directory
- [ ] 2.1.2 Create `bengal/postprocess/output_formats/__init__.py` (orchestrator, 200 lines)
- [ ] 2.1.3 Create `bengal/postprocess/output_formats/base.py` (config, filtering, 200 lines)
- [ ] 2.1.4 Move `_normalize_config()`, `_default_config()`, `_filter_pages()` → `base.py`
- [ ] 2.1.5 Run tests: `pytest tests/unit/test_output_formats.py -v`

**Commit**:
```bash
git add -A && git commit -m "postprocess: create output_formats package structure; extract base config and filtering to base.py"
```

---

#### 2.2 Extract Per-Page JSON Generator

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 2.2.1 Create `bengal/postprocess/output_formats/page_json.py`
- [ ] 2.2.2 Move `_generate_page_json()` → `PageJSONGenerator.generate()`
- [ ] 2.2.3 Move `_page_to_json()` → `PageJSONGenerator._page_to_json()`
- [ ] 2.2.4 Move `_get_page_json_path()` → `PageJSONGenerator._get_path()`
- [ ] 2.2.5 Move `_get_page_connections()` → `PageJSONGenerator._get_connections()`
- [ ] 2.2.6 Update orchestrator to use `PageJSONGenerator`
- [ ] 2.2.7 Run tests

**Commit**:
```bash
git add -A && git commit -m "postprocess: extract PageJSONGenerator to output_formats/page_json.py"
```

---

#### 2.3 Extract Per-Page LLM Text Generator

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 2.3.1 Create `bengal/postprocess/output_formats/page_txt.py`
- [ ] 2.3.2 Move `_generate_page_txt()` → `PageTxtGenerator.generate()`
- [ ] 2.3.3 Move `_page_to_llm_text()` → `PageTxtGenerator._page_to_text()`
- [ ] 2.3.4 Move `_get_page_txt_path()` → `PageTxtGenerator._get_path()`
- [ ] 2.3.5 Update orchestrator to use `PageTxtGenerator`
- [ ] 2.3.6 Run tests

**Commit**:
```bash
git add -A && git commit -m "postprocess: extract PageTxtGenerator to output_formats/page_txt.py"
```

---

#### 2.4 Extract Site Index JSON Generator

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 2.4.1 Create `bengal/postprocess/output_formats/site_index.py`
- [ ] 2.4.2 Move `_generate_site_index_json()` → `SiteIndexGenerator.generate()`
- [ ] 2.4.3 Move `_page_to_summary()` → `SiteIndexGenerator._page_to_summary()`
- [ ] 2.4.4 Update orchestrator to use `SiteIndexGenerator`
- [ ] 2.4.5 Run tests

**Commit**:
```bash
git add -A && git commit -m "postprocess: extract SiteIndexGenerator to output_formats/site_index.py"
```

---

#### 2.5 Extract Site LLM Text Generator

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 2.5.1 Create `bengal/postprocess/output_formats/site_llm_txt.py`
- [ ] 2.5.2 Move `_generate_site_llm_txt()` → `SiteLlmTxtGenerator.generate()`
- [ ] 2.5.3 Update orchestrator to use `SiteLlmTxtGenerator`
- [ ] 2.5.4 Run tests

**Commit**:
```bash
git add -A && git commit -m "postprocess: extract SiteLlmTxtGenerator to output_formats/site_llm_txt.py"
```

---

#### 2.6 Extract Shared Utilities

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 2.6.1 Create `bengal/postprocess/output_formats/utils.py`
- [ ] 2.6.2 Move `_strip_html()` → `utils.strip_html()`
- [ ] 2.6.3 Move `_generate_excerpt()` → `utils.generate_excerpt()`
- [ ] 2.6.4 Move `_get_page_url()` → `utils.get_page_url()`
- [ ] 2.6.5 Update all generators to use shared utilities
- [ ] 2.6.6 Run full test suite

**Commit**:
```bash
git add -A && git commit -m "postprocess: extract shared utils (strip_html, generate_excerpt, get_page_url) to output_formats/utils.py"
```

---

#### 2.7 Clean Up and Finalize

**Status**: `[ ]` Pending

**Tasks**:
- [ ] 2.7.1 Remove old `bengal/postprocess/output_formats.py`
- [ ] 2.7.2 Update `bengal/postprocess/__init__.py` to re-export from package
- [ ] 2.7.3 Update any internal imports across codebase
- [ ] 2.7.4 Run full test suite
- [ ] 2.7.5 Verify backward compatibility

**Commit**:
```bash
git add -A && git commit -m "postprocess: complete output_formats modularization (1,146 → 6 focused modules); remove monolithic file"
```

**Verification**:
```bash
# Full test suite
pytest tests/ -v

# Verify public API unchanged
python -c "from bengal.postprocess import OutputFormatsGenerator; print('API OK')"

# Line counts
wc -l bengal/postprocess/output_formats/*.py
```

---

### Phase 2 Success Criteria

- [ ] `output_formats.py` converted to package with 6 modules
- [ ] Each module <300 lines
- [ ] All existing tests pass
- [ ] Public API unchanged (`OutputFormatsGenerator` interface preserved)
- [ ] No performance regression
- [ ] Easy to add new output formats

---

## Phase 3: Site Refactoring (Deferred)

**Status**: Deferred pending Phase 1-2 completion  
**Decision Point**: Re-evaluate after Phases 1-2

**Criteria for proceeding**:
- [ ] Pain points remain after other refactors
- [ ] Contributors report difficulty working with `site.py`
- [ ] Clear boundaries identified

**If proceeding**, follow the `bengal/core/page/` mixin pattern:
- `bengal/core/site/__init__.py` - Main Site class with mixins
- `bengal/core/site/discovery.py` - SiteDiscoveryMixin
- `bengal/core/site/caching.py` - SiteCachingMixin
- `bengal/core/site/references.py` - SiteReferencesMixin
- `bengal/core/site/factory.py` - SiteFactory (from_config, for_testing)

---

## Test Commands Reference

```bash
# Phase 1 tests
pytest tests/unit/test_knowledge_graph.py -v
pytest tests/integration/ -v -k graph

# Phase 2 tests
pytest tests/unit/test_output_formats.py -v
pytest tests/integration/ -v -k output

# Full test suite
pytest tests/ -v

# Performance check
pytest tests/performance/ -v --benchmark-only

# Type checking
mypy bengal/analysis/ bengal/postprocess/
```

---

## Rollback Plan

If issues are found during refactoring:

1. **Revert to last working commit**: `git revert HEAD`
2. **Keep old file as backup**: Don't delete original file until all tests pass
3. **Incremental commits**: Each extraction is atomic and revertible

---

## Timeline Summary

| Phase | Target | Duration | Status |
|-------|--------|----------|--------|
| 1.1 | `graph_analysis.py` | 1 day | `[ ]` Pending |
| 1.2 | `graph_reporting.py` | 1 day | `[ ]` Pending |
| 1.3 | Clean up & exports | 0.5 day | `[ ]` Pending |
| 2.1 | Package structure | 0.5 day | `[ ]` Pending |
| 2.2 | `page_json.py` | 1 day | `[ ]` Pending |
| 2.3 | `page_txt.py` | 0.5 day | `[ ]` Pending |
| 2.4 | `site_index.py` | 1 day | `[ ]` Pending |
| 2.5 | `site_llm_txt.py` | 0.5 day | `[ ]` Pending |
| 2.6 | `utils.py` | 0.5 day | `[ ]` Pending |
| 2.7 | Clean up | 0.5 day | `[ ]` Pending |
| 3 | `site.py` | Deferred | `[ ]` Pending |

**Total**: ~1.5 weeks for Phases 1-2

---

## References

- **RFC**: `plan/active/rfc-large-file-refactoring.md`
- **Pattern Example**: `bengal/core/page/` (successful mixin pattern)
- **Existing Modules**: `bengal/analysis/page_rank.py`, `community_detection.py`, `path_analysis.py`, `link_suggestions.py`
