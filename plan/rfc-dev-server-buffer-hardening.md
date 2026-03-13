# RFC: Dev Server Double-Buffer Edge Case Hardening

**Status**: Draft (v2 — revised after deep code review)  
**Created**: 2026-03-13  
**Author**: AI Assistant  
**Related**: `rfc-output-cache-architecture.md`, `rfc-graceful-shutdown-cancellation.md`

---

## Executive Summary

The dev server double-buffer architecture prevents serving torn content during warm rebuilds
and (as of recent fix) during serve-first validation. A deep code review revealed **three
critical issues** not covered in v1, plus the original five edge cases. The most severe—
subprocess builds not forcing atomic writes—silently corrupts the active buffer through
hardlinks, likely explaining ongoing instability in local previewing.

**Target**: Eliminate asset 404s, torn content, and silent corruption across all dev server
build and startup paths.

---

## Background

### Double-Buffer Architecture

| Build Type | Uses Buffer? | Build Executor | Flow |
|------------|--------------|----------------|------|
| **Warm rebuilds** (file changes) | Yes | In-process (`site.build()`) | Build → staging → swap → serve |
| **Initial build** (build-first) | No (not needed) | Subprocess (`BuildExecutor`) | Build completes → start server |
| **Serve-first validation** | Yes (fixed in v1) | Subprocess (`BuildExecutor`) | Server starts → build to staging → swap → serve |
| **Reactive path** (content-only) | No | In-process (single page) | Atomic write to active buffer |

The server always serves from `active_dir`; builds write to `staging_dir`. Swap only after
a successful build. `prepare_staging()` seeds staging via **hardlinks** from active for O(1)
per-file copying—the build must use **atomic writes** (temp + rename) to break the hardlink
and avoid corrupting the active buffer.

### Config Split: In-Process vs Subprocess

This distinction is central to several bugs in this RFC:

| Setting | In-process (warm build) | Subprocess (validation/initial) |
|---------|------------------------|-------------------------------|
| `fast_writes=False` | Set by `_prepare_dev_config()` | **NOT forwarded** — reads from disk |
| `fingerprint_assets=False` | Set by `_prepare_dev_config()` | Forwarded in `_execute_build()` |
| `minify_assets=False` | Set by `_prepare_dev_config()` | Forwarded in `_execute_build()` |
| `social_cards.enabled=False` | Set by `_prepare_dev_config()` | **NOT forwarded** |
| `search_preload=off` | Set by `_prepare_dev_config()` | **NOT forwarded** |

Warm builds inherit all dev overrides because they use the existing `site` object.
Subprocess builds create a fresh `Site.from_config()` and only receive overrides that
`_execute_build()` explicitly copies—currently just two of six.

### Recent Fix (v1)

**Problem**: Serve-first validation used `BuildExecutor` (subprocess), which wrote directly
to `output_dir` (public/). The server was serving from the same directory, causing a race:
HTML could be served before assets were written → 404s.

**Solution**: Added `output_dir_override` to `BuildRequest`; validation build now writes to
staging, then swaps. Validation is fully protected by the double-buffer.

---

## Problem Statement

### Edge Cases (sorted by severity)

| # | Scenario | Impact | Likelihood | Source |
|---|----------|--------|------------|--------|
| **A** | Subprocess builds use direct writes through hardlinks | **Active buffer corruption, torn content** | **High** | v2 (code review) |
| **B** | Validation build failure crashes server | **Server dies, no recovery** | Medium | v2 (code review) |
| **C** | Watcher never starts if validation fails | **No file watching until restart** | Medium | v2 (code review) |
| 1 | Serve-first with incomplete cached assets | 404s on first load | Medium | v1 |
| 2 | BuildInput/BuildRequest field mismatch | `output_dir_override` lost if conversion used | Low | v1 |
| 3 | Edits during validation window | User edits lost until next save | Low | v1 |
| 4 | Reactive path writes to active buffer | Theoretical torn read (atomic writes mitigate) | Very Low | v1 |
| 5 | Concurrent validation + warm rebuild | Undefined (prevented by watcher timing) | Very Low | v1 |

---

### Issue A: Subprocess Builds Don't Force Atomic Writes (CRITICAL)

The double-buffer depends on atomic writes to break hardlinks. `_prepare_dev_config()` forces
`fast_writes=False` on the in-memory config:

```python
# dev_server.py:658-662
build_settings = cfg.get("build")
if isinstance(build_settings, dict):
    build_settings["fast_writes"] = False
else:
    cfg["build"] = {"fast_writes": False}
```

But subprocess builds in `_execute_build()` (build_executor.py) create a fresh
`Site.from_config()` from disk and only copy two overrides:

```python
# build_executor.py:158-163 — missing fast_writes!
cfg = site.config
site.dev_mode = True
cfg["fingerprint_assets"] = False
cfg.setdefault("minify_assets", False)
```

**`fast_writes=False` is never propagated to the subprocess.**

The corruption sequence:
1. `prepare_staging()` seeds staging via hardlinks (same inodes as active)
2. Subprocess builds to staging using direct `write_text()` (fast_writes default)
3. Direct writes go **through** the hardlinks — both files share an inode
4. Active buffer is silently corrupted mid-serve
5. Browser gets torn content: half old HTML, half new CSS, or vice versa

This affects **every serve-first validation build** — the most common startup path for
returning users. The existing test suite documents this exact hazard:

```python
# test_buffer_manager.py:110-122
def test_direct_write_shares_through_hardlink(self, mgr):
    """Direct write_text() writes through hardlinks (same inode).

    This is why the build pipeline MUST use atomic writes when
    double buffering is active.
    """
```

The invariant is documented in tests but **not enforced in the subprocess path**.

---

### Issue B: Validation Build Failure Crashes Server

In serve-first mode, validation runs in the foreground after the server thread starts:

```python
# dev_server.py:283-284
self._run_validation_build(BuildProfile.WRITER, actual_port)
```

`_run_validation_build` calls `_run_build_via_executor`, which raises `BengalServerError`
on build failure (line 555). There is **no try/except** around the validation call in
`start()`.

If validation fails (template error, config issue, disk full, etc.):
- Exception propagates through `start()`
- Server thread is already running as a daemon thread
- Main thread exits → daemon thread dies
- Browser gets a connection reset
- Cached content that *could* be served is abandoned

The correct behavior for serve-first: catch the failure, log it, and **keep serving the
cached content**. That's the entire value proposition of serve-first.

---

### Issue C: Watcher Never Starts If Validation Fails

The watcher start is at the end of `_run_validation_build()`:

```python
# dev_server.py:511-515
if self.watch and hasattr(self, "_watcher_runner") and hasattr(self, "_build_trigger"):
    self._build_trigger.seed_content_hash_cache(list(self.site.pages))
    self._watcher_runner.start()
```

If validation throws (Issue B), this code never executes. The user is left with a running
server that:
- Serves stale cached content (best case)
- Shows nothing (worst case, if Issue B also fires)
- **Never rebuilds** on file changes — they must Ctrl+C and restart

Even if Issue B is fixed (validation failure caught), the watcher must still start afterward.

---

### Issue 1: Serve-First with Incomplete Cached Assets

`_has_cached_output()` checks for:
- `output_dir` exists
- Build cache exists
- `index.html` exists (or any `*.html`)

It does **not** check for assets. If a user runs `rm -rf public/assets` but leaves
`public/index.html`, serve-first activates. The server serves stale HTML immediately;
assets 404 until validation completes (or forever if validation also fails per Issue B).

---

### Issue 2: BuildInput/BuildRequest Field Sync

`BuildInput.to_build_request()` does not include `output_dir_override`. Currently safe
because the dev server creates `BuildRequest` directly (bypassing `BuildInput`), and
`_execute_build()` applies the override before creating `BuildInput`:

```python
# build_executor.py:155-156
if request.output_dir_override:
    site.output_dir = Path(request.output_dir_override)
```

**Risk**: Future refactors that route through `BuildInput.to_build_request()` for
validation-like flows would silently lose the override. Low priority — defensive only.

---

### Issue 3: Edits During Validation

The watcher starts only after validation completes. Edits made during validation
(~5–15s window) are not detected until the watcher is running. Small impact.

---

### Issue 4: Reactive Path (Very Low Risk)

The reactive path writes directly to the active buffer using atomic writes. Risk is
theoretical. The `ReactiveContentHandler` processes a single page and writes one file.
Atomic rename is sufficient.

---

### Issue 5: Concurrent Builds (Very Low Risk)

The `_build_lock` in `BuildTrigger` and the watcher-after-validation ordering prevent
concurrent builds today. Defer unless the architecture changes.

---

## Proposed Solution

### Phase 0: Force Atomic Writes in Subprocess (CRITICAL — Fix First)

**Goal**: Enforce the hardlink-safety invariant across all build paths.

**Change**: In `_execute_build()` (build_executor.py), force `fast_writes=False` alongside
the other dev overrides:

```python
# build_executor.py — in _execute_build(), after existing overrides:
cfg = site.config
site.dev_mode = True
cfg["fingerprint_assets"] = False
cfg.setdefault("minify_assets", False)

# CRITICAL: Force atomic writes (temp+rename) so builds break hardlinks.
# Without this, writes to staging go through hardlinks and corrupt the
# active buffer that the server is currently serving.
build_settings = cfg.get("build")
if isinstance(build_settings, dict):
    build_settings["fast_writes"] = False
else:
    cfg["build"] = {"fast_writes": False}
```

**Acceptance**:
- `test_buffer_manager.py::test_atomic_overwrite_breaks_hardlink` continues to pass
- New test: subprocess build to hardlinked staging does not modify active buffer contents
- All existing dev server tests pass

**Risk**: None. Atomic writes are already forced for in-process builds. This aligns the
subprocess path.

**Future hardening**: Consider forwarding ALL dev overrides through a single
`DevConfig` dataclass instead of copying individual fields. This prevents future config
drift. Candidates currently not forwarded:
- `social_cards.enabled = False`
- `search_preload = "off"`
- Template bytecode cache clearing

---

### Phase 1: Resilient Validation (HIGH — Serve-First Stability)

**Goal**: Validation failure must not crash the server or prevent file watching.

**Changes**:

1. Wrap `_run_validation_build()` call in `start()` with try/except:

```python
# dev_server.py — in serve-first branch of start():
try:
    self._run_validation_build(BuildProfile.WRITER, actual_port)
except Exception as exc:
    logger.error(
        "validation_build_failed",
        error=str(exc),
        action="continuing_with_cached_content",
    )
    icons = get_icons()
    print(f"\n  {icons.warning} Validation failed: {exc}")
    print(f"  {icons.arrow} Serving cached content — next file change will trigger rebuild")

    # Start watcher despite failure so rebuilds work
    if self.watch and hasattr(self, "_watcher_runner"):
        self._watcher_runner.start()
```

2. Move watcher start out of `_run_validation_build()` into a `finally` block or
   unconditional post-validation step, ensuring it starts regardless of outcome.

**Acceptance**:
- Validation failure → server keeps running, cached content served
- Watcher starts after failed validation
- Next file save triggers a full rebuild (recovers from failure)
- New test: mock validation failure, assert server thread alive + watcher started

---

### Phase 2: Asset Check for Serve-First (HIGH)

**Goal**: Reject serve-first when critical assets are missing.

**Change**: Extend `_has_cached_output()` to require at least one CSS asset:

```python
# In _has_cached_output(), after index check:
assets_css = output_dir / "assets" / "css"
if not assets_css.exists() or not any(assets_css.iterdir()):
    logger.debug("cached_output_rejected", reason="no_css_assets")
    return False
```

**Acceptance**:
- `rm -rf public/assets` → falls back to build-first
- `rm -rf public/assets/css` → falls back to build-first
- Existing cached output with assets → serve-first (no regression)

**Design decision**: Check for `assets/css/` directory with any content, not a specific
filename. This is theme-agnostic — works for default theme (`style.css`) and custom themes
with different CSS filenames. No config needed.

---

### Phase 3: BuildInput/BuildRequest Sync (LOW — Defensive)

**Goal**: Ensure `output_dir_override` propagates through all conversion paths.

**Changes**:

1. Add `output_dir_override: Path | None = None` to `BuildInput`
2. Propagate in `to_build_request()` and `from_build_request()`

**Acceptance**:
- Round-trip `BuildRequest` → `BuildInput` → `BuildRequest` preserves `output_dir_override`
- Unit test

**Priority**: Low. No current code path triggers the bug. Defensive future-proofing.

---

### Phase 4: Edits During Validation (LOW — Doc Only)

**Recommendation**: Document the behavior. The 5–15s window is small, and the user
just saves again. Option B (early watcher with queue) adds complexity for minimal gain.

---

### Phase 5: Reactive Path Buffer (DEFER)

**Recommendation**: Defer. Atomic writes are sufficient for single-file reactive updates.
Revisit only if torn-read reports surface.

---

### Phase 6: Concurrent Build Guard (DEFER)

**Recommendation**: Defer. `_build_lock` in `BuildTrigger` and watcher-after-validation
ordering prevent this today. Add a guard if the architecture ever allows overlapping builds.

---

## Implementation Order

| Phase | Priority | Effort | Risk if Skipped | Dependencies |
|-------|----------|--------|----------------|--------------|
| **0. Atomic writes in subprocess** | **Critical** | Tiny (3 lines) | Active buffer corruption | None |
| **1. Resilient validation** | **High** | Small | Server crash on validation failure | None |
| **2. Asset check** | **High** | Small | 404s on serve-first with missing assets | None |
| 3. BuildInput sync | Low | Small | Latent bug for future refactors | None |
| 4. Edits during validation | Low | Doc only | Minor UX gap (5–15s window) | None |
| 5. Reactive path buffer | Defer | Medium | Theoretical torn reads | None |
| 6. Concurrent build guard | Defer | Small | Theoretical concurrent builds | None |

Phases 0–2 should ship together as they address the root causes of dev server instability.
Phases 3–6 can land opportunistically.

---

## Success Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| 0 | Subprocess builds always use atomic writes | New test: hardlink integrity after subprocess build |
| 1 | Validation failure doesn't crash the server | New test: mock failure, assert server alive + watcher started |
| 2 | Serve-first never runs when CSS assets are missing | `rm -rf public/assets` → build-first |
| 3 | BuildInput/BuildRequest round-trip preserves `output_dir_override` | Unit test |
| 4 | All existing dev server tests pass | `poe test` |

---

## Architecture Notes

### Why the Subprocess Path Is the Odd One Out

Warm rebuilds run in-process via `site.build()` on the existing `Site` object, inheriting
all dev-mode config overrides. Subprocess builds (validation, initial) create a fresh
`Site.from_config()` from disk. This means every dev override must be explicitly forwarded
in `_execute_build()` — and currently only 2 of 6 are.

Long-term, consider one of:
- **A.** A `DevConfig` frozen dataclass passed through `BuildRequest` with all overrides
- **B.** A `bengal.toml` dev-server section that the config loader applies automatically
- **C.** Eliminating the subprocess path for validation (use in-process warm build instead)

Option C is attractive because warm builds already handle double-buffering correctly via
`BuildTrigger._execute_build()`, and the subprocess path exists primarily for crash
isolation during initial builds (less important for validation of cached content).

### Build Path Summary (Post-Fix)

```
┌─────────────────────┐
│     Dev Server      │
│                     │
│  ┌───────────────┐  │    Subprocess (BuildExecutor)
│  │ Build-First   │──────→ _execute_build()
│  │ (no buffer)   │  │    - Site.from_config() from disk
│  └───────────────┘  │    - Phase 0: now forces fast_writes=False
│                     │
│  ┌───────────────┐  │    Subprocess (BuildExecutor)
│  │ Serve-First   │──────→ _execute_build() with output_dir_override
│  │ Validation    │  │    - Writes to staging, then swap
│  │ (buffered)    │  │    - Phase 0: now forces fast_writes=False
│  └───────────────┘  │    - Phase 1: failure caught, keeps serving
│                     │
│  ┌───────────────┐  │    In-process (site.build())
│  │ Warm Rebuild  │──────→ BuildTrigger._execute_build()
│  │ (buffered)    │  │    - Uses existing Site with dev overrides
│  └───────────────┘  │    - Double-buffer: staging → swap → active
│                     │
│  ┌───────────────┐  │    In-process (single page)
│  │ Reactive Path │──────→ ReactiveContentHandler
│  │ (atomic write)│  │    - Writes directly to active buffer
│  └───────────────┘  │    - Atomic rename (fast_writes=False)
│                     │
└─────────────────────┘
```

---

## Open Questions

1. ~~Theme-agnostic asset check~~ **Resolved**: Check for `assets/css/` directory with any
   content. Theme-agnostic, no config needed.

2. **Subprocess config forwarding strategy**: Should we forward individual fields (status
   quo + Phase 0 fix), or introduce a `DevConfig` dataclass for all dev overrides?

3. **Validation build recovery**: After a caught validation failure (Phase 1), should the
   next watcher-triggered build be incremental or forced-full? Incremental may hit the same
   error; full build is slower but more likely to recover.

4. **Reactive path**: Is there any real-world report of torn reads with atomic writes?
   If not, Phase 5 remains unnecessary.

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-13 | 1.0 | Initial draft |
| 2026-03-13 | 2.0 | Deep code review: added Issues A/B/C (subprocess atomic writes, validation crash resilience, watcher start guarantee). Reprioritized phases. Added architecture notes and build path diagram. Resolved Open Question 1. |
