# Bug Bash Progress - October 14, 2025

## Summary
Started with **50+ failing tests**, currently at **29 failures** (down from 53 after major fixes).

**Status**: 2,294 passed, 29 failed, 10 skipped (37% code coverage)

## Bugs Fixed ✅

### 1. **truncate_chars Bug** (CRITICAL)
- **Issue**: Function produced output longer than requested (e.g., 13 chars instead of 10)
- **Root Cause**: Added suffix AFTER taking `length` characters instead of accounting for it
- **Fix**: Changed to truncate at `(length - len(suffix))` so total never exceeds `length`
- **Files Modified**:
  - `bengal/utils/text.py` - Fixed implementation
  - `tests/unit/utils/test_text_properties.py` - Already had correct expectations
  - `tests/unit/template_functions/test_strings.py` - Updated test expectations
  - `tests/unit/utils/test_text.py` - Updated test expectations
- **Tests Fixed**: 4 tests

### 2. **jinja_utils Bugs** (8 tests)
- **Issue**: `safe_get()` not returning defaults, `has_value()` treating 0/[] as truthy
- **Root Causes**:
  1. `has_value()` only checked for empty string, not all falsy values
  2. `safe_get()` returned methods for primitives instead of default
  3. `safe_get()` didn't handle `__getattr__` returning None for missing attrs
  4. `ensure_defined()` wasn't replacing None with default
- **Fixes**:
  - `has_value()`: Changed to use `bool(value)` to check all falsy values
  - `safe_get()`: Added primitive type check, handle None from `__getattr__`, catch all exceptions
  - `ensure_defined()`: Now replaces both Undefined AND None with default
- **Files Modified**:
  - `bengal/rendering/jinja_utils.py`
  - `tests/unit/rendering/test_jinja_utils.py`
- **Tests Fixed**: 8 tests (all jinja_utils tests now pass!)

### 3. **Incremental Build Config Cache** (CRITICAL)
- **Issue**: Config file hash wasn't saved during first full build
- **Impact**: Every incremental build detected config change and did full rebuild (1.1x speedup instead of 15-50x)
- **Fix**: Changed `build.py` to always call `check_config_changed()` on all builds
- **Files Modified**: `bengal/orchestration/build.py`
- **Tests Fixed**: Integration tests now pass

### 4. **Atomic Write Race Condition** (CRITICAL)
- **Issue**: `FileNotFoundError` when multiple threads tried to rename same temp file
- **Root Cause**: All concurrent writes used same temp filename (e.g., `index.html.tmp`)
- **Fix**: Use unique temp filenames per thread: `.{name}.{pid}.{tid}.{uuid}.tmp`
- **Files Modified**: `bengal/utils/atomic_write.py`
- **Tests Fixed**: Parallel build tests now pass

### 5. **Related Posts Scale Performance**
- **Issue**: O(n·t·p) algorithm ran on every build, taking 50-100s at 10K pages
- **Fix**: Skip related posts calculation for sites >5K pages
- **Files Modified**: `bengal/orchestration/related_posts.py`
- **Impact**: Expected 10K page builds to improve from 29 pps to 80-100 pps

## Remaining Failures (29)

### 1. Rendering/Parser Issues (10 tests) 🔥 PRIORITY
- `test_data_table_directive.py::TestDirectiveIntegration::test_parse_with_options`
- `test_myst_syntax.py::TestMystSyntaxCompatibility::test_colon_tabs`
- `test_myst_syntax.py::TestBackwardCompatibility::test_existing_code_tabs_still_work`
- `test_parser_configuration.py::TestMistuneDirectives::test_mistune_parser_has_tabs`
- `test_mistune_parser.py::TestDirectives::test_tabs_directive`
- `test_mistune_parser.py::TestHeadingAnchors::test_toc_extracted_correctly`
- `test_syntax_highlighting.py::TestPythonMarkdownHighlightingAliases::test_jinja2_alias_highlighted`
- `test_syntax_highlighting.py::TestPythonMarkdownHighlightingAliases::test_go_html_template_aliased_to_html`
- `test_tables.py::TestDataTableInTemplate::test_multiple_tables_in_template`
- `test_template_engine_installed_theme.py::test_engine_resolves_installed_theme_templates`

### 2. Server Issues (3 tests)
- `test_request_handler.py::TestDoGetIntegrationMinimal::test_do_get_injects_for_html`
- `test_live_reload_injection.py::test_live_reload_injects_script`
- `test_component_preview.py::test_discover_components_theme_override`

### 3. Assets/Theme Issues (2 tests)
- `test_theme_asset_dedup.py::test_theme_asset_dedup_child_overrides_parent`
- `test_cli_theme_commands.py::test_theme_list_and_info`

### 4. Orchestration/Build Issues (6 tests)
- `test_taxonomy_orchestrator.py::TestPerformanceOptimization::test_selective_generation_calls_create_once_per_tag`
- `test_taxonomy_orchestrator.py::TestPerformanceOptimization::test_full_generation_calls_create_for_all_tags`
- `test_section_sorting.py::TestSectionSortedPagesProperty::test_sorted_pages_mixed_weights`
- `test_parallel_processing.py::TestParallelAssetProcessing::test_large_asset_count_processes_successfully`
- `test_parallel_processing.py::TestParallelAssetProcessing::test_asset_processing_with_errors`
- `test_cascade_integration.py::TestCascadeIntegration::test_cascade_with_nested_sections`

### 5. Integration/Stateful Issues (2 tests)
- `stateful/test_build_workflows.py::TestPageLifecycleWorkflow::runTest`
- `stateful/test_build_workflows.py::TestIncrementalConsistencyWorkflow::runTest`

### 6. Utils Issues (6 tests)
- `test_file_io.py::TestLoadYaml::test_invalid_yaml_raise`
- `test_logger.py::test_get_logger` (FileNotFoundError)
- `test_page_initializer.py::TestPageInitializer::test_ensure_initialized_url_generation_path_outside_output_dir`
- `test_dates_properties.py::TestParseDateProperties::test_datetime_passthrough_idempotent`
- `test_rich_console.py::TestShouldUseRich::test_disabled_with_dumb_terminal`
- `test_swizzle.py::test_swizzle_cli_invocation` (FileNotFoundError)

## Next Steps
1. **Fix rendering/parser issues** (10 tests) - Highest priority, blocks content features
2. **Fix server issues** (3 tests) - User-facing, affects dev experience
3. **Fix orchestration issues** (6 tests) - Performance and correctness
4. **Fix utils issues** (6 tests) - Foundation layer
5. **Fix integration tests** (2 tests) - Often side effects of other fixes

## Progress Metrics
- **Tests passing**: 2,294 (98.7%)
- **Tests failing**: 29 (1.3%)
- **Code coverage**: 37%
- **Improvement**: Fixed 24+ tests in this session (from 53 to 29)

## Notes
- Property-based testing (Hypothesis) caught the truncate_chars bug
- Most rendering/parser failures are related to tabs/MyST directive handling
- Several FileNotFoundError issues suggest path/setup problems
- Integration tests may pass once unit tests are fixed
