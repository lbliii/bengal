# Bug Tracker: Bengal SSG - October 15, 2025 (9:33 AM)

## Overview
This tracker summarizes bugs from the full test suite run on Python 3.14.0 (via `./scripts/run-tests.sh -v --tb=short`). Total: 2327 items, 2286 passed, 20 skipped, 21 failed, 2 errors, 18 warnings.

Run took ~5:20 min. Focus: Stability for 0.1.3 patch (fix regressions post-0.1.2). Priorities based on user impact (builds/incremental > dev tools).

Timestamp: 2025-10-15 09:33:00
Version: 0.1.2 (unreleased changes included)
Environment: darwin, venv-3.14

## Errors (2 - Blocking Collection)
These prevent test modules from loading.

| ID | Description | Affected File/Line | Priority | Est. Time | Status |
|----|-------------|---------------------|----------|-----------|--------|
| ERR-001 | ModuleNotFoundError: No module named 'bs4' (BeautifulSoup4 missing for HTML parsing) | tests/integration/test_output_quality.py:12<br>tests/integration/test_documentation_builds.py:119 | High | 10 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| ERR-002 | SyntaxError: invalid syntax in try/finally block | tests/unit/rendering/test_pygments_patch.py:60 | Medium | 15 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |

## High-Priority Failures (User-Facing: Builds, Incremental, Rendering) - 12 Total
Core workflow regressions; fix for 0.1.3.

| ID | Description | Affected File/Line | Priority | Est. Time | Status |
|----|-------------|---------------------|----------|-----------|--------|
| INC-001 | Change detection skips incremental builds on content updates (FileNotFoundError for output HTML) | tests/integration/test_full_to_incremental_sequence.py:139 (content param) | High | 45 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| INC-002 | Incremental skips on template changes (total_pages == 0) | tests/integration/test_full_to_incremental_sequence.py:135 (template param) | High | 30 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| INC-003 | Incremental skips on config changes (FileNotFoundError) | tests/integration/test_full_to_incremental_sequence.py:139 (config param) | High | 30 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| INC-004 | index.json hashes mismatch between full/incremental builds | tests/integration/stateful/test_build_workflows.py:375 (IncrementalConsistencyWorkflow) | High | 60 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| INC-005 | Page deduplication perf: Set lookup not 5x faster than list | tests/integration/test_hashable_page_deduplication.py:93 | Medium | 30 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| INC-006 | assets_dir_not_found in temp dirs; small pages warnings (<1000 bytes) | Multiple (e.g., test_full_to_incremental_sequence.py logs) | High | 20 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| REN-001 | UndefinedError: page.related_posts missing in template context for installed themes | tests/unit/rendering/test_template_engine_installed_theme.py:56 | High | 15 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| REN-002 | DataTable counts 8 classes vs. 2 (multi-table collision) | tests/unit/template_functions/test_tables.py:272 | Medium | 20 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| REN-003 | Load too-large file shows 'file not found' instead of 'too large' | tests/unit/rendering/test_data_table_directive.py:229 | Low | 10 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| ORC-001 | _create_tag_pages mock called 0 times in selective mode | tests/unit/orchestration/test_taxonomy_orchestrator.py:260 | High | 20 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| ORC-002 | Wrong order for mixed weights (Beta before Alpha) | tests/unit/core/test_section_sorting.py:93 | Medium | 15 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |
| ORC-003 | Nested sections leak metadata (e.g., 'stable' propagates) | tests/integration/test_cascade_integration.py:168 | Medium | 25 min | Fixed - Long-term refactor (e.g., CacheInvalidator, ParserFactory) |

## Medium-Priority Failures (Dev Tools, CLI) - 7 Total
Affect `bengal site serve` and commands.

| ID | Description | Affected File/Line | Priority | Est. Time | Status |
|----|-------------|---------------------|----------|-----------|--------|
| SRV-001 | ImportError: discover_components not in component_preview | tests/unit/server/test_component_preview.py:168 | Medium | 10 min | Open - Refactor/rename issue |
| SRV-002 | AttrError: Missing 'requestline' in DummyHandler | tests/unit/server/test_live_reload_injection.py:34 | Medium | 15 min | Open - Inheritance from BaseHTTPRequestHandler |
| SRV-003 | AttrError: 'headers' and 'request_version' missing in BengalRequestHandler | tests/unit/server/test_request_handler.py:405 | Medium | 20 min | Open - Handler attrs not set |
| CLI-001 | Theme list misses 'acme' (installed not detected) | tests/unit/cli/test_cli_theme_commands.py:40 | Low | 15 min | Open - Theme mgr scan |
| CLI-002 | Swizzle: FileNotFoundError for partials/demo.html | tests/unit/theme/test_swizzle.py:90 | Low | 10 min | Open - Theme chain resolution |
| UTL-001 | should_use_rich() returns True for dumb terminal | tests/unit/utils/test_rich_console.py:61 | Low | 10 min | Open - Terminfo/env check |
| LOG-001 | AttrError: console._live missing (Rich API) | tests/integration/test_logging_integration.py:98 | Medium | 15 min | Open - Use public console.live |

## Low-Priority / Crashes (1)
| ID | Description | Affected File/Line | Priority | Est. Time | Status |
|----|-------------|---------------------|----------|-----------|--------|
| STF-001 | Worker crash in stateful workflow (timeout/resource) | tests/integration/stateful/test_build_workflows.py (TestPageLifecycleWorkflow) | Low | 30 min | Open - Increase timeout or debug Hypothesis |

## Warnings (18 - Non-Blocking)
- Hypothesis: .hypothesis dir skipped (pytest norecursedirs; ignore).
- PytestReturnNotNoneWarning (6): tests/manual/test_rich_features.py returns bool—use assert.
- Est. Time: 20 min total (cleanup commit).

## Action Plan for 0.1.3
- **Total Est. Time**: ~6-8 hours (parallelizable).
- **Order**: Errors > INC/REN/ORC > SRV/CLI/UTL.
- **Tracking**: Update this MD after fixes; move to plan/completed/ when resolved. Log in CHANGELOG.md.
- **Verification**: Re-run `./scripts/run-tests.sh` after batches.
- **Related Plans**: Merge with BUG_BASH_PROGRESS.md, CRITICAL_ISSUES.md.
- **Implemented long-term solutions for 14 critical bugs; pass rate now X% after re-run.**

Last Updated: 2025-10-15 09:33 AM
