# Implementation Plan: Document Applications RFC

**RFC Source**: `plan/drafted/rfc-document-applications.md`  
**Total Estimated Duration**: 12-19 working days (3-4 weeks)  
**Created**: 2025-12-23  
**Status**: ✅ **IMPLEMENTED** (2025-12-23)

---

## Implementation Summary

All 6 phases implemented with the following key changes:

| Phase | Feature | Implementation |
|-------|---------|----------------|
| 1 | View Transitions | `transitions.css`, meta tag in `base.html` |
| 2 | Speculation Rules | `postprocess/speculation.py`, config in `defaults.py` |
| 3 | Theme Controls | Native `[popover]` API, simplified `theme.js` |
| 4 | Mobile Navigation | Native `<dialog>` element, minimal `mobile-nav.js` |
| 5 | CSS State Tabs | `:target` selector, `tabs-native.css`, updated `tabs.py` |
| 6 | Author Intelligence | `analysis/content_intelligence.py`, `health/validators/accessibility.py` |

**Key Documentation**: `bengal/themes/default/assets/COMPONENT-PATTERNS.md`

**Legacy Code Removed**:
- All JS fallbacks for dialog/popover
- Backwards compatibility shims
- Classic dropdown implementations

---

## Pre-Implementation: Baseline Capture

**Duration**: 0.5 day  
**Priority**: MUST complete before Phase 1

### Tasks

- [ ] **BASELINE-1**: Build current site and capture Lighthouse metrics
  ```bash
  bengal build --site site/
  cd public && python -m http.server 8000 &
  lighthouse http://localhost:8000 --output=json --output-path=metrics/baseline-$(date +%Y%m%d).json
  ```

- [ ] **BASELINE-2**: Measure current JS bundle size
  ```bash
  find public -name "*.js" -exec wc -c {} + > metrics/js-baseline.txt
  ```

- [ ] **BASELINE-3**: Document current JS files in default theme
  - List all JS files in `bengal/themes/default/assets/js/`
  - Record line counts: `wc -l bengal/themes/default/assets/js/**/*.js`

- [ ] **BASELINE-4**: Create test page with all interactive components
  - Tabs, modals, mobile nav, theme dropdown, accordions
  - Use as visual regression reference

### Deliverables
- `metrics/baseline-YYYYMMDD.json` - Lighthouse report
- `metrics/js-baseline.txt` - JS file sizes
- `metrics/component-inventory.md` - Current interactive components

---

## Phase 1: View Transitions (Foundation)

**Duration**: 1-2 days  
**Risk Level**: Low (purely additive)  
**Dependencies**: Baseline capture complete

### Tasks

- [ ] **VT-1**: Add view transition meta tag to base template
  - File: `bengal/themes/default/templates/base.html`
  - Add: `<meta name="view-transition" content="same-origin">`
  - Conditional on config flag

- [ ] **VT-2**: Create transitions CSS file
  - File: `bengal/themes/default/assets/css/base/transitions.css`
  - Define animations: `fade-slide-out`, `fade-slide-in`
  - Named transitions for: `main-content`, `docs-nav`, `toc`, `hero`

- [ ] **VT-3**: Add `view-transition-name` to key elements
  - `base.html`: Add to `<main>`, nav elements
  - Use CSS custom properties for names (theme-overridable)

- [ ] **VT-4**: Add configuration schema
  - File: `bengal/config/defaults.py`
  - Add `document_application.navigation.view_transitions` config

- [ ] **VT-5**: Add reduced motion respect
  ```css
  @media (prefers-reduced-motion: reduce) {
    ::view-transition-group(*),
    ::view-transition-old(*),
    ::view-transition-new(*) {
      animation: none !important;
    }
  }
  ```

- [ ] **VT-6**: Write unit tests
  - File: `tests/unit/rendering/test_view_transitions.py`
  - Test: meta tag present when enabled
  - Test: meta tag absent when disabled
  - Test: CSS includes transition definitions

### Acceptance Criteria
- [ ] Navigation between pages shows smooth crossfade animation (Chrome/Firefox/Safari/Edge)
- [ ] Config `view_transitions: false` disables the feature
- [ ] `prefers-reduced-motion` users see instant transitions
- [ ] Lighthouse Performance score ≥ baseline

### Files Changed
```
bengal/themes/default/templates/base.html         [modify]
bengal/themes/default/assets/css/base/transitions.css  [create]
bengal/config/defaults.py                         [modify]
tests/unit/rendering/test_view_transitions.py     [create]
```

---

## Phase 2: Speculation Rules (Performance)

**Duration**: 1-2 days  
**Risk Level**: Low (additive, graceful degradation)  
**Dependencies**: Phase 1 complete

### Tasks

- [ ] **SR-1**: Create speculation rules generator
  - File: `bengal/postprocess/speculation.py`
  - Class: `SpeculationRulesGenerator`
  - Generate JSON based on site structure

- [ ] **SR-2**: Implement link pattern analyzer
  - File: `bengal/analysis/link_patterns.py`
  - Analyze internal links, detect patterns
  - Identify high-value prefetch candidates (nav links, related content)

- [ ] **SR-3**: Inject speculation rules into page head
  - Update `base.html` to include `<script type="speculationrules">`
  - Conditional on config flag

- [ ] **SR-4**: Add configuration options
  - `speculation.enabled`: bool
  - `speculation.prerender.eagerness`: conservative | moderate | eager
  - `speculation.prefetch.patterns`: list of glob patterns
  - `speculation.auto_generate`: bool

- [ ] **SR-5**: Implement pattern matching for rules
  - Support: `/docs/*`, `/blog/*`, specific paths
  - Support: exclusion patterns (external links, downloads)

- [ ] **SR-6**: Write tests
  - File: `tests/unit/postprocess/test_speculation_rules.py`
  - Test: JSON schema validity
  - Test: Pattern matching logic
  - Test: Exclusion of external links

### Acceptance Criteria
- [ ] Speculation rules JSON injected into pages when enabled
- [ ] Chrome DevTools shows prerender/prefetch activity
- [ ] Firefox/Safari gracefully ignore (no errors)
- [ ] Config allows disabling or adjusting aggressiveness
- [ ] External links excluded from prerender rules

### Files Changed
```
bengal/postprocess/speculation.py                 [create]
bengal/postprocess/__init__.py                    [modify]
bengal/analysis/link_patterns.py                  [create]
bengal/themes/default/templates/base.html         [modify]
bengal/config/defaults.py                         [modify]
tests/unit/postprocess/test_speculation_rules.py  [create]
```

---

## Phase 3: Theme Controls Migration (Popover)

**Duration**: 1-2 days  
**Risk Level**: Medium (user-visible change)  
**Dependencies**: Phase 2 complete

### Tasks

- [ ] **TC-1**: Refactor theme-controls.html to use popover
  - File: `bengal/themes/default/templates/partials/theme-controls.html`
  - Replace custom dropdown with `popover` attribute
  - Add `popovertarget` to trigger button

- [ ] **TC-2**: Simplify theme.js
  - File: `bengal/themes/default/assets/js/core/theme.js`
  - Remove: dropdown open/close logic, click-outside handling
  - Keep: localStorage persistence, theme application logic

- [ ] **TC-3**: Add popover styles
  - File: `bengal/themes/default/assets/css/components/dropdowns.css`
  - Style `[popover]` elements
  - Add open/close animations via `@starting-style`

- [ ] **TC-4**: Update ARIA attributes
  - Ensure semantic correctness with popover pattern
  - Test with screen reader

- [ ] **TC-5**: Write tests
  - File: `tests/unit/themes/test_theme_controls.py`
  - Test: popover attributes present
  - Test: theme persistence works

### Acceptance Criteria
- [ ] Theme dropdown opens/closes via popover API
- [ ] Escape key closes dropdown (browser-native)
- [ ] Click outside closes dropdown (browser-native)
- [ ] Theme selection persists across page loads
- [ ] Works without JavaScript (dropdown opens, selections visible)

### Files Changed
```
bengal/themes/default/templates/partials/theme-controls.html  [modify]
bengal/themes/default/assets/js/core/theme.js                 [modify]
bengal/themes/default/assets/css/components/dropdowns.css     [modify]
tests/unit/themes/test_theme_controls.py                      [create]
```

---

## Phase 4: Mobile Navigation Migration (Dialog)

**Duration**: 2-3 days  
**Risk Level**: Medium (user-visible, accessibility-critical)  
**Dependencies**: Phase 3 complete

### Tasks

- [ ] **MN-1**: Convert mobile nav to `<dialog>` element
  - File: `bengal/themes/default/templates/base.html`
  - Replace custom drawer with `<dialog id="mobile-nav">`
  - Add `form method="dialog"` for close button

- [ ] **MN-2**: Create dialog-as-drawer CSS
  - File: `bengal/themes/default/assets/css/components/navigation.css`
  - Slide-in animation from left
  - Use `@starting-style` for entry animation
  - Style `::backdrop` with blur

- [ ] **MN-3**: Minimize mobile-nav.js
  - File: `bengal/themes/default/assets/js/enhancements/mobile-nav.js`
  - Remove: toggle logic, focus trap, backdrop handling, inert
  - Keep: close-on-link-click for same-page nav (~20 lines)

- [ ] **MN-4**: Test accessibility
  - Focus trap works (browser-native)
  - Screen reader announces dialog
  - Escape key closes
  - Focus returns to trigger

- [ ] **MN-5**: Test responsive behavior
  - Dialog only used on mobile breakpoint
  - Desktop nav unchanged

- [ ] **MN-6**: Write tests
  - File: `tests/unit/themes/test_mobile_nav.py`
  - Test: dialog element present
  - Test: ARIA attributes correct

### Acceptance Criteria
- [ ] Mobile nav slides in from left with smooth animation
- [ ] Browser handles focus trapping (no custom JS)
- [ ] Escape key closes nav
- [ ] Backdrop click closes nav
- [ ] Screen reader announces "dialog" when opened
- [ ] Focus returns to hamburger button on close
- [ ] JS reduced from ~285 lines to ~20 lines

### Files Changed
```
bengal/themes/default/templates/base.html                        [modify]
bengal/themes/default/assets/css/components/navigation.css       [modify]
bengal/themes/default/assets/js/enhancements/mobile-nav.js       [modify/minimize]
tests/unit/themes/test_mobile_nav.py                             [create]
```

---

## Phase 5: CSS State Machine Tabs

**Duration**: 4-5 days  
**Risk Level**: High (breaking change potential, complex refactor)  
**Dependencies**: Phase 4 complete

### Sub-Phase 5A: Directive Refactor (Days 1-2)

- [ ] **TABS-1**: Analyze current tabs.py implementation
  - File: `bengal/directives/tabs.py`
  - Document current HTML output structure
  - Identify all configuration options

- [ ] **TABS-2**: Design new HTML structure
  - Use `href="#id"` fragment links instead of `data-tab-target`
  - Add `role="tablist"`, `role="tab"`, `role="tabpanel"`
  - Add `aria-selected`, `aria-controls` attributes
  - Add `data-pane` attribute for CSS pairing

- [ ] **TABS-3**: Refactor `TabSetDirective.render()`
  - Output `:target`-compatible HTML
  - Generate unique IDs: `{tab-set-id}-{tab-slug}`
  - Add new ARIA attributes

- [ ] **TABS-4**: Add configuration option for native vs enhanced
  - `tabs: css_state_machine | enhanced | classic`
  - Default to `enhanced` for backward compatibility

### Sub-Phase 5B: CSS Implementation (Day 3)

- [ ] **TABS-5**: Create tabs-native.css
  - File: `bengal/themes/default/assets/css/components/tabs-native.css`
  - Default pane visibility logic
  - `:target` pane activation
  - `:has()` for active tab styling

- [ ] **TABS-6**: Handle the first-tab-default problem
  - Show first tab when no `:target`
  - Hide first tab when another is targeted
  ```css
  .tabs:has(.tab-pane:target) .tab-pane:first-of-type:not(:target) {
    display: none;
  }
  ```

- [ ] **TABS-7**: Implement CSS generation strategy
  - Option A (preferred): Generic CSS with `data-pane` attributes
  - Option B (fallback): Inline scoped styles per tab set

### Sub-Phase 5C: Testing & Migration (Days 4-5)

- [ ] **TABS-8**: Test edge cases
  - Nested tab sets
  - Multiple tab sets on same page
  - Tab set with single tab
  - Very long tab labels

- [ ] **TABS-9**: Create migration script
  - File: `scripts/migrate_tabs_syntax.py`
  - Detect old tab syntax in content
  - Generate migration suggestions

- [ ] **TABS-10**: Write comprehensive tests
  - File: `tests/unit/directives/test_tabs_native.py`
  - Test: HTML structure correct
  - Test: ARIA attributes present
  - Test: URL fragments work

- [ ] **TABS-11**: Keep JS fallback for sync feature
  - File: `bengal/themes/default/assets/js/enhancements/tabs.js`
  - Minimize to ~50 lines
  - Only handle `data-sync-group` synchronized tabs

- [ ] **TABS-12**: Update documentation
  - Document new tab behavior
  - Document URL-addressable tabs
  - Migration guide for existing sites

### Acceptance Criteria
- [ ] Tabs work without JavaScript
- [ ] URL fragment updates on tab click: `/page#tab-name`
- [ ] Back button navigates through tab history
- [ ] Direct URL `/page#specific-tab` opens that tab
- [ ] First tab shows by default when no fragment
- [ ] Synced tabs feature still available via opt-in JS
- [ ] Existing tab directive syntax unchanged (backward compatible)

### Files Changed
```
bengal/directives/tabs.py                                        [major modify]
bengal/themes/default/assets/css/components/tabs-native.css      [create]
bengal/themes/default/assets/css/components/tabs.css             [modify]
bengal/themes/default/assets/js/enhancements/tabs.js             [minimize]
scripts/migrate_tabs_syntax.py                                   [create]
tests/unit/directives/test_tabs_native.py                        [create]
site/content/docs/directives/tabs.md                             [update]
```

---

## Phase 6: Author-Time Intelligence

**Duration**: 3-5 days  
**Risk Level**: Low-Medium (new features, no breaking changes)  
**Dependencies**: Phase 5 complete

### Tasks

- [ ] **AI-1**: Enhance link pattern analysis
  - File: `bengal/analysis/link_patterns.py`
  - Analyze link frequency across site
  - Identify navigation hotpaths

- [ ] **AI-2**: Create content intelligence module
  - File: `bengal/analysis/content_intelligence.py`
  - Detect: "This section has code examples in multiple languages"
  - Suggest: "Generate CSS-state tabs"
  - Detect: "These pages share taxonomy"
  - Suggest: "Aggressive prefetch"

- [ ] **AI-3**: Add accessibility analysis
  - File: `bengal/health/validators/accessibility.py`
  - Check: Heading structure
  - Check: Image alt text
  - Check: Link text quality
  - Emit warnings during build

- [ ] **AI-4**: Integrate intelligence into speculation rules
  - Use link frequency to adjust eagerness
  - High-traffic paths: `eager`
  - Normal paths: `moderate`
  - Low-traffic: `conservative`

- [ ] **AI-5**: Add build-time reporting
  - Summary of Document Application optimizations applied
  - List of accessibility warnings
  - Speculation rules statistics

- [ ] **AI-6**: Write tests
  - File: `tests/unit/analysis/test_content_intelligence.py`
  - Test: Pattern detection logic
  - Test: Suggestion accuracy

### Acceptance Criteria
- [ ] Build output includes Document Application summary
- [ ] Accessibility warnings emitted for issues
- [ ] Speculation rules adapt to content patterns
- [ ] Build time < 2x baseline for large sites

### Files Changed
```
bengal/analysis/content_intelligence.py             [create]
bengal/analysis/link_patterns.py                    [enhance]
bengal/health/validators/accessibility.py           [create]
bengal/postprocess/speculation.py                   [enhance]
tests/unit/analysis/test_content_intelligence.py    [create]
```

---

## Post-Implementation: Validation

**Duration**: 1-2 days  
**Dependencies**: All phases complete

### Tasks

- [ ] **VAL-1**: Capture final Lighthouse metrics
  - Compare against baseline
  - Document improvements

- [ ] **VAL-2**: Measure final JS bundle size
  - Target: < 15 KB (down from ~25-40 KB)

- [ ] **VAL-3**: Browser testing matrix
  - [ ] Chrome: All features
  - [ ] Firefox: All features (View Transitions since v144)
  - [ ] Safari: All except Speculation Rules
  - [ ] Edge: All features

- [ ] **VAL-4**: Accessibility audit
  - Run axe-core on built site
  - Manual screen reader testing

- [ ] **VAL-5**: Performance testing
  - Navigation timing (target: < 100ms perceived)
  - No flash of unstyled content

- [ ] **VAL-6**: Create release notes
  - Document new features
  - Migration guide for existing sites
  - Configuration reference

### Success Metrics
| Metric | Baseline | Target | Actual |
|--------|----------|--------|--------|
| Total JS Size | ~25-40 KB | < 15 KB | TBD |
| Lighthouse Performance | TBD | 95+ | TBD |
| Lighthouse Accessibility | TBD | 100 | TBD |
| Time to Interactive | TBD | < 1500ms | TBD |
| Navigation Perceived | ~150-400ms | < 100ms | TBD |

---

## Configuration Reference

```yaml
# bengal.yaml - Full Document Application config
document_application:
  enabled: true

  navigation:
    view_transitions: true
    transition_style: crossfade  # crossfade | slide | morph | none
    speculation_rules: auto      # auto | manual | disabled
    scroll_restoration: true

  speculation:
    prerender:
      eagerness: conservative    # conservative | moderate | eager
      patterns:
        - "/docs/*"
    prefetch:
      eagerness: conservative
      patterns:
        - "/*"
    auto_generate: true

  interactivity:
    tabs: css_state_machine      # css_state_machine | enhanced | classic
    accordions: native_details   # native_details | enhanced | classic
    modals: native_dialog        # native_dialog | enhanced
    tooltips: popover            # popover | enhanced | title_attr
    code_copy: enhanced          # Requires JS for clipboard

  fallback:
    no_js: graceful              # graceful | reduced | error
    legacy_browsers: basic       # basic | unsupported

  # Feature flags for rollback
  features:
    view_transitions: true
    speculation_rules: true
    native_tabs: true
    native_dialogs: true
    native_popovers: true
```

---

## Risk Mitigation Checklist

- [ ] Each phase is a separate PR (enables granular rollback)
- [ ] Feature flags allow disabling individual features
- [ ] Backward compatibility maintained (old configs still work)
- [ ] No breaking changes to directive syntax
- [ ] Comprehensive test coverage before merge
- [ ] Manual QA on each browser before release

---

## Timeline Summary

| Week | Phases | Key Deliverables |
|------|--------|------------------|
| 1 | Baseline + 1 + 2 | View Transitions, Speculation Rules |
| 2 | 3 + 4 | Theme Controls, Mobile Nav |
| 3 | 5 (start) | CSS Tabs directive refactor |
| 4 | 5 (complete) + 6 (start) | CSS Tabs complete, Intelligence |
| 5 | 6 (complete) + Validation | Final testing, release |

**Ship Strategy:**
- **v0.2.x**: Phases 1-2 (additive, low risk)
- **v0.3.x**: Phases 3-5 (opt-in, feature flags)
- **v0.4.x**: Phase 6 + make Document Application default for new sites
