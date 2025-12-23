# Plan: Content-Aware CSS Tree Shaking

**RFC**: `rfc-css-tree-shaking.md`
**Status**: Draft
**Created**: 2025-12-23
**Estimated Time**: 8-12 hours

---

## Summary

Implement build-time CSS optimization that analyzes content types and features in use, then generates a minimal `style.css` containing only the CSS needed for that specific site. Expected 50%+ reduction for single-purpose sites.

---

## Tasks

### Phase 1: CSS Manifest (Foundation)

#### Task 1.1: Create CSS Manifest for Default Theme
- **Files**: `bengal/themes/default/css_manifest.py`
- **Action**: Create manifest categorizing all CSS into CORE, SHARED, TYPE_MAP, FEATURE_MAP, PALETTES
- **Commit**: `themes(default): add css_manifest.py with categorized CSS for tree shaking`

#### Task 1.2: Create CSS Manifest Types Module
- **Files**: `bengal/orchestration/css_manifest_types.py`
- **Action**: Define TypedDict or Protocol for manifest structure (CSS_CORE, CSS_SHARED, etc.)
- **Commit**: `orchestration: add css_manifest_types module for CSS manifest schema`

---

### Phase 2: Feature Detection Infrastructure

#### Task 2.1: Add features_detected Attribute to Site
- **Files**: `bengal/core/site.py`
- **Action**: Add `features_detected: set[str] = field(default_factory=set)` attribute
- **Commit**: `core(site): add features_detected attribute for CSS optimization`

#### Task 2.2: Integrate Feature Detection into Content Discovery
- **Files**: `bengal/orchestration/content_orchestrator.py`
- **Action**: During page parsing, detect features (mermaid, graph, data_tables) and populate `site.features_detected`
- **Depends on**: Task 2.1
- **Commit**: `orchestration(content): detect features during discovery for CSS optimization`

---

### Phase 3: CSS Optimizer Implementation

#### Task 3.1: Create CSSOptimizer Class
- **Files**: `bengal/orchestration/css_optimizer.py`
- **Action**: Implement CSSOptimizer with:
  - `_load_manifest()` - load from theme
  - `get_used_content_types()` - scan site.pages and site.sections
  - `get_enabled_features()` - read site.features_detected + config
  - `get_required_css_files()` - combine all sources with dedup
  - `generate()` - output optimized CSS with @layer imports
- **Depends on**: Task 1.1, Task 1.2
- **Commit**: `orchestration: add CSSOptimizer for content-aware CSS tree shaking`

#### Task 3.2: Add Convenience Function
- **Files**: `bengal/orchestration/css_optimizer.py`
- **Action**: Add `optimize_css_for_site(site: Site) -> str` convenience function
- **Depends on**: Task 3.1
- **Commit**: `orchestration(css_optimizer): add optimize_css_for_site convenience function`

---

### Phase 4: Build Pipeline Integration

#### Task 4.1: Add CSS Config Schema
- **Files**: `bengal/config/schema.py` (or equivalent)
- **Action**: Add `css:` config section with `optimize`, `all_palettes`, `include`, `exclude` options
- **Commit**: `config: add css optimization schema (optimize, all_palettes, include, exclude)`

#### Task 4.2: Integrate Optimizer into Asset Phase
- **Files**: `bengal/orchestration/build/rendering.py`
- **Action**: Call CSSOptimizer before asset bundling in phase_assets, write to cache, override entry point
- **Depends on**: Task 3.1, Task 4.1
- **Commit**: `orchestration(build): integrate CSS optimizer into asset processing phase`

#### Task 4.3: Add Asset Source Override Support
- **Files**: `bengal/core/asset.py`
- **Action**: Add `_source_override` attribute and `is_css_entry_point()` method to Asset class
- **Depends on**: Task 4.2
- **Commit**: `core(asset): add source override support for optimized CSS entry point`

---

### Phase 5: CLI Integration

#### Task 5.1: Add CLI Output for CSS Optimization
- **Files**: `bengal/cli/commands/build.py`
- **Action**: Display CSS optimization summary (reduction %, types detected, features)
- **Depends on**: Task 4.2
- **Commit**: `cli(build): add CSS optimization report to build output`

#### Task 5.2: Add --no-css-optimize Flag
- **Files**: `bengal/cli/commands/build.py`, `bengal/cli/commands/serve.py`
- **Action**: Add CLI flag to disable CSS optimization for dev mode
- **Commit**: `cli: add --no-css-optimize flag for build and serve commands`

---

### Phase 6: Testing

#### Task 6.1: Unit Tests for CSSOptimizer
- **Files**: `tests/unit/orchestration/test_css_optimizer.py`
- **Action**: Test type detection, feature detection, CSS generation, force include/exclude
- **Depends on**: Task 3.1
- **Commit**: `tests: add unit tests for CSSOptimizer`

#### Task 6.2: Unit Tests for Feature Detection
- **Files**: `tests/unit/orchestration/test_feature_detection.py`
- **Action**: Test mermaid, graph, data_tables detection from page content
- **Depends on**: Task 2.2
- **Commit**: `tests: add unit tests for feature detection in content discovery`

#### Task 6.3: Integration Test for Optimized Build
- **Files**: `tests/integration/test_css_optimization.py`
- **Action**: Test full build with optimization produces smaller CSS for blog-only site
- **Depends on**: Task 4.2
- **Commit**: `tests: add integration tests for CSS optimization end-to-end`

#### Task 6.4: Create Test Fixture Site
- **Files**: `tests/roots/test-blog-only/` (new directory)
- **Action**: Create minimal blog-only test site for CSS optimization tests
- **Commit**: `tests(roots): add test-blog-only fixture for CSS optimization tests`

---

### Phase 7: Documentation

#### Task 7.1: Add Configuration Documentation
- **Files**: `site/content/docs/configuration/css.md`
- **Action**: Document css: config section with examples
- **Commit**: `docs: add CSS optimization configuration reference`

#### Task 7.2: Update Theme Development Guide
- **Files**: `site/content/docs/extending/theme-customization.md`
- **Action**: Document css_manifest.py for theme developers
- **Commit**: `docs: add css_manifest.py documentation for theme developers`

---

### Phase 8: Validation

- [ ] Unit tests pass (`pytest tests/unit/orchestration/test_css_optimizer.py`)
- [ ] Feature detection tests pass (`pytest tests/unit/orchestration/test_feature_detection.py`)
- [ ] Integration tests pass (`pytest tests/integration/test_css_optimization.py`)
- [ ] Linter passes (`ruff check bengal/orchestration/css_optimizer.py`)
- [ ] Type checking passes (`pyright bengal/orchestration/css_optimizer.py`)
- [ ] Blog-only test site shows 50%+ CSS reduction
- [ ] Full site shows no regression

---

## Task Dependencies

```
Phase 1 (Manifest)
├── 1.1: css_manifest.py
└── 1.2: css_manifest_types.py

Phase 2 (Feature Detection)
├── 2.1: Site.features_detected ──┐
└── 2.2: ContentOrchestrator ────┴── depends on 2.1

Phase 3 (Optimizer)
├── 3.1: CSSOptimizer ─── depends on 1.1, 1.2
└── 3.2: convenience fn ─ depends on 3.1

Phase 4 (Integration)
├── 4.1: Config schema
├── 4.2: Build integration ─── depends on 3.1, 4.1
└── 4.3: Asset override ────── depends on 4.2

Phase 5 (CLI)
├── 5.1: Build output ──── depends on 4.2
└── 5.2: --no-css-optimize

Phase 6 (Tests) ──────────── depends on 3.1, 2.2, 4.2

Phase 7 (Docs) ───────────── depends on all above
```

---

## Execution Order (Recommended)

| Order | Task | Est. Time |
|-------|------|-----------|
| 1 | 1.1 CSS Manifest | 1h |
| 2 | 1.2 Manifest Types | 30m |
| 3 | 2.1 Site.features_detected | 15m |
| 4 | 2.2 Feature Detection | 1h |
| 5 | 3.1 CSSOptimizer | 2h |
| 6 | 3.2 Convenience Function | 15m |
| 7 | 4.1 Config Schema | 30m |
| 8 | 4.3 Asset Override | 30m |
| 9 | 4.2 Build Integration | 1h |
| 10 | 6.4 Test Fixture | 30m |
| 11 | 6.1 Unit Tests (Optimizer) | 1h |
| 12 | 6.2 Unit Tests (Features) | 30m |
| 13 | 6.3 Integration Tests | 1h |
| 14 | 5.1 CLI Output | 30m |
| 15 | 5.2 CLI Flag | 15m |
| 16 | 7.1 Config Docs | 30m |
| 17 | 7.2 Theme Docs | 30m |

**Total**: ~11 hours

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Theme without manifest | Graceful fallback: skip optimization |
| Wrong type detection | Extensive unit tests + force-include config |
| Build performance impact | Target < 50ms; cache optimization result |
| CSS layer conflicts | Follow existing @layer pattern exactly |

---

## Changelog Entry

```markdown
### Added

- **CSS Tree Shaking**: Automatic content-aware CSS optimization reduces bundle size by 50%+ for single-purpose sites (blog-only, docs-only). No configuration required. (#xxx)
  - Detects content types (blog, doc, tutorial, etc.) from pages and sections
  - Detects features (search, graph, mermaid) from content and config
  - Generates minimal `style.css` with only needed imports
  - New `css:` config section for overrides (`include`, `exclude`, `all_palettes`)
  - `--no-css-optimize` flag for development mode
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Blog-only CSS reduction | ≥ 50% |
| Docs-only CSS reduction | ≥ 50% |
| Mixed site reduction | ≥ 30% |
| Build time impact | < 50ms |
| External dependencies | 0 |
| Test coverage | 90%+ for optimizer |
