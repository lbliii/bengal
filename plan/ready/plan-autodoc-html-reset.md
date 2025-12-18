# Plan: Autodoc HTML/CSS Complete Reset

**Status**: Ready  
**RFC**: `plan/drafted/rfc-autodoc-html-reset.md`  
**Estimated Duration**: 8 days  
**Confidence**: 90% 🟢

---

## Executive Summary

Strip 7,044 lines of autodoc CSS across 16 files. Replace with a single ~400-line `autodoc.css` file. Migrate all autodoc templates to use a unified HTML skeleton with semantic structure and data attributes.

---

## Phase 1: Foundation (Day 1)

### 1.1 Create new autodoc.css file

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Create `autodoc.css` with `@layer autodoc` wrapper
- [ ] Add CSS custom properties (tokens) block
- [ ] Add dark mode token overrides
- [ ] Add surgical `.prose` override rules
- [ ] Add typography exclusions for `article[data-autodoc]`

**Commit**: `css(autodoc): create foundational autodoc.css with layer, tokens, and prose overrides`

### 1.2 Add base layout styles

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc` container styles (flex column, gap)
- [ ] Add `.autodoc-header` layout
- [ ] Add `.autodoc-section` layout
- [ ] Add responsive container queries

**Commit**: `css(autodoc): add base layout styles for article, header, and sections`

### 1.3 Add typography styles

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc-title` styles
- [ ] Add `.autodoc-section-title` styles
- [ ] Add `.autodoc-label` styles (small uppercase)
- [ ] Add `.autodoc-description` styles

**Commit**: `css(autodoc): add typography styles for titles, labels, and descriptions`

---

## Phase 2: Component Styles (Day 2)

### 2.1 Add code styling

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc-signature` block styles
- [ ] Add `.autodoc-usage` block styles
- [ ] Add `[data-autodoc] code` inline code styles
- [ ] Add `[data-autodoc] pre code` reset for code blocks

**Commit**: `css(autodoc): add signature, usage, and code styling`

### 2.2 Add badge styling

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc-badges` container
- [ ] Add `.autodoc-badge` base styles
- [ ] Add `[data-badge="deprecated"]` variant
- [ ] Add `[data-badge="async"]` variant
- [ ] Add `[data-badge="abstract"]` variant

**Commit**: `css(autodoc): add badge styles with data-badge variants`

### 2.3 Add table styling

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc-table` base styles
- [ ] Add `.autodoc-cell-*` cell styles (name, type, default, desc)
- [ ] Add `tr[data-required="true"]` indicator
- [ ] Add hover states
- [ ] Add mobile responsive stacking

**Commit**: `css(autodoc): add table styles with responsive mobile layout`

### 2.4 Add definition list styling

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc-params` container
- [ ] Add `.autodoc-param` grid layout
- [ ] Add `.autodoc-param-name`, `.autodoc-param-type` styles
- [ ] Add `.autodoc-param-desc`, `.autodoc-param-default` styles

**Commit**: `css(autodoc): add definition list styles for parameters`

---

## Phase 3: Advanced Components (Day 3)

### 3.1 Add collapsible member styling

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc-member` details/summary styles
- [ ] Add `.autodoc-member-header` layout with chevron
- [ ] Add `.autodoc-member-name`, `.autodoc-member-sig` styles
- [ ] Add `.autodoc-member-body` content area
- [ ] Add open/closed state transitions

**Commit**: `css(autodoc): add collapsible member card styles using native details`

### 3.2 Add card grid styling

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc-cards` grid container
- [ ] Add `.autodoc-card` link styles
- [ ] Add `.autodoc-card-name`, `.autodoc-card-desc` styles
- [ ] Add hover and focus states
- [ ] Add `.autodoc-method` HTTP method badges (GET/POST/etc.)

**Commit**: `css(autodoc): add card grid and HTTP method badge styles`

### 3.3 Add stats and source link styling

**File**: `bengal/themes/default/assets/css/components/autodoc.css`

**Tasks**:
- [ ] Add `.autodoc-stats` row layout
- [ ] Add `.autodoc-stat-value`, `.autodoc-stat-label` styles
- [ ] Add `.autodoc-source` link styles
- [ ] Add `.autodoc-returns`, `.autodoc-raises` section styles

**Commit**: `css(autodoc): add stats row, source link, and returns/raises styles`

### 3.4 Test CSS in isolation

**Tasks**:
- [ ] Create `tests/_fixtures/autodoc-skeleton-test.html` with all sections
- [ ] Load standalone HTML file with only `autodoc.css`
- [ ] Verify all components render correctly
- [ ] Test light/dark mode switching
- [ ] Test responsive breakpoints (375px, 768px, 1200px)
- [ ] Fix any issues discovered

**Commit**: `tests: add autodoc CSS isolation test fixture`

---

## Phase 4: Template Partials (Day 4-5)

### 4.1 Create partials directory

**Directory**: `bengal/themes/default/templates/autodoc/partials/`

**Tasks**:
- [ ] Create `partials/` directory
- [ ] Create `_README.md` documenting partial usage

**Commit**: `templates(autodoc): create partials directory structure`

### 4.2 Create header partial

**File**: `bengal/themes/default/templates/autodoc/partials/header.html`

**Tasks**:
- [ ] Create header partial with badges, title, description
- [ ] Add conditional stats row
- [ ] Add conditional source link
- [ ] Test with sample data

**Commit**: `templates(autodoc): add header partial with badges, title, stats`

### 4.3 Create signature and usage partials

**Files**:
- `bengal/themes/default/templates/autodoc/partials/signature.html`
- `bengal/themes/default/templates/autodoc/partials/usage.html`

**Tasks**:
- [ ] Create signature partial for code signatures
- [ ] Create usage partial for CLI/import usage blocks
- [ ] Test with Python and CLI data

**Commit**: `templates(autodoc): add signature and usage partials`

### 4.4 Create params partials

**Files**:
- `bengal/themes/default/templates/autodoc/partials/params-table.html`
- `bengal/themes/default/templates/autodoc/partials/params-list.html`

**Tasks**:
- [ ] Create table partial for complex parameter displays
- [ ] Create definition list partial for simple parameters
- [ ] Add data-required attribute handling
- [ ] Add mobile-friendly data-label attributes

**Commit**: `templates(autodoc): add params-table and params-list partials`

### 4.5 Create returns and raises partials

**Files**:
- `bengal/themes/default/templates/autodoc/partials/returns.html`
- `bengal/themes/default/templates/autodoc/partials/raises.html`

**Tasks**:
- [ ] Create returns partial with type and description
- [ ] Create raises partial as definition list

**Commit**: `templates(autodoc): add returns and raises partials`

### 4.6 Create examples partial

**File**: `bengal/themes/default/templates/autodoc/partials/examples.html`

**Tasks**:
- [ ] Create examples partial with titled code blocks
- [ ] Support multiple examples

**Commit**: `templates(autodoc): add examples partial`

### 4.7 Create members partial

**File**: `bengal/themes/default/templates/autodoc/partials/members.html`

**Tasks**:
- [ ] Create collapsible members partial using `<details>`
- [ ] Add signature and badges in summary
- [ ] Add recursive body content
- [ ] Support methods, attributes, properties

**Commit**: `templates(autodoc): add collapsible members partial`

### 4.8 Create cards partial

**File**: `bengal/themes/default/templates/autodoc/partials/cards.html`

**Tasks**:
- [ ] Create card grid partial
- [ ] Support command, class, function, endpoint card types
- [ ] Add HTTP method badge support for OpenAPI

**Commit**: `templates(autodoc): add cards partial for subcommands and endpoints`

---

## Phase 5: CLI Template Migration (Day 5-6)

### 5.1 Migrate CLI command template

**File**: `bengal/themes/default/templates/cli-reference/command.html`

**Tasks**:
- [ ] Replace `<article class="prose docs-content">` with `<article data-autodoc data-type="cli">`
- [ ] Replace inline header with `{% include 'autodoc/partials/header.html' %}`
- [ ] Replace usage block with `{% include 'autodoc/partials/usage.html' %}`
- [ ] Replace options table with `{% include 'autodoc/partials/params-table.html' %}`
- [ ] Replace examples with `{% include 'autodoc/partials/examples.html' %}`
- [ ] Run integration test checklist

**Commit**: `templates(cli): migrate command.html to autodoc skeleton`

### 5.2 Migrate CLI command group template

**File**: `bengal/themes/default/templates/cli-reference/command_group.html`

**Tasks**:
- [ ] Update article root with data-autodoc attributes
- [ ] Replace header with partial
- [ ] Replace subcommands grid with `{% include 'autodoc/partials/cards.html' %}`
- [ ] Run integration test checklist

**Commit**: `templates(cli): migrate command_group.html to autodoc skeleton`

### 5.3 Migrate CLI module template

**File**: `bengal/themes/default/templates/cli-reference/module.html` (if exists)

**Tasks**:
- [ ] Update article root
- [ ] Replace sections with partials
- [ ] Run integration test checklist

**Commit**: `templates(cli): migrate module.html to autodoc skeleton`

### 5.4 Visual regression test: CLI

**Tasks**:
- [ ] Build site with `bengal build`
- [ ] Screenshot CLI pages before and after
- [ ] Compare rendered output
- [ ] Fix any visual regressions
- [ ] Test all palettes (default, snow-lynx, charcoal-bengal)

**Commit**: `fix(cli): resolve visual regressions from template migration` (if needed)

---

## Phase 6: Python API Template Migration (Day 6-7)

### 6.1 Migrate Python module template

**File**: `bengal/themes/default/templates/api-reference/module.html`

**Tasks**:
- [ ] Update article root with data-autodoc data-type="python"
- [ ] Replace header with partial
- [ ] Replace class/function cards with partials
- [ ] Run integration test checklist

**Commit**: `templates(api): migrate module.html to autodoc skeleton`

### 6.2 Migrate Python class template

**File**: `bengal/themes/default/templates/api-reference/class.html`

**Tasks**:
- [ ] Update article root
- [ ] Replace signature with partial
- [ ] Replace attributes table with partial
- [ ] Replace methods list with members partial
- [ ] Run integration test checklist

**Commit**: `templates(api): migrate class.html to autodoc skeleton`

### 6.3 Migrate Python function template

**File**: `bengal/themes/default/templates/api-reference/function.html`

**Tasks**:
- [ ] Update article root
- [ ] Replace signature with partial
- [ ] Replace parameters with partial
- [ ] Replace returns/raises with partials
- [ ] Replace examples with partial
- [ ] Run integration test checklist

**Commit**: `templates(api): migrate function.html to autodoc skeleton`

### 6.4 Visual regression test: Python API

**Tasks**:
- [ ] Build site with `bengal build`
- [ ] Screenshot API pages before and after
- [ ] Compare rendered output
- [ ] Fix any visual regressions

**Commit**: `fix(api): resolve visual regressions from template migration` (if needed)

---

## Phase 7: OpenAPI Template Migration (Day 7)

### 7.1 Migrate OpenAPI endpoint template

**File**: `bengal/themes/default/templates/openapi-reference/endpoint.html`

**Tasks**:
- [ ] Update article root with data-autodoc data-type="openapi"
- [ ] Replace header with partial (include HTTP method badge)
- [ ] Replace parameters with partial
- [ ] Replace request/response sections
- [ ] Run integration test checklist

**Commit**: `templates(openapi): migrate endpoint.html to autodoc skeleton`

### 7.2 Migrate OpenAPI schema template

**File**: `bengal/themes/default/templates/openapi-reference/schema.html` (if exists)

**Tasks**:
- [ ] Update article root
- [ ] Replace properties table with partial
- [ ] Run integration test checklist

**Commit**: `templates(openapi): migrate schema.html to autodoc skeleton`

### 7.3 Visual regression test: OpenAPI

**Tasks**:
- [ ] Build site and screenshot OpenAPI pages
- [ ] Compare rendered output
- [ ] Fix any visual regressions

**Commit**: `fix(openapi): resolve visual regressions from template migration` (if needed)

---

## Phase 8: Cleanup & Integration (Day 8)

### 8.1 Update CSS imports

**File**: `bengal/themes/default/assets/css/main.css` (or equivalent)

**Tasks**:
- [ ] Add `@import 'components/autodoc.css'`
- [ ] Comment out or remove old autodoc imports (but don't delete files yet)
- [ ] Build and verify site renders correctly

**Commit**: `css: integrate autodoc.css into main stylesheet`

### 8.2 Delete legacy CSS files

**Files to delete**:
```
bengal/themes/default/assets/css/components/api-explorer.css (2,629 lines)
bengal/themes/default/assets/css/components/api-docs.css (913 lines)
bengal/themes/default/assets/css/components/reference-docs.css (838 lines)
bengal/themes/default/assets/css/components/autodoc/_base.css (640 lines)
bengal/themes/default/assets/css/components/autodoc/_card.css (518 lines)
bengal/themes/default/assets/css/components/autodoc/_rest.css (370 lines)
bengal/themes/default/assets/css/components/autodoc/_reset.css (260 lines)
bengal/themes/default/assets/css/components/autodoc/_badges.css (177 lines)
bengal/themes/default/assets/css/components/autodoc/_table.css (145 lines)
bengal/themes/default/assets/css/components/autodoc/*.css (remaining files)
```

**Tasks**:
- [ ] Delete all files listed above
- [ ] Remove old import statements from main.css
- [ ] Build site and verify no broken references
- [ ] Run full integration test checklist

**Commit**: `css(autodoc): delete legacy CSS files (7,044 lines removed)`

### 8.3 Delete old template fragments (if any orphaned)

**Tasks**:
- [ ] Identify any orphaned template includes
- [ ] Delete unused template files
- [ ] Verify all includes resolve

**Commit**: `templates: remove orphaned autodoc template files` (if needed)

### 8.4 Final integration test

**Run full checklist**:

**Visual Tests**:
- [ ] Light mode: All sections render correctly
- [ ] Dark mode: Colors adapt, no contrast issues
- [ ] Palette switching: Test with snow-lynx, charcoal-bengal palettes
- [ ] Mobile (375px): Tables stack, cards single-column
- [ ] Tablet (768px): Layout transitions correctly
- [ ] Desktop (1200px+): Full layout, proper spacing

**Functional Tests**:
- [ ] `<details>` collapse/expand: Click toggles visibility
- [ ] Keyboard navigation: Tab through interactive elements
- [ ] Screen reader: VoiceOver announces structure correctly
- [ ] Code highlighting: Syntax highlighting still works
- [ ] Internal links: Anchor links to sections work
- [ ] External links: Source links open in new tab

**Integration Tests**:
- [ ] Search results: Autodoc pages appear with API badge
- [ ] Navigation: Docs sidebar highlights current page
- [ ] Breadcrumbs: Path renders correctly
- [ ] TOC: Table of contents picks up section headings
- [ ] No console errors: Check browser devtools

**Content Type Tests**:
- [ ] CLI command: Options table, usage block, examples
- [ ] CLI command group: Subcommand cards
- [ ] Python module: Class cards, function cards
- [ ] Python class: Attributes table, methods list, signature
- [ ] Python function: Parameters, returns, raises
- [ ] OpenAPI endpoint: Method badge, path, parameters

**Commit**: (no commit needed for testing)

### 8.5 Update documentation

**Tasks**:
- [ ] Update any internal docs referencing old CSS structure
- [ ] Document new partial system in `templates/autodoc/partials/_README.md`
- [ ] Move RFC to completed: `plan/drafted/rfc-autodoc-html-reset.md` → DELETE
- [ ] Add changelog entry

**Commit**: `docs: document autodoc skeleton and partial system`

---

## Success Metrics

| Metric | Before | Target | Actual |
|--------|--------|--------|--------|
| CSS lines | 7,044 | <500 | ___ |
| CSS files | 16 | 1 | ___ |
| HTML nesting | 5-6 levels | 2-3 levels | ___ |
| Unique class names | 200+ | <50 | ___ |
| Fix CLI table styling | >30 min | <5 min | ___ |
| New dev understand time | >30 min | <10 min | ___ |

---

## Risk Checkpoints

After each phase, verify:

- [ ] **Phase 3**: CSS isolation test passes (standalone HTML renders correctly)
- [ ] **Phase 5**: CLI templates render without visual regression
- [ ] **Phase 6**: Python API templates render without visual regression
- [ ] **Phase 7**: OpenAPI templates render without visual regression
- [ ] **Phase 8**: Full site builds without errors, all tests pass

**If visual regression detected**: Stop and fix before proceeding.

---

## File Summary

### New Files (11)
```
bengal/themes/default/assets/css/components/autodoc.css (~400 lines)
bengal/themes/default/templates/autodoc/partials/header.html
bengal/themes/default/templates/autodoc/partials/signature.html
bengal/themes/default/templates/autodoc/partials/usage.html
bengal/themes/default/templates/autodoc/partials/params-table.html
bengal/themes/default/templates/autodoc/partials/params-list.html
bengal/themes/default/templates/autodoc/partials/returns.html
bengal/themes/default/templates/autodoc/partials/raises.html
bengal/themes/default/templates/autodoc/partials/examples.html
bengal/themes/default/templates/autodoc/partials/members.html
bengal/themes/default/templates/autodoc/partials/cards.html
```

### Modified Files (~8)
```
bengal/themes/default/templates/cli-reference/command.html
bengal/themes/default/templates/cli-reference/command_group.html
bengal/themes/default/templates/api-reference/module.html
bengal/themes/default/templates/api-reference/class.html
bengal/themes/default/templates/api-reference/function.html
bengal/themes/default/templates/openapi-reference/endpoint.html
bengal/themes/default/templates/openapi-reference/schema.html
bengal/themes/default/assets/css/main.css
```

### Deleted Files (~16)
```
bengal/themes/default/assets/css/components/api-explorer.css
bengal/themes/default/assets/css/components/api-docs.css
bengal/themes/default/assets/css/components/reference-docs.css
bengal/themes/default/assets/css/components/autodoc/_base.css
bengal/themes/default/assets/css/components/autodoc/_card.css
bengal/themes/default/assets/css/components/autodoc/_rest.css
bengal/themes/default/assets/css/components/autodoc/_reset.css
bengal/themes/default/assets/css/components/autodoc/_badges.css
bengal/themes/default/assets/css/components/autodoc/_table.css
(+ remaining autodoc/*.css files)
```

---

## Commit History (Expected)

```
1.  css(autodoc): create foundational autodoc.css with layer, tokens, and prose overrides
2.  css(autodoc): add base layout styles for article, header, and sections
3.  css(autodoc): add typography styles for titles, labels, and descriptions
4.  css(autodoc): add signature, usage, and code styling
5.  css(autodoc): add badge styles with data-badge variants
6.  css(autodoc): add table styles with responsive mobile layout
7.  css(autodoc): add definition list styles for parameters
8.  css(autodoc): add collapsible member card styles using native details
9.  css(autodoc): add card grid and HTTP method badge styles
10. css(autodoc): add stats row, source link, and returns/raises styles
11. tests: add autodoc CSS isolation test fixture
12. templates(autodoc): create partials directory structure
13. templates(autodoc): add header partial with badges, title, stats
14. templates(autodoc): add signature and usage partials
15. templates(autodoc): add params-table and params-list partials
16. templates(autodoc): add returns and raises partials
17. templates(autodoc): add examples partial
18. templates(autodoc): add collapsible members partial
19. templates(autodoc): add cards partial for subcommands and endpoints
20. templates(cli): migrate command.html to autodoc skeleton
21. templates(cli): migrate command_group.html to autodoc skeleton
22. templates(cli): migrate module.html to autodoc skeleton
23. templates(api): migrate module.html to autodoc skeleton
24. templates(api): migrate class.html to autodoc skeleton
25. templates(api): migrate function.html to autodoc skeleton
26. templates(openapi): migrate endpoint.html to autodoc skeleton
27. templates(openapi): migrate schema.html to autodoc skeleton
28. css: integrate autodoc.css into main stylesheet
29. css(autodoc): delete legacy CSS files (7,044 lines removed)
30. docs: document autodoc skeleton and partial system
```
