# Plan: Autodoc stability + Dev dropdown auto-registration (Python, CLI, OpenAPI)
**Status**: Draft  
**Created**: 2025-12-12  
**Related**:
- `plan/drafted/plan-autodoc-output-prefix.md` (URL namespaces)
- `plan/drafted/rfc-theme-003-autodoc-integration.md` (theme templates as the presentation layer)

---

## Executive summary

Today, **Python autodoc can be silently “disabled” by config** and therefore fails to create the `/api/` section that the **Dev dropdown bundler** depends on. The immediate stability fix is to make Python autodoc’s exclude matching behave like real globs so patterns such as `*/.*` do not match everything.

Then, to mature the system for **3 outputs with different layout needs**, we add invariants + tests for:
- **output prefix → section tree → menu/dev dropdown registration**
- **page type → template directory mapping**
- **render-time deferred autodoc templates (with full nav context)**

---

## Current behavior (evidence)

### Python autodoc can skip all files due to exclude matching

- The site’s autodoc config includes the pattern `*/.*` under `autodoc.python.exclude`:
  - Evidence: `site/config/_default/autodoc.yaml:27-48`
- The Python extractor implements exclude patterns using **substring extraction**:
  - Evidence: `bengal/autodoc/extractors/python.py:195-248`
  - Specifically, it derives `core_pattern` via `replace("*", "")` and checks `core_pattern in path_str`:
    - Evidence: `bengal/autodoc/extractors/python.py:236-246`
  - For `*/.*`, the derived `core_pattern` becomes `"."`, which is present in essentially every path string, causing **all** files to be skipped.

### Dev dropdown bundling depends on an `api` Section being present

In auto-menu mode, Dev dropdown links are built from:
- GitHub repo URL (config)
- an `api` section (`section.name == "api"`)
- a `cli` section (`section.name == "cli"`)

Evidence: `bengal/orchestration/menu.py:205-351`

So if Python autodoc fails to create an aggregating `/api/` section, **the “API Reference” link cannot be added**.

### Autodoc already has an “aggregating /api/” mechanism (good foundation)

Autodoc creates “aggregating parent sections” like `/api/` to support menu detection, even when there is only one child:
- Evidence: `bengal/autodoc/orchestration/section_builders.py:271-343`

And the autodoc orchestrator prefers returning aggregating sections as “root sections”:
- Evidence: `bengal/autodoc/orchestration/orchestrator.py:588-626`

### Layout separation is already modeled via `type → template_dir` mapping

Autodoc uses a page `type` to drive CSS (e.g. `python-reference`) while mapping templates to a directory:
- Evidence: `bengal/autodoc/orchestration/utils.py:14-33`

---

## Goals

1. **Stability**: Python autodoc extraction cannot be “accidentally disabled” by reasonable glob patterns.
2. **Robust 3-output support**: Python / CLI / OpenAPI can coexist with distinct URL namespaces and layout templates.
3. **Dev dropdown auto-registration**: when the system auto-defines the main menu, autodoc outputs are registered under **Dev** automatically.
4. **Regression protection**: add tests that fail if any of the above breaks.

## Non-goals

- Redesign of theme dropdown CSS/JS behavior (see `plan/drafted/plan-dropdown-refactor.md`).
- Manual menu authoring; this plan focuses on the auto-menu path.

---

## Proposed work (phased)

### Phase 0 (hotfix): make Python exclude patterns safe and predictable

**Why now**: this restores Python autodoc output, which restores `/api/` and therefore re-enables Dev dropdown “API Reference”.

1. **Fix PythonExtractor exclude matching to use proper glob semantics**
   - **File**: `bengal/autodoc/extractors/python.py`
   - **Change**: replace substring-based matching (`core_pattern in path_str`) with `fnmatch`-style matching on a normalized POSIX path (and optionally the basename).
   - **Contract**:
     - `*/.*` matches hidden files/dirs, not all files.
     - Existing patterns like `*/tests/*`, `*/__pycache__/*`, `*_test.py` continue to work.
   - **Commit**: `fix(autodoc): make python exclude patterns use glob matching; prevent */.* from skipping all files`

2. **Unit tests for exclude patterns**
   - **Files**: `tests/unit/autodoc/test_python_extractor_exclude_patterns.py` (new)
   - **Cases**:
     - `*/.*` does **not** skip a normal file path (e.g. `bengal/core/site.py`)
     - `*/.venv/*` skips `.venv/...`
     - `*_test.py` skips `foo_test.py`
   - **Commit**: `tests(autodoc): add unit tests for python extractor exclude patterns`

3. **Make “0 python elements extracted” visible in non-debug logs**
   - **File**: `bengal/autodoc/orchestration/extractors.py`
   - **Change**: when `autodoc.python.enabled` and all `source_dirs` exist but extraction yields 0 elements, emit a warning with the active exclude patterns (or a count + hint).
   - Evidence for current wrapper behavior: `bengal/autodoc/orchestration/extractors.py:22-54`
   - **Commit**: `autodoc(python): warn when enabled but extraction yields 0 elements`

---

### Phase 1 (stability): Dev dropdown registration invariants + tests

1. **Integration test: auto-menu builds Dev dropdown with API Reference when python autodoc is enabled**
   - **Files**: `tests/integration/autodoc/test_dev_dropdown_registration.py` (new)
   - **Assert**:
     - after build, `site.menu["main"]` contains an item `name == "Dev"` with a child `name == "API Reference"`
     - the API link targets `/api/` (aggregating section) or the resolved prefix root
   - **Evidence for current bundling logic**: `bengal/orchestration/menu.py:205-334`
   - **Commit**: `tests(autodoc): add integration test for Dev dropdown auto-registration`

2. **Integration test: autodoc creates an aggregating `/api/` section when output_prefix is `api/...`**
   - **Files**: `tests/integration/autodoc/test_aggregating_api_section.py` (new)
   - **Assert**:
     - When Python output prefix is `api/python`, an aggregating section with `name == "api"` exists.
   - **Evidence for aggregating section creation**: `bengal/autodoc/orchestration/section_builders.py:271-343`
   - **Commit**: `tests(autodoc): add integration test for aggregating /api/ section`

---

### Phase 2 (maturity): decouple Dev dropdown from hard-coded section names

**Problem**: `MenuOrchestrator` currently discovers Dev links by searching for `section.name in {"api","cli"}`. That is fragile if:
- output prefixes change (see `plan/drafted/plan-autodoc-output-prefix.md`)
- a site wants API docs outside `/api/`

1. **Have autodoc publish “dev menu links” explicitly**
   - **Files**:
     - `bengal/autodoc/orchestration/orchestrator.py`
     - `bengal/core/site/` (add a new ephemeral attribute similar to `_dev_menu_metadata`)
     - `bengal/orchestration/menu.py`
   - **Approach**:
     - Virtual autodoc generation knows which doc types are enabled and their resolved prefixes.
     - It should export a structured list like:
       - `[{name: "Python API", url: "/api/python/"}, {name: "REST API", url: "/api/rest/"}, {name: "CLI", url: "/cli/"}]`
     - Menu bundler uses this list instead of searching for section names.
   - **Commit**: `orchestration(menu): source Dev dropdown links from autodoc-provided registry; avoid hard-coded section names`

2. **Tests**
   - Add integration tests that customize `output_prefix` and still get a Dev dropdown entry for each enabled output.
   - **Commit**: `tests(autodoc): ensure Dev dropdown registration works with custom output_prefix values`

---

### Phase 3 (maturity): layout + template guarantees across 3 outputs

1. **Contract test: each autodoc page type maps to an existing template directory**
   - **Evidence**: `bengal/autodoc/orchestration/utils.py:14-33`
   - **Goal**: prevent regressions where a page type is emitted but templates do not exist.
   - **Commit**: `tests(rendering): add contract tests for autodoc type→template_dir mapping`

2. **Smoke render test: render 1 representative page per autodoc type**
   - Render a python module page, a cli command page, and an openapi endpoint page using the default theme templates.
   - Assert “no TemplateNotFound / StrictUndefined” and the output contains a key marker (title/header).
   - **Commit**: `tests(rendering): add autodoc smoke render tests for python/cli/openapi templates`

---

## Success criteria (ship gates)

- **Python autodoc extraction works** with the site’s current config (including `*/.*`) and produces pages.
- **Auto menu** produces a **Dev dropdown** containing **API Reference** when Python autodoc is enabled.
- With Python + CLI + OpenAPI enabled, each has:
  - a stable URL namespace (per output_prefix RFC)
  - a stable template/layout path (per type→template mapping)
- CI includes unit + integration tests covering the above.

---

## User-permutation support matrix (auto topbar menu)

This section enumerates the main “auto menu” permutations and whether they work **today** (current code), versus the intended target after the phases above.

### Definitions

- **Auto menu mode**: `menu.main` not configured, so `MenuOrchestrator` builds `menu.main` from sections (`bengal/orchestration/menu.py:205-373`).
- **GitHub link**: rendered directly from `params.repo_url` unless “bundled” into Dev (`bengal/themes/default/templates/base.html:272-286`).
- **Dev dropdown**: only created when `len(dev_assets) >= 2` (`bengal/orchestration/menu.py:287-334`).
- **API section detection**: hard-coded `section.name == "api"` (`bengal/orchestration/menu.py:227-234`).
- **CLI section detection**: hard-coded `section.name == "cli"` (`bengal/orchestration/menu.py:235-241`).

### Results (current behavior)

- [OK] **No Dev assets** (no repo_url, no api section, no cli section): auto menu shows discovered sections.
- [OK] **GitHub only** (repo_url set; no api, no cli): GitHub appears as a topbar link (not under Dev).
- [BROKEN] **CLI only** (cli section exists; no repo_url; no api): `cli` is excluded from auto-nav but Dev dropdown is not created (requires 2+ assets), so CLI can disappear.
- [BROKEN] **API only** (api section exists; no repo_url; no cli): `api` is excluded from auto-nav but Dev dropdown is not created (requires 2+ assets), so API can disappear.
- [OK] **GitHub + CLI**: Dev dropdown is created; GitHub is bundled (top-level GitHub suppressed) and CLI appears under Dev.
- [OK] **GitHub + API**: Dev dropdown is created; GitHub is bundled and API appears under Dev.
- [OK] **API + CLI**: Dev dropdown is created with both entries.
- [PARTIAL] **OpenAPI only**: no explicit Dev entry for OpenAPI exists today; it is only reachable indirectly via an aggregating `/api/` section when output prefixes create it.

### Target behavior (post plan)

- Phase 0 + Phase 1: ensure “Python API enabled” reliably produces pages and `/api/` so Dev can include **API Reference**.
- Phase 2: remove hard-coded detection (api/cli) and let autodoc publish the exact “Dev links” to bundle, so:
  - “just CLI” and “just API” can be shown without disappearing (either as top-level items or as a Dev dropdown with a single item — explicit product decision).
  - OpenAPI can get its own explicit entry (not only via `/api/` umbrella).
