## 📋 Implementation Plan: Autodoc Resilience

### Executive Summary
Harden autodoc so failures are surfaced, strict mode is available, and fallback usage is tagged without losing partial output. Work is phased: add run summaries and tolerant orchestration wiring, then strict-mode enforcement and metadata tagging, followed by targeted tests and docs.

### Plan Details
- **Total Tasks**: 12  
- **Estimated Time**: 2-3 days  
- **Complexity**: Moderate  
- **Confidence Gates**: Plan ≥85%, Implementation ≥90%

---

## Phase 1: Foundation (3 tasks)

### Autodoc (`bengal/autodoc/`)
#### Task 1.1: Add AutodocRunResult summary
- **Files**: `bengal/autodoc/virtual_orchestrator.py` (or nearby models helper)  
- **Action**: Introduce `AutodocRunResult` dataclass to capture extracted/rendered counts and failed identifiers; populate during generation.  
- **Dependencies**: None  
- **Status**: pending  
- **Commit**: `autodoc: add AutodocRunResult summary capture`

### Orchestration (`bengal/orchestration/`)
#### Task 1.2: Return summary from autodoc discovery
- **Files**: `bengal/orchestration/content.py`, `bengal/autodoc/virtual_orchestrator.py`  
- **Action**: Update `VirtualAutodocOrchestrator.generate` to return `(pages, sections, result)`; adjust `_discover_autodoc_content` to tolerate the third value and pass it through for logging/storage without breaking non-autodoc callers.  
- **Dependencies**: Task 1.1  
- **Status**: pending  
- **Commit**: `orchestration: plumb autodoc run summary through discovery`

### Orchestration (`bengal/orchestration/`)
#### Task 1.3: Remove blanket exception swallow
- **Files**: `bengal/orchestration/content.py`  
- **Action**: Drop broad `except Exception` in `_discover_autodoc_content`; keep `ImportError` handling; rely on summary/strict flow for other errors.  
- **Dependencies**: Task 1.2  
- **Status**: pending  
- **Commit**: `orchestration: stop swallowing autodoc errors outside ImportError`

---

## Phase 2: Implementation (4 tasks)

### Autodoc Config (`bengal/autodoc/config.py`)
#### Task 2.1: Add autodoc.strict config flag
- **Files**: `bengal/autodoc/config.py`  
- **Action**: Add `autodoc.strict` defaulting to False; merge behavior preserved; expose through loader helpers.  
- **Dependencies**: None  
- **Status**: pending  
- **Commit**: `autodoc(config): add strict flag default false`

### Autodoc (`bengal/autodoc/virtual_orchestrator.py`)
#### Task 2.2: Enforce strict mode with partial context
- **Files**: `bengal/autodoc/virtual_orchestrator.py`  
- **Action**: On extraction or render failure, record failure and in strict mode raise after recording partial results; keep best-effort when strict is False.  
- **Dependencies**: Tasks 1.1, 2.1  
- **Status**: pending  
- **Commit**: `autodoc: enforce strict mode while retaining partial results`

### Autodoc (`bengal/autodoc/virtual_orchestrator.py`)
#### Task 2.3: Tag fallback-rendered pages in metadata
- **Files**: `bengal/autodoc/virtual_orchestrator.py`  
- **Action**: When `_render_fallback` is used, attach a metadata flag (e.g., `_autodoc_fallback_template: true`) on created `Page` objects so downstream checks/tests can assert fallback usage.  
- **Dependencies**: Task 1.1  
- **Status**: pending  
- **Commit**: `autodoc: tag fallback-rendered pages in metadata`

### Autodoc (`bengal/autodoc/virtual_orchestrator.py`)
#### Task 2.4: Emit structured summary logging
- **Files**: `bengal/autodoc/virtual_orchestrator.py`, `bengal/orchestration/content.py`  
- **Action**: Emit a single summarized warning/info with counts and sample failures from `AutodocRunResult`; ensure logging integrates with orchestrator return path.  
- **Dependencies**: Tasks 1.1, 1.2  
- **Status**: pending  
- **Commit**: `autodoc: add structured summary logging for autodoc runs`

---

## Phase 3: Validation (3 tasks)

### Tests (`tests/unit/autodoc/`)
#### Task 3.1: Unit tests for extraction/render failure paths
- **Files**: `tests/unit/autodoc/test_virtual_page_rendering.py` (or new focused file)  
- **Action**: Cover extraction exception and missing template scenarios: non-strict yields warnings + summaries; strict raises after recording failures.  
- **Dependencies**: Tasks 2.1, 2.2, 2.4  
- **Status**: pending  
- **Commit**: `tests(autodoc): cover strict vs non-strict failure handling`

### Tests (`tests/unit/autodoc/`)
#### Task 3.2: Summary coverage for OpenAPI/CLI elements
- **Files**: `tests/unit/autodoc/test_virtual_page_rendering.py` or new helper tests  
- **Action**: Ensure summary counts include OpenAPI and CLI element paths; assert fallback tagging metadata when templates are missing.  
- **Dependencies**: Tasks 1.1, 2.3  
- **Status**: pending  
- **Commit**: `tests(autodoc): assert summary counts and fallback tags for all element types`

### Tests (`tests/integration/`)
#### Task 3.3: RenderingPipeline integration with fallback pages
- **Files**: `tests/integration/` (extend existing autodoc integration)  
- **Action**: Verify pages rendered via fallback still write output and carry metadata tags; strict mode path raises.  
- **Dependencies**: Tasks 2.2, 2.3  
- **Status**: pending  
- **Commit**: `tests(integration): ensure fallback-tagged autodoc pages render outputs`

---

## Phase 4: Polish (2 tasks)

### Docs (`bengal/autodoc/README.md`)
#### Task 4.1: Document strict mode and summaries
- **Files**: `bengal/autodoc/README.md`  
- **Action**: Add strict-mode usage, summary logging behavior, and fallback metadata notes; include examples.  
- **Dependencies**: Implementation complete  
- **Status**: pending  
- **Commit**: `docs(autodoc): document strict mode and run summaries`

### Changelog (`changelog.md`)
#### Task 4.2: Add changelog entry after implementation
- **Files**: `changelog.md`  
- **Action**: Add entry noting autodoc resilience improvements once shipped; move plan to `plan/implemented/` at completion.  
- **Dependencies**: All prior phases  
- **Status**: pending  
- **Commit**: `docs: note autodoc resilience changes in changelog`

---

## Phase 3: Validation Checklist
- [ ] Unit tests for autodoc strict/non-strict failure paths
- [ ] Summary logging asserts counts and sample failures
- [ ] Integration ensures fallback-tagged pages render
- [ ] Linter/mypy clean

---

## 📊 Task Summary
| Area | Tasks | Status |
|------|-------|--------|
| Autodoc | 6 | pending |
| Orchestration | 2 | pending |
| Tests | 3 | pending |
| Docs | 1 | pending |

---

## 📋 Next Steps
- [ ] Review plan for completeness
- [ ] Start Phase 1 (Task 1.1)
- [ ] Update task statuses and TODOs as work progresses
