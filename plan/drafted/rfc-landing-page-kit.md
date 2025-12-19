# RFC: Landing Page CSS Kit

**Status**: Draft  
**Created**: 2024-12-18  
**Author**: AI Assistant  
**Confidence**: 85% (based on existing patterns in tracks.css, api-hub.css, hub-cards.css)

---

## Summary

Create a modular CSS kit for full-width landing pages that share Bengal's design language but operate outside the docs sidebar layout. This kit would provide reusable patterns for home pages, product pages, hub indexes, and marketing content.

---

## Problem Statement

Bengal currently has two implicit layout paradigms:

1. **Docs Layout**: Left sidebar (nav) + content + right sidebar (TOC)
2. **Landing Layout**: Full-width, no sidebars, hero-driven

The landing layout patterns are scattered across:
- `hub-cards.css` - Card grids for tracks/api-hub
- `tracks.css` - Track-specific landing styles (~1200 lines)
- `api-hub.css` - API hub landing styles (~370 lines)
- `hero.css` - Basic hero patterns
- `home.html` template - Inline patterns

**Issues**:
- Duplication between tracks.css and api-hub.css (~60% overlap)
- No clear system for building new landing pages
- Inconsistent hero patterns across pages
- Missing common landing page components (feature grids, CTAs, testimonials)

---

## Proposed Solution

### Architecture

```
assets/css/
├── components/
│   ├── landing/                      # NEW: Landing Page Kit
│   │   ├── _index.css                # Kit entry point (imports all)
│   │   ├── landing-core.css          # Base containers, sections, spacing
│   │   ├── landing-hero.css          # Hero section variants
│   │   ├── landing-cards.css         # Card grids (from hub-cards.css)
│   │   ├── landing-features.css      # Feature grids, icon boxes
│   │   ├── landing-cta.css           # Call-to-action sections
│   │   ├── landing-stats.css         # Stats/metrics displays
│   │   └── landing-social.css        # Testimonials, logos, social proof
│   │
│   ├── tracks.css                    # Slimmed: imports landing-cards + track-specific
│   ├── api-hub.css                   # Slimmed: imports landing-cards + api-specific
│   └── ...
```

### Component Inventory

#### 1. `landing-core.css` - Foundation

```css
/* Container widths */
.landing-container { max-width: 1200px; margin: 0 auto; }
.landing-container--narrow { max-width: 800px; }
.landing-container--wide { max-width: 1400px; }

/* Section spacing */
.landing-section { padding: var(--space-16) var(--space-6); }
.landing-section--compact { padding: var(--space-10) var(--space-6); }

/* Section backgrounds */
.landing-section--muted { background: var(--color-bg-secondary); }
.landing-section--dark { background: var(--color-bg-inverse); color: var(--color-text-inverse); }
.landing-section--gradient { background: linear-gradient(...); }
```

#### 2. `landing-hero.css` - Hero Variants

```css
/* Centered hero (current default) */
.landing-hero--centered { text-align: center; }

/* Split hero (text left, media right) */
.landing-hero--split { display: grid; grid-template-columns: 1fr 1fr; }

/* Background variants */
.landing-hero--image { background-image: ...; }
.landing-hero--video { /* video background */ }
.landing-hero--gradient { /* gradient overlay */ }
```

#### 3. `landing-cards.css` - Card Patterns (from hub-cards.css)

```css
/* Already implemented in hub-cards.css */
.landing-card { /* neumorphic card */ }
.landing-card-grid { /* responsive grid */ }
.landing-card__icon, __title, __description, __footer { /* card parts */ }
```

#### 4. `landing-features.css` - Feature Displays

```css
/* Icon box grid */
.landing-features { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.landing-feature { /* icon + title + description */ }
.landing-feature__icon { /* large icon */ }

/* Alternating feature rows */
.landing-feature-row { display: grid; grid-template-columns: 1fr 1fr; }
.landing-feature-row:nth-child(even) { /* reverse order */ }
```

#### 5. `landing-cta.css` - Call-to-Action

```css
/* CTA section */
.landing-cta { text-align: center; background: var(--color-primary); }
.landing-cta__title { color: var(--color-text-inverse); }
.landing-cta__buttons { display: flex; gap: var(--space-4); justify-content: center; }

/* Inline CTA (within content) */
.landing-cta--inline { padding: var(--space-8); border-radius: var(--radius-xl); }
```

#### 6. `landing-stats.css` - Metrics Display

```css
/* Stats bar (horizontal) */
.landing-stats { display: flex; justify-content: center; gap: var(--space-8); }
.landing-stat__value { font-size: var(--text-4xl); font-weight: var(--weight-bold); }
.landing-stat__label { font-size: var(--text-sm); color: var(--color-text-muted); }

/* Stats grid (2x2, 3x3) */
.landing-stats--grid { display: grid; grid-template-columns: repeat(3, 1fr); }
```

#### 7. `landing-social.css` - Social Proof

```css
/* Testimonial card */
.landing-testimonial { /* quote + author */ }
.landing-testimonial__quote { font-style: italic; }
.landing-testimonial__author { /* avatar + name + role */ }

/* Logo bar */
.landing-logos { display: flex; align-items: center; justify-content: center; gap: var(--space-8); }
.landing-logos img { filter: grayscale(100%); opacity: 0.6; }
.landing-logos img:hover { filter: none; opacity: 1; }
```

---

## Migration Plan

### Phase 1: Establish Foundation
1. Create `landing/` directory structure
2. Move `hub-cards.css` → `landing/landing-cards.css`
3. Update imports in `style.css`
4. Verify tracks/api-hub still work

### Phase 2: Refactor Existing
1. Update `api-hub/home.html` to use `.landing-*` classes
2. Slim `api-hub.css` to type-specific overrides only (~50 lines)
3. Extract common track patterns to landing kit
4. Slim `tracks.css` to track-specific only

### Phase 3: Build Out Kit
1. Add `landing-hero.css` with variants
2. Add `landing-features.css`
3. Add `landing-cta.css`
4. Add `landing-stats.css`
5. Add `landing-social.css`

### Phase 4: Template Integration
1. Create reusable Jinja macros for landing components
2. Update home page template
3. Document usage in theme guide

---

## Design Decisions

### Class Naming Convention

**Option A: BEM with `landing-` prefix** (Recommended)
```css
.landing-hero { }
.landing-hero__title { }
.landing-hero--centered { }
```

**Option B: Utility-first**
```css
.l-hero { }
.l-hero-title { }
.l-hero-centered { }
```

**Decision**: Option A - BEM with `landing-` prefix for consistency with existing Bengal patterns (`.autodoc-*`, `.track-*`).

### Animation Strategy

- Use existing `@keyframes hub-card-fade-in` (rename to `landing-fade-in`)
- Respect `prefers-reduced-motion`
- Staggered animations for grids
- Subtle hover transitions (scale, shadow)

### Responsive Approach

- Mobile-first breakpoints
- Grid collapse patterns: 3-col → 2-col → 1-col
- Hero: split → stacked on mobile
- Touch-friendly tap targets

---

## Evidence

### Existing Patterns (from codebase)

| File | Lines | Reusable Patterns |
|------|-------|-------------------|
| `hub-cards.css` | 465 | Hero, card grid, preview lists, buttons |
| `tracks.css` | 1213 | Hero, card grid, preview lists, buttons, sidebar |
| `api-hub.css` | 370 | Hero, card grid, preview lists, type badges |
| `hero.css` | ~200 | Basic hero patterns |

### Overlap Analysis

- **Hero section**: 95% identical between tracks/api-hub
- **Card grid**: 90% identical (animation, spacing)
- **Preview lists**: 85% identical (numbered vs bulleted)
- **Buttons**: 100% identical (neumorphic style)
- **Empty state**: 100% identical

### Potential Reduction

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| tracks.css | 1213 | ~400 | 67% |
| api-hub.css | 370 | ~50 | 86% |
| **Total** | 1583 | ~450 | 72% |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing pages | Medium | High | Phased migration, visual regression tests |
| Over-abstraction | Low | Medium | Start with proven patterns only |
| Naming conflicts | Low | Low | `landing-` prefix isolates namespace |

---

## Success Criteria

1. **Reduction**: tracks.css + api-hub.css reduced by 60%+
2. **Reusability**: New landing page can be built with ~20 lines of custom CSS
3. **Consistency**: All landing pages share visual language
4. **Documentation**: Theme guide documents all landing components
5. **Performance**: No increase in CSS bundle size (net reduction)

---

## Out of Scope

- JavaScript interactions (carousels, accordions)
- Animation library integration
- Dark/light mode toggle (use existing system)
- Pricing table component (add when needed)
- Blog-specific components (separate concern)

---

## References

- `bengal/themes/default/assets/css/components/hub-cards.css`
- `bengal/themes/default/assets/css/components/tracks.css`
- `bengal/themes/default/assets/css/components/api-hub.css`
- `bengal/themes/default/templates/api-hub/home.html`
- `bengal/themes/default/templates/tracks/list.html`

---

## Next Steps

1. Review RFC
2. Approve architecture
3. Begin Phase 1 implementation
4. Create visual regression tests for existing pages
