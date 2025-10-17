# Bengal Cache Strategy – Comprehensive Proposal (SSG-grade)

Status: Draft

## Goals
- Maximize incremental build speed while preserving correctness.
- Keep caches resilient (atomic writes, tolerant loads) and debuggable.
- Provide clean invalidation semantics for content, templates, config, assets, data, i18n, plugins.

## Current Strengths
- BuildCache with JSON-serializable data, dependency tracking, parsed-content caching, tag index.
- Atomic writes for primary and secondary caches (now added to page/asset maps).
- Auto-mode incremental detection and safe full-rebuild on config changes.
- Dev server clears ephemeral state and HTML cache to avoid stale objects.
- Incremental taxonomy generation and cascade detection for section index changes.

## Gaps / Opportunities
1) Data files (data/*.yaml|json|toml) – detect and rebuild dependents.
2) i18n files (i18n/*.yaml|json|toml) – per-locale invalidation.
3) Asset pipeline deps – SCSS/JS partials and manifests tracked for page-level invalidation.
4) Plugin/shortcode dependency declarations – allow directives to register file deps.
5) Parsed-content cache caps – LRU/size limits to avoid unbounded growth.
6) Build-flags/environment hash – profile, theme version, baseurl, minify/fingerprint toggles.
7) Multi-process safety – file lock to avoid concurrent writers racing on .bengal/*.json.
8) Move/rename detection – prefer rename over delete+add for better cleanup and taxonomy stability.

## Proposed Architecture

### A. Dependency Domains
- Content deps: page → {template.html, partials.html, config, data/*, i18n/*}
- Asset deps: page → {referenced assets}; and pipeline graph: asset_entry → {partials/imports}
- Taxonomy deps: tag_slug → {page_paths}
- Plugin deps: page → {declared extra files}

Extend `DependencyTracker` to accept:
```python
track_data(file: Path)
track_i18n(file: Path)
track_plugin_dep(file: Path)
```
All resolve to `cache.add_dependency(page, file)` so existing invalidation works without schema churn.

### B. Data/i18n Tracking
- During discovery/render, when `site.data[...]` or `i18n.t()` accesses a key, record the underlying file path via small wrappers in data/i18n loaders.
- Hash data/i18n files into `BuildCache.file_hashes` and leverage `get_affected_pages()` to rebuild only dependents.

### C. Asset Pipeline Graph
- When pipeline runs, emit a manifest (JSON) of entry → transitive partials/imports.
- Store in `.bengal/asset_graph.json` with atomic write.
- On change to a partial, identify impacted entry outputs; if any pages reference those outputs (via `AssetDependencyMap`), rebuild only those pages.

### D. Plugin/Shortcode Deps
- Expose a minimal API for directives:
```python
def declare_dependencies(files: list[Path]): ...
```
- Under the hood call `DependencyTracker.track_plugin_dep(file)` for the current page.

### E. Parsed-content Cache LRU
- Add global caps: max_cached_pages (e.g., 5_000), max_total_mb (e.g., 200 MB).
- Maintain `size_bytes` already stored; evict least-recently-used on store.

### F. Build Flags Hash
- Compute a stable build context hash: {profile, theme_name+version, baseurl, fingerprint_assets, minify_assets}.
- Persist in BuildCache (e.g., `build_context_hash`). If mismatch, force full rebuild and refresh.

### G. Multi-process Locking
- Wrap `.bengal/cache.json` and related writes in an interprocess file lock. Keep atomic writes as last step.

### H. Rename/Move Handling
- Detect potential renames by hashing new files and matching against deleted hashes. If matched, remap dependencies and outputs instead of delete+add.

## Phased Roadmap

Phase 1 (Low-risk, high value)
- Implement AtomicFile (done for secondary caches).
- Add BuildCache VERSION (done).
- Add build-context hash (profile, theme, baseurl, asset flags) → full rebuild on change.
- Cap parsed-content cache with LRU by page count + total MB.

Phase 2 (Core dependency completeness)
- Data/i18n dependency tracking via loaders + DependencyTracker hooks.
- Asset pipeline manifest and incremental asset impact mapping.

Phase 3 (Ecosystem + robustness)
- Plugin/shortcode dependency API.
- Interprocess file lock for cache writes.
- Rename/move detection using hash matching and remap.

## Migration & Compatibility
- Schema: increment `BuildCache.VERSION`; tolerant load keeps old caches working.
- Feature flags: allow disabling new trackers per site config if needed.
- Clear messaging: log when full rebuild is forced due to build-context hash change.

## Success Criteria
- Single-page edits: 15–50x speedups sustained with taxonomies, menus, and assets stable.
- Data/i18n change: only affected pages regenerate.
- Asset partial change: only pages referencing resulting bundles regenerate.
- Caches remain intact across crashes (atomic writes) and across branches (no bleed if context differs).

## Risks & Mitigations
- Over-tracking causing false positives → keep dependencies file-granular, avoid coarse invalidations.
- Complex asset graphs → start with entry→partials manifest; expand if needed.
- Plugin API misuse → document clearly; default to no-op if dependencies missing.

---

Implementation next steps (shortlist):
1. Build-context hash in `BuildCache` and check in `BuildOrchestrator`.
2. LRU limits for `parsed_content` with eviction on insert.
3. Data/i18n loaders: expose file-path during access and call tracker.
4. Asset pipeline manifest emit + use in incremental.
5. Lockfile around `.bengal/cache.json` writes.
