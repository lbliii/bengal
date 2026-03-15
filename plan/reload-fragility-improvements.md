# Reload/Rebuild Fragility Improvements — Consolidated Proposals

**Status**: Proposal (revised)  
**Date**: 2025-03-14  
**Revised**: 2026-03-14  
**Context**: Analysis of Bengal's most fragile reload/rebuild areas and proposed improvements.

---

## Executive Summary

Five areas of fragility were identified in the reload pipeline. This document consolidates proposals and recommends an implementation order grouped into two PRs.

| Area | Severity | Effort | Proposal Doc |
|------|----------|--------|--------------|
| Fragment extraction | High | Medium | See §1 |
| Content selector contract | Medium | Low | See §2 |
| Content hash baseline timing | Low (docstring fix) | Trivial | See §3 |
| Reactive path page lookup | Medium | Low | See §4 |
| Reload controller dual paths | Medium | Medium | `reload-controller-dual-path-proposal.md` |

---

## 1. Fragment Extraction (Most Brittle)

**Current**: Regex-based HTML parsing in `bengal/server/live_reload/fragment.py` (72 lines). Only supports `#id` selectors (regex at line 31). Silent failure → full reload with no logging anywhere in the function.

**Proposed**:
- **Option A (recommended)**: Add `beautifulsoup4` as a **dev-server-only dependency** (optional extra, e.g. `bengal[dev]`); use `soup.select_one(selector)` with `html.parser` backend. Add `logger.debug()` when extraction returns `""`. This only runs during `bengal serve`, so production builds carry no extra dependency.
- **Option B (no new deps)**: Harden regex: add logging on failure, basic `.class` support, comment-aware preprocessing, edge-case tests.

**Migration**: Add BeautifulSoup-based impl with regex fallback when `bs4` is not installed; extend `dev.content_selector` docs for `#id`, `.class`, `tag.class`.

**Test scenarios** (required for either option):
- Nested same-tag elements (`<div id="main-content"><div>inner</div></div>`)
- Self-closing tags within the target element
- HTML comments containing the selector ID
- Malformed/unclosed tags
- Missing selector (no matching element)
- `.class` and `tag.class` selectors (once supported)

**Files**: `bengal/server/live_reload/fragment.py`, `pyproject.toml`, `tests/unit/server/`.

---

## 2. Content Selector Contract (#main-content)

**Current**: No validation. The selector defaults to `#main-content` (`build_trigger.py:338`). When `extract_main_content` returns `""`, the reactive path silently falls through to `_handle_reload` for a full page reload (`build_trigger.py:358-364`) with no warning logged.

**Proposed** (priority order):
1. **Dev-mode warning** when fragment extraction returns empty (in reactive path) — `build_trigger.py`, one-time `logger.warning("fragment_extraction_empty", selector=..., path=...)`.
2. **Document contract** in extension guide / dev server docs: themes must include an element matching `dev.content_selector` for instant reload to work.
3. **Add `content_selector` to config defaults** — trivial.
4. **Class selector support** in `extract_main_content` (if not using BeautifulSoup).
5. **Fallback chain**: try `#main-content` → `.main-content` → `<main>` before giving up.

**Files**: `bengal/server/build_trigger.py`, `site/content/docs/`, `bengal/config/defaults.py`.

---

## 3. Content Hash Baseline Timing

**Finding**: The docstring at `reload_controller.py:339` warns "Build writes may overlap with this scan if called during build." This describes hypothetical misuse. The actual call site (`build_trigger.py:292-293`) is strictly sequential: `capture_content_hash_baseline` → `site.build()` → `decide_with_content_hashes`. No overlap exists.

**Proposed**:
- **Minimal**: Update docstring to replace the race warning with a precondition: "Callers MUST invoke before build starts, never during build. Current call site in BuildTrigger guarantees this."
- **Stronger (optional)**: Capture baseline from previous build output (path→hash from build) instead of pre-scan — eliminates the scan entirely and prevents any future race risk; requires build pipeline changes.

**Files**: `bengal/server/reload_controller.py` (docstring), optionally build pipeline.

---

## 4. Reactive Path Page Lookup

**Current**: `_find_page` in `handler.py:117-134` uses `Path.resolve()` for both index building (from `page.source_path`) and lookup (from watcher path). Discovery vs watcher can disagree when symlinks, casing, or relative-vs-absolute paths are involved.

**Proposed**: Use `content_key(path, site_root)` from `bengal/build/contracts/keys.py` for both index and lookup — matches BuildCache normalization. `content_key` internally calls `_relative_key`, which resolves and computes a POSIX-relative `CacheKey` string.

```python
# Key change in ReactiveContentHandler._find_page
from bengal.build.contracts.keys import content_key, CacheKey

self._page_index: dict[CacheKey, PageLike] = {}
for page in self.site.pages:
    key = content_key(Path(page.source_path), self.site.root_path)
    self._page_index[key] = page

# Lookup
key = content_key(path, self.site.root_path)
return self._page_index.get(key)
```

**Regression risk**: If `page.source_path` is stored in a form that `content_key` normalizes differently than the watcher-provided `path`, lookups will miss. Mitigation: add a `logger.debug("reactive_page_not_found")` (already present at line 70) and a fallback to `Path.resolve()` lookup on miss during a one-release transition period.

**Files**: `bengal/server/reactive/handler.py`.

---

## 5. Reload Controller Dual Paths

**Current**: Three decision entry points exist — `decide_from_outputs` (typed), `decide_with_content_hashes`, `decide_and_update` (snapshot). The module docstring at `reload_controller.py:49` says "build_trigger.py: Calls decide_and_update after builds" — this is **outdated**; `BuildTrigger._handle_reload` actually uses `decide_from_outputs` (line 1308) or `decide_from_changed_paths` (line 1320). `decide_and_update` is only called from DevServer validation when `use_content_hashes=False`.

**Proposed** (see `plan/reload-controller-dual-path-proposal.md`):
1. Add `decide_reload()` orchestrator with explicit fallback chain: typed outputs → content hashes → changed paths → snapshot.
2. Add fallback logging at each step (which path was used and why).
3. Startup validation when `content_hash_in_html=False` with content-hash mode.
4. Fix outdated docstrings (module docstring line 49, `capture_content_hash_baseline` race warning at line 339).

**Files**: `bengal/server/reload_controller.py`, `bengal/server/build_trigger.py`, `bengal/server/dev_server.py`.

---

## Recommended Implementation Order

Group into two PRs to keep reviews manageable and risk contained.

### PR 1: Low-effort observability + correctness (Phases 1–5)

All changes are orthogonal, low-risk, and independently valuable.

| Phase | Change | Effort | Impact |
|-------|--------|--------|--------|
| 1 | Dev-mode warning when fragment empty (§2.1) | Low | Immediate visibility |
| 2 | Fragment extraction: add logging on failure (§1) | Low | Debuggability |
| 3 | Reactive path: use `content_key` with resolve fallback (§4) | Low | Fix path mismatches |
| 4 | Content hash docstring fix (§3) | Trivial | Clarity |
| 5 | Document content selector contract (§2.2) | Low | Theme author guidance |

### PR 2+: Structural improvements (Phases 6–8, individual PRs)

Each carries more structural risk and should be reviewed separately.

| Phase | Change | Effort | Impact |
|-------|--------|--------|--------|
| 6 | Fragment extraction: BeautifulSoup or hardened regex (§1) | Medium | Robustness |
| 7 | Reload controller: `decide_reload()` + fallback chain (§5) | Medium | Consolidation |
| 8 | Content selector: class support + fallback chain (§2.4–2.5) | Medium | Theme flexibility |

---

## Related Documents

- `plan/reload-tier-architecture.md` — Reload tier flow
- `plan/reload-controller-dual-path-proposal.md` — Full dual-path analysis and flow diagram
