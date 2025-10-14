# Bug Tracking - October 14, 2025

**Test Results:** 55 failures, 2,267 passed, 10 skipped (97.6% pass rate)  
**Code Coverage:** 67%  
**Linter Status:** ✅ Clean

---

## Priority 1: CRITICAL - Rich LiveError (20 failures) ✅ **FIXED**

### Issue
`rich.errors.LiveError: Only one live display may be active at once`

Multiple Rich `Progress` or `Live` displays being created without proper cleanup, causing nested or parallel progress bars to conflict.

**STATUS: RESOLVED** - 19/20 tests now passing. The remaining 1 failure is due to a different issue (log file corruption)

### Root Cause
The `LiveProgressManager` or Rich `Progress` contexts aren't being properly managed when:
- Running multiple builds in sequence (tests)
- Parallel rendering with progress displays
- Progress manager not cleaned up between builds

### Affected Files
- `bengal/orchestration/render.py:320` (`_render_sequential_with_progress`)
- `bengal/orchestration/render.py:426` (`_render_parallel_with_progress`)
- `bengal/utils/live_progress.py` (likely cleanup issue)

### Failing Tests (20)
**Integration - Full to Incremental Sequence (7)**
- `test_full_build_saves_cache`
- `test_incremental_after_full_build`
- `test_incremental_single_page_change`
- `test_config_change_triggers_full_rebuild`
- `test_first_incremental_build_no_cache`
- `test_multiple_incremental_builds`
- `test_cache_survives_site_reload`

**Integration - Logging (11)**
- `test_basic_logging_during_build`
- `test_all_phases_logged`
- `test_phase_timings_captured`
- `test_content_discovery_logging`
- `test_nested_phase_tracking`
- `test_logging_with_incremental_build`
- `test_warning_logging`
- `test_log_file_format`
- `test_verbose_vs_normal_mode`

**Integration - Stateful Workflows (2)**
- `TestPageLifecycleWorkflow::runTest`
- `TestIncrementalConsistencyWorkflow::runTest` (also has hash mismatch issue)

### Fix Strategy
1. ✅ Add proper cleanup in `LiveProgressManager.__exit__`
2. ✅ Check for existing live display before creating new one
3. ✅ Ensure progress contexts are properly closed in error cases
4. ✅ Add test fixtures to ensure progress cleanup between tests

### Fixes Applied
1. **LiveProgressManager cleanup** (`bengal/utils/live_progress.py:138-147`): Added `finally` block to ensure `self.live = None` after exit, fully releasing the Live display
2. **Detection helper** (`bengal/utils/rich_console.py:132-142`): Added `is_live_display_active()` function to check if a Live display is currently active on the console
3. **Guards in render orchestrator** (`bengal/orchestration/render.py:166-169, 253-256`): Added checks to prevent creating Progress bars when a Live display is already active
4. **Test cleanup fixture** (`tests/conftest.py:173-192`): Added `reset_console_between_tests()` autouse fixture that calls `reset_console()` after each test to ensure clean state

### Test Results
- **Before fix:** 20 failing tests with Rich LiveError
- **After fix:** 19 tests passing, 1 test failing due to unrelated log file corruption issue
- **Success rate:** 95% of Rich LiveError issues resolved

---

## Priority 2: HIGH - Parser & Rendering Issues (13 failures)

### Issue 1: Code Blocks Not Highlighted in Directives
Code blocks inside cards, tabs, and other directives aren't being syntax highlighted.

**Affected Tests (3)**
- `test_code_in_card` - Code in card directive not highlighted
- `test_tab_with_code_blocks` - Code in tab directive not highlighted  
- `test_colon_tabs` - MyST-style tabs with code not highlighted

**Symptoms:**
- Expected: `'def hello' in output` or `'<span class="k">'` (syntax spans)
- Actual: Raw text or improperly rendered code

**Root Cause:**
Directive content processing may not be running through markdown parser or Pygments highlighting.

**Files to Check:**
- `bengal/rendering/plugins/cards.py`
- `bengal/rendering/plugins/tabs.py`
- `bengal/rendering/pipeline.py` (directive processing order)

### Issue 2: Mistune Parser - Missing TOC & Heading Anchors
The Mistune parser isn't generating headerlinks or proper TOC anchors.

**Affected Tests (3)**
- `test_code_blocks` - Language class not in output
- `test_parse_with_toc` - Missing `class="headerlink"`
- `test_headerlink_anchors_injected` - Anchors not injected

**Expected Behavior:**
```html
<h2 id="section-1">
  Section 1
  <a class="headerlink" href="#section-1" title="Permalink">¶</a>
</h2>
```

**Actual Behavior:**
```html
<h2 id="section-1">Section 1</h2>
```

**Root Cause:**
Mistune renderer not applying headerlink plugin or TOC generation.

**Files to Check:**
- `bengal/rendering/parsers/mistune.py`
- Missing Mistune plugin configuration

### Issue 3: Parser Selection Defaulting Incorrectly
Test expects Python-Markdown as default, but Mistune is being used.

**Affected Test:**
- `test_python_markdown_parser_default`

**Assertion:**
```python
assert isinstance(pipeline.parser, PythonMarkdownParser)
# Actually getting: MistuneParser
```

**Fix:**
Check `bengal/rendering/pipeline.py` parser selection logic and default configuration.

### Issue 4: Syntax Highlighting Aliases Not Working
Jinja2 and go-html-template aliases not being recognized.

**Affected Tests (2)**
- `test_jinja2_alias_highlighted` - Not highlighting Jinja2
- `test_go_html_template_aliased_to_html` - Not aliasing to HTML

**Expected:** Highlighted code with `<div class="highlight">` and syntax spans
**Actual:** Raw markdown code block syntax in output

**Files to Check:**
- `bengal/rendering/pygments_cache.py`
- Lexer alias configuration

### Issue 6: Data Table Error Messages
Wrong error message for unsupported format.

**Affected Test:**
- `test_load_unsupported_format`
- Expected: 'unsupported' in error
- Actual: 'file not found: data/file.txt'

**Files to Check:**
- `bengal/rendering/plugins/data_table.py` - Error handling logic

### Issue 7: Data Table Directive Options
Directive not parsing correctly.

**Affected Test:**
- `test_parse_with_options`
- Assertion: `assert True is False` (test is broken or feature not working)

**Files to Check:**
- `bengal/rendering/plugins/data_table.py`

---

## Priority 3: MEDIUM - Theme & Template Issues (7 failures)

### Issue 1: Theme Asset Deduplication
Child theme not properly overriding parent theme assets.

**Affected Test:**
- `test_theme_asset_dedup_child_overrides_parent`
- Error: `FileNotFoundError: .bengal-build.log`

**Root Cause:**
Build log not being created, or theme asset resolution not working.

**Files to Check:**
- `bengal/orchestration/asset.py`
- `bengal/utils/theme_resolution.py`

### Issue 2: Theme Inheritance Chain
Template resolution broken for theme chains.

**Affected Test:**
- `test_theme_chain_child_overrides_parent`
- Error: `AttributeError: 'DummySite' object has no attribute 'output_dir'`

**Root Cause:**
Test mock or actual Site object missing required attributes.

**Files to Check:**
- `bengal/rendering/template_engine.py`
- Test setup in `test_theme_inheritance.py`

### Issue 3: Installed Theme Templates
Engine can't resolve installed theme templates.

**Affected Test:**
- `test_engine_resolves_installed_theme_templates`
- Error: `jinja2.exceptions.UndefinedError: 'page' is undefined`

**Root Cause:**
Template found but context not set up properly, or wrong template being used.

**Files to Check:**
- `bengal/rendering/template_engine.py`
- `bengal/utils/theme_resolution.py`

### Issue 4: Component Preview Theme Override
Not finding child theme components.

**Affected Test:**
- `test_discover_components_theme_override`
- Expected: 'Child Button'
- Actual: 'Parent Button'

**Root Cause:**
Component discovery not respecting theme inheritance order.

**Files to Check:**
- `bengal/server/component_preview.py`

### Issue 5: Swizzle CLI
Template not found in theme chain.

**Affected Test:**
- `test_swizzle_cli_invocation`
- Error: `FileNotFoundError: Template not found in theme chain: partials/demo.html`

**Files to Check:**
- `bengal/utils/swizzle.py`
- `bengal/cli/commands/theme.py`

### Issue 6: Theme List Command
Not showing installed themes.

**Affected Test:**
- `test_theme_list_and_info`
- Expected: 'acme' in output
- Actual: Shows only bundled themes

**Files to Check:**
- `bengal/cli/commands/theme.py`
- `bengal/utils/theme_registry.py`

### Issue 7: Theme Package Entry Points
Entry point discovery not working.

**Affected Test:**
- `test_get_installed_themes_discovers_entry_point`
- Assertion: `templates_exists()` returns False

**Root Cause:**
Mock entry points not being properly discovered or templates directory check failing.

**Files to Check:**
- `bengal/utils/theme_registry.py`

---

## Priority 4: MEDIUM - Asset Processing Issues (5 failures)

### Issue 1: Asset Minification Hints
Not detecting minification opportunities.

**Affected Test:**
- `test_asset_validator_minification_hints`
- Assertion: `assert False = any(<generator>)`

**Root Cause:**
Validator not generating hints or logic broken.

**Files to Check:**
- `bengal/health/validators/assets.py`

### Issue 2: Parallel Asset Processing Threshold
Small asset counts using parallel instead of sequential.

**Affected Test:**
- `test_small_asset_count_uses_sequential`
- Expected: 2+ assets output
- Actual: 1 asset output

**Root Cause:**
Parallel processing threshold logic incorrect or assets not being processed.

**Files to Check:**
- `bengal/orchestration/asset.py`
- `bengal/core/parallel_processing.py` (if exists)

### Issue 3: Large Asset Count Processing
Not processing all assets.

**Affected Tests (2)**
- `test_large_asset_count_processes_successfully`
- `test_asset_processing_with_errors`
- Expected: 18 assets output
- Actual: 5 assets output

**Root Cause:**
Parallel processing dropping assets or not completing.

**Files to Check:**
- `bengal/orchestration/asset.py`
- `bengal/assets/pipeline.py`

---

## Priority 5: MEDIUM - Data & Orchestration Issues (8 failures)

### Issue 1: Section Sorted Pages with Mixed Weights
Incorrect sort order when pages have mixed weight values.

**Affected Test:**
- `test_sorted_pages_mixed_weights`
- Expected: Page 'Alpha' 
- Actual: Page 'Beta'

**Root Cause:**
Sorting algorithm not handling None/0 weights correctly.

**Files to Check:**
- `bengal/core/section.py` (`sorted_pages` property)

### Issue 2: Section Finalization Without Index
Wrong template being selected.

**Affected Tests (2)**
- `test_finalize_section_without_index`
- `test_archive_page_metadata`
- Expected: 'archive.html'
- Actual: 'blog/list.html'

**Root Cause:**
Template selection logic for sections without index pages.

**Files to Check:**
- `bengal/orchestration/section.py`

### Issue 3: Taxonomy Orchestrator Not Creating Tag Pages
`_create_tag_pages` method never called.

**Affected Tests (2)**
- `test_selective_generation_calls_create_once_per_tag`
- `test_full_generation_calls_create_for_all_tags`
- Expected: Mock called 1/3 times
- Actual: Mock called 0 times

**Root Cause:**
Method renamed, removed, or orchestration flow changed.

**Files to Check:**
- `bengal/orchestration/taxonomy.py`
- Check if `_create_tag_pages` exists or was refactored

### Issue 4: Incremental Build Cache Initialization
Mock cache doesn't have expected attributes.

**Affected Tests (2)**
- `test_initialize_with_cache_enabled`
- `test_check_config_changed_file_exists`
- Errors: OSError read-only filesystem, AttributeError `file_hashes`

**Root Cause:**
Test mocks not matching actual BuildCache structure.

**Files to Check:**
- `tests/unit/orchestration/test_incremental_orchestrator.py`
- `bengal/cache/build_cache.py`

### Issue 5: Content Discovery Sorting
Nested section not being created.

**Affected Test:**
- `test_discover_sorts_nested_sections_recursively`
- Assertion: `assert None is not None` (section doesn't exist)

**Root Cause:**
Section discovery not creating nested sections properly.

**Files to Check:**
- `bengal/discovery/content_discovery.py`

### Issue 6: Incremental vs Full Build Output Mismatch
Different content hashes for same site.

**Affected Test:**
- `TestIncrementalConsistencyWorkflow::runTest`
- Different SHA256 hashes for `llm-full.txt` between incremental and full builds

**Root Cause:**
Non-deterministic output (timestamps, ordering) or incremental build missing updates.

**Files to Check:**
- `bengal/postprocess/special_pages.py` (llm-full.txt generation)
- Build ordering/determinism

---

## Priority 6: LOW - Server & Utility Issues (2 failures)

### Issue 1: Live Reload Injection
Script not being injected into HTML.

**Affected Test:**
- `test_live_reload_injects_script`
- Assertion: `assert False is True`

**Files to Check:**
- `bengal/server/live_reload.py`
- Injection logic

### Issue 2: Request Handler
Missing `requestline` attribute.

**Affected Test:**
- `test_do_get_injects_for_html`
- Error: `AttributeError: 'BengalRequestHandler' object has no attribute 'requestline'`

**Root Cause:**
Test not properly initializing request handler mock.

**Files to Check:**
- `tests/unit/server/test_request_handler.py`

### Issue 3: Rich Console Should Use Rich
Test expects rich to be disabled with TERM=dumb.

**Affected Test:**
- `test_disabled_with_dumb_terminal`
- Expected: False
- Actual: True

**Files to Check:**
- `bengal/utils/rich_console.py`
- Environment detection logic

### Issue 4: Template Function - Multiple Tables
Count wrong for multiple data tables in template.

**Affected Test:**
- `test_multiple_tables_in_template`
- Expected: 2 tables
- Actual: 8 instances of 'bengal-data-table'

**Root Cause:**
Test counting all occurrences instead of unique tables, or tables being duplicated.

**Files to Check:**
- `bengal/rendering/template_functions/tables.py`
- Test assertion logic

### Issue 5: YAML Loading Exception Handling
Wrong exception type raised.

**Affected Test:**
- `test_invalid_yaml_raise`
- Expected: Custom exception
- Actual: `yaml.parser.ParserError`

**Files to Check:**
- `bengal/utils/file_io.py`
- Exception wrapping

### Issue 6: Page Initializer Warning
Warning not being output for URL generation issue.

**Affected Test:**
- `test_ensure_initialized_url_generation_path_outside_output_dir`
- Expected: 'Warning' in output
- Actual: Empty output

**Files to Check:**
- `bengal/utils/page_initializer.py`
- Warning emission

---

## Summary by Category

| Category | Count | Priority |
|----------|-------|----------|
| Rich LiveError | 20 | CRITICAL |
| Parser/Rendering | 13 | HIGH |
| Theme/Template | 7 | MEDIUM |
| Asset Processing | 5 | MEDIUM |
| Data/Orchestration | 8 | MEDIUM |
| Server/Utility | 2 | LOW |
| **TOTAL** | **55** | |

---

## Recommended Fix Order

1. **Fix Rich LiveError** (P1) - Unblocks 20 tests, most critical
   - Add cleanup to `LiveProgressManager`
   - Check for existing displays before creating
   - Add test cleanup fixtures

2. **Fix Mistune Parser Issues** (P2) - Core functionality
   - Add headerlink plugin
   - Configure TOC generation
   - Fix code block rendering

3. **Fix Code in Directives** (P2) - Important feature
   - Ensure directive content runs through markdown parser
   - Test with cards, tabs, admonitions

4. **Fix Asset Processing** (P3) - Performance feature
   - Debug parallel processing logic
   - Check asset pipeline completion

5. **Fix Theme Issues** (P3) - Important but less critical
   - Theme resolution chain
   - Component discovery
   - Entry point discovery

6. **Fix Data/Orchestration** (P3) - Edge cases
   - Section sorting
   - Taxonomy page creation
   - Incremental build determinism

7. **Fix Low Priority Issues** (P4) - Nice to have
   - Server testing issues
   - Warning messages
   - Exception wrapping

---

## Next Steps

- [ ] Create feature branches for each priority level
- [ ] Start with Rich LiveError fix
- [ ] Create tests to prevent regression
- [ ] Document fixes in CHANGELOG.md
- [ ] Move this file to `plan/completed/` when done

