---
name: S-Tier Docs Versioning
overview: Enhance Bengal's documentation versioning for S-tier quality with performance optimizations that scale to many versions.
todos: []
isProject: true
---

# S-Tier Docs Versioning Plan

**Status**: Planning  
**Scope**: `bengal/content/versioning`, `bengal/orchestration`, `bengal/core/site`, themes  
**Goal**: S-tier docs versioning that minimizes performance issues as docs scale with many versions.

---

## Executive Summary

Bengal has solid versioning foundations: folder mode (`_versions/<id>/`), git mode (branches/tags), version selector UI, cross-version links with fallback URLs, incremental build awareness. The main gaps are: (1) **performance at scale** — all versions rebuild every build; (2) **missing UX pieces** — `versions.json`, root redirect; (3) **no deploy model** for building one version at a time.

This plan adds incremental version builds, optional merge-deploy mode, `versions.json`, root redirect, and version-scoped cache invalidation.

---

## Current State (Evidence)


| Component                | Location                                        | Behavior                                                          |
| ------------------------ | ----------------------------------------------- | ----------------------------------------------------------------- |
| VersionConfig            | `bengal/core/version.py`                        | Folder + git modes, aliases, shared content                       |
| VersionResolver          | `bengal/content/versioning/resolver.py`         | Path resolution, cross-version links                              |
| GitVersionAdapter        | `bengal/content/versioning/git_adapter.py`      | Worktrees, `is_version_changed()` for commit tracking             |
| Version selector         | `partials/version-selector.html`                | Uses `site.get_version_target_url()` — pre-computed fallback URLs |
| Incremental invalidation | `orchestration/incremental/orchestrator.py:646` | Shared content change → all versioned pages rebuild               |
| Directive cache          | `rendering/pipeline/core.py:144`                | Auto-enabled for versioned sites                                  |
| Version config           | `site.version_config`                           | Passed to parser for `[[v2:path]]` resolution                     |


**Performance bottleneck**: All versions build in one pass. With 20 versions × 100 pages = 2000 page renders per full build. Incremental helps when *content* changes, but config/version-list changes still trigger full rebuild.

---

## Goals

1. **Scale to many versions** — Build time grows sub-linearly with version count where possible
2. **Incremental version builds** — Only rebuild versions whose content/config changed
3. **Merge-deploy mode** — Optional: build one version, merge into existing output (Mike-style)
4. **Complete UX** — `versions.json`, root redirect to default version
5. **Version-scoped invalidation** — Change in v3 doesn't invalidate v2 cache
6. **Preserve existing behavior** — Folder mode, git mode, version selector unchanged for current users

## Non-Goals

- Replacing folder or git mode with a new model
- Client-side version loading (all versions remain static HTML)
- Breaking `get_version_target_url` or cross-version link semantics

---

## Architecture Options

### Option A: Incremental Version Builds Only

**Idea**: Track per-version content hashes. Only build versions whose content changed.

**Pros**: Minimal change, fits existing architecture  
**Cons**: Full build still processes all versions; no deploy model for CI

### Option B: Merge-Deploy Mode (Mike-Style)

**Idea**: New `bengal build --version 1.0` builds one version and merges into `public/`. Old versions untouched.

**Pros**: CI can deploy latest only; old docs never rebuild  
**Cons**: Requires merge logic, output layout compatibility, different workflow

### Option C: Hybrid (Recommended)

**Idea**: Combine A + B. Add incremental version builds for normal `bengal build`, add optional `--version` flag for merge-deploy.

**Pros**: Best of both; normal users get faster builds, CI gets Mike-style deploys  
**Cons**: More implementation surface

---

## Recommended Approach: Hybrid

### Phase 1: Low-Risk UX & Data (Quick Wins)


| Task | Description                                               | Effort |
| ---- | --------------------------------------------------------- | ------ |
| 1.1  | Emit `versions.json` at build when versioning enabled     | S      |
| 1.2  | Add root redirect (config: `versioning.default_redirect`) | S      |
| 1.3  | Document `versions.json` format (Mike-compatible)         | XS     |


### Phase 2: Version-Scoped Cache Invalidation


| Task | Description                                           | Effort |
| ---- | ----------------------------------------------------- | ------ |
| 2.1  | Add version_id to BuildCache key / EffectTracer scope | M      |
| 2.2  | Invalidate only pages in changed versions             | M      |
| 2.3  | Shared content: keep current behavior (all versions)  | —      |


**Evidence**: `incremental/orchestrator.py` already checks `version_config.shared`. Need to scope `is_changed` / dependency tracking by version.

### Phase 3: Incremental Version Builds


| Task | Description                                                   | Effort |
| ---- | ------------------------------------------------------------- | ------ |
| 3.1  | Persist per-version content hash in BuildCache                | M      |
| 3.2  | Skip build for versions with unchanged hash                   | M      |
| 3.3  | Git mode: use `is_version_changed(version_id, cached_commit)` | S      |
| 3.4  | Folder mode: hash `_versions/<id>/` + shared                  | M      |


**Output**: `bengal build` with 20 versions, 2 changed → only 2 versions rebuild.

### Phase 4: Merge-Deploy Mode (Optional)


| Task | Description                                                   | Effort |
| ---- | ------------------------------------------------------------- | ------ |
| 4.1  | Add `bengal build --version <id>` flag                        | M      |
| 4.2  | Build single version into temp dir, merge into `public/`      | L      |
| 4.3  | Update `versions.json` in place (append/update version entry) | M      |
| 4.4  | CI workflow docs for `bengal build --version latest -p`       | S      |


**Merge rules**: Overwrite `public/<version>/` and `public/` (latest). Never delete other version dirs.

### Phase 5: Polish & Observability


| Task | Description                                                   | Effort |
| ---- | ------------------------------------------------------------- | ------ |
| 5.1  | Build log: "Built 3/20 versions (17 skipped)"                 | XS     |
| 5.2  | `bengal version list` — show versions, last-built, hash       | S      |
| 5.3  | MkDocs migration doc: add Mike comparison, versioning section | S      |


---

## Implementation Order

```
Phase 1 (1–2 days)  →  Phase 2 (2–3 days)  →  Phase 3 (2–3 days)
        ↓                       ↓                       ↓
   versions.json          version-scoped           incremental
   root redirect              invalidation          version builds

Phase 4 (3–4 days)  →  Phase 5 (1 day)
        ↓                       ↓
   merge-deploy             polish
```

**Dependencies**: Phase 2 enables Phase 3. Phase 4 can start after Phase 1.

---

## Config Additions

```toml
[versioning]
enabled = true
default_redirect = true   # / → redirect to latest
emit_versions_json = true # default: true when enabled

# Merge-deploy (Phase 4)
# No config needed; --version flag is CLI-only
```

---

## versions.json Format (Mike-Compatible)

```json
[
  {"version": "1.0", "title": "1.0.1", "aliases": ["latest"], "url_prefix": ""},
  {"version": "0.9", "title": "0.9", "aliases": [], "url_prefix": "/0.9"}
]
```

Emit to `public/versions.json` (or `public/<deploy_prefix>/versions.json` if deploy_prefix set).

---

## Risks & Mitigations


| Risk                         | Mitigation                                      |
| ---------------------------- | ----------------------------------------------- |
| Merge-deploy corrupts output | Dry-run mode; backup before merge               |
| Version hash false negatives | Include frontmatter, shared deps in hash        |
| Breaking existing versioning | All changes additive; existing config unchanged |


---

## Success Criteria

- `versions.json` emitted when versioning enabled
- Root redirect works with `default_redirect = true`
- Version-scoped invalidation: change in v3 doesn't rebuild v2
- Incremental version builds: unchanged versions skipped
- `bengal build --version 1.0` merges into existing output
- Build time with 20 versions, 1 changed: ~5% of full build (not 100%)

---

## Related

- `bengal/content/versioning/resolver.py` — path resolution
- `bengal/content/versioning/git_adapter.py` — `is_version_changed`
- `bengal/orchestration/incremental/orchestrator.py` — invalidation
- `bengal/rendering/template_functions/version_url.py` — target URL fallbacks
- Mike: [https://github.com/jimporter/mike](https://github.com/jimporter/mike)

