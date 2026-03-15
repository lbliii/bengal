# Epic: Architecture Audit Remediation

**Status**: Planned  
**Created**: 2026-03-14  
**Target**: v0.3.x  
**Estimated Effort**: 20-30 hours  
**Dependencies**: Coordinate with Epic: Protocol Migration (Phase 1) and Site Cleanup & Service Wiring  
**Source**: ARCH Audit (2026-03-14)

---

## Why This Matters

The architecture audit identified **2 high-severity** and **5 medium-severity** structural issues across Bengal's 228k-line codebase. The highest-risk findings are:

1. **Model purity violations** — `bengal/core/` contains file I/O and logging in 6 files, breaking the foundational passive-model contract
2. **Boundary violations** — `core/` imports upward into `orchestration/`, `rendering/`, `cache/`, and `server/` through 11 deferred imports
3. **136 files exceed the 400-line threshold**, with 6 files over 1,000 lines

Left unaddressed, these erode the model/orchestrator boundary that enables safe free-threading, make refactoring fragile, and confuse contributors about where logic belongs.

---

## Sprint Structure

| Sprint | Focus | Effort | Risk |
|--------|-------|--------|------|
| **1** | Core model purity — remove I/O and logging from `core/` | 4-6h | Low (isolated changes) |
| **2** | Boundary violations — eliminate upward imports from `core/` | 6-8h | Medium (touches Site god object) |
| **3** | Provenance naming + build/ disambiguation | 2-3h | Low |
| **4** | File size reduction — split top offenders | 6-10h | Medium (large refactors) |
| **5** | Server god module decomposition | 4-6h | Medium |

---

## Sprint 1: Core Model Purity

**Goal**: `bengal/core/` has zero logger imports, zero `open()` calls, zero file I/O.

### Task 1.1 — Extract `core/resources/processor.py` I/O to services layer

| Field | Value |
|-------|-------|
| **Files** | `bengal/core/resources/processor.py` (593 lines) |
| **Issue** | Lines 220, 255, 291: `open()`, `os.fdopen()`, `Image.open()` + logger at line 41 |
| **Action** | Move file read/write operations to `bengal/services/asset_io.py` (already exists at 413 lines). Core processor retains pure data transforms; orchestration/services handle disk access. |
| **Validation** | `rg "open\(" bengal/core/resources/processor.py` returns 0 matches |

### Task 1.2 — Extract `core/resources/image.py` I/O to services layer

| Field | Value |
|-------|-------|
| **Files** | `bengal/core/resources/image.py` (line 121) |
| **Issue** | `Image.open(self.source_path)` — Pillow file I/O inside a core model |
| **Action** | `ImageResource` should receive already-opened image data or dimensions. Move `Image.open()` to the orchestration/services call site. |
| **Validation** | `rg "Image\.open" bengal/core/` returns 0 matches |

### Task 1.3 — Remove logger from core type/model files

| Field | Value |
|-------|-------|
| **Files** | `core/resources/types.py:18`, `core/page/page_core.py:116`, `core/output/collector.py:20` |
| **Issue** | Logger imports in passive models. Models should raise exceptions, not log. |
| **Action** | Replace `logger.warning(...)` with explicit exceptions or return error values. Remove `get_logger` imports. |
| **Validation** | `rg "get_logger\|import logging" bengal/core/` returns 0 matches |

### Task 1.4 — Extract `core/theme/resolution.py` manifest I/O

| Field | Value |
|-------|-------|
| **Files** | `bengal/core/theme/resolution.py` (lines 43, 67, 95) |
| **Issue** | Three `open()` calls reading manifest JSON files |
| **Action** | Accept manifest data as a parameter instead of reading from disk. Caller (orchestration or config layer) handles file reads. |
| **Validation** | `rg "open\(" bengal/core/theme/resolution.py` returns 0 matches |

**Sprint 1 done-check**: `rg "(get_logger|import logging|open\(|\.write\(|\.read\()" bengal/core/` returns only false positives (e.g., `open` in docstrings).

---

## Sprint 2: Boundary Violation Elimination

**Goal**: `bengal/core/` has zero imports from `orchestration/`, `rendering/`, `server/`, or `cache/`.

### Task 2.1 — Extract `Site.build()` / `Site.serve()` from `core/site/lifecycle.py`

| Field | Value |
|-------|-------|
| **Files** | `bengal/core/site/lifecycle.py` (imports at lines 23-26, 169, 196, 294, 298) |
| **Issue** | `SiteLifecycleMixin` imports `BuildOrchestrator`, `DevServer`, `BuildState`, `BuildStats`, rendering thread-locals. This makes `Site` a god object. |
| **Action** | Move `build()`, `serve()`, `clean()` methods to a new `bengal/orchestration/site_runner.py`. `Site` becomes a pure data container; CLI calls `SiteRunner(site).build()` instead of `site.build()`. |
| **Validation** | `rg "from bengal\.(orchestration\|server\|rendering)" bengal/core/site/lifecycle.py` returns 0 |
| **Coordination** | Overlaps with Site Cleanup & Service Wiring Phases 4-5. Sequence after those land. |

### Task 2.2 — Remove `core/site/cascade.py` → orchestration import

| Field | Value |
|-------|-------|
| **Files** | `bengal/core/site/cascade.py:19` |
| **Issue** | `TYPE_CHECKING` import of `BuildState` from orchestration |
| **Action** | Use `Protocol` or move the type reference to `bengal/protocols/` |
| **Validation** | `rg "from bengal\.orchestration" bengal/core/site/cascade.py` returns 0 |

### Task 2.3 — Remove `core/site/__init__.py` → cache/orchestration imports

| Field | Value |
|-------|-------|
| **Files** | `bengal/core/site/__init__.py` (lines 78-83, 396, 557) |
| **Issue** | Imports `BengalPaths`, `QueryIndexRegistry`, `BuildState` from cache/orchestration |
| **Action** | Inject these as constructor params or move to `BuildContext`. `Site` should not know about `BengalPaths` or `QueryIndexRegistry`. |
| **Validation** | `rg "from bengal\.(cache\|orchestration)" bengal/core/site/__init__.py` returns 0 |

### Task 2.4 — Remove `core/page/` → rendering imports

| Field | Value |
|-------|-------|
| **Files** | `core/page/metadata.py:300`, `core/page/proxy.py:377`, `core/page/__init__.py:924` |
| **Issue** | Page models import `extract_toc_structure` and `has_shortcode` from rendering |
| **Action** | Move shortcode detection to a utility or make it a property set by the rendering layer. TOC extraction should be injected, not pulled. |
| **Validation** | `rg "from bengal\.rendering" bengal/core/page/` returns 0 |

### Task 2.5 — Remove `core/section/ergonomics.py` → rendering import

| Field | Value |
|-------|-------|
| **Files** | `bengal/core/section/ergonomics.py:40` |
| **Issue** | `TYPE_CHECKING` import of `TemplateEngine` from rendering |
| **Action** | Use `Protocol` in `bengal/protocols/rendering.py` instead |
| **Validation** | `rg "from bengal\.rendering" bengal/core/section/` returns 0 |

**Sprint 2 done-check**: `rg "from bengal\.(orchestration|rendering|cache|server|build)" bengal/core/` returns 0 matches (excluding `bengal/core/` self-imports).

---

## Sprint 3: Provenance Naming & Build Disambiguation

**Goal**: Eliminate naming confusion between `build/` and `orchestration/build/`.

### Task 3.1 — Rename `orchestration/build/provenance_filter.py`

| Field | Value |
|-------|-------|
| **Files** | `bengal/orchestration/build/provenance_filter.py` (988 lines) |
| **Issue** | Name collision with `bengal/build/provenance/filter.py` (909 lines) |
| **Action** | Rename to `provenance_orchestration.py` or `provenance_phase.py`. Update all 4 import sites. |
| **Validation** | No file named `*provenance_filter*` exists in `orchestration/` |

### Task 3.2 — Add `build/` vs `orchestration/build/` README

| Field | Value |
|-------|-------|
| **Files** | `bengal/build/README.md`, `bengal/orchestration/build/README.md` |
| **Action** | Document the distinction: `build/` = contracts, types, provenance data; `orchestration/build/` = coordination, phases, build lifecycle |

---

## Sprint 4: File Size Reduction (Top Offenders)

**Goal**: No file exceeds 800 lines. Files over 1,000 lines are split into packages.

### Task 4.1 — Convert `core/nav_tree.py` (845 lines) to package

| Field | Value |
|-------|-------|
| **Issue** | 5 classes in one file: `NavNode`, `NavTree`, `NavTreeContext`, `NavNodeProxy`, `NavTreeCache` |
| **Action** | Create `core/nav_tree/` package: `node.py`, `tree.py`, `context.py`, `proxy.py`, `cache.py` |

### Task 4.2 — Split `core/page/__init__.py` (1,053 lines)

| Field | Value |
|-------|-------|
| **Issue** | Page class too large even after mixin extraction |
| **Action** | Audit which methods remain in `__init__.py` vs should move to existing mixins (`metadata.py`, `content.py`, `navigation.py`, `computed.py`). Target: `__init__.py` ≤ 400 lines. |

### Task 4.3 — Split `core/site/__init__.py` (827 lines)

| Field | Value |
|-------|-------|
| **Issue** | After Sprint 2 boundary fixes, residual size should be addressed |
| **Action** | Move data-loading and query methods to existing accessors/content mixins. Target: ≤ 500 lines. |

### Task 4.4 — Split `orchestration/menu.py` (1,037 lines)

| Field | Value |
|-------|-------|
| **Action** | Convert to `orchestration/menu/` package — separate builders, resolvers, and weight calculators |

### Task 4.5 — Split `orchestration/content.py` (990 lines)

| Field | Value |
|-------|-------|
| **Action** | Extract content discovery coordination from content population logic |

### Task 4.6 — Split `rendering/renderer.py` (937 lines)

| Field | Value |
|-------|-------|
| **Action** | Extract render method dispatch (page vs section vs special) into sub-modules |

---

## Sprint 5: Server God Module Decomposition

**Goal**: No server file exceeds 800 lines. Build triggering logic lives in `orchestration/`.

### Task 5.1 — Split `server/build_trigger.py` (1,450 lines)

| Field | Value |
|-------|-------|
| **Issue** | Largest file in the codebase — mixes event detection, debouncing, build coordination |
| **Action** | Extract into `server/build_trigger/` package: `events.py` (FS event detection), `debouncer.py` (timing/batching), `coordinator.py` (build dispatch). Move build coordination to `orchestration/`. |

### Task 5.2 — Split `server/dev_server.py` (1,307 lines)

| Field | Value |
|-------|-------|
| **Issue** | HTTP serving + build integration + reload orchestration in one file |
| **Action** | Extract HTTP route handlers, keep server lifecycle thin. Build integration should delegate to orchestration layer. |

### Task 5.3 — Reduce `server/reload_controller.py` (934 lines)

| Field | Value |
|-------|-------|
| **Action** | Extract reload strategy selection and WebSocket management into separate modules |

---

## Verification

After all sprints:

```bash
# Model purity
rg "(get_logger|import logging|open\()" bengal/core/ --type py

# Boundary violations
rg "from bengal\.(orchestration|rendering|cache|server)" bengal/core/ --type py

# File sizes (should be 0 over 1000, minimal over 800)
find bengal/ -name '*.py' -not -path '*__pycache__*' | while read f; do
  lines=$(wc -l < "$f")
  [ "$lines" -gt 800 ] && echo "$lines $f"
done | sort -rn
```

---

## Related Plans

- `epic-protocol-migration.md` — Protocol adoption (Sprint 2 here aligns)
- `rfc-bengal-v2-architecture.md` — v2 architecture roadmap
- `rfc-package-separation-of-concerns.md` — Package restructuring
- `rfc-module-coupling-reduction.md` — Module coupling reduction
- `rfc-remaining-coupling-fixes.md` — Remaining coupling fixes
