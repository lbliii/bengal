# Plan: Autodoc stability + Dev dropdown auto-registration (Python, CLI, OpenAPI)
**Status**: Draft  
**Created**: 2025-12-12  
**Last Updated**: 2025-01-XX  
**Related**:
- `plan/drafted/plan-autodoc-output-prefix.md` (URL namespaces)
- `plan/drafted/rfc-theme-003-autodoc-integration.md` (theme templates as the presentation layer)

---

## Executive summary

**Phase 0 (stability hotfix) is complete**: Python autodoc exclude pattern matching now uses proper glob semantics via `fnmatch`, preventing patterns like `*/.*` from accidentally skipping all files. This ensures Python autodoc reliably creates the `/api/` section needed for Dev dropdown registration.

**Remaining work** focuses on maturing the system for robust 3-output support (Python/CLI/OpenAPI) with:
- **Integration test coverage** for Dev dropdown registration
- **Decoupling Dev dropdown from hard-coded section names** to support custom `output_prefix` values
- **Template contract tests** to prevent regressions

---

## Current state

### ✅ Phase 0: Python exclude patterns fixed (COMPLETED)

Python autodoc exclude matching now uses proper glob semantics:
- **Implementation**: `bengal/autodoc/extractors/python/skip_logic.py:55-148` uses `fnmatch` for pattern matching
- **Tests**: `tests/unit/autodoc/test_python_extractor_exclude_patterns.py` covers `*/.*` and other patterns
- **Integration**: `PythonExtractor` uses `should_skip()` via `_should_skip()` wrapper (`bengal/autodoc/extractors/python/extractor.py:655-667`)

The site's autodoc config includes `*/.*` under `autodoc.python.exclude` (`site/config/_default/autodoc.yaml:49`), and this pattern now correctly matches only hidden files/directories, not all paths.

### Dev dropdown bundling depends on hard-coded section names

In auto-menu mode, Dev dropdown links are discovered by searching for specific section names:
- GitHub repo URL (from `params.repo_url`)
- `api` section (`section.name == "api"` at `bengal/orchestration/menu.py:228`)
- `cli` section (`section.name == "cli"` at `bengal/orchestration/menu.py:236`)

**Evidence**: `bengal/orchestration/menu.py:205-351`

This hard-coded approach is fragile when:
- `output_prefix` values change (see `plan/drafted/plan-autodoc-output-prefix.md`)
- Sites want API docs outside `/api/`
- OpenAPI needs explicit Dev menu entry (currently only accessible via aggregating `/api/` section)

### Autodoc foundation is solid

- **Aggregating sections**: Autodoc creates parent sections like `/api/` to support menu detection, even with a single child (`bengal/autodoc/orchestration/section_builders.py:324-403`)
- **Type→template mapping**: Page types map to template directories (`bengal/autodoc/orchestration/utils.py:14-33`)
- **Unit test coverage**: Dev dropdown logic and aggregating sections have unit tests (`tests/unit/orchestration/test_menu_dev_dropdown_autodoc.py`, `tests/unit/autodoc/test_aggregating_sections.py`)

---

## Goals

1. ✅ **Stability**: Python autodoc extraction cannot be "accidentally disabled" by reasonable glob patterns. **(COMPLETED)**
2. **Robust 3-output support**: Python / CLI / OpenAPI can coexist with distinct URL namespaces and layout templates.
3. **Dev dropdown auto-registration**: When the system auto-defines the main menu, autodoc outputs are registered under **Dev** automatically, regardless of `output_prefix` configuration.
4. **Regression protection**: Add integration tests that fail if any of the above breaks.

## Non-goals

- Redesign of theme dropdown CSS/JS behavior (see `plan/drafted/plan-dropdown-refactor.md`).
- Manual menu authoring; this plan focuses on the auto-menu path.
- Changes to single-dev-asset behavior (currently shows as top-level item; Phase 2 may revisit this).

---

## Proposed work (phased)

### ✅ Phase 0 (hotfix): make Python exclude patterns safe and predictable — COMPLETED

**Status**: ✅ Complete

1. ✅ **Fixed PythonExtractor exclude matching to use proper glob semantics**
   - **File**: `bengal/autodoc/extractors/python/skip_logic.py`
   - **Implementation**: Uses `fnmatch` with path-separator-aware semantics
   - **Contract**: `*/.*` matches hidden files/dirs, not all files; existing patterns continue to work
   - **Commit**: `fix(autodoc): make python exclude patterns use glob matching; prevent */.* from skipping all files`

2. ✅ **Unit tests for exclude patterns**
   - **File**: `tests/unit/autodoc/test_python_extractor_exclude_patterns.py`
   - **Coverage**: `*/.*` pattern, `*/.venv/*`, `*_test.py`, shadowed module detection
   - **Commit**: `tests(autodoc): add unit tests for python extractor exclude patterns`

3. ⚠️ **Make "0 python elements extracted" visible in non-debug logs** — NOT YET IMPLEMENTED
   - **File**: `bengal/autodoc/orchestration/extractors.py`
   - **Change**: When `autodoc.python.enabled` and all `source_dirs` exist but extraction yields 0 elements, emit a warning with active exclude patterns
   - **Priority**: Low (nice-to-have for debugging)
   - **Commit**: `autodoc(python): warn when enabled but extraction yields 0 elements`

---

### Phase 1 (stability): Integration test coverage for Dev dropdown registration

**Priority**: High — ensures Phase 0 fix is protected and validates end-to-end behavior

1. **Integration test: auto-menu builds Dev dropdown with API Reference when python autodoc is enabled**
   - **Files**: `tests/integration/autodoc/test_dev_dropdown_registration.py` (new)
   - **Setup**: Create a minimal site with Python autodoc enabled, build it
   - **Assert**:
     - After build, `site.menu["main"]` contains an item `name == "Dev"` with a child `name == "API Reference"`
     - The API link targets `/api/` (aggregating section) or the resolved prefix root
     - Python autodoc pages are generated
   - **Evidence for current bundling logic**: `bengal/orchestration/menu.py:205-334`
   - **Commit**: `tests(autodoc): add integration test for Dev dropdown auto-registration`

2. **Integration test: autodoc creates an aggregating `/api/` section when output_prefix is `api/...`**
   - **Files**: `tests/integration/autodoc/test_aggregating_api_section.py` (new)
   - **Setup**: Configure Python autodoc with `output_prefix: "api/python"`, build site
   - **Assert**:
     - An aggregating section with `name == "api"` exists
     - The aggregating section has `metadata.type == "autodoc-hub"`
     - Python section is a child of the aggregating section
   - **Evidence for aggregating section creation**: `bengal/autodoc/orchestration/section_builders.py:324-403`
   - **Commit**: `tests(autodoc): add integration test for aggregating /api/ section`

3. **Integration test: Dev dropdown works with custom output_prefix values**
   - **Files**: `tests/integration/autodoc/test_dev_dropdown_custom_prefix.py` (new)
   - **Setup**: Configure Python autodoc with `output_prefix: "reference/python-api"`, build site
   - **Assert**:
     - Dev dropdown still includes "API Reference" link
     - Link points to correct custom prefix path
   - **Commit**: `tests(autodoc): ensure Dev dropdown registration works with custom output_prefix values`

---

### Phase 2 (maturity): Decouple Dev dropdown from hard-coded section names

**Priority**: High — removes fragility and enables custom `output_prefix` support

**Problem**: `MenuOrchestrator` currently discovers Dev links by searching for `section.name in {"api","cli"}`. This is fragile when:
- `output_prefix` values change (see `plan/drafted/plan-autodoc-output-prefix.md`)
- Sites want API docs outside `/api/`
- OpenAPI needs explicit Dev menu entry (currently only accessible via aggregating `/api/` section)

1. **Have autodoc publish "dev menu links" explicitly**
   - **Files**:
     - `bengal/autodoc/orchestration/orchestrator.py` — add method to export dev menu links
     - `bengal/core/site/core.py` — add ephemeral attribute `_autodoc_dev_links: list[dict[str, Any]] | None`
     - `bengal/orchestration/menu.py` — use `site._autodoc_dev_links` instead of searching by name
   - **Approach**:
     - `VirtualAutodocOrchestrator` tracks enabled doc types and their resolved prefixes during generation
     - Export structured list: `[{name: "Python API", url: "/api/python/", type: "python"}, ...]`
     - Include display names from config (`display_name` field) or sensible defaults
     - Menu bundler uses this list instead of `_find_section_by_name()`
   - **Design decisions**:
     - Links point to aggregating sections when they exist, otherwise to the specific output prefix root
     - OpenAPI gets explicit entry when enabled (not just via `/api/` umbrella)
   - **Commit**: `orchestration(menu): source Dev dropdown links from autodoc-provided registry; avoid hard-coded section names`

2. **Update unit tests**
   - Modify `tests/unit/orchestration/test_menu_dev_dropdown_autodoc.py` to use `_autodoc_dev_links` instead of mocking sections by name
   - **Commit**: `tests(menu): update Dev dropdown tests to use autodoc dev links registry`

3. **Integration tests for custom prefixes**
   - Extend Phase 1 tests to verify Dev dropdown works with various `output_prefix` combinations
   - Test Python + CLI + OpenAPI all enabled with custom prefixes
   - **Commit**: `tests(autodoc): ensure Dev dropdown registration works with custom output_prefix values`

---

### Phase 3 (maturity): Layout + template guarantees across 3 outputs

**Priority**: Medium — prevents template regressions but lower risk than Phase 2

1. **Contract test: each autodoc page type maps to an existing template directory**
   - **File**: `tests/unit/autodoc/test_type_template_mapping.py` (new)
   - **Evidence**: `bengal/autodoc/orchestration/utils.py:14-33` (`get_template_dir_for_type()`)
   - **Approach**: Enumerate all autodoc types (`autodoc-python`, `autodoc-cli`, `autodoc-rest`, `autodoc-hub`) and verify template directories exist in default theme
   - **Goal**: Prevent regressions where a page type is emitted but templates do not exist
   - **Commit**: `tests(rendering): add contract tests for autodoc type→template_dir mapping`

2. **Smoke render test: render 1 representative page per autodoc type**
   - **File**: `tests/integration/autodoc/test_template_rendering.py` (new)
   - **Setup**: Create minimal site with Python/CLI/OpenAPI enabled, build it
   - **Assert**:
     - Python module page renders without `TemplateNotFound` or `StrictUndefined` errors
     - CLI command page renders successfully
     - OpenAPI endpoint page renders successfully
     - Each output contains expected markers (title/header)
   - **Commit**: `tests(rendering): add autodoc smoke render tests for python/cli/openapi templates`

---

## Success criteria (ship gates)

### Phase 0 (COMPLETED)
- ✅ Python autodoc extraction works with the site's current config (including `*/.*`) and produces pages
- ✅ Unit tests cover exclude pattern edge cases

### Phase 1 (Integration tests)
- Integration test verifies auto-menu produces **Dev dropdown** containing **API Reference** when Python autodoc is enabled
- Integration test verifies aggregating `/api/` section creation
- Integration test verifies Dev dropdown works with custom `output_prefix` values

### Phase 2 (Decoupling)
- Dev dropdown links are sourced from autodoc-provided registry, not hard-coded section names
- Custom `output_prefix` values work correctly with Dev dropdown
- OpenAPI gets explicit Dev menu entry when enabled
- Unit and integration tests updated to use new registry approach

### Phase 3 (Template guarantees)
- Contract tests verify all autodoc types map to existing template directories
- Smoke render tests verify all autodoc types render without errors

---

## User-permutation support matrix (auto topbar menu)

This section enumerates the main "auto menu" permutations and whether they work **today** (current code), versus the intended target after the phases above.

### Definitions

- **Auto menu mode**: `menu.main` not configured, so `MenuOrchestrator` builds `menu.main` from sections (`bengal/orchestration/menu.py:205-373`).
- **GitHub link**: Rendered directly from `params.repo_url` unless "bundled" into Dev (`bengal/themes/default/templates/base.html:272-286`).
- **Dev dropdown**: Only created when `len(dev_assets) >= 2` (`bengal/orchestration/menu.py:246`).
- **API section detection**: Hard-coded `section.name == "api"` (`bengal/orchestration/menu.py:228`).
- **CLI section detection**: Hard-coded `section.name == "cli"` (`bengal/orchestration/menu.py:236`).

### Current behavior (post Phase 0)

- [OK] **No Dev assets** (no repo_url, no api section, no cli section): Auto menu shows discovered sections.
- [OK] **GitHub only** (repo_url set; no api, no cli): GitHub appears as a topbar link (not under Dev).
- [OK] **CLI only** (cli section exists; no repo_url; no api): CLI appears as top-level item (single dev asset doesn't create dropdown).
- [OK] **API only** (api section exists; no repo_url; no cli): API appears as top-level item (single dev asset doesn't create dropdown).
- [OK] **GitHub + CLI**: Dev dropdown is created; GitHub is bundled (top-level GitHub suppressed) and CLI appears under Dev.
- [OK] **GitHub + API**: Dev dropdown is created; GitHub is bundled and API appears under Dev.
- [OK] **API + CLI**: Dev dropdown is created with both entries.
- [PARTIAL] **OpenAPI only**: No explicit Dev entry for OpenAPI exists today; it is only reachable indirectly via an aggregating `/api/` section when output prefixes create it.
- [FRAGILE] **Custom output_prefix**: Works if section name happens to match "api" or "cli", but breaks if prefix is `reference/python-api` (section name would be "reference").

### Target behavior (post all phases)

- **Phase 1**: Integration tests verify all current permutations work correctly.
- **Phase 2**: Remove hard-coded detection (api/cli) and let autodoc publish exact "Dev links" to bundle:
  - Custom `output_prefix` values work correctly (e.g., `reference/python-api` still gets Dev entry)
  - OpenAPI gets its own explicit entry when enabled (not only via `/api/` umbrella)
  - All enabled autodoc types appear in Dev dropdown regardless of section names
- **Phase 3**: Template contract tests prevent regressions where types are emitted but templates don't exist.

---

## Implementation notes

### Phase 2: Autodoc dev links registry design

The `_autodoc_dev_links` attribute should be populated during autodoc orchestration:

```python
# In VirtualAutodocOrchestrator.run()
dev_links = []
if python_enabled:
    prefix = resolve_output_prefix("python")
    display_name = config.get("python", {}).get("display_name", "API Reference")
    dev_links.append({
        "name": display_name,
        "url": f"/{prefix}/",
        "type": "python"
    })
# Similar for CLI and OpenAPI
site._autodoc_dev_links = dev_links
```

Menu orchestrator then uses this list instead of searching by section name:

```python
# In MenuOrchestrator._build_auto_menu_with_dev_bundling()
if site._autodoc_dev_links:
    for link in site._autodoc_dev_links:
        dev_assets.append({
            "name": link["name"],
            "url": link["url"],
            "type": link["type"]
        })
```

This decouples menu generation from section naming conventions.
