# RFC-002: CSS Architecture Simplification

**Status**: Draft  
**Created**: 2024-12-08  
**Part of**: [Theme Architecture Series](rfc-theme-architecture-series.md)  
**Priority**: P2 (Medium)  
**Dependencies**: None  
**Note**: Renumbered from RFC-005 in series refactor  

---

## Summary

Consolidate the theme's CSS from 45+ component files into ~15 domain-grouped files, improve token organization, and establish clearer naming conventions.

---

## Problem Statement

### Current State

```
themes/default/assets/css/
├── tokens/                 # 3 core + 5 palettes
│   ├── foundation.css      # Core design tokens
│   ├── semantic.css        # Semantic mappings
│   ├── typography.css      # Type scale
│   └── palettes/           # 5 color palettes
│       ├── blue-bengal.css
│       ├── brown-bengal.css
│       ├── charcoal-bengal.css
│       ├── silver-bengal.css
│       └── snow-lynx.css
├── base/                   # 6 files
│   ├── reset.css
│   ├── typography.css
│   ├── fonts.css
│   ├── accessibility.css
│   ├── print.css
│   └── utilities.css
├── components/             # 45 files (!)
│   ├── action-bar.css, admonitions.css, alerts.css
│   ├── api-docs.css, api-explorer.css, archive.css
│   ├── author.css, author-page.css, badges.css
│   ├── blog.css, buttons.css, cards.css
│   ├── ... (33 more)
├── layouts/                # 6 files
│   ├── changelog.css, footer.css, grid.css
│   ├── header.css, page-header.css, resume.css
├── composition/            # 1 file (layouts.css)
├── utilities/              # 6 files
│   ├── fluid-blobs.css, gradient-borders.css
│   ├── lazy-loading.css, motion.css
│   ├── scroll-animations.css, smooth-animations.md
├── experimental/           # 6 files (holo-cards, border-styles)
├── pages/                  # 1 file (landing.css)
└── style.css               # Entry point
```

**Evidence**: `bengal/themes/default/assets/css/components/` contains exactly 45 CSS files.

### Problems

1. **Too many files** - 45+ component files is overwhelming
2. **Inconsistent granularity** - Some files are 20 lines, others 500+
3. **Hard to find** - Where is button styling? `buttons.css`? `interactive.css`?
4. **Import overhead** - Many small files = many HTTP requests in dev
5. **Token sprawl** - 8 token files with overlap

---

## Proposal

### Consolidated Structure

```
themes/default/assets/css/
├── tokens.css              # All design tokens (single file)
├── base.css                # Reset + typography + global
├── layouts.css             # All layout patterns
├── components/             # ~10 domain-grouped files
│   ├── navigation.css      # Nav, sidebar, mobile-nav, breadcrumbs, toc
│   ├── content.css         # Prose, headings, lists, tables, blockquotes
│   ├── interactive.css     # Buttons, forms, tabs, accordions, details
│   ├── feedback.css        # Alerts, badges, toasts, progress
│   ├── media.css           # Images, lightbox, embeds, figures
│   ├── cards.css           # Card variants, grids
│   ├── code.css            # Code blocks, syntax highlighting, copy button
│   ├── search.css          # Search modal, results, highlights
│   ├── api-explorer.css    # API documentation components
│   └── theme-controls.css  # Theme/palette switcher
├── utilities.css           # Utility classes
├── print.css               # Print styles
└── style.css               # Entry point (~15 imports)
```

### Token Consolidation

**Current Structure** (3 core + 5 palettes):
```
tokens/
├── foundation.css     # Base tokens (spacing, borders, shadows, motion, z-index)
├── semantic.css       # Semantic color mappings
├── typography.css     # Type scale and fonts
└── palettes/          # Switchable color palettes
    ├── blue-bengal.css
    ├── brown-bengal.css
    ├── charcoal-bengal.css
    ├── silver-bengal.css
    └── snow-lynx.css
```

**Note**: Token organization is already reasonable. The main issue is component fragmentation.

**Proposed** (consolidated but maintaining separation):
```
tokens/
├── tokens.css         # All tokens in one file (sections preserve organization)
└── palettes/          # Keep palettes separate (user-switchable)
```

After (1 file with sections):
```css
/* tokens.css */

/*===============================================================================
  COLOR TOKENS
===============================================================================*/
:root {
  /* Semantic colors */
  --color-bg: var(--color-bg-light);
  --color-text: var(--color-text-light);
  --color-primary: #2563eb;
  --color-success: #16a34a;
  --color-warning: #d97706;
  --color-error: #dc2626;

  /* Light mode */
  --color-bg-light: #ffffff;
  --color-text-light: #1f2937;

  /* Dark mode */
  --color-bg-dark: #0f172a;
  --color-text-dark: #f1f5f9;
}

[data-theme="dark"] {
  --color-bg: var(--color-bg-dark);
  --color-text: var(--color-text-dark);
}

/*===============================================================================
  TYPOGRAPHY TOKENS
===============================================================================*/
:root {
  --font-sans: system-ui, -apple-system, sans-serif;
  --font-serif: Georgia, serif;
  --font-mono: ui-monospace, 'Fira Code', monospace;

  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;
  --font-size-4xl: 2.25rem;

  --line-height-tight: 1.25;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;
}

/*===============================================================================
  SPACING TOKENS
===============================================================================*/
:root {
  --space-0: 0;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;
  --space-24: 6rem;
}

/*===============================================================================
  LAYOUT TOKENS
===============================================================================*/
:root {
  --content-max-width: 65ch;
  --sidebar-width: 280px;
  --toc-width: 240px;
  --header-height: 64px;
}

/*===============================================================================
  BREAKPOINTS (as custom properties for JS access)
===============================================================================*/
:root {
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
}

/*===============================================================================
  MOTION TOKENS
===============================================================================*/
:root {
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 400ms;

  --easing-default: cubic-bezier(0.4, 0, 0.2, 1);
  --easing-in: cubic-bezier(0.4, 0, 1, 1);
  --easing-out: cubic-bezier(0, 0, 0.2, 1);
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-fast: 0ms;
    --duration-normal: 0ms;
    --duration-slow: 0ms;
  }
}

/*===============================================================================
  Z-INDEX SCALE
===============================================================================*/
:root {
  --z-below: -1;
  --z-base: 0;
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-overlay: 300;
  --z-modal: 400;
  --z-toast: 500;
}

/*===============================================================================
  SHADOWS
===============================================================================*/
:root {
  --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px rgb(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px rgb(0 0 0 / 0.1);
}

/*===============================================================================
  BORDERS
===============================================================================*/
:root {
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-full: 9999px;

  --border-width: 1px;
  --border-color: rgb(0 0 0 / 0.1);
}
```

### Component Grouping

**navigation.css** combines:
- `header.css`
- `mobile-nav.css`
- `sidebar.css`
- `docs-nav.css`
- `breadcrumbs.css`
- `toc.css`
- `back-to-top.css`

**content.css** combines:
- `prose.css`
- `headings.css`
- `lists.css`
- `tables.css`
- `blockquotes.css`
- `footnotes.css`

**interactive.css** combines:
- `buttons.css`
- `forms.css`
- `tabs.css`
- `accordion.css`
- `details.css`
- `dropdown.css`

### Naming Conventions

**BEM with component prefix**:
```css
/* Component: .c-card */
.c-card { }
.c-card__header { }
.c-card__body { }
.c-card--elevated { }

/* Layout: .l-grid */
.l-grid { }
.l-sidebar { }

/* Utility: .u-hidden */
.u-hidden { }
.u-visually-hidden { }
```

**Token references**:
```css
.c-button {
  padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-base);
  border-radius: var(--radius-md);
  transition: background-color var(--duration-fast) var(--easing-default);
}
```

### Entry Point

```css
/* style.css - Theme entry point */

/* Tokens (design system foundation) */
@import 'tokens.css';

/* Base (resets and global styles) */
@import 'base.css';

/* Layouts (structural patterns) */
@import 'layouts.css';

/* Components (UI elements) */
@import 'components/navigation.css';
@import 'components/content.css';
@import 'components/interactive.css';
@import 'components/feedback.css';
@import 'components/media.css';
@import 'components/cards.css';
@import 'components/code.css';
@import 'components/search.css';
@import 'components/api-explorer.css';
@import 'components/theme-controls.css';

/* Utilities (helper classes) */
@import 'utilities.css';

/* Print (print-specific overrides) */
@import 'print.css' print;
```

---

## Migration Path

### File Mapping

| Old Files | New File |
|-----------|----------|
| `tokens/*.css` (8 files) | `tokens.css` |
| `base/*.css` (6 files) | `base.css` |
| `layouts/*.css` (6 files) | `layouts.css` |
| `components/header.css`, `mobile-nav.css`, ... | `components/navigation.css` |
| `components/prose.css`, `headings.css`, ... | `components/content.css` |
| ... | ... |

### Automated Migration

```bash
bengal theme migrate-css themes/default --check  # Dry run
bengal theme migrate-css themes/default          # Merge files
```

The tool:
1. Reads all existing CSS files
2. Groups by domain mapping
3. Concatenates with section comments
4. Writes new consolidated files
5. Updates `style.css` imports
6. Optionally removes old files

---

## Benefits

1. **Fewer files** - 45+ → ~15 files
2. **Easier navigation** - Domain grouping is intuitive
3. **Faster dev** - Fewer HTTP requests
4. **Single token source** - All tokens in one file
5. **Clearer organization** - tokens → base → layouts → components → utilities

---

## Implementation

### Phase 1: Token Consolidation
- [ ] Merge 8 token files into `tokens.css`
- [ ] Add section comments for organization
- [ ] Update all token references

### Phase 2: Component Consolidation
- [ ] Create domain-grouped component files
- [ ] Merge existing component CSS
- [ ] Update `style.css` imports

### Phase 3: Base & Layout
- [ ] Merge base files
- [ ] Merge layout files
- [ ] Verify no regressions

### Phase 4: Cleanup
- [ ] Remove old files
- [ ] Update documentation
- [ ] Add migration tool

---

## Open Questions

1. **Should we use CSS layers?**  
   Proposal: Consider for v3.0, adds complexity

2. **What about CSS-in-JS components?**  
   Proposal: Not for Bengal, stick with CSS files

3. **Should utilities be more comprehensive (Tailwind-like)?**  
   Proposal: Keep minimal, users can add if needed
