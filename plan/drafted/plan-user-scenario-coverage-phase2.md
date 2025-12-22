# Plan: User Scenario Coverage Phase 2 - Extended Validation

**Status**: ✅ **COMPLETE**  
**RFC**: `plan/drafted/rfc-user-scenario-coverage-phase2.md`  
**Depends On**: Phase 1 RFC (Evaluated)  
**Total Estimate**: 6 days  
**Actual**: Complete  
**Confidence**: 95% 🟢

> **Note**: All tasks have been implemented and verified. Ready for archival.

---

## Executive Summary

Extends Phase 1 with resume/changelog integration tests, i18n validation, language switcher UI, gallery directive, and product template. Three tiers with clear dependencies.

---

## Pre-Implementation Verification (All Verified ✅)

All prerequisites were verified and implementation is complete:

- [x] Phase 1 is evaluated/ready → `plan/ready/rfc-user-scenario-coverage.md`
- [x] `test-blog-paginated/` exists with 25 posts
- [x] `test-i18n-content/bengal.toml` exists
- [x] `bengal/cli/templates/resume/` exists
- [x] `bengal/cli/templates/changelog/` exists
- [x] i18n functions exist in `bengal/rendering/template_functions/i18n.py`

---

## Tier 1: Template Testing & Performance (2 days)

### Phase 1.1: Resume Template Test Root

**Goal**: Create test root and integration tests for resume template

#### Task 1.1.1: Create test-resume test root structure

**Files**:
- `tests/roots/test-resume/bengal.toml`
- `tests/roots/test-resume/data/resume.yaml`
- `tests/roots/test-resume/content/_index.md`
- `tests/roots/test-resume/skeleton.yaml`

**Source Data Schema**: Copy from `bengal/cli/templates/resume/data/resume.yaml`

```yaml
# tests/roots/test-resume/bengal.toml
[site]
title = "Test Resume"
baseurl = "/"

[build]
content_dir = "content"
output_dir = "public"
theme = "resume"

[data]
dir = "data"
```

**Commit**:
```bash
git add -A && git commit -m "tests(roots): add test-resume root with resume.yaml data fixture"
```

#### Task 1.1.2: Write resume integration tests

**File**: `tests/integration/test_resume_changelog.py`

**Tests**:
1. `test_resume_data_loaded` - Verify resume YAML data accessible
2. `test_resume_builds_successfully` - Build completes without errors
3. `test_resume_renders_all_sections` - Key sections (experience, education, skills) rendered

**Commit**:
```bash
git add -A && git commit -m "tests(integration): add resume template integration tests for data loading and rendering"
```

---

### Phase 1.2: Changelog Template Test Root

**Goal**: Create test root and integration tests for changelog template

#### Task 1.2.1: Create test-changelog test root structure

**Files**:
- `tests/roots/test-changelog/bengal.toml`
- `tests/roots/test-changelog/data/changelog.yaml`
- `tests/roots/test-changelog/content/_index.md`
- `tests/roots/test-changelog/skeleton.yaml`

**Source Data Schema**: Copy from `bengal/cli/templates/changelog/data/changelog.yaml`

**Commit**:
```bash
git add -A && git commit -m "tests(roots): add test-changelog root with changelog.yaml data fixture"
```

#### Task 1.2.2: Add changelog integration tests

**File**: Append to `tests/integration/test_resume_changelog.py`

**Tests**:
1. `test_changelog_data_loaded` - Verify releases array accessible
2. `test_changelog_builds_successfully` - Build completes
3. `test_changelog_displays_versions` - Version numbers rendered

**Commit**:
```bash
git add -A && git commit -m "tests(integration): add changelog template integration tests for releases rendering"
```

---

### Phase 1.3: 10k Page Performance Benchmark

**Goal**: Establish performance baseline for large sites

#### Task 1.3.1: Create benchmark test file

**File**: `benchmarks/test_10k_site.py`

**Functions**:
1. `generate_large_site(root, sections, pages_per_section)` - Site generator helper
2. `test_10k_site_discovery_performance` - Discovery benchmark with 30s gate
3. `test_10k_site_memory_usage` - Memory usage test with 2GB gate

**Commit**:
```bash
git add -A && git commit -m "benchmarks: add 10k page site generator and performance tests with time/memory gates"
```

#### Task 1.3.2: Document baseline performance

**File**: Update `benchmarks/README.md` with:
- Test description
- Expected baseline metrics
- How to run: `pytest benchmarks/test_10k_site.py -v --benchmark`
- CI integration notes (`@pytest.mark.slow` for nightly runs)

**Commit**:
```bash
git add -A && git commit -m "docs(benchmarks): document 10k site performance baseline and CI integration"
```

---

## Tier 2: i18n Testing & Language Switcher (1 day)

### Phase 2.1: Populate i18n Test Root

**Goal**: Add missing content and i18n strings to test-i18n-content

#### Task 2.1.1: Create i18n translation files

**Files**:
- `tests/roots/test-i18n-content/i18n/en.yaml`
- `tests/roots/test-i18n-content/i18n/fr.yaml`

**Content**:
```yaml
# en.yaml
ui:
  home: "Home"
  about: "About"
  language_selection: "Language"

# fr.yaml
ui:
  home: "Accueil"
  about: "À propos"
  language_selection: "Langue"
```

**Commit**:
```bash
git add -A && git commit -m "tests(roots): add en/fr translation files to test-i18n-content"
```

#### Task 2.1.2: Create content directories with pages

**Files**:
- `tests/roots/test-i18n-content/content/en/_index.md`
- `tests/roots/test-i18n-content/content/en/about.md`
- `tests/roots/test-i18n-content/content/fr/_index.md`
- `tests/roots/test-i18n-content/content/fr/about.md`

**Commit**:
```bash
git add -A && git commit -m "tests(roots): add en/fr content pages to test-i18n-content for bilingual testing"
```

---

### Phase 2.2: i18n Integration Tests

**Goal**: Validate existing i18n template functions

#### Task 2.2.1: Create i18n integration test file

**File**: `tests/integration/test_i18n.py`

**Tests**:
1. `test_t_function_translates` - UI strings translate correctly
2. `test_alternate_links_generated` - hreflang tags present
3. `test_languages_returns_configured` - Language list accessible
4. `test_current_lang_detected` - Current language detected
5. `test_locale_date_formats` - Date localization works

**Commit**:
```bash
git add -A && git commit -m "tests(integration): add i18n integration tests for t(), alternate_links(), languages()"
```

---

### Phase 2.3: Language Switcher Partial

**Goal**: Create reusable language switcher component for themes

#### Task 2.3.1: Create partials directory and language switcher

**File**: `bengal/themes/default/partials/language-switcher.html`

**Note**: Check if `bengal/themes/default/partials/` exists; if not, create directory.

**Implementation**: Use existing `alternate_links()`, `languages()`, `current_lang()` functions.

**Commit**:
```bash
git add -A && git commit -m "themes(default): add language-switcher partial using existing i18n functions"
```

#### Task 2.3.2: Add language switcher CSS

**File**: Append to `bengal/themes/default/static/css/components/language-switcher.css` or main stylesheet

**Commit**:
```bash
git add -A && git commit -m "themes(default): add language-switcher CSS with dropdown menu styles"
```

#### Task 2.3.3: Test language switcher rendering

**File**: Add test in `tests/integration/test_i18n.py`

**Test**: `test_language_switcher_renders` - Verify partial renders in multi-language sites

**Commit**:
```bash
git add -A && git commit -m "tests(integration): add language switcher rendering test"
```

---

## Tier 3: Content Features (3 days)

### Phase 3.1: Gallery Directive

**Goal**: Implement responsive image gallery directive

#### Task 3.1.1: Create gallery directive module

**File**: `bengal/directives/gallery.py`

**Class**: `GalleryDirective` extending `BengalDirective`

**Options**:
- `columns` (default: 3)
- `lightbox` (default: true)
- `gap` (default: "1rem")

**Commit**:
```bash
git add -A && git commit -m "directives: add GalleryDirective for responsive image galleries with lightbox support"
```

#### Task 3.1.2: Register gallery directive

**File**: Update `bengal/directives/registry.py`

**Add**: Gallery directive to `KNOWN_DIRECTIVE_NAMES` and lazy loader

**Commit**:
```bash
git add -A && git commit -m "directives(registry): register GalleryDirective for :::{gallery} syntax"
```

#### Task 3.1.3: Add gallery CSS to default theme

**File**: `bengal/themes/default/static/css/components/gallery.css`

**Styles**:
- Grid layout with CSS custom properties
- Responsive breakpoints (2 cols @ 768px, 1 col @ 480px)
- Hover effects
- Caption overlay styling

**Commit**:
```bash
git add -A && git commit -m "themes(default): add gallery CSS with responsive grid and hover effects"
```

#### Task 3.1.4: Create test-gallery test root

**Files**:
- `tests/roots/test-gallery/bengal.toml`
- `tests/roots/test-gallery/content/_index.md`
- `tests/roots/test-gallery/content/gallery.md` (with gallery directive)

**Commit**:
```bash
git add -A && git commit -m "tests(roots): add test-gallery root with gallery directive example"
```

#### Task 3.1.5: Add gallery directive tests

**File**: `tests/integration/test_gallery.py`

**Tests**:
1. `test_gallery_renders_grid` - CSS grid class applied
2. `test_gallery_parses_images` - Images extracted from markdown
3. `test_gallery_lightbox_attribute` - data-lightbox attribute present
4. `test_gallery_custom_columns` - Custom columns option works

**Commit**:
```bash
git add -A && git commit -m "tests(integration): add gallery directive tests for rendering and options"
```

---

### Phase 3.2: Product Template

**Goal**: Create product-focused site template with JSON-LD

#### Task 3.2.1: Create product template package

**Files**:
- `bengal/cli/templates/product/__init__.py`
- `bengal/cli/templates/product/template.py`
- `bengal/cli/templates/product/skeleton.yaml`

**Commit**:
```bash
git add -A && git commit -m "templates: add product template package with skeleton.yaml"
```

#### Task 3.2.2: Create product data schema

**File**: `bengal/cli/templates/product/data/products.yaml`

**Schema**:
```yaml
products:
  - sku: "PROD-001"
    name: "Example Product"
    price: 99.99
    currency: USD
    in_stock: true
    images: ["/images/product-1.jpg"]
    features: ["Feature 1", "Feature 2"]
```

**Commit**:
```bash
git add -A && git commit -m "templates(product): add products.yaml data schema with sample products"
```

#### Task 3.2.3: Create product content pages

**Files**:
- `bengal/cli/templates/product/pages/_index.md`
- `bengal/cli/templates/product/pages/products/_index.md`
- `bengal/cli/templates/product/pages/products/product-1.md`
- `bengal/cli/templates/product/pages/products/product-2.md`
- `bengal/cli/templates/product/pages/features.md`
- `bengal/cli/templates/product/pages/pricing.md`
- `bengal/cli/templates/product/pages/contact.md`

**Commit**:
```bash
git add -A && git commit -m "templates(product): add product, features, pricing, and contact pages"
```

#### Task 3.2.4: Create JSON-LD partial for products

**File**: `bengal/themes/default/partials/product-jsonld.html`

**Implementation**: Generate schema.org Product JSON-LD from frontmatter

**Commit**:
```bash
git add -A && git commit -m "themes(default): add product-jsonld partial for schema.org structured data"
```

#### Task 3.2.5: Register product template

**File**: Update `bengal/cli/templates/registry.py`

**Commit**:
```bash
git add -A && git commit -m "templates(registry): register product template"
```

---

### Phase 3.3: Product Template Tests

**Goal**: Validate product template builds and generates JSON-LD

#### Task 3.3.1: Create test-product test root

**Files**:
- `tests/roots/test-product/bengal.toml`
- `tests/roots/test-product/data/products.yaml`
- `tests/roots/test-product/content/_index.md`
- `tests/roots/test-product/content/products/_index.md`
- `tests/roots/test-product/content/products/product-1.md`

**Commit**:
```bash
git add -A && git commit -m "tests(roots): add test-product root with sample product pages"
```

#### Task 3.3.2: Add product template tests

**File**: `tests/integration/test_product.py`

**Tests**:
1. `test_product_jsonld_generated` - JSON-LD script present
2. `test_product_jsonld_valid_schema` - schema.org @type: Product
3. `test_product_listing` - Products listed on index
4. `test_product_template_scaffolds` - Template scaffolds successfully

**Commit**:
```bash
git add -A && git commit -m "tests(integration): add product template tests for JSON-LD and scaffolding"
```

---

## Implementation Order & Dependencies

```
Tier 1 (Days 1-2) - Can parallelize
├── Phase 1.1: Resume tests
├── Phase 1.2: Changelog tests  
└── Phase 1.3: 10k benchmark

Tier 2 (Day 3) - Sequential
├── Phase 2.1: Populate i18n test root
├── Phase 2.2: i18n integration tests
└── Phase 2.3: Language switcher

Tier 3 (Days 4-6) - Sequential
├── Phase 3.1: Gallery directive (Day 4)
├── Phase 3.2: Product template (Day 5)
└── Phase 3.3: Product tests (Day 6)
```

---

## Task Checklist (All Complete ✅)

### Tier 1: Template Testing & Performance (Day 1-2)

- [x] **1.1.1** Create test-resume test root → `tests/roots/test-resume/`
- [x] **1.1.2** Write resume integration tests → `tests/integration/test_resume_changelog.py`
- [x] **1.2.1** Create test-changelog test root → `tests/roots/test-changelog/`
- [x] **1.2.2** Add changelog integration tests → `tests/integration/test_resume_changelog.py`
- [x] **1.3.1** Create 10k benchmark test file → `benchmarks/test_10k_site.py`
- [x] **1.3.2** Document baseline performance → `benchmarks/README.md`

### Tier 2: i18n Testing & Language Switcher (Day 3)

- [x] **2.1.1** Create i18n translation files → `tests/roots/test-i18n-content/i18n/en.yaml`, `fr.yaml`
- [x] **2.1.2** Create content directories → `tests/roots/test-i18n-content/content/en/`, `fr/`
- [x] **2.2.1** Create i18n integration tests → `tests/integration/test_i18n.py`
- [x] **2.3.1** Create language switcher → `partials/language-switcher.html`
- [x] **2.3.2** Add language switcher CSS → `components/language-switcher.css`
- [x] **2.3.3** Test language switcher → Tests in `test_i18n.py`

### Tier 3: Content Features (Days 4-6)

- [x] **3.1.1** Create gallery directive → `bengal/directives/gallery.py`
- [x] **3.1.2** Register gallery directive → In registry
- [x] **3.1.3** Add gallery CSS → `components/gallery.css`
- [x] **3.1.4** Create test-gallery test root → `tests/roots/test-gallery/`
- [x] **3.1.5** Add gallery directive tests → `tests/integration/test_gallery.py`
- [x] **3.2.1** Create product template → `bengal/cli/templates/product/`
- [x] **3.2.2** Create product data schema → `data/products.yaml`
- [x] **3.2.3** Create product content pages → Multiple product pages
- [x] **3.2.4** Create JSON-LD partial → `partials/product-jsonld.html`
- [x] **3.2.5** Register product template → In registry
- [x] **3.3.1** Create test-product test root → `tests/roots/test-product/`
- [x] **3.3.2** Add product template tests → `tests/integration/test_product.py`

---

## Success Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Resume template ≥3 integration tests | `pytest tests/integration/test_resume_changelog.py -v` |
| 2 | Changelog template ≥3 integration tests | `pytest tests/integration/test_resume_changelog.py -v` |
| 3 | 10k page discovery <30s | `pytest benchmarks/test_10k_site.py -v --benchmark` |
| 4 | 10k page memory <2GB | `pytest benchmarks/test_10k_site.py -v` |
| 5 | i18n functions have integration tests | `pytest tests/integration/test_i18n.py -v` |
| 6 | Language switcher renders | `pytest tests/integration/test_i18n.py::test_language_switcher_renders` |
| 7 | Gallery directive renders grid | `pytest tests/integration/test_gallery.py -v` |
| 8 | Product template generates JSON-LD | `pytest tests/integration/test_product.py -v` |
| 9 | All new code has tests | Coverage check |
| 10 | Scenario coverage ≥95% | Manual assessment |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| 10k benchmark too slow for CI | Mark `@pytest.mark.slow`, run nightly only |
| Gallery lightbox JS complexity | Use existing library (GLightbox) or CSS-only |
| Product template too opinionated | Make `structured_data` opt-in via frontmatter |
| Theme partials directory missing | Create `partials/` directory if needed |

---

## Post-Implementation (Current Status)

All implementation tasks are complete. Remaining steps:

- [x] Run full test suite: `pytest tests/ -v` - All tests passing
- [x] Run benchmarks: `pytest benchmarks/ -v --benchmark` - Gates met
- [x] Verify linting: `ruff check bengal/ tests/` - Clean
- [x] Update RFC status to `Implemented` - Done
- [ ] Move RFC and Plan to `plan/ready/` or DELETE
- [ ] Add changelog entry

**Recommended Action**: Delete RFC and Plan, add changelog entry per workflow.

---

## References

- **RFC**: `plan/drafted/rfc-user-scenario-coverage-phase2.md`
- **Phase 1**: `plan/ready/rfc-user-scenario-coverage.md`
- **i18n Functions**: `bengal/rendering/template_functions/i18n.py`
- **Directive Pattern**: `bengal/directives/admonitions.py`
- **Template Pattern**: `bengal/cli/templates/blog/`
