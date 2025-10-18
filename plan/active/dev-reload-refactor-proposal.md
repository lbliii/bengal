Title: Dev Server Live Reload – Robust Architecture Proposal

Context
- The dev server sometimes hard-reloads without visible changes and sometimes fails to reflect edits without a hard reload. Recent mitigations improved cache headers, debounce, watcher ignores, and suppressing reload when build is skipped, but a cohesive architecture will make behavior predictable and fast.

Goals
- Deterministic reloads only when outputs change.
- Prefer CSS hot swap when possible; avoid full-page reload.
- Eliminate spurious triggers from irrelevant files and temp artifacts.
- Provide clear diagnostics (why a reload happened, what changed).
- Keep implementation simple, testable, and maintainable.

Non-Goals
- Full-fledged hot module replacement for JS; we only need CSS swap + page reload.

Current Pain Points (observed)
- Watcher triggers on transient files/dirs; debounce too low amplifies noise.
- Browser caches sometimes hold onto HTML/CSS; hard reload needed.
- Reloads can be sent even when the build was effectively a no-op (skipped).
- Live-reload script injection done at serve time complicates handler.

Proposed Architecture
1) OutputDiff ReloadController
   - After each build, compute OutputDiff against previous build outputs under `public/`.
   - Mechanism: Maintain a memory map of file path -> (mtime, size, optional hash). On build complete, scan `public/` and diff against previous snapshot.
   - Decision logic:
     - If no diffs: do nothing (suppress reload).
     - If only `.css` diffs: notify `reload-css` with the exact set of hrefs.
     - Else: notify `reload` (full reload).
   - Expose reason and top changed paths for diagnostics.

2) Centralized ReloadController API
   - Module `bengal/server/reload_controller.py` with a stateful controller:
     - `record_build_outputs(snapshot)`
     - `get_reload_action(prev, curr) -> (action, reasons, changed_paths)`
     - `notify_clients(action, reasons, changed_paths)` delegates to SSE.
   - Includes coalescing/throttling: suppress duplicate notifications within N ms unless the action severity increases (e.g., CSS -> full).

3) Strong Watcher Policy
   - Replace ad-hoc ignore with explicit directory exclusions and pattern filters using path segments: `.git`, `node_modules`, virtualenvs, `__pycache__`, IDE caches, `.cache`, `dist`, `build`, etc.
   - Treat atomic save patterns (temp -> rename) as a single change via debounce + grouping by basename.

4) Dev Response Policy
   - Central small utility to apply dev cache headers consistently for HTML/CSS/JS: `no-store, no-cache, must-revalidate, max-age=0` + `Pragma`.
   - Toggle based on `site.config.dev_server`.

5) Template-based Live Reload Include
   - Replace dynamic HTML mutation with a dev-only include in `base.html` guarded by `site.config.dev_server`.
   - Benefits: simpler handler, fewer moving parts, no need for injection cache.

6) BuildStats Enrichment
   - Add fields: `outputs_written_count`, `outputs_changed_paths[:N]`, possibly grouped by type (pages/assets).
   - Consumer: ReloadController logs, tests, and CLI summary.

7) Targeted CSS HMR
   - Include exact changed CSS URLs in SSE payload (relative to site root).
   - Client replaces only those `<link rel="stylesheet">` with new `?v=timestamp` query.

8) Observability
   - SSE payload includes: `{action, reason, changed_paths[:5], generation}`.
   - Dev console logs a concise message.
   - Optional tiny overlay showing the last reload reason and count (toggle via config).

Phased Plan
Phase 1 (Low risk, immediate value)
- Implement OutputDiff scanner and ReloadController (action computation + throttling).
- Wire into `BuildHandler` post-build path; skip SSE if no diffs.
- Send reasons + changed paths to SSE (server + client).

Phase 2 (Stability + Simplification)
- Centralize dev response headers utility; apply in handler and live reload endpoints.
- Strengthen watcher ignores using segment-based rules (already partially done).
- Increase debounce tunables via env/config (e.g., `BENGAL_DEBOUNCE_MS`).

Phase 3 (UX polish)
- Switch from runtime injection to dev-only template include.
- Targeted CSS HMR: send exact CSS URLs and update only those links.
- Enrich BuildStats with outputs written/changed for logs/tests.

Test Plan
- Unit: OutputDiff logic (new/modified/deleted handling), Controller throttling, CSS-only decisions, SSE payload formatting.
- Integration: Save CSS only -> CSS HMR; Save HTML/template -> full page reload; No-op save -> no reload.
- Regression: Watcher ignores across `.git`, venvs, `node_modules`; debounce coalescing under rapid saves.

Risks & Mitigations
- Scanning `public/` post-build: O(n) with n output files; constrain to mtime/size by default; opt-in hashing for correctness if needed.
- Throttling edge cases: ensure escalation (CSS -> full) always passes; log suppressed events in debug.
- Template include: consumers with custom themes must include the dev snippet in their `base.html`; provide clear docs and fallback injection for legacy.

Acceptance Criteria
- No reload when no outputs changed.
- CSS-only edits swap styles in <500ms without page navigation.
- Full reload when HTML/JS/other assets change.
- Clear console message with reason and top changed paths.

Timeline
- Phase 1: 1–2 days.
- Phase 2: 0.5–1 day.
- Phase 3: 1–2 days (depending on tests and docs).

Deliverables
- `bengal/server/reload_controller.py` + tests
- Updated `BuildHandler` integration
- Dev response policy helper
- Optional dev overlay + docs

Notes
- The recent fixes (no-store headers, watcher ignores, debounce, skip on skipped builds) reduced symptoms already; this proposal hardens correctness and observability long-term.


