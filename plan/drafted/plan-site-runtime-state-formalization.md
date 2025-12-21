# Implementation Plan: Site Runtime State Formalization

**RFC**: `rfc-site-runtime-state-formalization.md`  
**Status**: Ready to Implement  
**Estimated Effort**: 3-4 hours  
**Priority**: P2 (Medium)

---

## Overview

This plan implements the two-phase approach from the RFC:
- **Phase A**: Cleanup unnecessary `type: ignore` comments (~1 hour)
- **Phase B**: Formalize 7 remaining fields in Site dataclass (~2-3 hours)

---

## Phase A: Cleanup Already-Formalized Fields

### A.1 Template Functions Cleanup

**File**: `bengal/rendering/template_functions/get_page.py`

**Tasks**:
- [ ] Remove `# type: ignore[attr-defined]` from `_template_parser` access (lines ~53, 57-60, 62)
- [ ] Remove `# type: ignore[attr-defined]` from `_page_lookup_maps` access (lines ~187, 214, 273)

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "rendering(get_page): remove unnecessary type: ignore for formalized Site fields"
```

---

### A.2 Orchestration Content Cleanup

**File**: `bengal/orchestration/build/content.py`

**Tasks**:
- [ ] Remove `# type: ignore[attr-defined]` from `_affected_tags` access (lines ~116, 123)

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "orchestration(content): remove type: ignore for _affected_tags (already formalized)"
```

---

### A.3 Orchestration Finalization Cleanup

**File**: `bengal/orchestration/build/finalization.py`

**Tasks**:
- [ ] Remove `# type: ignore[attr-defined]` from `_last_build_stats` access (line ~97)

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "orchestration(finalization): remove type: ignore for _last_build_stats (already formalized)"
```

---

### A.4 Menu Orchestrator Cleanup

**File**: `bengal/orchestration/menu.py`

**Tasks**:
- [ ] Remove `# type: ignore[attr-defined]` from `_dev_menu_metadata` access (lines ~251, 334)
- [ ] Remove `hasattr` check if field is guaranteed to exist

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "orchestration(menu): remove type: ignore for _dev_menu_metadata (already formalized)"
```

---

### A.5 Health Validators Cleanup

**File**: `bengal/health/validators/tracks.py`

**Tasks**:
- [ ] Remove `# type: ignore[attr-defined]` from `_page_lookup_maps` access (line ~158)

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "health(tracks): remove type: ignore for _page_lookup_maps (already formalized)"
```

---

### A.6 Phase A Validation

**Tasks**:
- [ ] Run `ruff check bengal/` to verify no new linting errors
- [ ] Run `mypy bengal/` to verify type checking passes
- [ ] Run `pytest tests/` to verify no test regressions

**Pre-drafted Commit** (if any fixes needed):
```bash
git add -A && git commit -m "chore: fix any issues from Phase A cleanup"
```

---

## Phase B: Formalize Remaining Fields

### B.1 Add Fields to Site Dataclass

**File**: `bengal/core/site/core.py`

**Tasks**:
- [ ] Add `_asset_manifest_previous: Any` field (default=None, repr=False, init=False)
- [ ] Add `_asset_manifest_fallbacks_global: set[str]` field (default_factory=set, repr=False, init=False)
- [ ] Add `_asset_manifest_fallbacks_lock: Any` field (default=None, repr=False, init=False)
- [ ] Add `_bengal_theme_chain_cache: dict[str, Any] | None` field
- [ ] Add `_bengal_template_dirs_cache: dict[str, Any] | None` field
- [ ] Add `_bengal_template_metadata_cache: dict[str, Any] | None` field
- [ ] Add `_discovery_breakdown_ms: dict[str, float] | None` field
- [ ] Update `__post_init__` to initialize `_asset_manifest_fallbacks_lock` with `threading.Lock()`
- [ ] Update `reset_ephemeral_state()` to clear new cache fields

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "core(site): add 7 runtime cache fields for asset manifest, template env, and discovery state"
```

---

### B.2 Update Jinja Engine

**File**: `bengal/rendering/engines/jinja.py`

**Tasks**:
- [ ] Remove `hasattr` check for `_asset_manifest_fallbacks_global` (line ~104)
- [ ] Remove `hasattr` check for `_asset_manifest_fallbacks_lock` (line ~106)
- [ ] Remove `# type: ignore[attr-defined]` comments (lines ~105, 107)
- [ ] Remove try/except wrapper if no longer needed

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "rendering(jinja): use formalized Site fields for asset manifest fallbacks"
```

---

### B.3 Update Asset Orchestrator

**File**: `bengal/orchestration/asset.py`

**Tasks**:
- [ ] Remove `# type: ignore[attr-defined]` from `_asset_manifest_previous` access (lines ~192, 194)

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "orchestration(asset): use formalized _asset_manifest_previous field"
```

---

### B.4 Update Content Orchestrator

**File**: `bengal/orchestration/content.py`

**Tasks**:
- [ ] Remove `# type: ignore[attr-defined]` from `_discovery_breakdown_ms` access (line ~216)

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "orchestration(content): use formalized _discovery_breakdown_ms field"
```

---

### B.5 Update Metadata Utils

**File**: `bengal/utils/metadata.py`

**Tasks**:
- [ ] Remove try/except wrapper around `_bengal_template_metadata_cache` access (line ~241)
- [ ] Remove `# type: ignore[attr-defined]` if present

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "utils(metadata): use formalized _bengal_template_metadata_cache field"
```

---

### B.6 Update Template Environment

**File**: `bengal/rendering/template_engine/environment.py`

**Tasks**:
- [ ] Remove try/except wrapper around `_bengal_theme_chain_cache` access (line ~185)
- [ ] Remove try/except wrapper around `_bengal_template_dirs_cache` access (line ~346)
- [ ] Remove `# type: ignore[attr-defined]` if present

**Pre-drafted Commit**:
```bash
git add -A && git commit -m "rendering(environment): use formalized theme/template cache fields"
```

---

### B.7 Phase B Validation

**Tasks**:
- [ ] Run `ruff check bengal/` to verify no linting errors
- [ ] Run `mypy bengal/` to verify type checking passes
- [ ] Run `pytest tests/` to verify no test regressions
- [ ] Test dev server with incremental rebuild

**Pre-drafted Commit** (if any fixes needed):
```bash
git add -A && git commit -m "chore: fix any issues from Phase B formalization"
```

---

## Phase C: Final Validation

### C.1 Full Test Suite

**Tasks**:
- [ ] Run `pytest tests/ -x` (stop on first failure)
- [ ] Run `pytest tests/integration/` specifically
- [ ] Verify parallel test execution works

---

### C.2 Type Checking

**Tasks**:
- [ ] Run `mypy bengal/` with strict mode
- [ ] Verify no new `type: ignore` comments needed

---

### C.3 Dev Server Testing

**Tasks**:
- [ ] Start dev server: `bengal serve site/`
- [ ] Make a content change, verify incremental rebuild
- [ ] Make a template change, verify full rebuild
- [ ] Make an asset change, verify asset manifest works

---

### C.4 Grep Verification

**Tasks**:
- [ ] Verify no remaining `type: ignore[attr-defined]` for Site fields:
  ```bash
  grep -r "site\._.*type: ignore\[attr-defined\]" bengal/
  ```
- [ ] Verify no remaining `hasattr(.*site.*"_` for formalized fields:
  ```bash
  grep -rE "hasattr\(.*site.*\"_(asset_manifest|bengal_template|discovery_breakdown)" bengal/
  ```

---

## Summary

| Phase | Tasks | Files | Est. Time |
|-------|-------|-------|-----------|
| A.1 | 2 | `get_page.py` | 15 min |
| A.2 | 1 | `content.py` | 5 min |
| A.3 | 1 | `finalization.py` | 5 min |
| A.4 | 1 | `menu.py` | 10 min |
| A.5 | 1 | `tracks.py` | 5 min |
| A.6 | 3 | (validation) | 10 min |
| **Phase A Total** | **9** | **5 files** | **~50 min** |
| B.1 | 9 | `core.py` | 30 min |
| B.2 | 4 | `jinja.py` | 15 min |
| B.3 | 1 | `asset.py` | 10 min |
| B.4 | 1 | `content.py` | 5 min |
| B.5 | 1 | `metadata.py` | 10 min |
| B.6 | 2 | `environment.py` | 15 min |
| B.7 | 4 | (validation) | 15 min |
| **Phase B Total** | **22** | **6 files** | **~100 min** |
| C.1-C.4 | 4 | (validation) | 30 min |
| **Grand Total** | **35** | **10 files** | **~3 hours** |

---

## Execution Order

1. **Phase A first** - Quick wins, zero risk
2. **Commit after each A.x task** - Atomic commits
3. **Phase B after A validated** - More involved changes
4. **Commit after each B.x task** - Atomic commits
5. **Phase C last** - Full validation

---

## Rollback Strategy

Each phase has atomic commits. If issues arise:

- **Phase A issues**: Revert individual A.x commits
- **Phase B issues**: Revert B.1 first (Site fields), then B.x commits
- **Full rollback**: `git revert` all commits back to pre-implementation

---

## Success Criteria

- [ ] All `type: ignore[attr-defined]` for Site fields removed
- [ ] All 7 fields formalized in Site dataclass
- [ ] Type checker passes without new errors
- [ ] All tests pass
- [ ] Dev server incremental builds work
- [ ] No runtime errors in production builds
