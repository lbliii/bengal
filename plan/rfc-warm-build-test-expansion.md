# RFC: Warm Build Integration Test Expansion

## Status: Draft
## Created: 2026-01-13
## Updated: 2026-01-13

---

## Summary

**Problem**: Bengal's warm build (incremental) test coverage is solid for core scenarios but has significant gaps in feature-specific warm builds, cross-feature interactions, and edge cases.

**Solution**: Expand integration test suite with 7 new test files covering navigation, taxonomy, data files, template chains, output formats, edge cases, and cross-feature interactions.

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

**Untested or weakly-tested scenarios** (❌):
- Navigation/menu changes
- Taxonomy (tags/categories) changes
- Data file changes
- Template inheritance chains
- Multi-output format consistency
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

### Existing Warm Build Tests

| File | Scenarios | Lines |
|------|-----------|-------|
| `test_warm_build_virtual_page_assets.py` | CSS/JS fingerprints, CI cache restore | 332 |
| `test_full_to_incremental_sequence.py` | Content/template/config changes | 298 |
| `test_incremental_cache_stability.py` | Cache consistency, autodoc output | 837 |
| `test_incremental_section_stability.py` | Section cascades, URL stability | 430 |
| `stateful/test_build_workflows.py` | Hypothesis page lifecycle | 477 |

**Total**: ~2,374 lines across 5 files

### Coverage Gaps by Feature

```yaml
Navigation System:
  tested: false
  risk: HIGH
  scenarios:
    - Menu config changes
    - Nav weight changes
    - Section add/remove from menu
    - Nested menu updates

Taxonomy System:
  tested: false
  risk: HIGH
  scenarios:
    - Tag added to page
    - Tag removed from page
    - Category rename
    - Taxonomy page rebuild triggers

Data Files:
  tested: false
  risk: MEDIUM
  scenarios:
    - data/*.yaml changes
    - Data file deletion
    - Nested data structures

Template Inheritance:
  tested: partial
  risk: MEDIUM
  scenarios:
    - base.html → child → grandchild chain
    - Partial/include changes
    - Theme override precedence

Output Formats:
  tested: false
  risk: MEDIUM
  scenarios:
    - index.json consistency
    - RSS/Atom feed updates
    - Sitemap regeneration
    - llm-full.txt updates

Cross-Feature:
  tested: false
  risk: MEDIUM
  scenarios:
    - Autodoc + navigation
    - i18n + warm build
    - Versioned docs + incremental
    - Collections + warm build

Edge Cases:
  tested: partial
  risk: LOW-MEDIUM
  scenarios:
    - Empty site (all content deleted)
    - Batch changes (100+ files)
    - Deep nesting (>5 levels)
    - Same-second modifications
```

---

## Proposed Solution

### New Test Files

Create 7 new integration test files:

```
tests/integration/
├── warm_build/                          # NEW directory
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures
│   ├── test_navigation.py               # P0
│   ├── test_taxonomy.py                 # P0
│   ├── test_data_files.py               # P1
│   ├── test_template_chain.py           # P1
│   ├── test_output_formats.py           # P1
│   ├── test_edge_cases.py               # P2
│   └── test_cross_features.py           # P2
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

### P0: Taxonomy Tests (`test_taxonomy.py`)

**Rationale**: Taxonomy pages are auto-generated. Stale taxonomy = broken user journeys.

```python
class TestWarmBuildTaxonomy:
    """Test taxonomy (tags/categories) updates during warm builds."""

    def test_new_tag_adds_page_to_taxonomy(self, site_with_taxonomy):
        """
        Adding tag to page should update taxonomy list page.
        
        Scenario:
        1. Build with post1 (tags: [python])
        2. Add tag "tutorial" to post1
        3. Incremental build
        4. Assert: /tags/tutorial/ exists and lists post1
        """

    def test_removed_tag_removes_page_from_taxonomy(self, site_with_taxonomy):
        """
        Removing tag from page should update taxonomy list page.
        
        Scenario:
        1. Build with post1 (tags: [python, tutorial])
        2. Remove "tutorial" tag from post1
        3. Incremental build
        4. Assert: /tags/tutorial/ doesn't list post1
        """

    def test_tag_only_page_creates_taxonomy_page(self, site_with_taxonomy):
        """
        When page with unique tag is added, taxonomy page is created.
        
        Scenario:
        1. Build with no "rust" tags
        2. Create post with tags: [rust]
        3. Incremental build
        4. Assert: /tags/rust/ exists
        """

    def test_tag_last_page_deletes_taxonomy_page(self, site_with_taxonomy):
        """
        When last page with tag is deleted, taxonomy page should be removed.
        
        Scenario:
        1. Build with only post1 having tag "unique"
        2. Delete post1
        3. Incremental build
        4. Assert: /tags/unique/ doesn't exist (or is empty)
        """

    def test_category_change_updates_category_page(self, site_with_taxonomy):
        """
        Changing page category updates category listing.
        
        Scenario:
        1. Build with post1 (category: tutorials)
        2. Change post1 category to guides
        3. Incremental build
        4. Assert: /categories/tutorials/ doesn't list post1
        Assert: /categories/guides/ lists post1
        """

    def test_taxonomy_term_page_content_change(self, site_with_taxonomy):
        """
        Changing content in _index.md for taxonomy term.
        
        Scenario:
        1. Build with /tags/python/_index.md
        2. Edit _index.md content
        3. Incremental build
        4. Assert: /tags/python/ shows new content
        """

    def test_multiple_taxonomy_changes_batch(self, site_with_taxonomy):
        """
        Multiple pages changing tags in single build.
        
        Scenario:
        1. Build with 5 posts with various tags
        2. Change tags on 3 posts simultaneously
        3. Incremental build
        4. Assert: All affected taxonomy pages updated
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

### P1: Output Format Tests (`test_output_formats.py`)

```python
class TestWarmBuildOutputFormats:
    """Test non-HTML output format consistency during warm builds."""

    def test_index_json_updated_on_content_change(self, warm_build_site):
        """
        index.json updated when page content changes.
        
        Scenario:
        1. Build with 5 pages → index.json
        2. Modify page title
        3. Incremental build
        4. Assert: index.json has new title
        """

    def test_index_json_page_added(self, warm_build_site):
        """
        New page appears in index.json.
        
        Scenario:
        1. Build with 5 pages
        2. Add new page
        3. Incremental build
        4. Assert: index.json has 6 entries
        """

    def test_index_json_page_deleted(self, warm_build_site):
        """
        Deleted page removed from index.json.
        
        Scenario:
        1. Build with 5 pages
        2. Delete page
        3. Incremental build
        4. Assert: index.json has 4 entries, no reference to deleted
        """

    def test_rss_feed_updated_on_blog_change(self, warm_build_site):
        """
        RSS feed updated when blog post changes.
        
        Scenario:
        1. Build with blog section having RSS
        2. Modify blog post
        3. Incremental build
        4. Assert: index.xml updated with new content
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

    def test_llm_txt_regenerated(self, warm_build_site):
        """
        llm-full.txt regenerated on content change.
        
        Scenario:
        1. Build with llm-full.txt enabled
        2. Modify page content
        3. Incremental build
        4. Assert: llm-full.txt contains new content
        """

    def test_asset_manifest_updated(self, warm_build_site):
        """
        asset-manifest.json updated when assets change.
        
        Scenario:
        1. Build with CSS assets
        2. Modify CSS
        3. Incremental build
        4. Assert: asset-manifest.json has new fingerprint
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
4. Add test utilities: `assert_page_rebuilt()`, `assert_output_contains()`

### Phase 2: P0 Tests (2 days)

1. `test_navigation.py` - 6 tests
2. `test_taxonomy.py` - 7 tests

### Phase 3: P1 Tests (2 days)

1. `test_data_files.py` - 4 tests
2. `test_template_chain.py` - 5 tests
3. `test_output_formats.py` - 7 tests

### Phase 4: P2 Tests (2 days)

1. `test_edge_cases.py` - 8 tests
2. `test_cross_features.py` - 6 tests

### Total Effort

- **New test files**: 7
- **New test methods**: ~43
- **Estimated lines**: ~2,500
- **Estimated time**: 7 days

---

## Success Criteria

### Test Coverage Goals

| Category | Tests | Status |
|----------|-------|--------|
| Navigation | 6 | ⬜ TODO |
| Taxonomy | 7 | ⬜ TODO |
| Data Files | 4 | ⬜ TODO |
| Template Chain | 5 | ⬜ TODO |
| Output Formats | 7 | ⬜ TODO |
| Edge Cases | 8 | ⬜ TODO |
| Cross Features | 6 | ⬜ TODO |

### Quality Gates

- [ ] All tests pass in CI
- [ ] No test takes > 5 seconds individually
- [ ] Tests are isolated (no shared state between tests)
- [ ] Test names clearly describe scenario
- [ ] Assertions include helpful error messages

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
   - Recommendation: Use for P2 edge cases only

2. **How to handle tests for features not yet implemented (i18n, versioning)?**
   - Option A: Skip tests, revisit later
   - Option B: Implement basic feature support first
   - Recommendation: Option A with clear `pytest.mark.skip` annotations

3. **Should we move existing warm build tests to new directory?**
   - Pro: Consolidated location
   - Con: Breaking change for existing test references
   - Recommendation: Keep existing, add new tests in new directory

---

## Related RFCs

- `rfc-global-build-state-dependencies.md` - Asset fingerprint detection
- `rfc-incremental-build-observability.md` - Build logging improvements
- `rfc-cache-invalidation-fixes.md` - Cache stability fixes

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
| TBD | Phase 1 approved | Infrastructure setup |
| TBD | P0 tests complete | Navigation + Taxonomy |
| TBD | P1 tests complete | Data + Templates + Formats |
| TBD | P2 tests complete | Edge cases + Cross-features |
