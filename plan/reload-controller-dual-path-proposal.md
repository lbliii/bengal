# ReloadController Dual Path Analysis & Consolidation Proposal

**Status**: Proposal  
**Date**: 2025-03-14  
**Context**: ReloadController has snapshot diff (mtime/size) vs content-hash mode. Different code paths run depending on config. Content-hash mode depends on `bengal:content-hash` meta tags; if missing, falls back to full content hash. The two paths can disagree.

---

## 1. Current Flow Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         RELOAD DECISION ENTRY POINTS                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─ BuildTrigger._handle_reload() [file-change-driven rebuilds] ─────────────────────┐
│                                                                                    │
│  changed_outputs?                                                                  │
│       │                                                                            │
│       ├─ YES ──► records = to_output_record() for each                             │
│       │              │                                                             │
│       │              ├─ records OK ──► decide_from_outputs(records, reload_hint)  │
│       │              │                   [PRIMARY: typed OutputRecord, no snapshot] │
│       │              │                                                             │
│       │              └─ records empty ──► decide_from_changed_paths(paths)       │
│       │                                      [FALLBACK: path list, extension CSS] │
│       │                                                                            │
│       └─ NO ──► changed_files?                                                    │
│                     ├─ YES ──► ReloadDecision("reload", "source-change-no-outputs")│
│                     └─ NO  ──► ReloadDecision("none", "no-changes")               │
│                                                                                    │
│  [Content-hash filter - conditional]                                               │
│  IF decision.action=="reload" AND decision_source!="fallback-source-change"        │
│     AND NOT changed_files AND use_content_hashes AND baseline exists:              │
│       enhanced = decide_with_content_hashes(output_dir)                           │
│       IF meaningful_change_count==0 → decision="none", reason="aggregate-only"    │
│                                                                                    │
│  NOTE: Content-hash filter almost never runs in normal dev flow (changed_files    │
│        is non-empty when user triggers build). Filter targets edge cases.          │
└────────────────────────────────────────────────────────────────────────────────────┘

┌─ DevServer._run_validation_build() [validation build on startup] ──────────────────┐
│                                                                                    │
│  Pre-build: capture_content_hash_baseline() OR decide_and_update() [legacy]       │
│                                                                                    │
│  Post-build:                                                                       │
│       use_content_hashes?                                                          │
│            ├─ YES ──► decide_with_content_hashes(output_dir)                      │
│            │            [Full HTML+CSS scan, compare hashes, categorize by type]  │
│            │                                                                       │
│            └─ NO  ──► decide_and_update(output_dir)  [LEGACY: snapshot mtime/size]│
│                         [Walk output dir, diff snapshots, optional hash verify]   │
└────────────────────────────────────────────────────────────────────────────────────┘

┌─ decide_and_update() [SNAPSHOT MODE] ────────────────────────────────────────────┐
│  1. _take_snapshot() → size, mtime per file                                        │
│  2. _diff(prev, curr) → changed, css_changed                                       │
│  3. Optional: hash_on_suspect → MD5 verify size-equal mtime-diff (false positive) │
│  4. Apply ignore globs                                                             │
│  5. _make_css_decision() → none | reload-css | reload                              │
│  Returns: ReloadDecision                                                           │
└────────────────────────────────────────────────────────────────────────────────────┘

┌─ decide_with_content_hashes() [CONTENT-HASH MODE] ────────────────────────────────┐
│  1. For each *.html: extract_content_hash() or hash_str(content, truncate=16)     │
│  2. For each *.css: hash_file(truncate=16)                                         │
│  3. Compare to _baseline_content_hashes (captured BEFORE build)                    │
│  4. Categorize: content_changes, aggregate_changes, asset_changes                  │
│  5. aggregate-only → action="none"; content/asset → action="reload"/"reload-css"  │
│  Returns: EnhancedReloadDecision                                                  │
└────────────────────────────────────────────────────────────────────────────────────┘

┌─ Content Hash Embedding (output.py) ──────────────────────────────────────────────┐
│  format_html() → embed_content_hash() when content_hash_in_html=True (default)    │
│  Meta tag: <meta name="bengal:content-hash" content="{sha256_truncate_16}">        │
│  extract_content_hash() → None if missing → fallback: hash_str(content, 16)       │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Entry Point Summary

| Entry Point | Caller | Condition | Method Used |
|-------------|--------|-----------|-------------|
| BuildTrigger (primary) | `_handle_reload` | `changed_outputs` + records OK | `decide_from_outputs` |
| BuildTrigger (fallback) | `_handle_reload` | `changed_outputs` but type reconstruction fails | `decide_from_changed_paths` |
| BuildTrigger (filter) | `_handle_reload` | `decision=="reload"` + `not changed_files` + content-hash mode | `decide_with_content_hashes` |
| DevServer validation | `_run_validation_build` | `use_content_hashes=True` | `decide_with_content_hashes` |
| DevServer validation | `_run_validation_build` | `use_content_hashes=False` | `decide_and_update` |

**Key finding**: `decide_and_update` (snapshot mode) is **never** called from BuildTrigger. It is only used in DevServer validation when `use_content_hashes=False`. The docstring in reload_controller.py says "build_trigger.py: Calls decide_and_update after builds" — **outdated**; BuildTrigger uses `decide_from_outputs` / `decide_from_changed_paths`.

---

## 3. When Content-Hash vs Snapshot Mode Is Used

| Mode | When Used |
|------|-----------|
| **Content-hash** | `use_content_hashes=True` (default): DevServer validation, BuildTrigger content-hash filter |
| **Snapshot** | `use_content_hashes=False`: DevServer validation only (legacy path) |
| **Typed outputs** | Always when BuildTrigger has `changed_outputs` — uses `decide_from_outputs` (no snapshot, no content hash) |

---

## 4. Failure Modes

### 4.1 Meta Tag Missing

- **Cause**: `content_hash_in_html=False`, or HTML has no `<head>` tag, or embedding skipped (e.g. `fast_mode` before hash).
- **Behavior**: `extract_content_hash()` returns `None` → fallback to `hash_str(content, truncate=16)`.
- **Impact**: Correct but slower (O(n) read + hash per HTML file). No silent wrong decision.
- **Location**: `reload_controller.py:375-377`, `432-433`; `output.py:394-396`.

### 4.2 Hash Collision

- **Cause**: 16-char hex truncation (64 bits) — theoretical collision possible.
- **Impact**: Extremely low probability for typical doc sizes. Would cause false "no change" (missed reload) or false "change" (spurious reload).
- **Mitigation**: Use full hash or longer truncation if needed.

### 4.3 Throttling Differences

- **decide_from_outputs**: Throttle check before `_record_notification()`; records only when sending reload.
- **decide_with_content_hashes**: Throttle check first; `_last_notify_time_ms` updated only for reload/reload-css.
- **decide_and_update**: Baseline updated before throttle check; throttle can suppress after baseline update.
- **Impact**: Minor. All paths use same `_min_interval_ms`; timing of `_record_notification` vs baseline update can differ slightly.

### 4.4 Path Disagreement

- **Cause**: Build says "page X changed" (OutputRecord) but content hash says "same" (e.g. mtime-only touch, or vice versa).
- **Impact**: In BuildTrigger, content-hash filter runs only when `not changed_files`, so it rarely runs. When it does, `decide_with_content_hashes` can override typed-output decision. DevServer validation uses content-hash or snapshot exclusively, so no cross-path disagreement there.

### 4.5 Baseline Stale / Empty

- **Cause**: `capture_content_hash_baseline` not called before build, or output_dir empty at capture.
- **Impact**: `decide_with_content_hashes` treats all files as new → may over-trigger reload. BuildTrigger calls `capture_content_hash_baseline` before build when `use_content_hashes=True`; DevServer does the same for validation.

---

## 5. Proposed Improvements

### 5.1 Unify to Single Decision Path with Optional Optimizations

**Recommendation**: Use a single primary path and make others explicit optimizations or fallbacks.

1. **Primary path**: `decide_from_outputs` when typed outputs exist (current behavior).
2. **Fallback chain** (when no typed outputs):
   - `decide_with_content_hashes` when `use_content_hashes=True` and baseline exists
   - `decide_from_changed_paths` when changed paths known
   - `decide_and_update` as last resort (snapshot mode)

3. **Deprecate** `decide_and_update` as a first-class path; keep for backward compatibility and legacy validation, but document it as fallback.

### 5.2 Explicit Fallback Chain with Logging

Add a single `decide_reload()` orchestrator that:

```python
def decide_reload(
    self,
    output_dir: Path,
    outputs: list[OutputRecord] | None = None,
    changed_paths: list[str] | None = None,
    reload_hint: ReloadHint | None = None,
) -> ReloadDecision:
    """Unified entry point with explicit fallback chain."""
    # 1. Typed outputs (preferred)
    if outputs:
        return self.decide_from_outputs(outputs, reload_hint)
    # 2. Content-hash (when enabled and baseline exists)
    if self._use_content_hashes and self._baseline_content_hashes:
        return self._to_reload_decision(
            self.decide_with_content_hashes(output_dir)
        )
    # 3. Changed paths (when known)
    if changed_paths:
        return self.decide_from_changed_paths(changed_paths)
    # 4. Snapshot (last resort)
    logger.debug("reload_decision_fallback", path="snapshot")
    return self.decide_and_update(output_dir)
```

Log each fallback with `reload_decision_fallback` (path used, reason).

### 5.3 Validate Content-Hash Mode Prerequisites at Startup

Add startup validation when `use_content_hashes=True`:

1. **Check** `build.content_hash_in_html` is not explicitly `False` (warn if disabled).
2. **Sample** one HTML output after first build: if `extract_content_hash()` returns `None`, log `content_hash_missing_fallback` (indicates full-content hashing will be used).
3. **Document** in config: content-hash mode requires `content_hash_in_html: true` for optimal performance.

```python
def _validate_content_hash_prerequisites(self, site: SiteLike) -> None:
    """Warn if content-hash mode may fall back to full hashing."""
    cfg = site.config.get("build", {}) or {}
    if cfg.get("content_hash_in_html", True) is False:
        logger.warning(
            "content_hash_disabled",
            hint="content_hash_in_html=false; content-hash mode will use full-content hashing",
        )
```

---

## 6. Recommended Consolidation (Summary)

| Change | Priority | Effort |
|--------|----------|--------|
| Add `decide_reload()` orchestrator with fallback chain | High | Medium |
| Add fallback logging at each step | High | Low |
| Startup validation for content-hash prerequisites | Medium | Low |
| Deprecate `decide_and_update` as primary (doc only) | Low | Low |
| Fix outdated docstring (build_trigger → decide_from_outputs) | Low | Trivial |

---

## 7. Validation / Fallback Improvements

1. **Log when meta tag is missing**: In `extract_content_hash` callers, when `None` triggers full-content hash, log `content_hash_meta_missing` (path, debug level).
2. **Log when content-hash filter runs**: Already present (`reload_filtered_aggregate_only`, `content_hash_breakdown`).
3. **Log baseline capture**: `content_hash_baseline_captured` (file_count, output_dir) at debug level.
4. **Unify throttle semantics**: Ensure `_record_notification` is called only when a reload is actually sent; document in one place.

---

## 8. Files to Modify

- `bengal/server/reload_controller.py`: Add `decide_reload()`, fallback logging, fix docstring
- `bengal/server/build_trigger.py`: Use `decide_reload()` in `_handle_reload`, simplify content-hash filter integration
- `bengal/server/dev_server.py`: Use `decide_reload()` in validation build
- `bengal/rendering/pipeline/output.py`: Optional: log when `extract_content_hash` returns None (or in controller)
