# Plan: Page Hero Template Separation

**Status**: Ready  
**RFC**: `plan/drafted/rfc-page-hero-template-separation.md`  
**Created**: 2025-01-11  
**Estimate**: 9-10 hours  
**Subsystems**: Tests, Templates, Rendering

---

## Executive Summary

Break down the page-hero-api template refactoring into atomic, testable tasks. Each task has a single responsibility, clear acceptance criteria, and a pre-drafted commit message.

**Key Principle**: Tests first (Phase 0), then refactor with confidence.

---

## Phase 0: Regression Tests (2 hours)

Establish baseline before any refactoring. All subsequent phases must pass these tests.

### Task 0.1: Create test infrastructure

**File**: `tests/unit/rendering/test_page_hero_templates.py`

**What**:
- Create test file with fixtures for DocElement and Section objects
- Set up template rendering test helper using `TemplateEngine`
- Add helper to compare HTML output (ignoring whitespace)

**Acceptance**:
- [ ] Test file exists and imports correctly
- [ ] Can render a template with mock context
- [ ] HTML comparison helper works

**Commit**:
```
tests(rendering): add test infrastructure for page-hero template testing
```

---

### Task 0.2: Test API module page (element with children)

**What**:
- Create mock `DocElement` with classes and functions as children
- Render `page-hero-api.html` with element context
- Snapshot expected HTML output
- Verify badges, qualified name, description, stats render correctly

**Acceptance**:
- [ ] Test passes with current template
- [ ] Verifies element.qualified_name in title
- [ ] Verifies element.description renders
- [ ] Verifies stats show "X Classes, Y Functions"

**Commit**:
```
tests(rendering): add regression test for API module page hero with element
```

---

### Task 0.3: Test API section-index page (section, no element)

**What**:
- Create mock `Section` with subsections and pages
- Render `page-hero-api.html` with section context (element=None)
- Snapshot expected HTML output
- Verify section title, description, stats render correctly

**Acceptance**:
- [ ] Test passes with current template
- [ ] Verifies section.title in title
- [ ] Verifies section.metadata.description renders
- [ ] Verifies stats show "X Packages, Y Modules"

**Commit**:
```
tests(rendering): add regression test for API section-index page hero
```

---

### Task 0.4: Test CLI command page (element)

**What**:
- Create mock `DocElement` with element_type='command', options/arguments children
- Render `page-hero-api.html` with CLI command context
- Verify CLI-specific stats render correctly

**Acceptance**:
- [ ] Test passes with current template
- [ ] Verifies command qualified_name in title
- [ ] Verifies stats show "X Options, Y Arguments"

**Commit**:
```
tests(rendering): add regression test for CLI command page hero
```

---

### Task 0.5: Test CLI section-index page (section, CLI labels)

**What**:
- Create mock `Section` with CLI URL pattern (`/cli/...`)
- Render `page-hero-api.html` with CLI section context
- Verify CLI-specific labels ("Groups", "Commands" not "Packages", "Modules")

**Acceptance**:
- [ ] Test passes with current template
- [ ] Verifies stats show "X Groups, Y Commands" (not Packages/Modules)
- [ ] Documents current URL-sniffing behavior

**Commit**:
```
tests(rendering): add regression test for CLI section-index page hero with CLI labels
```

---

## Phase 1: Create New Templates (2 hours)

Create new template structure without modifying consumers. All tests from Phase 0 must still pass.

### Task 1.1: Create page-hero directory

**What**:
- Create `bengal/themes/default/templates/partials/page-hero/` directory
- Add empty `__init__` marker or README explaining the directory

**Acceptance**:
- [ ] Directory exists
- [ ] No template changes yet

**Commit**:
```
templates(partials): create page-hero/ directory for separated templates
```

---

### Task 1.2: Extract share dropdown component

**File**: `partials/page-hero/_share-dropdown.html`

**What**:
- Extract lines 49-124 from `page-hero-api.html` (share dropdown)
- Create standalone `_share-dropdown.html` (~70 lines)
- Include page URL computation logic

**Acceptance**:
- [ ] File contains complete share dropdown
- [ ] Includes Claude, ChatGPT, Gemini, Copilot links
- [ ] No changes to original template yet

**Commit**:
```
templates(page-hero): extract _share-dropdown.html component (~70 lines)
```

---

### Task 1.3: Create wrapper template

**File**: `partials/page-hero/_wrapper.html`

**What**:
- Create shared wrapper with breadcrumbs and share dropdown include
- Opens `.page-hero` div (caller closes it)
- Include navigation-components import for breadcrumbs

**Acceptance**:
- [ ] File renders breadcrumbs
- [ ] File includes `_share-dropdown.html`
- [ ] Opens but does NOT close `.page-hero` div
- [ ] ~40 lines

**Commit**:
```
templates(page-hero): create _wrapper.html with breadcrumbs and share dropdown
```

---

### Task 1.4: Create element stats component

**File**: `partials/page-hero/_element-stats.html`

**What**:
- Extract element children stats logic
- Handle classes, functions, methods, commands, options, arguments
- Expect `children` variable to be set by caller

**Acceptance**:
- [ ] Renders correct stats for API elements (Classes, Functions)
- [ ] Renders correct stats for CLI elements (Options, Arguments)
- [ ] ~30 lines

**Commit**:
```
templates(page-hero): create _element-stats.html for element children stats
```

---

### Task 1.5: Create element.html template

**File**: `partials/page-hero/element.html`

**What**:
- Create template for DocElement pages
- Include `_wrapper.html`, add badges, title, description, footer
- Use attribute access (element.description, element.qualified_name)
- Close `.page-hero` div

**Acceptance**:
- [ ] Renders same output as `page-hero-api.html` for element pages
- [ ] <80 lines
- [ ] No `is defined` checks for element
- [ ] Clear contract documented in header comment

**Commit**:
```
templates(page-hero): create element.html for DocElement pages (~60 lines)
```

---

### Task 1.6: Create section.html template

**File**: `partials/page-hero/section.html`

**What**:
- Create template for section-index pages
- Include `_wrapper.html`, add title, description, stats
- Use dict access (section.metadata.get())
- Support `hero_context.is_cli` for CLI label switching
- Close `.page-hero` div

**Acceptance**:
- [ ] Renders same output as `page-hero-api.html` for section pages
- [ ] <80 lines
- [ ] No URL sniffing - uses `hero_context.is_cli` or `page.type`
- [ ] Clear contract documented in header comment

**Commit**:
```
templates(page-hero): create section.html for section-index pages (~55 lines)
```

---

### Task 1.7: Verify new templates pass Phase 0 tests

**What**:
- Add parallel tests that render new templates directly
- Verify output matches original template output
- Ensure no regression in any test case

**Acceptance**:
- [ ] All Phase 0 tests pass with original template
- [ ] New templates produce equivalent output when tested directly
- [ ] Document any intentional differences

**Commit**:
```
tests(rendering): verify new page-hero templates match original output
```

---

## Phase 2: Migration (4-5 hours)

Update consumer templates to use new page-hero templates. Run Phase 0 tests after each subsystem.

### Task 2.1: Migrate api-reference/module.html

**File**: `api-reference/module.html`

**What**:
- Change `{% include 'partials/page-hero-api.html' %}`
- To `{% include 'partials/page-hero/element.html' %}`
- Ensure `element` context variable is passed

**Acceptance**:
- [ ] Template renders correctly
- [ ] Phase 0 API module test passes
- [ ] No visible changes in rendered output

**Commit**:
```
templates(api-reference): migrate module.html to page-hero/element.html
```

---

### Task 2.2: Migrate api-reference/section-index.html

**File**: `api-reference/section-index.html`

**What**:
- Change `{% include 'partials/page-hero-api.html' %}`
- To `{% include 'partials/page-hero/section.html' %}`
- Ensure `section` context variable is passed

**Acceptance**:
- [ ] Template renders correctly
- [ ] Phase 0 API section-index test passes
- [ ] Stats show "Packages, Modules" labels

**Commit**:
```
templates(api-reference): migrate section-index.html to page-hero/section.html
```

---

### Task 2.3: Migrate cli-reference/command.html

**File**: `cli-reference/command.html`

**What**:
- Change `{% include 'partials/page-hero-api.html' %}`
- To `{% include 'partials/page-hero/element.html' %}`
- Ensure `element` context variable is passed

**Acceptance**:
- [ ] Template renders correctly
- [ ] Phase 0 CLI command test passes
- [ ] Stats show "Options, Arguments" labels

**Commit**:
```
templates(cli-reference): migrate command.html to page-hero/element.html
```

---

### Task 2.4: Migrate cli-reference/command-group.html

**File**: `cli-reference/command-group.html`

**What**:
- Change `{% include 'partials/page-hero-api.html' %}`
- To `{% include 'partials/page-hero/element.html' %}`
- Ensure `element` context variable is passed

**Acceptance**:
- [ ] Template renders correctly
- [ ] CLI command-group renders with correct stats

**Commit**:
```
templates(cli-reference): migrate command-group.html to page-hero/element.html
```

---

### Task 2.5: Migrate cli-reference/section-index.html

**File**: `cli-reference/section-index.html`

**What**:
- Change `{% include 'partials/page-hero-api.html' %}`
- To `{% include 'partials/page-hero/section.html' %}`
- Add `{% set hero_context = {'is_cli': true} %}` before include
- Ensure `section` context variable is passed

**Acceptance**:
- [ ] Template renders correctly
- [ ] Phase 0 CLI section-index test passes
- [ ] Stats show "Groups, Commands" labels (not Packages/Modules)

**Commit**:
```
templates(cli-reference): migrate section-index.html to page-hero/section.html with is_cli context
```

---

### Task 2.6: Audit and migrate openapi-reference templates

**What**:
- Check which templates in `openapi-reference/` use `page-hero-api.html`
- Migrate to appropriate new template
- Run tests to verify

**Acceptance**:
- [ ] All openapi-reference templates migrated
- [ ] Tests pass (add tests if needed)

**Commit**:
```
templates(openapi-reference): migrate to page-hero/element.html and section.html
```

---

### Task 2.7: Update partials/page-hero.html if needed

**What**:
- Check if `partials/page-hero.html` includes `page-hero-api.html`
- If so, update to use appropriate new template
- This is for non-API pages that might share the hero

**Acceptance**:
- [ ] Verify current usage
- [ ] Update if needed
- [ ] Tests pass

**Commit**:
```
templates(partials): update page-hero.html to use new page-hero/ templates if applicable
```

---

## Phase 3: Cleanup (1 hour)

Finalize migration, add deprecation warning, update documentation.

### Task 3.1: Add deprecation warning to page-hero-api.html

**File**: `partials/page-hero-api.html`

**What**:
- Add Jinja comment at top warning of deprecation
- Add console.warn() in dev mode (if possible)
- Keep full functionality for backward compatibility

**Acceptance**:
- [ ] Deprecation warning visible in source
- [ ] Template still works for site-level overrides
- [ ] Warning appears in dev server output (if implemented)

**Commit**:
```
templates(partials): add deprecation warning to page-hero-api.html
```

---

### Task 3.2: Update theme customization documentation

**What**:
- Document new `page-hero/` template structure
- Explain migration path for site-level overrides
- Document `hero_context` pattern for CLI sections

**Acceptance**:
- [ ] Documentation updated
- [ ] Migration guide included
- [ ] `hero_context` usage documented

**Commit**:
```
docs(themes): document page-hero template separation and migration guide
```

---

### Task 3.3: Final verification and cleanup

**What**:
- Run full test suite
- Verify all Phase 0 tests pass
- Check for any console warnings or errors
- Remove any debug code

**Acceptance**:
- [ ] All tests pass
- [ ] No console errors
- [ ] Code is clean

**Commit**:
```
templates(page-hero): final cleanup and verification after migration
```

---

## Task Summary

| Phase | Tasks | Est. Time |
|-------|-------|-----------|
| Phase 0: Tests | 5 tasks | 2 hours |
| Phase 1: Create | 7 tasks | 2 hours |
| Phase 2: Migrate | 7 tasks | 4-5 hours |
| Phase 3: Cleanup | 3 tasks | 1 hour |
| **Total** | **22 tasks** | **9-10 hours** |

---

## Execution Order

```
Phase 0 (Tests)
├── 0.1 Test infrastructure
├── 0.2 API module test
├── 0.3 API section-index test
├── 0.4 CLI command test
└── 0.5 CLI section-index test

Phase 1 (Create) - after Phase 0 complete
├── 1.1 Create directory
├── 1.2 Extract share dropdown
├── 1.3 Create wrapper
├── 1.4 Create element stats
├── 1.5 Create element.html
├── 1.6 Create section.html
└── 1.7 Verify tests pass

Phase 2 (Migrate) - after Phase 1 complete
├── 2.1 api-reference/module.html
├── 2.2 api-reference/section-index.html
├── 2.3 cli-reference/command.html
├── 2.4 cli-reference/command-group.html
├── 2.5 cli-reference/section-index.html
├── 2.6 openapi-reference templates
└── 2.7 partials/page-hero.html

Phase 3 (Cleanup) - after Phase 2 complete
├── 3.1 Deprecation warning
├── 3.2 Documentation
└── 3.3 Final verification
```

---

## Dependencies

- **Phase 0 → Phase 1**: Must have tests before refactoring
- **Phase 1 → Phase 2**: Must have new templates before migration
- **Phase 2 → Phase 3**: Must complete migration before cleanup

---

## Rollback Plan

If issues discovered after partial migration:

1. **Revert consumer template changes** - Simple include path change back
2. **Keep new templates** - They don't affect anything until included
3. **Run Phase 0 tests** - Verify original behavior restored

---

## Quality Gates

### After Phase 0
- [ ] 5 regression tests pass
- [ ] Test coverage for API module, API section, CLI command, CLI section

### After Phase 1
- [ ] New templates exist and render correctly
- [ ] No changes to consumer templates yet
- [ ] All Phase 0 tests still pass

### After Phase 2
- [ ] All consumer templates migrated
- [ ] All Phase 0 tests pass
- [ ] No visible changes in rendered output

### After Phase 3
- [ ] Deprecation warning in place
- [ ] Documentation updated
- [ ] Full test suite passes
