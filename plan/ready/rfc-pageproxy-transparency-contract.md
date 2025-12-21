# RFC: Close remaining `PageProxy` transparency gaps for output formats (and lock in with tests)

**Status**: Ready  
**Author**: AI Assistant  
**Created**: 2025-12-12  
**Updated**: 2025-12-21  
**Confidence**: 90% 🟢  
**Priority**: P0 (Correctness)  

---

## Executive summary

Incremental builds intentionally leave `site.pages` as a mix of `Page` and `PageProxy` immediately before postprocess. Postprocess always generates output formats when enabled, and those generators depend on the page “content surface area” (notably `plain_text`).

This RFC narrows scope to **(1) closing the concrete `PageProxy` gaps required by output formats** and **(2) adding contract tests that fail at review time** if output formats regress under mixed `Page`/`PageProxy` lists.

---

## Problem statement

### Current behavior (evidence-backed)

- `PageProxy` is a lazy-loaded stand-in used in incremental builds, and the code explicitly treats proxy transparency as critical:
  - `bengal/core/page/proxy.py:33-75`

- Cached discovery replaces unchanged pages with `PageProxy` and keeps enough state for later phases (including copying `output_path` when available):
  - `bengal/discovery/content_discovery.py:315-403` (proxy creation)
  - `bengal/discovery/content_discovery.py:375-377` (copy `output_path`)

- In incremental builds, Phase 15 explicitly keeps existing entries (including proxies) for pages that were not rebuilt:
  - `bengal/orchestration/build/rendering.py:293-345`

- Postprocess always generates output formats when enabled (even for incremental builds):
  - `bengal/orchestration/postprocess.py:124-166`

- Output-format generators depend on `page.plain_text`:
  - `bengal/postprocess/output_formats/index_generator.py:286-374`
  - `bengal/postprocess/output_formats/json_generator.py:138-244`
  - `bengal/postprocess/output_formats/llm_generator.py:82-118`
  - `bengal/postprocess/output_formats/txt_generator.py:100-160`

- `plain_text` is a first-class `Page` API (via `PageContentMixin`):
  - `bengal/core/page/content.py:37-145`

### The concrete gap (why this is still needed)

Today, `PageProxy` does not define `plain_text` (verified by code search), but output formats unconditionally read it. Given that proxies can survive into postprocess (Phase 15), this is a correctness hazard that can produce runtime errors only in incremental scenarios.

More broadly, the transparency contract is still **implicit**: there is no single, tested “minimum surface” for postprocess/output formats, so it is easy to introduce regressions by reading new page attributes without updating `PageProxy`.

---

## Goals

- **Correctness**: Output formats succeed when `site.pages` includes `PageProxy`.
- **Contract enforcement**: Tests fail if output formats add new required attributes that `PageProxy` does not expose.
- **Minimal blast radius**: Avoid broad refactors; fix only what output formats require today.

## Non-goals

- Proving arbitrary user templates are safe (Jinja can access anything dynamically).
- Moving `plain_text` (or other derived content) into caches as part of this RFC.
- Changing incremental build semantics (when proxies exist, when postprocess runs).

---

## Proposed changes (rescope)

### 1) Close the output-formats contract gap: add `PageProxy.plain_text`

Add a `plain_text` property on `PageProxy` that **delegates to the full page** (triggering `_ensure_loaded()`).

- This aligns with the existing `PageProxy` approach for non-core fields like `href`, `_path`, `parsed_ast`, and `content` (all delegate to the full page):
  - `bengal/core/page/proxy.py:237-388` (lazy-load + delegates)

### 2) Add contract tests that exercise output formats with real proxies

Add tests that fail loudly if output formats regress under mixed `Page`/`PageProxy` lists.

Suggested minimum:

- **Unit test** (`tests/unit/core/test_page_proxy.py`):
  - Construct a `PageProxy` with a loader returning a `Page` whose `parsed_ast` and/or `content` makes `plain_text` non-empty.
  - Assert:
    - `proxy.plain_text` exists and returns `str`
    - Access triggers lazy-load (matches existing lazy-loading tests style)

- **Integration test** (`tests/integration/test_incremental_output_formats.py`):
  - Ensure incremental build path includes at least one `PageProxy` (or directly construct via `PageDiscoveryCache` + discovery).
  - Verify output-format artifacts are generated successfully (`index.json`, `llm-full.txt`) under that state.

Note: There is already strong integration coverage that `index.json` exists and remains populated across incremental builds:
`tests/integration/test_incremental_output_formats.py:17-80`.
This RFC extends coverage to assert that proxies are present in the scenario being tested (so we know we are testing the contract, not accidentally avoiding it).

---

## Acceptance criteria

- `PageProxy` exposes `plain_text` suitable for output formats.
- At least one test fails if `PageProxy` is missing an attribute that current output formats read.
- Integration coverage proves output formats succeed with a mixed `Page`/`PageProxy` list (not only full `Page` lists).

---

## Rollout plan (atomic commits)

1. **core(page)**: add `PageProxy.plain_text` delegate (lazy-loads full page).
2. **tests(core)**: add/extend unit tests for `PageProxy.plain_text` behavior (exists + triggers load).
3. **tests(integration)**: ensure incremental output-formats tests exercise at least one proxy path (and still generate output formats).

---

## Risks and mitigations

- **Risk**: Adding `plain_text` may increase I/O in incremental builds (it can trigger full page loads for unchanged pages).
  - **Mitigation**: Keep this RFC correctness-only; treat any caching/perf work (e.g., caching `plain_text`) as a follow-up RFC/plan once correctness is locked in.

- **Risk**: Contract stays implicit and drifts.
  - **Mitigation**: The contract tests must be updated whenever output formats begin reading new page attributes; this creates review-time friction (the desired behavior).

---

## References (evidence)

- `bengal/core/page/proxy.py:33-75` — Explicit “TRANSPARENCY CONTRACT” warning and incremental-build lifecycle notes.
- `bengal/discovery/content_discovery.py:315-403` — Cached discovery replaces unchanged pages with `PageProxy`.
- `bengal/discovery/content_discovery.py:375-377` — Copies `output_path` for postprocessing.
- `bengal/orchestration/build/rendering.py:293-345` — Phase 15 keeps proxies for unchanged pages (mixed `site.pages`).
- `bengal/orchestration/postprocess.py:124-166` — Output formats are treated as critical and always generated when enabled.
- `bengal/postprocess/output_formats/index_generator.py:286-374` — Reads `page.plain_text`.
- `bengal/postprocess/output_formats/json_generator.py:138-244` — Reads `page.plain_text` and `page.parsed_ast`.
- `bengal/postprocess/output_formats/llm_generator.py:82-118` — Reads `page.plain_text`.
- `bengal/postprocess/output_formats/txt_generator.py:100-160` — Reads `page.plain_text`.
- `bengal/core/page/content.py:37-145` — Defines `plain_text` on `Page` via `PageContentMixin`.
