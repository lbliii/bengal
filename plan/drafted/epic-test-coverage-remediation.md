# Epic: Test Coverage Remediation

**Status**: Planned  
**Created**: 2026-03-15  
**Target**: v0.3.x  
**Estimated Effort**: 40-55 hours  
**Dependencies**: None (standalone, can run in parallel with other epics)  
**Source**: Coverage Audit (2026-03-15)

---

## Why This Matters

The coverage audit identified **5 critical gaps** and **4 significant gaps** across Bengal's 214k-line source base. Despite 11,960 tests and strong coverage in rendering (1.20 ratio) and utils (1.38), several high-risk subsystems have dangerously low test-to-source ratios:

1. **Content discovery** (0.08 ratio) — the pipeline that finds and builds every page has almost no unit tests
2. **CLI commands** (0.17 ratio) — 20,866 lines of user-facing code with 3,585 lines of tests
3. **Asset pipeline** (0.10 ratio) — asset manifest and discovery nearly untested
4. **Error handling** (0.26 ratio) — untested error recovery means failure paths are unpredictable
5. **Cache core** (793-line `build_cache/core.py`) — no direct test file for the central cache module

Left unaddressed, these gaps mean regressions in page discovery, build caching, and error recovery will go undetected until users hit them. The project's `fail_under = 85` target (pytest.ini:69) is at risk.

---

## Sprint Structure

| Sprint | Focus | Effort | Risk |
|--------|-------|--------|------|
| **1** | Content discovery + cache core — the build pipeline backbone | 8-10h | Medium (needs test fixtures) |
| **2** | Error handling + error recovery paths | 6-8h | Low (isolated modules) |
| **3** | CLI commands — user-facing regression protection | 8-12h | Medium (Click testing patterns) |
| **4** | Asset pipeline + i18n + output module | 6-8h | Low |
| **5** | Autodoc orchestration + scaffolds | 6-8h | Medium (complex test setup) |
| **6** | Test infrastructure improvements | 4-6h | Low |

---

## Sprint 1: Content Discovery + Cache Core

**Goal**: Unit test coverage for the content discovery pipeline and the central build cache module.

### Task 1.1 — `bengal/content/discovery/content_discovery.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/content/discovery/content_discovery.py` |
| **Issue** | Core content discovery logic with no direct unit tests. This is the entry point for finding all markdown files in a site. |
| **Action** | Create `tests/unit/content/discovery/test_content_discovery.py`. Test: directory scanning, file filtering (`.md` vs ignored), symlink handling, nested section discovery. |
| **Fixtures** | Use `tmp_path` to create synthetic site structures. |
| **Validation** | New test file exists, passes, covers happy path + edge cases (empty dirs, nested dirs, symlinks). |

### Task 1.2 — `bengal/content/discovery/page_factory.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/content/discovery/page_factory.py` |
| **Issue** | Creates Page objects from discovered files — untested factory logic. |
| **Action** | Create `tests/unit/content/discovery/test_page_factory.py`. Test: page creation from frontmatter, `_index.md` vs regular pages, bundle pages, pages with/without dates. |
| **Validation** | Factory returns correct Page types for different inputs. |

### Task 1.3 — `bengal/content/discovery/section_builder.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/content/discovery/section_builder.py` |
| **Issue** | Builds the section tree hierarchy — no unit tests. |
| **Action** | Create `tests/unit/content/discovery/test_section_builder.py`. Test: nested section hierarchy, section ordering, root section creation, sections with `_index.md`. |
| **Validation** | Section tree matches expected hierarchy for synthetic inputs. |

### Task 1.4 — `bengal/content/discovery/directory_walker.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/content/discovery/directory_walker.py` |
| **Issue** | Filesystem traversal logic without tests. |
| **Action** | Create `tests/unit/content/discovery/test_directory_walker.py`. Test: walk order, hidden file exclusion, `.bengalignore` patterns, max depth. |
| **Validation** | Walker yields expected paths for synthetic directory trees. |

### Task 1.5 — `bengal/cache/build_cache/core.py` (793 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/cache/build_cache/core.py` |
| **Issue** | The central build cache module — 793 lines with no direct test file. Related tests exist for mixins (`test_build_cache.py`) but not the core class itself. |
| **Action** | Create `tests/unit/cache/test_build_cache_core.py`. Test: cache creation, get/set/invalidate, serialization round-trip, corruption recovery, thread safety under concurrent access. |
| **Validation** | Core cache operations work correctly, including edge cases (missing keys, corrupted data, concurrent writes). |

### Task 1.6 — `bengal/cache/build_cache/rendered_output_cache.py` (248 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/cache/build_cache/rendered_output_cache.py` |
| **Issue** | Rendered output caching with no direct tests. |
| **Action** | Create `tests/unit/cache/test_rendered_output_cache.py`. Test: cache hit/miss, invalidation on content change, stale entry cleanup. |
| **Validation** | Rendered output cache correctly detects stale entries. |

**Sprint 1 done-check**: `tests/unit/content/discovery/` has 4+ test files. `tests/unit/cache/test_build_cache_core.py` exists. All pass.

---

## Sprint 2: Error Handling + Recovery

**Goal**: Test coverage for error handling, recovery, and session tracking — the failure path safety net.

### Task 2.1 — `bengal/errors/recovery.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/errors/recovery.py` |
| **Issue** | Error recovery strategies are untested — untested recovery is worse than no recovery. |
| **Action** | Create `tests/unit/errors/test_recovery.py`. Test: each recovery strategy, fallback chains, recovery from template errors, recovery from build errors. |
| **Validation** | Each recovery strategy produces expected fallback behavior. |

### Task 2.2 — `bengal/errors/session.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/errors/session.py` |
| **Issue** | Error session tracking accumulates errors during a build — untested. |
| **Action** | Create `tests/unit/errors/test_session.py`. Test: session lifecycle (start/add/close), error deduplication, session summary generation, concurrent error additions (free-threading). |
| **Validation** | Session correctly tracks, deduplicates, and summarizes errors. |

### Task 2.3 — `bengal/errors/aggregation.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/errors/aggregation.py` |
| **Issue** | Error aggregation logic without tests. |
| **Action** | Create `tests/unit/errors/test_aggregation.py`. Test: grouping by type, grouping by file, severity ordering, threshold-based suppression. |
| **Validation** | Aggregation produces correct groups and ordering. |

### Task 2.4 — `bengal/errors/traceback/renderer.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/errors/traceback/renderer.py` |
| **Issue** | Custom traceback rendering — currently only has `test_traceback_renderer_output.py` in `tests/unit/utils/` which may not cover the renderer itself. |
| **Action** | Create `tests/unit/errors/test_traceback_renderer.py`. Test: template error formatting, nested exception chains, line highlighting, file path normalization. |
| **Validation** | Rendered tracebacks are human-readable and contain correct file:line references. |

### Task 2.5 — `bengal/errors/reporter.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/errors/reporter.py` |
| **Issue** | Error reporting (build summary, health warnings) without targeted tests. |
| **Action** | Create `tests/unit/errors/test_reporter.py`. Test: report generation, severity filtering, quiet mode suppression. |
| **Validation** | Reports match expected format for various error combinations. |

**Sprint 2 done-check**: `tests/unit/errors/` has 8+ test files (5 existing + 3-5 new). All pass.

---

## Sprint 3: CLI Commands

**Goal**: Regression protection for user-facing CLI commands.

### Task 3.1 — `bengal/cli/commands/validate.py` (464 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/cli/commands/validate.py` |
| **Issue** | The `bengal validate` command — user-facing validation with no unit tests. |
| **Action** | Create `tests/unit/cli/test_validate_command.py`. Use Click's `CliRunner`. Test: validate with clean site, validate with errors, validate with warnings, `--strict` flag, output formatting. |
| **Validation** | `CliRunner` invocations return expected exit codes and output. |

### Task 3.2 — `bengal/cli/commands/project.py` (497 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/cli/commands/project.py` |
| **Issue** | Project management commands untested. |
| **Action** | Create `tests/unit/cli/test_project_command.py`. Test: project info display, project listing, path resolution. |
| **Validation** | Commands return expected output for synthetic project structures. |

### Task 3.3 — `bengal/cli/commands/serve.py` (186 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/cli/commands/serve.py` |
| **Issue** | Dev server startup command untested. |
| **Action** | Create `tests/unit/cli/test_serve_command.py`. Test: port selection, host binding, `--open` flag handling, error on missing site directory. Mock actual server startup. |
| **Validation** | Command validates arguments correctly before server launch. |

### Task 3.4 — `bengal/cli/commands/sources.py` (299 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/cli/commands/sources.py` |
| **Issue** | Content source management commands untested. |
| **Action** | Create `tests/unit/cli/test_sources_command.py`. Test: list sources, add source, validate source config. |
| **Validation** | Source commands correctly read/write config entries. |

### Task 3.5 — `bengal/cli/commands/graph/` (~1,588 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/cli/commands/graph/` (bridges, communities, orphans, pagerank, report, suggest) |
| **Issue** | The entire graph analysis CLI — 6 command files with zero tests. |
| **Action** | Create `tests/unit/cli/test_graph_commands.py`. Test each subcommand with a mock Site object: orphans detection, bridge pages, pagerank display, community grouping, suggestion output. |
| **Validation** | Each graph subcommand returns expected output format. |

### Task 3.6 — `bengal/cli/commands/upgrade/` (~529 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/cli/commands/upgrade/` (check.py, command.py, installers.py) |
| **Issue** | Upgrade workflow commands untested. |
| **Action** | Create `tests/unit/cli/test_upgrade_commands.py`. Test: version check logic, upgrade recommendation display, installer selection. Mock network calls. |
| **Validation** | Upgrade commands correctly compare versions and suggest actions. |

**Sprint 3 done-check**: `tests/unit/cli/` has 19+ test files (13 existing + 6 new). All pass.

---

## Sprint 4: Asset Pipeline + i18n + Output

**Goal**: Close remaining critical and significant gaps in asset processing, internationalization, and output formatting.

### Task 4.1 — `bengal/assets/pipeline.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/assets/pipeline.py` |
| **Issue** | Asset processing pipeline with minimal test coverage (167 lines total in tests/unit/assets/). |
| **Action** | Expand `tests/unit/assets/test_assets_pipeline.py`. Test: asset discovery, fingerprinting, copy-to-output, CSS bundling trigger, JS bundling trigger. |
| **Validation** | Pipeline correctly processes assets from theme and content directories. |

### Task 4.2 — `bengal/assets/manifest.py`

| Field | Value |
|-------|-------|
| **Source** | `bengal/assets/manifest.py` |
| **Issue** | Asset manifest generation and lookup barely tested. |
| **Action** | Expand `tests/unit/assets/test_manifest.py`. Test: manifest generation, fingerprinted URL lookup, cache busting, manifest serialization. |
| **Validation** | Manifest maps original paths to fingerprinted URLs correctly. |

### Task 4.3 — `bengal/assets/_discovery.py` (144 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/assets/_discovery.py` |
| **Issue** | Asset discovery logic untested. |
| **Action** | Create `tests/unit/assets/test_asset_discovery.py`. Test: discovering CSS/JS/images from theme dirs, content dirs, ignoring non-asset files. |
| **Validation** | Discovery returns correct asset lists for synthetic directory layouts. |

### Task 4.4 — `bengal/i18n/catalog.py` (209 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/i18n/catalog.py` |
| **Issue** | Zero unit tests. Integration tests exist but don't isolate catalog logic. |
| **Action** | Create `tests/unit/i18n/test_catalog.py`. Test: catalog loading, message lookup, fallback to default locale, plural forms, missing translation behavior. |
| **Validation** | Catalog returns correct translations and handles missing keys gracefully. |

### Task 4.5 — `bengal/output/core.py` (848 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/output/core.py` |
| **Issue** | CLI output formatting — the largest file in the module with minimal tests. |
| **Action** | Create `tests/unit/output/test_output_core.py`. Test: progress bar rendering, summary table formatting, color/no-color mode, quiet mode suppression, verbose mode expansion. |
| **Validation** | Output functions produce expected strings for various verbosity levels. |

### Task 4.6 — `bengal/output/dev_server.py` (229 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/output/dev_server.py` |
| **Issue** | Dev server output formatting untested. |
| **Action** | Create `tests/unit/output/test_output_dev_server.py`. Test: request log formatting, rebuild notification display, error display. |
| **Validation** | Dev server messages render correctly in terminal. |

**Sprint 4 done-check**: `tests/unit/i18n/` directory exists with test files. `tests/unit/output/` has 3+ test files. `tests/unit/assets/` has 5+ test files. All pass.

---

## Sprint 5: Autodoc Orchestration + Scaffolds + Debug

**Goal**: Cover complex autodoc generation and remaining gaps.

### Task 5.1 — `bengal/autodoc/orchestration/orchestrator.py` (717 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/autodoc/orchestration/orchestrator.py` |
| **Issue** | The autodoc build orchestrator — coordinates extraction, page generation, and section building with no direct tests. |
| **Action** | Create `tests/unit/autodoc/test_orchestrator.py`. Test: full orchestration flow with mock extractors, incremental detection, error handling during extraction. |
| **Validation** | Orchestrator produces expected page/section structure from mock Python packages. |

### Task 5.2 — `bengal/autodoc/orchestration/page_builders.py` (461 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/autodoc/orchestration/page_builders.py` |
| **Issue** | Page builder for API documentation untested. |
| **Action** | Create `tests/unit/autodoc/test_page_builders.py`. Test: module page creation, class page creation, function page creation, index page generation, template selection. |
| **Validation** | Builders produce correct page structures with expected metadata. |

### Task 5.3 — `bengal/autodoc/orchestration/section_builders.py` (464 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/autodoc/orchestration/section_builders.py` |
| **Issue** | Section hierarchy builder for API docs untested. |
| **Action** | Create `tests/unit/autodoc/test_section_builders.py`. Test: nested module sections, flat vs hierarchical modes, section ordering, grouping by package. |
| **Validation** | Section tree mirrors the Python package hierarchy correctly. |

### Task 5.4 — `bengal/autodoc/base.py` (504 lines)

| Field | Value |
|-------|-------|
| **Source** | `bengal/autodoc/base.py` |
| **Issue** | Base autodoc classes with no direct tests. |
| **Action** | Create `tests/unit/autodoc/test_base.py`. Test: base extractor interface, configuration validation, source path resolution. |
| **Validation** | Base classes enforce the extractor protocol correctly. |

### Task 5.5 — Scaffold templates (995 lines across 11 files)

| Field | Value |
|-------|-------|
| **Source** | `bengal/scaffolds/` (blog, changelog, default, docs, landing, portfolio, product, resume templates) |
| **Issue** | Only 1 test file (250 lines) for 11 source files. Scaffold templates generate user sites — regressions break `bengal new`. |
| **Action** | Create `tests/unit/scaffolds/test_scaffold_templates.py`. Test each scaffold: generates expected directory structure, creates valid `bengal.yaml`, creates `_index.md`, no missing template variables. |
| **Validation** | Each scaffold produces a buildable site skeleton in `tmp_path`. |

### Task 5.6 — Debug tools (selected)

| Field | Value |
|-------|-------|
| **Source** | `bengal/debug/delta_analyzer.py`, `bengal/debug/dependency_visualizer.py`, `bengal/debug/incremental_debugger.py` |
| **Issue** | DX tools with no tests — broken debug tools waste developer time. |
| **Action** | Create `tests/unit/debug/test_delta_analyzer.py` and `tests/unit/debug/test_dependency_visualizer.py`. Test: diff generation between builds, dependency graph visualization output, taxonomy debugging output. |
| **Validation** | Debug tools produce expected output for synthetic build states. |

**Sprint 5 done-check**: `tests/unit/autodoc/` has 31+ test files (28 existing + 3 new). `tests/unit/scaffolds/` has 2+ test files. All pass.

---

## Sprint 6: Test Infrastructure

**Goal**: Improve the test suite itself — speed, organization, and reliability.

### Task 6.1 — Diagnose coverage instrumentation slowness

| Field | Value |
|-------|-------|
| **Issue** | `pytest --cov` stalls at ~45% of unit tests after 10+ minutes. Without reliable `--cov` runs, the 85% `fail_under` gate is unenforceable. |
| **Action** | Profile the test suite with `--durations=0` to find slowest tests. Check if specific test files cause the stall (likely `test_high_concurrency_stress.py` or `test_thread_safety.py` under coverage instrumentation). Consider `pytest-split` for parallelized coverage collection. |
| **Validation** | `poe test-cov` completes within 10 minutes. |

### Task 6.2 — Create missing test directories

| Field | Value |
|-------|-------|
| **Issue** | Several source modules lack corresponding test directories: `tests/unit/i18n/`, `tests/unit/output/` (only 1 file), `tests/unit/content/discovery/`. |
| **Action** | Create directory structure with `__init__.py` files: `tests/unit/i18n/__init__.py`, `tests/unit/output/__init__.py`, `tests/unit/content/discovery/__init__.py`. |
| **Validation** | `find tests/unit/ -name "__init__.py"` shows all expected directories. |

### Task 6.3 — Consolidate parser tests

| Field | Value |
|-------|-------|
| **Issue** | Parser tests split across `tests/unit/rendering/parsers/` (1,064 lines) and `tests/rendering/parsers/` (3,955 lines). The non-unit location is not covered by `poe test-unit`. |
| **Action** | Evaluate moving `tests/rendering/parsers/` into `tests/unit/rendering/parsers/` or `tests/integration/`. Document the decision. |
| **Validation** | All parser tests are discoverable by `poe test-unit` or `poe test-integration`. |

### Task 6.4 — Add coverage CI gate

| Field | Value |
|-------|-------|
| **Issue** | The `fail_under = 85` in pytest.ini is only enforced if `--cov` is used. The `ci` task sequence in pyproject.toml runs `lint → ty → test` without `--cov`. |
| **Action** | Add a `test-cov-check` poe task that runs `pytest --cov=bengal --cov-fail-under=85`. Add to CI sequence after Task 6.1 resolves performance. |
| **Validation** | CI fails if coverage drops below 85%. |

**Sprint 6 done-check**: `poe test-cov` completes within 10 minutes. All new test directories exist. Parser tests are consolidated.

---

## Progress Tracking

| Sprint | Status | Tests Added | Source Lines Covered |
|--------|--------|-------------|---------------------|
| 1 — Content Discovery + Cache | Done | 62 tests | ~2,800 lines |
| 2 — Error Handling | Not Started | — | ~2,500 lines |
| 3 — CLI Commands | Not Started | — | ~3,500 lines |
| 4 — Assets + i18n + Output | Not Started | — | ~2,200 lines |
| 5 — Autodoc + Scaffolds + Debug | Not Started | — | ~3,700 lines |
| 6 — Test Infrastructure | Not Started | — | (meta) |

---

## Success Criteria

1. **Coverage target met**: `pytest --cov=bengal --cov-fail-under=85` passes
2. **Zero untested critical paths**: Content discovery, cache core, and error recovery all have unit tests
3. **CLI regression protection**: All user-facing commands have at least smoke-level unit tests
4. **CI enforcement**: Coverage gate runs in CI pipeline
5. **Test suite health**: Full `--cov` run completes in < 10 minutes

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Tests too tightly coupled to implementation | Write behavioral tests (assert outcomes, not internals). Use protocols/interfaces as test boundaries. |
| Test fixtures too complex | Reuse existing `tests/roots/` fixtures. Create shared factory helpers in `tests/_testing/`. |
| Coverage run too slow for CI | Use `pytest-split` to parallelize. Profile and fix slow tests first (Sprint 6). |
| Mocking hides real bugs | Prefer `tmp_path` synthetic sites over mocks where feasible. Reserve mocks for I/O and network. |
