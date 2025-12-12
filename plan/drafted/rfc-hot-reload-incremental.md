# RFC: Fast & Correct Hot Reload for Markdown Changes

- **Status:** Draft
- **Owner:** AI (pairing with llane)
- **Date:** 2025-12-11
- **Scope:** Dev server hot reload, incremental build, caching
- **Motivation:** Restore fast iteration while ensuring Markdown edits (body + frontmatter) always surface in the browser without manual refresh or full rebuilds.

## Problem
- Recent regression: Markdown edits built but did not appear even after manual refresh; hot reload events were sent but output stayed stale.
- Temporary mitigation: force full rebuild on `.md/.markdown` edits (`bengal/server/build_handler.py`), which fixes correctness but slows dev loops.
- Underlying risks:
  - Change classification for Markdown is coarse; frontmatter/navigation changes aren’t distinguished from body-only edits.
  - Cache reuse can serve stale HTML when detection is too permissive.
  - Reload notifications rely on source-gated decisions and may not reflect missed content rebuilds.

## Current State (Evidence)
- **Build handler**: Watches filesystem, debounced rebuild, source-gated reload decision; currently forces full rebuild for content edits (temporary). `bengal/server/build_handler.py`.
- **Incremental change detection**: Uses `BuildCache.is_changed` on content/templates/assets to choose pages/assets to rebuild; hashes recorded in `save_cache()` post-build. `bengal/orchestration/incremental.py`.
- **Caches**: Parsed/rendered cache consulted per page; skip_cache flag now uses `cache.is_changed(page.source_path)` to avoid stale hits, but only when the change set is accurate. `bengal/rendering/pipeline/core.py`.
- **Dependency tracking**: `DependencyTracker.start_page` no longer updates file hashes to avoid masking changes; dependencies are recorded, and hashes are updated at `save_cache()`. `bengal/cache/dependency_tracker.py`, `bengal/cache/build_cache/file_tracking.py`.
- **Reload delivery**: SSE endpoint `/__bengal_reload__`; controller decides `reload` vs `reload-css` vs none based on outputs. `bengal/server/live_reload.py`, `bengal/server/reload_controller.py`.

## Goals
- Keep hot reload near-instant for body-only Markdown edits.
- Preserve correctness for frontmatter/navigation-sensitive changes and structural events (create/move/delete).
- Avoid serving stale cached HTML/parsed content.
- Maintain existing reload ergonomics (CSS-only vs full reload) with better observability.

## Non-Goals
- No change to production build behavior.
- No redesign of the SSE channel; only correctness/observability.
- No taxonomy or autodoc redesign (only ensure they stay consistent).

## Options
### Option A (Recommended): Frontmatter-aware selective rebuild + targeted cache skip
- Parse changed Markdown frontmatter (first YAML block only) to classify:
  - **Body-only edits:** incremental, page-scoped; skip caches for those pages/templates.
  - **Nav-affecting edits:** section-scoped rebuild; include keys impacting URL/nav/cascade: `title`, `slug`, `permalink`, `aliases`, `hidden`, `draft`, `visibility`, `menu`/`weight`, `cascade`, `redirect`, i18n keys (`lang`, `language`, `translationKey`), and `_section` overrides.
  - **Create/Delete/Move:** full rebuild (already).
  - **SVG theme icons:** full rebuild (already).
- Feed the classified change set through build→incremental→rendering so caches are bypassed only for the affected pages/templates (see plan below).
- Keep reload source-gated; emit structured reload event after any non-skipped build.

### Option B: Output-diff only
- Rely solely on `reload_controller` output diffs to decide reload and cache invalidation.
- Risk: Misses nav/cascade semantics; still needs content re-render decisions upstream.

### Option C: Always full rebuild on content
- Current stopgap; correct but slow.

## Proposed Plan (Option A)
1) **Frontmatter classifier in build handler**  
   - On `.md/.markdown` change, parse YAML frontmatter once to detect nav-impacting keys (allowlist above).  
   - Tag change as `body-only`, `nav`, or `structural` and pass a structured payload to the build orchestrator.
2) **Scope-aware rebuild selection** (`BuildOrchestrator` → `IncrementalOrchestrator`)  
   - Extend build orchestration to accept classifier output alongside filesystem events.  
   - If `nav` flagged: rebuild the section of the changed page plus cascade descendants; ensure prev/next/nav metadata recomputes.  
   - If `body-only`: rebuild only the page; keep existing cascade + prev/next propagation.  
   - Preserve create/delete/move → full rebuild; preserve autodoc full rebuild fallback.
3) **Cache bypass keyed to change set** (`RenderOrchestrator` → `RenderingPipeline`)  
   - Thread classifier `changed_sources` through render entrypoints; for those sources, force skip of parsed/rendered caches even if `cache.is_changed` returns False (covers revert-to-same-content).  
   - Keep current cache reuse for untouched pages; assert/log when classifier-tagged sources are reported unchanged by cache.
4) **Fingerprint/update ordering guard** (`BuildCache`)  
   - Ensure file hashes update only after successful render (`save_cache`), never before cache checks.  
   - Add a quick assert/log if `is_changed` returns False for a path tagged as changed in the current build to catch classification/cache disagreement early.
5) **Reload observability** (`BuildHandler` + `reload_controller`)  
   - Log and, when reasonable, include a redacted summary of classified sources in `send_reload_payload` logging (`action`, `reason`, counts by type).  
   - Preserve CSS-only optimization; ensure a reload payload is emitted for any non-skipped build.
6) **Tests**  
   - Unit: frontmatter classifier (body vs nav keys; revert-to-same-content still tags as changed).  
   - Integration:  
     - Body-only change → incremental page rebuild; HTML changes; reload event emitted.  
     - Nav/frontmatter change on section index → descendant pages rebuilt (cascade + prev/next).  
     - Create/Delete/Move → full rebuild; cached outputs cleared.  
     - CSS-only → `reload-css` path unchanged.  
     - Classifier/cache disagreement surfaces via assertion/log, not silent skip.

## Risks / Mitigations
- **Parsing overhead:** Keep frontmatter parse lightweight (first YAML block only).  
- **False negatives on nav keys:** Maintain explicit allowlist; add config hook if needed.  
- **Cache inconsistency:** Guardrails/logs when `changed_sources` disagrees with `is_changed`; skip caches when classifier says changed.  
- **Reload noise:** Keep CSS-only optimization; throttle unchanged outputs via existing controller.

## Migration / Rollout
- Stage behind a dev flag (e.g., `dev.watch.frontmatter_classification=true`) default-on after soak.  
- Keep current full-rebuild fallback during rollout; log classification decisions.  
- Remove forced full rebuild for content after confidence is high.

## Open Questions
- Do we need per-key nav dependency tracking for custom sidebar generators?  
- Should taxonomy/tag changes also trigger section-scoped rebuilds beyond current cascade logic?  
- Do we need a “max pages per incremental cycle” guard to avoid pathological section rebuilds?

## Success Metrics
- Hot reload latency for body-only Markdown edits ≈ current incremental baseline.  
- Zero observed stale renders after edits (manual refresh not required).  
- Reload payload emitted for every successful build that changes content/templates.  
- No increase in spurious full rebuilds for Markdown-only changes.
