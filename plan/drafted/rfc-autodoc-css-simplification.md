# RFC: Autodoc CSS Simplification

**Status**: Draft  
**Created**: 2025-12-12  
**Author**: Claude (pair programming session)  
**Related**:
- `bengal/themes/default/assets/css/components/autodoc-explorer.css` (current monolith)
- `plan/drafted/plan-autodoc-stability-and-dev-menu.md`

---

## Executive Summary

The autodoc CSS has grown to **2,633 lines** with **311 distinct `.api-*` classes** and **6+ card variants** that share 80% of their styling. This RFC proposes splitting the monolithic file, consolidating redundant card types, and establishing a cleaner architecture while preserving visual quality (including stagger animations).

---

## Problem Statement

### Current State (Evidence)

**File size**: `autodoc-explorer.css` is 2,633 lines
- Evidence: `wc -l bengal/themes/default/assets/css/components/autodoc-explorer.css`

**Card type proliferation**: 6+ similar card components
- `.api-member` (classes, functions, methods) - lines 325-426
- `.api-card` (legacy/fallback) - lines 1211-1307
- `.api-hub-card` (hub landing) - lines 2369-2557
- `.api-package-card` (section indexes) - lines 1565-1658
- `.api-module-card` (section indexes) - lines 1660-1736
- `.api-endpoint-card` (OpenAPI) - lines 1741-1834

**Shared patterns duplicated**: Each card type repeats:
- Window chrome styling (border-radius, shadows, backgrounds)
- Hover/focus states with glow effects
- Header/body/footer structure
- Icon containers
- Badge styling
- Animation keyframes

**Recent bugs caused by complexity**:
- Scrollbar flash during stagger animation (fixed with `overflow: clip`)
- Jinja whitespace issues in templates
- Difficulty reasoning about which card type to use where

### Impact

1. **Maintainability**: Changes require updating multiple similar sections
2. **Consistency**: Slight variations between card types create visual inconsistency
3. **Onboarding**: New contributors struggle to understand which component to use
4. **Performance**: Browser parses 2600+ lines even if page uses one card type
5. **Bug surface**: More code = more places for bugs to hide

---

## Goals

1. **Split** the monolithic CSS into focused, importable modules
2. **Consolidate** 6+ card types into 1-2 base components with modifiers
3. **Reduce** total CSS by ~40% through deduplication
4. **Preserve** visual quality, including stagger animations
5. **Improve** developer experience and maintainability

## Non-Goals

- Redesigning the visual language (terminal chrome, neumorphic shadows)
- Changing template structure (that's a separate effort)
- Removing features users depend on

---

## Proposed Architecture

### Phase 1: Split into Modules

Split `autodoc-explorer.css` (2,633 lines) into focused files:

```
components/
├── autodoc/
│   ├── _tokens.css          # (~60 lines) Design tokens & CSS custom properties
│   ├── _base.css            # (~200 lines) .autodoc-explorer container, sections
│   ├── _card.css            # (~300 lines) Unified .api-card component
│   ├── _table.css           # (~150 lines) .api-table variations
│   ├── _badges.css          # (~100 lines) All badge styles
│   ├── _signature.css       # (~80 lines) Code signature blocks
│   ├── _animations.css      # (~50 lines) Stagger reveal, transitions
│   ├── _grid.css            # (~100 lines) Grid layouts for index pages
│   ├── _hub.css             # (~150 lines) Hub-specific styles (if needed)
│   └── index.css            # Barrel file that @imports all modules
└── autodoc-explorer.css     # → becomes @import './autodoc/index.css'
```

**Estimated total**: ~1,200 lines (55% reduction)

### Phase 2: Consolidate Card Types

Replace 6 card types with **one unified `.api-card` component**:

```css
/* Base card - handles all shared styling */
.api-card {
  --card-accent: var(--color-primary);
  --card-radius: var(--api-window-radius);

  position: relative;
  background: var(--api-window-bg);
  border: 1px solid var(--api-window-border);
  border-radius: var(--card-radius);
  overflow: hidden;

  box-shadow: var(--api-shadow-diffused);
  transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

/* Variants via modifier classes */
.api-card--class    { --card-accent: var(--color-info); }
.api-card--function { --card-accent: var(--color-success); }
.api-card--method   { --card-accent: var(--color-secondary); }
.api-card--endpoint { --card-accent: var(--color-success); }
.api-card--command  { --card-accent: var(--color-primary); }
.api-card--package  { --card-accent: var(--color-primary); }
.api-card--hub      { --card-accent: var(--color-primary); }

/* Size variants */
.api-card--sm { --card-radius: 8px; padding: var(--space-2); }
.api-card--lg { --card-radius: 16px; padding: var(--space-5); }

/* Layout variants */
.api-card--collapsible { /* <details> specific styles */ }
.api-card--link        { /* <a> specific styles, hover lift */ }
.api-card--static      { /* non-interactive card */ }

/* Subcomponents (BEM) */
.api-card__header  { /* ... */ }
.api-card__icon    { /* ... */ }
.api-card__title   { /* ... */ }
.api-card__meta    { /* ... */ }
.api-card__body    { /* ... */ }
.api-card__footer  { /* ... */ }
.api-card__toggle  { /* for collapsible */ }
```

### Phase 3: Simplify Animations

Keep stagger animation but centralize it:

```css
/* _animations.css */

/* Base reveal animation */
@keyframes api-reveal {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Apply to any grid/list that wants stagger */
.api-card-list--animated > .api-card {
  animation: api-reveal 0.3s ease backwards;
}

/* Stagger delays (works for any animated list) */
.api-card-list--animated > *:nth-child(1) { animation-delay: 0ms; }
.api-card-list--animated > *:nth-child(2) { animation-delay: 40ms; }
.api-card-list--animated > *:nth-child(3) { animation-delay: 80ms; }
.api-card-list--animated > *:nth-child(4) { animation-delay: 120ms; }
.api-card-list--animated > *:nth-child(5) { animation-delay: 160ms; }
.api-card-list--animated > *:nth-child(n+6) { animation-delay: 200ms; }

/* Container must clip to prevent scrollbar flash */
.api-card-list--animated {
  overflow: clip;
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  .api-card-list--animated > * {
    animation: none !important;
  }
}
```

---

## Migration Strategy

### Step 1: Create New File Structure (Non-Breaking)

1. Create `components/autodoc/` directory
2. Extract tokens into `_tokens.css`
3. Create barrel `index.css` that imports old monolith
4. Verify nothing breaks

### Step 2: Extract Modules Incrementally

For each module:
1. Copy relevant CSS to new file
2. Update `index.css` to import new file
3. Comment out (don't delete) original in monolith
4. Test thoroughly
5. Delete commented code once stable

### Step 3: Consolidate Cards

1. Create unified `.api-card` in `_card.css`
2. Add aliases for backward compatibility:
   ```css
   /* Temporary aliases - remove after template migration */
   .api-member { @extend .api-card; @extend .api-card--collapsible; }
   .api-hub-card { @extend .api-card; @extend .api-card--link; @extend .api-card--lg; }
   ```
3. Migrate templates one at a time to use new classes
4. Remove aliases once all templates updated

### Step 4: Update Templates

Update templates to use new unified classes:

**Before:**
```html
<details class="api-member api-member--class">
```

**After:**
```html
<details class="api-card api-card--class api-card--collapsible">
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Visual regressions | Medium | High | Screenshot comparison tests, staged rollout |
| Breaking existing sites | Low | High | Backward-compatible aliases during migration |
| Increased import complexity | Low | Low | Barrel file hides internal structure |
| Browser caching issues | Low | Medium | Cache-bust via build hash |

---

## Success Criteria

- [ ] CSS reduced from 2,633 lines to <1,500 lines (43% reduction)
- [ ] Card types reduced from 6+ to 1 unified component
- [ ] No visual regressions (verified via screenshot tests)
- [ ] Stagger animations preserved and working
- [ ] Existing sites continue to work without template changes (via aliases)
- [ ] New file structure documented in CSS_ARCHITECTURE.md

---

## Alternatives Considered

### 1. Do Nothing
**Rejected**: Technical debt will continue to accumulate, making future changes harder.

### 2. Complete Redesign
**Rejected**: Too risky, and current visual design is good. Just needs cleanup.

### 3. CSS-in-JS / Tailwind
**Rejected**: Would require rewriting all templates and changing build system.

### 4. Remove Stagger Animation
**Rejected**: User explicitly wants to keep it; it adds visual polish.

---

## Open Questions

1. **Should hub cards remain distinct?** Hub cards are significantly larger/different - worth keeping as separate variant or integrate into unified card?

2. **CSS nesting support**: Should we use native CSS nesting (`&`) now that browser support is good? Would further reduce line count.

3. **Template migration timeline**: Should template changes happen in same PR as CSS refactor, or separately?

---

## Appendix: Current vs Proposed Line Counts

| Module | Current (estimated) | Proposed |
|--------|---------------------|----------|
| Tokens | scattered | 60 |
| Base container | 100 | 100 |
| Cards (6 types) | 1,200 | 300 |
| Tables | 200 | 150 |
| Badges | 200 | 100 |
| Signatures | 100 | 80 |
| Animations | 100 | 50 |
| Grids | 200 | 100 |
| Hub-specific | 300 | 150 |
| 3-panel layout | 200 | 100 |
| Responsive | 200 | (distributed) |
| **Total** | **2,633** | **~1,200** |

---

## References

- Current file: `bengal/themes/default/assets/css/components/autodoc-explorer.css`
- CSS architecture docs: `bengal/themes/default/assets/css/CSS_ARCHITECTURE_EVALUATION.md`
- Related templates: `bengal/themes/default/templates/autodoc/python/`
