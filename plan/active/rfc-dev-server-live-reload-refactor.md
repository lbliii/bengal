---
title: RFC — Robust Dev Live Reload (Eliminate Spurious Reloads)
status: Draft
owners: llane
created: 2025-10-27
subsystems: server (dev), orchestration
---

## Summary

Fix spurious page reloads in the dev server by tightening the output-change detection and improving reload classification, without a full redesign. We will:

- Prefer builder-provided lists of written/updated outputs when available
- Add content-aware diffing (conditional hashing when mtime changes but size is equal)
- Support ignore globs for known benign-churn outputs during dev
- Slightly raise notification throttling and keep detailed diagnostics
- Remove dead/duplicate HTML injection paths

This preserves the current, modular architecture (watch → build → output-diff → decision → SSE) and makes reloads reflect real content changes rather than filesystem noise.

## Problem Statement

During development, small saves or internal processes can cause output files to be rewritten with unchanged content but new mtimes. The current reload decision treats mtime changes as content changes, causing unnecessary full-page reloads and degraded DX.

## Current State (with evidence)

- Decision is based on mtime/size snapshot diffs of the output directory:

```78:84:bengal/server/reload_controller.py
        for path, entry in curr_files.items():
            pentry = prev_files.get(path)
            if pentry is None or pentry.size != entry.size or pentry.mtime != entry.mtime:
                changed.append(path)
                if path.lower().endswith(".css"):
                    css_changed.append(path)
```

- Controller was built with future hashing in mind but not implemented yet:

```10:12:bengal/server/reload_controller.py
Uses file size and modification time for fast diffing. This is sufficient
for dev; a hashing option can be added later if needed.
```

- Build pipeline triggers reload decisions after each rebuild and sends SSE payloads:

```271:283:bengal/server/build_handler.py
                    decision = controller.decide_and_update(self.site.output_dir)

                    if decision.action == "none":
                        logger.info("reload_suppressed", reason=decision.reason)
                    else:
                        from bengal.server.live_reload import send_reload_payload
                        send_reload_payload(
                            decision.action, decision.reason, decision.changed_paths
                        )
```

- Client supports CSS-only hot reload when the server classifies it as such:

```78:101:bengal/server/live_reload.py
                    if (changedPaths.length > 0) {
                        const path = url.pathname.replace(/^\//, '');
                        if (!changedPaths.includes(path)) return;
                    }
                    // Bust cache with a version param
                    const newLink = link.cloneNode();
                    newLink.href = url.toString();
                    newLink.onload = () => { link.remove(); };
                    link.parentNode.insertBefore(newLink, link.nextSibling);
```

- Dev server reduces asset churn (no fingerprinting, minify off, baseurl cleared) but benign rewrites still occur:

```221:249:bengal/server/dev_server.py
        cfg["dev_server"] = True
        cfg["fingerprint_assets"] = False
        cfg.setdefault("minify_assets", False)
        ...
        clear_build_cache(self.site.root_path, logger)
        clear_output_directory(self.site.output_dir, logger)
```

## Goals

- Eliminate spurious reloads caused by mtime-only changes when content is identical
- Correctly classify CSS-only changes for fast, non-destructive hot reload
- Allow users to ignore known noisy outputs during dev
- Keep performance predictable for large sites
- Avoid a full architectural rewrite

## Non-Goals

- Implementing a full content hashing database of the entire output on every build
- Hot-module replacement for JS beyond current CSS reload capability

## Design Options

1) Conditional content hashing on suspect changes

- On diff, when mtime changed but size is equal, compute a fast hash of the file (e.g., xxh3 via `xxhash` if present, fall back to `hashlib.md5`). If hash is unchanged vs a small in-memory cache keyed by path+size, ignore the change.
- Hash only on-demand for suspect files; cap the number per cycle (e.g., 200) and short-circuit for big files (size threshold).

Pros: Targets the noisy case precisely, keeps costs bounded. Cons: Some overhead; needs small cache.

2) Prefer builder-provided changed outputs (when available)

- If `Site.build()` exposes a list of written/updated output paths (e.g., `stats.changed_outputs`), pass that to the controller and base the decision on that list rather than scanning mtimes.
- Fall back to snapshot diff when hints are missing.

Pros: Semantically correct and cheap. Cons: Requires plumbing from builder → server.

3) Configurable ignore globs for dev

- Introduce `dev.reload.ignore_paths: ["public/index.json", "public/search/**", ...]` (globs relative to output dir). Filter these paths before making a decision.

Pros: Immediate relief for known noisy artifacts. Cons: Relies on users knowing what to ignore.

4) Throttling and diagnostics

- Increase `min_notify_interval_ms` (e.g., 150 → 300–500) to coalesce short bursts.
- Keep printing the first few changed files and additionally log when a suspect change was ignored due to hash-equal content.

Pros: Better UX and debuggability. Cons: Slightly delays reloads in bursty edits.

5) Cleanup duplication

- Remove `_inject_live_reload` in `BengalRequestHandler` and rely solely on `LiveReloadMixin.serve_html_with_live_reload()` which already handles caching and injection.

Pros: Less surface area, fewer edge cases. Cons: None.

## Recommended Approach

Adopt Options 1 + 2 + 3 + 4 + 5 in phases, keeping the current architecture:

- Phase A (low risk): implement conditional hashing and ignore globs; raise throttle to 300–500ms; add ignored-change diagnostics.
- Phase B (integration): plumb builder-provided changed outputs (if/when available) into the controller and prefer them.
- Phase C (hygiene): remove duplicate injection code.

## API Changes

ReloadController:

- New optional constructor params:
  - `ignored_globs: list[str] | None = None`
  - `hash_on_suspect: bool = True`
  - `suspect_hash_limit: int = 200`
  - `suspect_size_limit_bytes: int = 2_000_000`
  - `min_notify_interval_ms: int = 300` (default raised)

- New runtime configuration setters (to avoid hard-wiring config at import time for the global `controller`):
  - `set_min_notify_interval_ms(value: int) -> None`
  - `set_ignored_globs(globs: list[str] | None) -> None`
  - `set_hashing_options(hash_on_suspect: bool, suspect_hash_limit: int, suspect_size_limit_bytes: int) -> None`

  Rationale: the global `controller` is instantiated at import-time in `bengal.server.reload_controller`. Exposing setters allows `DevServer`/`BuildHandler` to apply `dev.reload.*` overrides from site config at runtime without changing the controller’s lifecycle.

- New methods:
  - `decide_from_changed_paths(changed_paths: list[str]) -> ReloadDecision`
    - Bypasses snapshot walking; classifies CSS-only vs full reload.
    - Applies ignore-globs filtering and throttling consistently with `decide_and_update`.

- Existing:
  - `decide_and_update(output_dir: Path) -> ReloadDecision` gains use of ignores and conditional hashing.

BuildHandler integration:

- If `stats` exposes `changed_outputs: list[str]` or similar, call `controller.decide_from_changed_paths(stats.changed_outputs)`; else call `decide_and_update`.
- On server startup (and after initial build), read `dev.reload.*` via `get_dev_config` and configure the controller using the new setters:
  - `set_min_notify_interval_ms(get_dev_config(cfg, "reload", "min_notify_interval_ms", default=300))`
  - `set_ignored_globs(get_dev_config(cfg, "reload", "ignore_paths", default=[]))`
  - `set_hashing_options(
        hash_on_suspect=get_dev_config(cfg, "reload", "hash_on_suspect", default=True),
        suspect_hash_limit=get_dev_config(cfg, "reload", "suspect_hash_limit", default=200),
        suspect_size_limit_bytes=get_dev_config(cfg, "reload", "suspect_size_limit_bytes", default=2_000_000)
    )`

## Config Schema

Extend `bengal.toml` (dev profile):

```toml
[dev.reload]
ignore_paths = [
  # Paths/globs relative to output dir (public/)
  "index.json",
  "search/**",
]
min_notify_interval_ms = 300
hash_on_suspect = true
suspect_hash_limit = 200
suspect_size_limit_bytes = 2000000
```

Existing:

- `dev.watch.debounce_ms` (already supported in `BuildHandler`)
- `BENGAL_WATCHDOG_BACKEND` env override (unchanged)

Notes:
- Ignore globs are matched relative to the output directory and applied both when diffing snapshots and when consuming builder-provided `changed_outputs`.
- If a config value is not provided, controller defaults are used (as listed above).

## Rollout Plan

Phase A

- Implement ignore globs and conditional hashing in `ReloadController`
- Raise default `min_notify_interval_ms` to 300
- Add logging for “hash-equal change ignored” events (debug/info)
- Wire controller runtime configuration in `DevServer.start()` (or immediately after initial build) using the new setters and `get_dev_config`.

Phase B

- Add optional `changed_outputs` to build stats (or similar) and wire through
- Make `BuildHandler` prefer `decide_from_changed_paths` when provided

Phase C

- Remove `_inject_live_reload` from `BengalRequestHandler` (dead path)
  - Update unit tests to validate `serve_html_with_live_reload()` behavior instead of `_inject_live_reload`.

## Testing Plan

Unit (controller):

- mtime-changed, size-equal, content-equal → no reload (hash ignored)
- CSS-only changed paths → `reload-css` with targeted `changed_paths`
- Mixed changes → full `reload`
- ignore globs exclude specified files from decisions
- throttle suppresses rapid consecutive notifications
- suspect hashing honors caps and size thresholds; log includes suppression reason
- decide_from_changed_paths applies ignore globs and throttle consistently

Integration:

- Saving a page that doesn’t change rendered HTML does not reload
- Editing only a CSS file performs CSS hot reload without page refresh
- With ignore globs set for `index.json`, changes to that file don’t reload
- When builder supplies `changed_outputs`, decisions match the hints
- Controller runtime configuration reflects `dev.reload.*` values (e.g., throttle raised when configured)

Performance:

- Large site snapshot diff with hashing caps stays within acceptable latency (measure N<200 hashes)

## Metrics & Observability

- Count of suppressed changes due to hash-equal content
- Distribution of decision reasons: baseline, throttled, css-only, content-changed, no-output-change
- First 5 changed files printed on each non-throttled decision (already present)
- Additional counters: number of suspect files hashed per cycle, number of cap hits; structured log event key `reload_controller_hash_equal_suppressed` when a change is ignored due to equal content hash.

## Risks & Mitigations

- Hashing overhead: bound hash count and size; only hash when size-equal and mtime-changed
- Incorrect ignores: defaults empty; documentation and CLI guidance
- Builder hint availability: optional; graceful fallback to snapshot diff
- Global controller lifecycle: settings are applied via thread-safe setters during server startup; updates are infrequent and safe during dev.

## Alternatives Considered

- Full output hashing DB each cycle: accurate but too expensive for large sites
- Source-level dependency graph for live reload: powerful but out of scope for this RFC

## Appendix: Minor Cleanup

- Remove unused `_inject_live_reload` path in `BengalRequestHandler`; rely on `LiveReloadMixin.serve_html_with_live_reload()` which already handles cache-keyed injection by file mtime.
