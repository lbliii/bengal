# RFC: Output Directory Isolation (Double-Buffer Dev Builds)

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-03-03 |
| **Author** | Bengal Core Team |
| **Priority** | P1 (High — recurring user-facing bug) |
| **Related** | `bengal/server/build_trigger.py`, `bengal/server/asgi_app.py`, `bengal/core/site/lifecycle.py`, `bengal/rendering/renderer.py:462-505` |
| **Confidence** | 92% |

---

## Executive Summary

During rapid content updates in the dev server, pages intermittently lose their
layouts and CSS, falling back to the emergency template
(`renderer.py:_render_fallback`). This has been observed multiple times over
several months. The root cause is that **builds write to the output directory
in-place while the ASGI app simultaneously serves from the same directory**.
There is no isolation between the write side (build) and the read side (server).

This RFC proposes **output directory double-buffering**: builds write to a
staging directory, then a single atomic rename swaps it into the serving path.
The server always reads from a complete, consistent output tree. This
eliminates the entire category of "partial output during rebuild" bugs
structurally, rather than with timing heuristics.

---

## Problem Analysis

### Observed Symptom

When editing content rapidly, the browser shows pages with:
- Emergency fallback styling (yellow warning banner, no nav/sidebar)
- Missing CSS (unstyled raw HTML)
- Broken layout (no theme, just content in `<article>`)

### Root Cause Chain

#### 1. In-place output writes

The build writes HTML, CSS, and assets directly to `output_dir` (`public/`).
The ASGI app (`asgi_app.py:237-299`) reads from the same directory:

```python
# asgi_app.py:279
content = await asyncio.to_thread(resolved.read_bytes)
```

#### 2. Build pipeline is multi-phase

The `BuildOrchestrator` runs phases sequentially:
1. Fonts → 2. Discovery → 3. Rendering (writes HTML) → 4. Assets (copies CSS/JS) → 5. Static files → 6. Postprocessing

HTML pages are written during phase 3, but theme CSS is copied during phase 4.
Between these phases, the output directory has new HTML referencing CSS that may
not exist yet (if this is a full rebuild that cleans and re-copies assets).

#### 3. Browser reload races with build completion

The `BuildTrigger` sends the live reload signal after the build finishes
(`build_trigger.py:502-508`). However:

- **Build A** completes → sends reload → browser starts fetching resources
- **Build B** starts immediately (queued changes, 100ms delay) →
  `prepare_for_rebuild()` clears site state → rendering begins
- Browser requests from Build A's reload may hit Build B's partially-written
  output

The existing 100ms stabilization delay (`build_trigger.py:237-240`) is a
timing heuristic that doesn't guarantee consistency:

```python
# 100ms is enough for most browser requests to complete while
# keeping the feedback loop fast.
time.sleep(0.1)
```

#### 4. Template render failures cascade to fallback

When rendering fails for any reason — missing context, stale template
cache, UndefinedError on an empty `site.menu` — the renderer catches the
exception and writes fallback HTML to disk (`renderer.py:464-505`):

```python
except Exception as e:
    # ...
    return self._render_fallback(page, content)
```

This fallback HTML persists in the output directory and is served until the
next successful build overwrites it.

#### 5. Incremental cleanup deletes before new output exists

The `_cleanup_deleted_files()` phase removes output files whose source no
longer exists. During URL changes or structural edits, old output files are
deleted before new ones are written, creating a window of missing content.

### Timeline of a Typical Failure

```
t=0ms    User saves file #1
t=300ms  Build A starts: prepare_for_rebuild() → discovery → render → write HTML
t=800ms  Build A: writing HTML pages to public/
t=900ms  User saves file #2 (queued — Build A in progress)
t=1100ms Build A: copying CSS/assets to public/assets/
t=1200ms Build A complete → send "reload" to browser
t=1300ms Build B starts (100ms delay): prepare_for_rebuild() → clears state
t=1350ms Browser processes reload → fetches /index.html (Build A output ✅)
t=1400ms Browser fetches /assets/css/style.css (Build B is rewriting ❌)
t=1500ms Build B: render fails on some pages (stale template state)
t=1600ms Build B: writes fallback HTML for failed pages
t=1800ms Build B complete → send "reload"
t=1850ms Browser reloads → sees fallback HTML pages with broken CSS
```

### Why Prior Fixes Haven't Worked

| Fix | Why insufficient |
|-----|-----------------|
| 100ms stabilization delay | Timing heuristic; doesn't guarantee all browser fetches complete |
| `serve_asset_with_cache` during build | Only caches 30 CSS/JS files; doesn't help HTML |
| `build_in_progress` flag + badge | Cosmetic — still serves partial output |
| Reactive content path | Only for single-file body-only edits; bypassed for structural changes |

---

## Design Options

### Option A: Double-Buffer with Atomic Swap (Recommended)

**Mechanism**: Builds write to `public/.staging/`, then `os.rename()` swaps
staging into the live path.

```
public/          ← server reads from here (always complete)
public/.staging/ ← build writes here (invisible to server)
```

**Swap strategy**: After build completes successfully:
1. `os.rename("public", "public/.old")`
2. `os.rename("public/.staging", "public")`
3. `shutil.rmtree("public/.old")` (background)

On macOS/Linux, `os.rename` of directories on the same filesystem is atomic
at the kernel level. Since `.staging` is a subdirectory of the same parent,
this is guaranteed to be same-filesystem.

**Pros**:
- Eliminates the entire bug class structurally
- Simple mental model (server always sees consistent state)
- Well-understood pattern (blue/green deployment, database WAL)
- Compatible with existing incremental build logic (staging dir is built from
  scratch or incrementally; swap is the only change)

**Cons**:
- Full rebuilds write all files to staging (can't incrementally update live dir)
- Extra disk I/O for the copy (mitigated: SSD, ~50ms for typical sites)
- Need to handle `.staging` cleanup on crash

**Implementation sketch**:

```python
# bengal/server/output_swap.py
import os
import shutil
from pathlib import Path

def atomic_swap(staging: Path, live: Path) -> None:
    """Swap staging directory into the live serving path."""
    old = live.parent / f".{live.name}.old"
    if old.exists():
        shutil.rmtree(old)
    os.rename(live, old)
    os.rename(staging, live)
    shutil.rmtree(old, ignore_errors=True)
```

### Option B: Overlay Filesystem (Copy-on-Write)

**Mechanism**: The server reads from a layered view: staging overlay on top of
base. During build, writes go to staging. After build, staging is merged into
base.

**Pros**: Incremental — only changed files are in staging
**Cons**: Complex; needs custom ASGI middleware to resolve layered paths;
hard to reason about correctness; no real OS support on macOS.

### Option C: Hold Reload Until Build Complete + Asset Lock

**Mechanism**: Don't send live reload until the entire build (including
asset copy) is verified complete. Add a read-write lock so the ASGI app
blocks on reads during the final write phase.

**Pros**: No extra disk I/O
**Cons**: Blocks all requests during writes; increases perceived latency;
timing-dependent (browser may still have in-flight requests from previous
reload).

### Option D: Immutable Output with Content-Addressed Paths

**Mechanism**: Every output file gets a content hash in its filename. Old
files are never deleted during build, only new files are added. HTML pages
reference the hashed paths.

**Pros**: Completely eliminates stale reads; great for CDN caching
**Cons**: Massive change to the entire output pipeline; breaks dev server URL
stability; overkill for dev mode.

---

## Recommended Approach: Option A (Double-Buffer)

Option A is the right trade-off: it's simple, well-understood, and eliminates
the bug class entirely. The extra disk I/O is negligible for dev-sized sites.

### Detailed Design

#### 1. Staging Directory Management

```python
# New module: bengal/server/output_swap.py

@dataclass(frozen=True, slots=True)
class OutputSwapConfig:
    live_dir: Path
    staging_dir: Path       # live_dir / ".staging"
    old_dir: Path           # live_dir.parent / ".public.old"

def prepare_staging(config: OutputSwapConfig) -> Path:
    """Create clean staging directory for build."""
    if config.staging_dir.exists():
        shutil.rmtree(config.staging_dir)
    config.staging_dir.mkdir(parents=True)
    return config.staging_dir

def commit_staging(config: OutputSwapConfig) -> None:
    """Atomic swap: staging → live."""
    # Clean up any prior failed swap
    if config.old_dir.exists():
        shutil.rmtree(config.old_dir)

    os.rename(config.live_dir, config.old_dir)
    os.rename(config.staging_dir, config.live_dir)

    # Background cleanup (non-blocking)
    threading.Thread(
        target=shutil.rmtree,
        args=(config.old_dir,),
        kwargs={"ignore_errors": True},
        daemon=True,
    ).start()

def rollback_staging(config: OutputSwapConfig) -> None:
    """Clean up staging on build failure (keep live dir intact)."""
    if config.staging_dir.exists():
        shutil.rmtree(config.staging_dir, ignore_errors=True)
```

#### 2. BuildTrigger Integration

In `_execute_build()`:

```python
# Before build
swap_config = OutputSwapConfig(
    live_dir=self.site.output_dir,
    staging_dir=self.site.output_dir / ".staging",
    old_dir=self.site.output_dir.parent / ".public.old",
)
staging = prepare_staging(swap_config)

# Redirect build output to staging
original_output_dir = self.site.output_dir
self.site.output_dir = staging

try:
    stats = self.site.build(options=build_opts)
    # Build succeeded — swap into live
    self.site.output_dir = original_output_dir
    commit_staging(swap_config)
except Exception:
    # Build failed — discard staging, keep live intact
    self.site.output_dir = original_output_dir
    rollback_staging(swap_config)
    raise
```

#### 3. First-Build Bootstrapping

The initial `bengal serve` build writes directly to `output_dir` (no staging
needed since there's no server yet). Double-buffering activates for subsequent
warm rebuilds only.

#### 4. Incremental Build Optimization

For content-only edits where only a few HTML files change, full staging is
wasteful. Optimization: **hard-link unchanged files** from the live directory
into staging, then only write changed files:

```python
def prepare_staging_incremental(
    config: OutputSwapConfig,
    changed_outputs: set[Path],
) -> Path:
    """Create staging with hard-links for unchanged files."""
    # Hard-link everything from live → staging
    for src in config.live_dir.rglob("*"):
        if src.is_file() and not src.name.startswith("."):
            dest = config.staging_dir / src.relative_to(config.live_dir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.link(src, dest)

    # Changed files will be overwritten by the build
    return config.staging_dir
```

Hard links are O(1) and share disk blocks, so this is fast and space-efficient.
The build overwrites the hard-linked files in staging without affecting the
live copies (copy-on-write semantics at the filesystem level).

#### 5. Watcher Ignore Rules

The file watcher must ignore `.staging` and `.public.old`:

```python
# bengal/server/file_watcher.py
IGNORE_DIRS.add(".staging")
IGNORE_DIRS.add(".public.old")
```

#### 6. Crash Recovery

On dev server startup, clean up leftover swap artifacts:

```python
def cleanup_swap_artifacts(output_dir: Path) -> None:
    staging = output_dir / ".staging"
    old = output_dir.parent / ".public.old"
    for d in (staging, old):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
```

### Reactive Path Compatibility

The reactive content path (`ReactiveContentHandler`) writes a single HTML file
directly to the output directory. Since this is a single file atomic write
(write to temp + rename), it's already safe and doesn't need double-buffering.
No changes needed.

---

## Migration Plan

### Phase 1: Core Swap Mechanism (This PR)

1. Add `bengal/server/output_swap.py` with prepare/commit/rollback
2. Integrate into `BuildTrigger._execute_build()` for warm builds only
3. Add watcher ignore rules for `.staging` and `.public.old`
4. Add crash recovery cleanup to `DevServer.start()`
5. Tests: unit tests for swap/rollback, integration test for dev server rebuild

### Phase 2: Incremental Hard-Link Optimization

1. Use hard-links for unchanged files (reduces I/O for incremental builds)
2. Benchmark: measure overhead for typical site sizes (100-1000 pages)

### Phase 3: Remove Timing Heuristics

Once double-buffering is proven stable:
1. Remove the 100ms stabilization delay (`build_trigger.py:237-240`)
2. Remove `serve_asset_with_cache` during-build path (no longer needed)
3. Simplify `build_in_progress` flag usage (badge only, no cache logic)

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| `os.rename` fails across filesystems | `.staging` is a subdirectory of `output_dir` — guaranteed same FS |
| Crash leaves `.staging` orphaned | Startup cleanup + `.gitignore` entry |
| Hard-link not supported (rare FS) | Fall back to full copy; detect with try/except on first link |
| Disk space for staging copy | Typical dev site is <100MB; hard-links share blocks |
| File watcher triggers on staging writes | Watcher ignore rules for `.staging` |
| Windows compatibility | `os.rename` on directories is not atomic on Windows; use `os.replace` or fall back to copy+delete. Windows dev is not a priority for Bengal. |

---

## Success Criteria

1. **Zero emergency fallback pages** during rapid content edits (stress test: 20 saves in 10 seconds)
2. **No CSS/layout drops** visible in browser during dev server operation
3. **Build overhead** < 50ms additional latency for swap operation
4. **No behavioral change** for production builds (`bengal build`)

---

## Evidence

| File | Lines | What |
|------|-------|------|
| `bengal/server/build_trigger.py` | 237-240 | 100ms stabilization delay (existing band-aid) |
| `bengal/server/build_trigger.py` | 373-403 | Warm build: prepare_for_rebuild → build (in-place writes) |
| `bengal/server/asgi_app.py` | 237-299 | ASGI app reads from output_dir during build |
| `bengal/server/live_reload/mixin.py` | 217-289 | Asset cache during build (insufficient mitigation) |
| `bengal/rendering/renderer.py` | 462-505 | Template error → `_render_fallback()` → emergency HTML |
| `bengal/rendering/renderer.py` | 872-938 | Emergency fallback HTML (what users see) |
| `bengal/core/site/lifecycle.py` | 84-148 | `prepare_for_rebuild()` clears all site state |
| `bengal/server/build_state.py` | 12-47 | `build_in_progress` flag (insufficient protection) |
