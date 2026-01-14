# RFC: Warm Build Integration Test Expansion

## Status: Draft
## Created: 2026-01-13
## Updated: 2026-01-13

---

## Summary

**Problem**: Bengal's warm build (incremental) test coverage is solid for core scenarios but has gaps in navigation warm builds, data file changes, deep template inheritance chains, and cross-feature interactions.

**Solution**: Expand integration test suite with 5 new test files and extend 2 existing files to cover navigation, data files, template chains, additional output formats, edge cases, and cross-feature interactions.

**Impact**: Prevent regression bugs in production CI builds and dev server workflows where incremental builds are the norm.

---

## Problem Statement

### What is a "Warm Build"?

A warm build is an incremental build where:
1. Cache exists from a previous build (`.bengal/cache.json.zst`)
2. Some source files have changed
3. Bengal must correctly identify what to rebuild

Warm builds are the **default experience** for users:
- Dev server: Every save triggers a warm build
- CI pipelines: Cache restored → incremental build
- Production: Content updates trigger partial rebuilds

### Current State

**Well-tested scenarios** (✅):
- CSS/JS fingerprint changes → page rebuild
- Full → incremental transitions
- Cache/output mismatch (CI restore scenarios)
- Autodoc output missing detection
- Section cascade changes
- Page lifecycle (Hypothesis stateful tests)
- index.json generation and PageProxy transparency
- Tag membership change detection via TaxonomyIndex

**Partially tested scenarios** (🟡):
- Taxonomy (tags/categories) - membership changes tested, but not end-to-end HTML output
- Output formats - index.json tested, but not RSS/sitemap/llm-full.txt
- Template changes - basic detection tested, but not deep inheritance chains

**Untested scenarios** (❌):
- Navigation/menu changes in warm builds
- Data file changes (data/*.yaml)
- Deep template inheritance (3+ levels)
- RSS/Atom feed regeneration
- Sitemap regeneration
- llm-full.txt updates
- Cross-feature interactions
- Edge cases (empty site, batch changes, deep nesting)

### Why This Matters

Each untested scenario represents a potential production bug:

```
User Experience:
1. Edit blog post, add new tag
2. Run `bengal build` (warm)
3. Tag page doesn't include new post → 🐛 BUG

CI Experience:
1. Cache restored from previous run
2. Menu config changed (new section added)
3. Nav shows old structure → 🐛 BUG
```

---

## Current Test Coverage Analysis

### Existing Warm Build Tests (Core)

| File | Scenarios | Lines |
|------|-----------|-------|
| `test_warm_build_virtual_page_assets.py` | CSS/JS fingerprints, CI cache restore | 331 |
| `test_full_to_incremental_sequence.py` | Content/template/config changes | 297 |
| `test_incremental_cache_stability.py` | Cache consistency, autodoc output | 836 |
| `test_incremental_section_stability.py` | Section cascades, URL stability | 429 |
| `stateful/test_build_workflows.py` | Hypothesis page lifecycle | 476 |

**Core Total**: 2,369 lines across 5 files

### Existing Related Tests (Feature-Specific)

| File | Scenarios | Lines |
|------|-----------|-------|
| `test_incremental_output_formats.py` | index.json generation, PageProxy transparency | 515 |
| `test_phase2c2_incremental_tags.py` | TaxonomyIndex membership tracking | 347 |
| `test_incremental_observability.py` | Template change detection logging | ~200 |
| `test_nav_tree_integration.py` | NavTree versioned builds (not warm-build specific) | 297 |

**Related Total**: ~1,359 lines across 4 files

**Grand Total**: ~3,728 lines of incremental build test coverage

### Coverage Gaps by Feature

```yaml
Navigation System:
  tested: false
  risk: HIGH
  existing_tests: none
  gaps:
    - Menu config changes → page rebuild
    - Nav weight changes → ordering updates
    - Section add/remove from menu
    - Nested menu updates
    - Breadcrumb parent title changes

Taxonomy System:
  tested: partial  # TaxonomyIndex membership tracking exists
  risk: MEDIUM
  existing_tests:
    - test_phase2c2_incremental_tags.py (membership change detection)
  gaps:
    - End-to-end HTML output verification
    - Category rename scenarios
    - Taxonomy term page content changes
    - Last-page-with-tag deletion

Data Files:
  tested: false
  risk: MEDIUM
  existing_tests: none
  gaps:
    - data/*.yaml changes → dependent page rebuild
    - Data file deletion handling
    - Nested data structure changes
    - New data file availability

Template Inheritance:
  tested: partial  # Basic template change detection exists
  risk: MEDIUM
  existing_tests:
    - test_full_to_incremental_sequence.py (template change flag)
  gaps:
    - Deep inheritance chains (3+ levels)
    - Partial/include selective rebuild
    - Theme override precedence on warm build
    - Shortcode template changes

Output Formats:
  tested: partial  # index.json covered
  risk: MEDIUM
  existing_tests:
    - test_incremental_output_formats.py (index.json, PageProxy)
  gaps:
    - RSS/Atom feed updates
    - Sitemap regeneration
    - llm-full.txt updates
    - asset-manifest.json updates

Cross-Feature:
  tested: false
  risk: MEDIUM
  existing_tests: none
  gaps:
    - Autodoc + navigation
    - i18n + warm build
    - Versioned docs + incremental
    - Collections + warm build
    - Cascade + taxonomy interaction

Edge Cases:
  tested: partial
  risk: LOW-MEDIUM
  existing_tests:
    - test_incremental_cache_stability.py (some edge cases)
  gaps:
    - Empty site (all content deleted)
    - Batch changes (100+ files)
    - Deep nesting (>5 levels)
    - Same-second modifications
    - Unicode filenames
    - Symlinked content
```

---

## Proposed Solution

### Strategy: Extend + Create

**Extend existing files** where partial coverage exists:
- `test_phase2c2_incremental_tags.py` → Add end-to-end taxonomy HTML tests
- `test_incremental_output_formats.py` → Add RSS, sitemap, llm-full.txt tests

**Create new files** for untested areas:

```
tests/integration/
├── warm_build/                          # NEW directory
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures
│   ├── test_navigation.py               # P0 - NEW (truly untested)
│   ├── test_data_files.py               # P1 - NEW (truly untested)
│   ├── test_template_chain.py           # P1 - NEW (inheritance chains untested)
│   ├── test_edge_cases.py               # P2 - NEW
│   └── test_cross_features.py           # P2 - NEW
│
├── test_phase2c2_incremental_tags.py    # EXTEND with HTML verification
└── test_incremental_output_formats.py   # EXTEND with RSS/sitemap/llm-txt
```

### Shared Test Infrastructure

```python
# tests/integration/warm_build/conftest.py

@pytest.fixture
def warm_build_site(tmp_path: Path) -> WarmBuildTestSite:
    """
    Creates a test site with all features enabled.
    
    Returns a helper class with methods for:
    - full_build() / incremental_build()
    - modify_file() / delete_file() / create_file()
    - assert_page_rebuilt() / assert_page_skipped()
    - assert_output_contains() / assert_output_missing()
    """
    ...

@pytest.fixture
def site_with_nav(warm_build_site) -> WarmBuildTestSite:
    """Site with navigation configured."""
    ...

@pytest.fixture
def site_with_taxonomy(warm_build_site) -> WarmBuildTestSite:
    """Site with tags and categories."""
    ...
```

---

## Test Specifications

### P0: Navigation Tests (`test_navigation.py`)

**Rationale**: Navigation is visible on every page. Stale nav is immediately noticeable.

```python
class TestWarmBuildNavigation:
    """Test navigation updates during warm builds."""

    def test_menu_config_change_rebuilds_pages_with_nav(self, site_with_nav):
        """
        When menu.yaml changes, pages displaying nav should rebuild.
        
        Scenario:
        1. Build site with nav (header menu with 3 items)
        2. Add new section to menu config
        3. Incremental build
        4. Assert: Pages with nav show new menu item
        """

    def test_nav_weight_change_updates_ordering(self, site_with_nav):
        """
        When page nav weight changes, nav ordering updates.
        
        Scenario:
        1. Build with pages A (weight=1), B (weight=2), C (weight=3)
        2. Change A weight to 10
        3. Incremental build
        4. Assert: Nav order is B, C, A
        """

    def test_new_section_appears_in_nav(self, site_with_nav):
        """
        When new section is created, it appears in nav if configured.
        
        Scenario:
        1. Build with blog/ and docs/ sections
        2. Create guides/ section with menu weight
        3. Incremental build
        4. Assert: Nav includes guides/
        """

    def test_deleted_section_removed_from_nav(self, site_with_nav):
        """
        When section is deleted, nav should not reference it.
        
        Scenario:
        1. Build with blog/, docs/, guides/
        2. Delete guides/
        3. Incremental build
        4. Assert: No broken nav links to guides/
        """

    def test_nested_menu_changes_cascade(self, site_with_nav):
        """
        Nested menu changes should cascade to all affected pages.
        
        Scenario:
        1. Build with nested menu (docs/ → guides/ → tutorials/)
        2. Change guides/ title in _index.md
        3. Incremental build
        4. Assert: Menu shows new title at all levels
        """

    def test_breadcrumb_updates_on_parent_change(self, site_with_nav):
        """
        Breadcrumb navigation updates when parent changes.
        
        Scenario:
        1. Build with docs/guides/intro.md
        2. Change docs/_index.md title
        3. Incremental build
        4. Assert: intro.md breadcrumb shows new parent title
        """
```

### P0: Taxonomy Tests (EXTEND `test_phase2c2_incremental_tags.py`)

**Rationale**: Taxonomy pages are auto-generated. Stale taxonomy = broken user journeys.

**Already Tested** (in `test_phase2c2_incremental_tags.py`):
- ✅ TaxonomyIndex membership tracking (add/remove pages from tags)
- ✅ Set semantics (order-independent comparison)
- ✅ Index persistence and reload

**Gaps to Fill** (add to existing file):

```python
class TestWarmBuildTaxonomyHtml:
    """End-to-end HTML verification for taxonomy warm builds.
    
    Extends existing TaxonomyIndex tests with actual HTML output checks.
    """

    def test_new_tag_renders_in_taxonomy_page_html(self, site_with_taxonomy):
        """
        Adding tag to page should render in taxonomy list page HTML.
        
        Scenario:
        1. Build with post1 (tags: [python])
        2. Add tag "tutorial" to post1
        3. Incremental build
        4. Assert: /tags/tutorial/index.html exists and lists post1
        
        Note: Complements existing TaxonomyIndex unit tests with HTML verification.
        """

    def test_tag_last_page_deletes_taxonomy_page_output(self, site_with_taxonomy):
        """
        When last page with tag is deleted, taxonomy HTML should be removed.
        
        Scenario:
        1. Build with only post1 having tag "unique"
        2. Delete post1
        3. Incremental build
        4. Assert: /tags/unique/index.html doesn't exist
        """

    def test_category_change_updates_both_category_pages(self, site_with_taxonomy):
        """
        Changing page category updates both old and new category HTML.
        
        Scenario:
        1. Build with post1 (category: tutorials)
        2. Change post1 category to guides
        3. Incremental build
        4. Assert: /categories/tutorials/index.html doesn't list post1
        5. Assert: /categories/guides/index.html lists post1
        """

    def test_taxonomy_term_page_content_change(self, site_with_taxonomy):
        """
        Changing content in _index.md for taxonomy term renders correctly.
        
        Scenario:
        1. Build with /tags/python/_index.md containing "Original description"
        2. Edit _index.md to "Updated description"
        3. Incremental build
        4. Assert: /tags/python/index.html shows "Updated description"
        """
```

### P1: Data File Tests (`test_data_files.py`)

```python
class TestWarmBuildDataFiles:
    """Test data file (data/*.yaml) changes during warm builds."""

    def test_data_file_change_rebuilds_dependent_pages(self, warm_build_site):
        """
        When data file changes, pages using that data rebuild.
        
        Scenario:
        1. Build with data/team.yaml and about.md using {{ site.data.team }}
        2. Modify data/team.yaml
        3. Incremental build
        4. Assert: about.md rebuilt with new data
        """

    def test_new_data_file_available_on_warm_build(self, warm_build_site):
        """
        New data file available to templates on warm build.
        
        Scenario:
        1. Build without data/pricing.yaml
        2. Create data/pricing.yaml
        3. Create page using {{ site.data.pricing }}
        4. Incremental build
        5. Assert: Page renders with pricing data
        """

    def test_deleted_data_file_handled_gracefully(self, warm_build_site):
        """
        Deleted data file doesn't crash build.
        
        Scenario:
        1. Build with data/config.yaml used in template
        2. Delete data/config.yaml
        3. Incremental build
        4. Assert: Build succeeds (template handles missing data)
        """

    def test_nested_data_structure_change(self, warm_build_site):
        """
        Deep changes in nested data structures detected.
        
        Scenario:
        1. Build with data/menu.yaml (deeply nested)
        2. Change nested property
        3. Incremental build
        4. Assert: Pages using nested property updated
        """
```

### P1: Template Chain Tests (`test_template_chain.py`)

```python
class TestWarmBuildTemplateChain:
    """Test template inheritance chain changes during warm builds."""

    def test_base_template_change_rebuilds_all_descendants(self, warm_build_site):
        """
        base.html change should rebuild all pages.
        
        Scenario:
        1. Build with base.html → single.html → pages
        2. Modify base.html (add footer)
        3. Incremental build
        4. Assert: All pages have new footer
        """

    def test_partial_change_rebuilds_users(self, warm_build_site):
        """
        Partial template change rebuilds pages that include it.
        
        Scenario:
        1. Build with partials/sidebar.html included in docs/*
        2. Modify sidebar.html
        3. Incremental build
        4. Assert: docs/* rebuilt, blog/* not rebuilt
        """

    def test_theme_override_precedence(self, warm_build_site):
        """
        Theme override takes precedence on warm build.
        
        Scenario:
        1. Build using theme's base.html
        2. Create local templates/base.html override
        3. Incremental build
        4. Assert: Pages use local override
        """

    def test_deep_template_inheritance(self, warm_build_site):
        """
        4-level inheritance chain correctly invalidates.
        
        Chain: base.html → layout.html → docs.html → page
        
        Scenario:
        1. Build with 4-level inheritance
        2. Modify layout.html (middle of chain)
        3. Incremental build
        4. Assert: docs.html descendants rebuilt, others not
        """

    def test_shortcode_definition_change(self, warm_build_site):
        """
        Shortcode template change rebuilds pages using shortcode.
        
        Scenario:
        1. Build with shortcodes/note.html
        2. Modify note.html template
        3. Incremental build
        4. Assert: Pages with {{< note >}} rebuilt
        """
```

### P1: Output Format Tests (EXTEND `test_incremental_output_formats.py`)

**Already Tested** (in `test_incremental_output_formats.py`):
- ✅ index.json generation in full and incremental builds
- ✅ index.json page count preservation
- ✅ PageProxy transparency contract
- ✅ index.json content updates on modification

**Gaps to Fill** (add to existing file):

```python
class TestWarmBuildAdditionalOutputFormats:
    """Test RSS, sitemap, and LLM output formats during warm builds.
    
    Extends existing index.json tests with other output format coverage.
    """

    def test_rss_feed_updated_on_blog_change(self, warm_build_site):
        """
        RSS feed updated when blog post changes.
        
        Scenario:
        1. Build with blog section having RSS enabled
        2. Modify blog post title and content
        3. Incremental build
        4. Assert: blog/index.xml updated with new content
        """

    def test_rss_feed_new_post_appears(self, warm_build_site):
        """
        New blog post appears in RSS feed on warm build.
        
        Scenario:
        1. Build with blog section (3 posts)
        2. Add new blog post
        3. Incremental build
        4. Assert: blog/index.xml has 4 items
        """

    def test_sitemap_updated_on_page_add(self, warm_build_site):
        """
        Sitemap includes new page on warm build.
        
        Scenario:
        1. Build with sitemap.xml
        2. Add new page
        3. Incremental build
        4. Assert: sitemap.xml includes new URL
        """

    def test_sitemap_removes_deleted_page(self, warm_build_site):
        """
        Deleted page removed from sitemap on warm build.
        
        Scenario:
        1. Build with sitemap.xml (5 URLs)
        2. Delete one page
        3. Incremental build
        4. Assert: sitemap.xml has 4 URLs, deleted page absent
        """

    def test_llm_txt_regenerated_on_content_change(self, warm_build_site):
        """
        llm-full.txt regenerated on content change.
        
        Scenario:
        1. Build with llm-full.txt enabled
        2. Modify page content
        3. Incremental build
        4. Assert: llm-full.txt contains new content
        """

    def test_llm_txt_includes_new_page(self, warm_build_site):
        """
        New page content appears in llm-full.txt.
        
        Scenario:
        1. Build with llm-full.txt enabled
        2. Add new page with unique content
        3. Incremental build
        4. Assert: llm-full.txt contains new page content
        """

    def test_asset_manifest_updated_on_css_change(self, warm_build_site):
        """
        asset-manifest.json updated when CSS changes.
        
        Scenario:
        1. Build with CSS assets
        2. Modify CSS content
        3. Incremental build
        4. Assert: asset-manifest.json has new fingerprint hash
        """
```

### P2: Edge Case Tests (`test_edge_cases.py`)

```python
class TestWarmBuildEdgeCases:
    """Test edge cases and boundary conditions in warm builds."""

    def test_empty_site_after_all_content_deleted(self, warm_build_site):
        """
        Warm build handles empty site gracefully.
        
        Scenario:
        1. Build with 5 pages
        2. Delete all content
        3. Incremental build
        4. Assert: Build succeeds, output is minimal/empty
        """

    def test_batch_changes_100_files(self, warm_build_site):
        """
        Warm build handles 100+ simultaneous file changes.
        
        Scenario:
        1. Build with 100 pages
        2. Modify all 100 pages
        3. Incremental build
        4. Assert: All pages rebuilt correctly
        """

    def test_deep_nesting_10_levels(self, warm_build_site):
        """
        Deep directory nesting handled correctly.
        
        Scenario:
        1. Build with a/b/c/d/e/f/g/h/i/j/page.md (10 levels)
        2. Modify intermediate _index.md
        3. Incremental build
        4. Assert: Cascade propagates to leaf page
        """

    def test_same_second_modifications(self, warm_build_site):
        """
        Multiple modifications in same second detected.
        
        Scenario:
        1. Build with page
        2. Modify page twice in <1 second
        3. Incremental build
        4. Assert: Final content reflected
        """

    def test_unicode_filenames(self, warm_build_site):
        """
        Unicode filenames in warm builds.
        
        Scenario:
        1. Build with 日本語.md, émojis-🎉.md
        2. Modify unicode files
        3. Incremental build
        4. Assert: Files rebuilt correctly
        """

    def test_symlinked_content(self, warm_build_site):
        """
        Symlinked content directories handled.
        
        Scenario:
        1. Build with symlinked content/shared/
        2. Modify file through symlink
        3. Incremental build
        4. Assert: Change detected and rebuilt
        """

    def test_case_sensitivity(self, warm_build_site):
        """
        Case sensitivity handled correctly.
        
        Scenario:
        1. Build with Page.md
        2. Rename to page.md (case change only)
        3. Incremental build
        4. Assert: URL reflects new filename
        """

    def test_content_and_output_same_mtime(self, warm_build_site):
        """
        Handles case where source and output have identical mtime.
        
        Scenario:
        1. Build page
        2. Touch source to match output mtime exactly
        3. Modify content but preserve mtime
        4. Incremental build
        5. Assert: Content hash detection triggers rebuild
        """
```

### P2: Cross-Feature Tests (`test_cross_features.py`)

```python
class TestWarmBuildCrossFeatures:
    """Test interactions between multiple features during warm builds."""

    def test_autodoc_pages_in_navigation(self, warm_build_site):
        """
        Virtual autodoc pages appear correctly in nav.
        
        Scenario:
        1. Build with autodoc enabled, api/ in nav
        2. Add new Python module
        3. Incremental build
        4. Assert: Nav includes new API page
        """

    def test_i18n_translation_change(self, warm_build_site):
        """
        Translation file change triggers correct rebuilds.
        
        Scenario:
        1. Build with i18n (en, es)
        2. Modify i18n/es.yaml
        3. Incremental build
        4. Assert: Spanish pages rebuilt, English not
        """

    def test_versioned_docs_incremental(self, warm_build_site):
        """
        Version-specific changes handled correctly.
        
        Scenario:
        1. Build with versions: [1.0, 2.0]
        2. Modify only 2.0 content
        3. Incremental build
        4. Assert: Only 2.0 pages rebuilt
        """

    def test_collection_with_taxonomy(self, warm_build_site):
        """
        Collection items with taxonomy updates.
        
        Scenario:
        1. Build with products collection having tags
        2. Add tag to product
        3. Incremental build
        4. Assert: Product and tag page updated
        """

    def test_related_pages_on_tag_change(self, warm_build_site):
        """
        Related pages section updates when tags change.
        
        Scenario:
        1. Build with related: tags
        2. Add shared tag between two posts
        3. Incremental build
        4. Assert: Related section shows new connection
        """

    def test_cascade_plus_taxonomy(self, warm_build_site):
        """
        Section cascade + taxonomy interaction.
        
        Scenario:
        1. Build with section cascade setting default tags
        2. Modify cascade tags
        3. Incremental build
        4. Assert: Taxonomy pages reflect cascade change
        """
```

---

## Implementation Plan

### Phase 1: Infrastructure (1 day)

1. Create `tests/integration/warm_build/` directory
2. Implement `conftest.py` with shared fixtures
3. Create `WarmBuildTestSite` helper class
4. Add test utilities: `assert_page_rebuilt()`, `assert_page_skipped()`, `assert_output_contains()`

### Phase 2: P0 Tests (1.5 days)

1. `warm_build/test_navigation.py` - 6 tests (NEW file)
2. Extend `test_phase2c2_incremental_tags.py` - 4 tests (HTML verification)

### Phase 3: P1 Tests (1.5 days)

1. `warm_build/test_data_files.py` - 4 tests (NEW file)
2. `warm_build/test_template_chain.py` - 5 tests (NEW file)
3. Extend `test_incremental_output_formats.py` - 7 tests (RSS/sitemap/llm-txt)

### Phase 4: P2 Tests (1.5 days)

1. `warm_build/test_edge_cases.py` - 8 tests (NEW file)
2. `warm_build/test_cross_features.py` - 6 tests (NEW file)

### Total Effort

- **New test files**: 5
- **Extended test files**: 2
- **New test methods**: ~40
- **Estimated new lines**: ~1,800
- **Estimated time**: 5.5 days

### Effort Comparison

| Metric | Original Estimate | Revised Estimate | Savings |
|--------|-------------------|------------------|---------|
| New files | 7 | 5 | -2 files |
| Test methods | 43 | 40 | -3 methods |
| Lines | 2,500 | 1,800 | -700 lines |
| Time | 7 days | 5.5 days | -1.5 days |

Savings come from leveraging existing test infrastructure in `test_phase2c2_incremental_tags.py` and `test_incremental_output_formats.py`.

---

## Success Criteria

### Test Coverage Goals

| Category | New Tests | Existing | Strategy | Status |
|----------|-----------|----------|----------|--------|
| Navigation | 6 | 0 | NEW file | ⬜ TODO |
| Taxonomy | 4 | 8 | EXTEND | ⬜ TODO |
| Data Files | 4 | 0 | NEW file | ⬜ TODO |
| Template Chain | 5 | 1 | NEW file | ⬜ TODO |
| Output Formats | 7 | 6 | EXTEND | ⬜ TODO |
| Edge Cases | 8 | ~3 | NEW file | ⬜ TODO |
| Cross Features | 6 | 0 | NEW file | ⬜ TODO |

### Pre-Implementation Verification

Before writing new tests, verify existing tests are working:

- [ ] `pytest tests/integration/test_phase2c2_incremental_tags.py -v` passes
- [ ] `pytest tests/integration/test_incremental_output_formats.py -v` passes
- [ ] Review existing test patterns for consistency

### Quality Gates

- [ ] All tests pass in CI
- [ ] No test takes > 5 seconds individually
- [ ] Tests are isolated (no shared state between tests)
- [ ] Test names clearly describe scenario
- [ ] Assertions include helpful error messages
- [ ] Extended tests follow existing file's patterns and fixtures

### Documentation Updates

- [ ] Update `TEST_COVERAGE.md` with new test matrix
- [ ] Add "Warm Build Testing" section to developer docs
- [ ] Document test fixtures in docstrings

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tests are flaky due to timing | HIGH | Use content hashes, not mtime; add retry logic |
| Tests are slow | MEDIUM | Use module-scoped fixtures; minimize disk I/O |
| Cross-feature tests have too many dependencies | MEDIUM | Use minimal site configs per test |
| Some scenarios require features not yet implemented | LOW | Mark tests as `pytest.mark.skip` with reason |

---

## Open Questions

1. **Should we use Hypothesis for stateful warm build tests?**
   - Pro: Better coverage of edge cases
   - Con: Slower, more complex
   - **Decision**: Use for P2 edge cases only ✅

2. **How to handle tests for features not yet implemented (i18n, versioning)?**
   - Option A: Skip tests, revisit later
   - Option B: Implement basic feature support first
   - **Decision**: Option A with `pytest.mark.skip(reason="i18n not implemented")` ✅

3. **Should we move existing warm build tests to new directory?**
   - Pro: Consolidated location
   - Con: Breaking change for existing test references
   - **Decision**: Keep existing tests in place, extend where appropriate ✅

4. **Should we extend existing tests or create parallel test files?** (NEW)
   - Analysis found `test_phase2c2_incremental_tags.py` and `test_incremental_output_formats.py` have partial coverage
   - **Decision**: Extend existing files to avoid duplication and maintain context ✅

---

## Related RFCs

- `rfc-global-build-state-dependencies.md` - Asset fingerprint detection
- `rfc-incremental-build-observability.md` - Build logging improvements
- `rfc-cache-invalidation-fixes.md` - Cache stability fixes

---

## Appendix: Existing Test Discovery

During RFC review, the following existing test coverage was discovered that wasn't initially accounted for:

### `test_incremental_output_formats.py` (515 lines)

```python
# Key existing tests:
- test_full_build_generates_index_json_with_pages()
- test_incremental_build_generates_index_json_with_pages()
- test_incremental_build_preserves_index_json_page_count()
- test_page_proxy_transparency_contract()
- test_index_json_content_updates_on_modification()
```

**Implication**: index.json warm build testing is already solid. Focus new tests on RSS/sitemap/llm-txt.

### `test_phase2c2_incremental_tags.py` (347 lines)

```python
# Key existing tests:
- TestTaxonomyIndexComparison (unit tests for membership tracking)
- test_new_tag_always_needs_generation()
- test_unchanged_tag_membership_skips_generation()
- test_added_page_to_tag_triggers_generation()
- test_removed_page_from_tag_triggers_generation()
```

**Implication**: TaxonomyIndex logic is tested. Focus new tests on end-to-end HTML output verification.

### `test_nav_tree_integration.py` (297 lines)

```python
# Key existing tests:
- test_nav_tree_builds_for_each_version()
- test_shared_content_in_all_versions()
- test_version_specific_content_filtering()
- test_nav_tree_cache_works()
```

**Implication**: NavTree structure is tested but NOT in warm-build context. Navigation warm build tests are truly needed.

---

## Appendix: Test Site Structure

```
test_site/
├── bengal.toml
├── config/
│   └── _default/
│       ├── site.yaml
│       ├── build.yaml
│       ├── menu.yaml          # For navigation tests
│       └── taxonomies.yaml    # For taxonomy tests
├── content/
│   ├── _index.md
│   ├── blog/
│   │   ├── _index.md
│   │   ├── post1.md           # tags: [python, tutorial]
│   │   └── post2.md           # tags: [rust]
│   └── docs/
│       ├── _index.md
│       └── guides/
│           ├── _index.md
│           └── intro.md
├── data/
│   ├── team.yaml
│   └── config.yaml
├── templates/
│   ├── base.html
│   ├── single.html
│   └── partials/
│       └── sidebar.html
└── assets/
    └── css/
        └── style.css
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-13 | RFC created | Address warm build test gaps |
| 2026-01-13 | Revised scope: 5 new files + 2 extensions | Analysis found existing partial coverage in `test_phase2c2_incremental_tags.py` (347 lines) and `test_incremental_output_formats.py` (515 lines) |
| 2026-01-13 | Extend vs. create strategy adopted | Avoids test duplication, maintains context, reduces effort by ~1.5 days |
| 2026-01-13 | Open questions 1-4 resolved | See Open Questions section |
| TBD | Phase 1 approved | Infrastructure setup |
| TBD | P0 tests complete | Navigation + Taxonomy HTML |
| TBD | P1 tests complete | Data + Templates + RSS/Sitemap |
| TBD | P2 tests complete | Edge cases + Cross-features |
