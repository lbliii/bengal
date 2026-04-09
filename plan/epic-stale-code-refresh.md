# Epic: Stale Code Refresh

**Status**: Complete (all 4 sprints)
**Created**: 2026-04-09
**Target**: v0.3.x
**Estimated Effort**: 12-18 hours
**Dependencies**: None — all sprints ship independently
**Source**: Stale Code Audit (2026-04-09) — 50+ files untouched since Jan 2026 or earlier

---

## Why This Matters

The stale code audit surfaced **6 tier-1** and **5 tier-2** issues across ~5,400 lines of untouched code. The highest-risk findings are:

1. **Thread-safety race** — `core/version.py:296` mutates `_version_map` dict via `add_discovered_version()` without synchronization, risking corruption under free-threading
2. **Shallow copy bug** — `config/deprecation.py:190` uses `.copy()` on nested config dicts; mutations to nested values leak through to the original
3. **Broken type hint** — `cli/dashboard/notifications.py:19` imports deleted `BengalDashboard` from `dashboard.base`; replaced by `BengalApp`
4. **~120 lines of dead code** — `health/validators/directives/analysis.py` contains two disabled nesting-check methods that are never called
5. **Repeated boilerplate** — all 6 `cli/commands/graph/` commands duplicate identical site-loading + graph-building scaffolding (~20 lines each)
6. **DRY violation** — `cli/commands/new/scaffolds.py` has three near-identical scaffold commands (page, layout, partial)

Left unaddressed, the thread-safety issue poses a real free-threading risk, the shallow copy can produce silent config corruption, and the duplicated graph boilerplate makes the graph commands fragile to evolve.

---

## Evidence Table

| Audit Finding | Sprint | Fixed? |
|--------------|--------|--------|
| Thread-unsafe `_version_map` mutation (version.py:296) | 1 | Done |
| Shallow copy on nested config (deprecation.py:190) | 1 | Done |
| ~~Broken `BengalDashboard` import (notifications.py:19)~~ | 1 | Dropped (false positive — class still exists) |
| Dead nesting-check methods (analysis.py:417-495, 678-727) | 2 | Done — removed 205 lines |
| Graph command boilerplate duplication (6 files) | 3 | Done — extracted `load_graph()` + helpers into `common.py` |
| Scaffold command DRY violation (scaffolds.py) | 3 | Done — extracted `_create_template_scaffold()` helper |
| Hardcoded autodoc types (url_policy.py:86) | 2 | Done — iterates autodoc_config.items() |
| Manual TOML generation (project.py:473-484) | 4 | Done — replaced with tomli_w.dumps(), moved tomli_w to core deps |
| Dead `_redirect_format` param (debug.py:420) | 2 | Done |
| Unreachable code (debug.py:462-466) | 2 | Done — simplified to single call |
| ~~Hash/equality contract (openapi.py:175-224)~~ | 2 | Dropped (custom __hash__ is necessary for unhashable dict fields; contract is preserved) |
| Unguarded version path parsing (version.py:418-422) | 4 | Done — added empty version_id guard |
| Silent exception handlers (report.py:113-120) | 4 | Done — added logger.debug() with exc_info |
| ~~Bare except Exception (section/utils.py:45-57)~~ | 4 | Dropped (explicit design intent: "intentionally silent on errors, core modules do not log") |

---

## Invariants

1. **Full test suite passes** after every sprint — no regressions
2. **Free-threading safety** — no unprotected shared mutable state in core/
3. **Each sprint ships independently** — partial completion still delivers value

---

## Sprint Overview

| Sprint | Focus | Ships Independently? | Effort | Risk |
|--------|-------|---------------------|--------|------|
| **1** | Safety fixes: thread-safety, shallow copy, broken import | Yes | 2-3h | Low |
| **2** | Dead code removal and correctness fixes | Yes | 3-4h | Low |
| **3** | DRY: graph command boilerplate + scaffold consolidation | Yes | 4-6h | Medium |
| **4** | Design improvements: TOML lib, dynamic autodoc types | Yes | 3-5h | Low |

---

## Sprint 1 — Safety Fixes

**Goal**: Fix the three issues that could cause runtime failures or data corruption.

### Tasks

1. **Thread-safe `_version_map`** (`core/version.py:296`)
   - Add a `threading.Lock` to guard `_version_map` mutations in `add_discovered_version()`
   - Or convert to a `@property` that rebuilds from `self.versions` on access (simpler, eliminates mutable shared state)
   - **Acceptance**: `rg '_version_map\[' bengal/core/version.py` shows no unguarded mutations

2. **Deep copy for nested config** (`config/deprecation.py:190`)
   - Replace `.copy()` with `copy.deepcopy()` when `in_place=False`
   - **Acceptance**: Unit test confirms nested dict mutation in output doesn't affect input

3. **Fix broken dashboard import** (`cli/dashboard/notifications.py:19`)
   - Change `from bengal.cli.dashboard.base import BengalDashboard` to import `BengalApp` from the correct module
   - Update all type hints in the file (`app: BengalDashboard` → `app: BengalApp`)
   - **Acceptance**: `python -c "from bengal.cli.dashboard.notifications import *"` succeeds

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| `_version_map` property rebuild is too slow | Low | Benchmark; dict rebuild from ~10 versions is negligible |
| `deepcopy` on config is slow for large configs | Low | Profile; configs are small (<1MB). Only runs once at startup |

---

## Sprint 2 — Dead Code and Correctness

**Goal**: Remove dead code and fix correctness issues in untouched files.

### Tasks

1. **Remove dead nesting checks** (`health/validators/directives/analysis.py:417-495, 678-727`)
   - Delete `_check_code_block_nesting()` and `_check_fence_nesting()` methods
   - Remove any orphaned index builders that only served these methods
   - **Acceptance**: `rg '_check_code_block_nesting|_check_fence_nesting' bengal/` returns zero hits; test suite passes

2. **Remove dead `_redirect_format` parameter** (`cli/commands/debug.py:420`)
   - Remove the click option and the unused parameter
   - **Acceptance**: `rg '_redirect_format' bengal/cli/` returns zero hits

3. **Fix unreachable code** (`cli/commands/debug.py:462-466`)
   - Analyze the migration preview logic and remove the dead branch
   - **Acceptance**: No behavior change; code path coverage unchanged

4. **Fix hash/equality contract** (`autodoc/models/openapi.py:175-224`)
   - Remove custom `__hash__` methods from frozen dataclasses (frozen dataclasses auto-generate correct hash)
   - Or ensure `__hash__` is consistent with `__eq__`
   - **Acceptance**: `hash(obj) == hash(identical_obj)` holds for equal objects

5. **Hardcoded autodoc types** (`config/url_policy.py:86`)
   - Replace `["python", "openapi", "cli"]` with `autodoc_config.keys()` or equivalent dynamic lookup
   - **Acceptance**: Adding a new autodoc type doesn't require updating url_policy.py

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Removing nesting checks breaks downstream validator orchestration | Medium | Verify no callers via grep before deletion |
| Removing custom `__hash__` changes set/dict behavior | Medium | Search for sets/dicts containing these objects; verify equality semantics |

---

## Sprint 3 — DRY Consolidation

**Goal**: Extract duplicated patterns in graph commands and scaffold creation.

### Tasks

1. **Extract graph command boilerplate** (`cli/commands/graph/*.py`)
   - Create a shared `_load_graph(site_root, ...)` utility that encapsulates:
     - `load_site_from_cli()`
     - `ContentOrchestrator` setup
     - `KnowledgeGraph.build()`
   - Refactor all 6 commands (bridges, communities, orphans, pagerank, report, suggest) to use it
   - Extract repeated `graph_obj.incoming_refs.get(page, 0)` pattern into a `PageMetrics` helper or cached dict
   - **Acceptance**: `rg 'load_site_from_cli' bengal/cli/commands/graph/` appears in exactly 1 file (the utility)

2. **Consolidate scaffold commands** (`cli/commands/new/scaffolds.py`)
   - Extract common logic from page/layout/partial commands into `_create_scaffold(kind, name, path, template)`
   - Keep CLI entry points thin (option parsing + delegation)
   - **Acceptance**: No duplicated file-creation logic; each command is <20 lines

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Graph utility changes command behavior subtly | Medium | Run `bengal graph --help` and all subcommands before/after; diff output |
| Scaffold refactor breaks preset/wizard integration | Low | Verify wizard.py and presets.py still work end-to-end |

---

## Sprint 4 — Design Improvements

**Goal**: Replace fragile patterns with proper library usage.

### Tasks

1. **Use TOML library for config writing** (`cli/commands/project.py:473-484`)
   - Replace manual string concatenation with `tomli_w.dumps()` or `tomllib`-compatible writer
   - Handle nested objects, arrays, and all TOML types correctly
   - **Acceptance**: Round-trip test: `write_config(read_config(path))` produces valid TOML

2. **Harden path parsing** (`core/version.py:416-420`)
   - Add bounds checking for `split("/")` operations on version paths
   - Handle malformed paths gracefully instead of crashing
   - **Acceptance**: Malformed version path produces clear error, not IndexError

3. **Tighten exception handling** (`core/section/utils.py:45-48`)
   - Replace bare `except Exception` with specific exceptions (AttributeError, TypeError)
   - **Acceptance**: `rg 'except Exception' bengal/core/section/utils.py` returns zero hits

4. **Add logging to silent exception handlers** (`cli/commands/graph/report.py:134-142`)
   - Replace silent `except` blocks with `logger.warning()` or `logger.debug()`
   - **Acceptance**: Failed bridge/community analysis produces a visible warning

---

## Success Metrics

| Metric | Before | After Sprint 2 | After Sprint 4 |
|--------|--------|----------------|----------------|
| Dead code lines | ~205 | 0 | 0 |
| Unguarded shared mutations in core/ | 1 | 0 | 0 |
| Duplicated graph boilerplate sites | 6 | 6 → 1 | 1 |
| Silent exception swallows | 3 | 3 | 1 (section/utils.py — by design) |
| Files with known correctness bugs | 3 | 0 | 0 |
| Manual TOML serialization | 1 | 1 | 0 |

---

## Tier 3 Items (Deferred / Opportunistic)

These are low-priority and can be addressed opportunistically when touching adjacent code:

- `config/feature_mappings.py:173-194` — O(n²) list membership; convert to set for dedup
- `cli/commands/graph/bridges.py` (+ others) — repeated `incoming_refs.get()` pattern (addressed partially by Sprint 3)
- `tests/unit/utils/test_sections_utils.py:272` — rename `test_with_cached_page_proxy` to remove stale PageProxy terminology
- `cache/version.py:21` — pickle format for version numbers is over-engineered but functional
- `errors/suggestions.py:806` — pre-compute searchable text for large suggestion registry
