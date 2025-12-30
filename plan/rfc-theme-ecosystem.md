# RFC: Theme Ecosystem Foundation

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2024-12-30 |
| **Author** | Bengal Team |
| **Scope** | Major Initiative |
| **Dependencies** | RFC-Directive-Base-CSS, RFC-Template-Object-Model |

## Summary

Enable community-driven themes by establishing a clear **Theme Developer Contract**: documented APIs, shared infrastructure, and validation tools that let theme authors focus on aesthetics rather than reimplementing directive functionality.

## Motivation

### Goal: Theme Marketplace

Bengal's differentiation is its visual polish (animations, gradients, holographic effects). To scale this:

1. **Community themes** multiply Bengal's appeal
2. **Theme authors** need clear contracts, not reverse-engineering
3. **Users** need confidence themes "just work"

### Current Barriers

| Barrier | Impact | Solution |
|---------|--------|----------|
| No directive base CSS | Theme authors write 4,000+ lines | RFC-Directive-Base-CSS |
| Confusing Page API | `page.content` surprises devs | RFC-Template-Object-Model |
| Undocumented context | Trial-and-error theme dev | Theme Context Reference |
| No CSS variable contract | Themes can't reliably override | CSS API Specification |
| No scaffolding | Cold start friction | `bengal theme new` |
| No validation | Broken themes reach users | Theme Validator |

## Design

### Architecture: Three-Tier CSS (From RFC-Directive-Base-CSS)

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 3: Theme Styles                                       │
│  - Colors, typography, spacing                              │
│  - Custom animations and effects                            │
│  - Brand-specific aesthetic                                 │
└─────────────────────────────────────────────────────────────┘
                              ↑ overrides via CSS variables
┌─────────────────────────────────────────────────────────────┐
│  Tier 2: Bengal Aesthetic Defaults (Optional)               │
│  - Default theme's animations, gradients                    │
│  - Can be imported: @import "bengal:aesthetic/tabs";        │
│  - Or completely replaced                                   │
└─────────────────────────────────────────────────────────────┘
                              ↑ extends
┌─────────────────────────────────────────────────────────────┐
│  Tier 1: Directive Base CSS (Auto-included)                 │
│  - Structural: display, visibility, layout                  │
│  - Accessibility: focus states, reduced motion              │
│  - Semantic CSS variables with fallbacks                    │
└─────────────────────────────────────────────────────────────┘
```

### CSS Variable Contract

**Core Design Tokens** (themes SHOULD define):

```css
:root {
  /* === REQUIRED: Color Palette === */
  --color-bg: #ffffff;
  --color-bg-alt: #f5f5f5;
  --color-surface: #ffffff;
  --color-border: #e5e5e5;
  --color-text: #1a1a1a;
  --color-text-muted: #6b7280;
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;

  /* === REQUIRED: Semantic Colors === */
  --color-info: #3b82f6;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;

  /* === REQUIRED: Spacing Scale === */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;

  /* === REQUIRED: Border Radius === */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;

  /* === OPTIONAL: Typography (has defaults) === */
  --font-sans: system-ui, sans-serif;
  --font-mono: ui-monospace, monospace;
}
```

**Directive-Specific Variables** (base CSS provides defaults):

```css
/* Themes can override these, but don't need to */
.tabs {
  --tab-border-color: var(--color-border);
  --tab-active-color: var(--color-primary);
  --tab-bg: var(--color-surface);
}

.admonition {
  --admonition-bg: var(--color-bg-alt);
  --admonition-border: var(--color-border);
}

.admonition.note { --admonition-accent: var(--color-info); }
.admonition.warning { --admonition-accent: var(--color-warning); }
.admonition.tip { --admonition-accent: var(--color-success); }
.admonition.danger { --admonition-accent: var(--color-error); }
```

### Template Context Contract

**Always Available Variables:**

```yaml
# Page Context (all page types)
page:              # Full Page object
content:           # Rendered HTML (use {{ content | safe }})
title:             # page.title shortcut
toc:               # Table of contents HTML
toc_items:         # Structured TOC data

# Site Context
site:              # Site configuration object
site.title:        # Site title
site.baseurl:      # Base URL
site.params:       # Custom site parameters

# Navigation
nav:               # Navigation tree
breadcrumbs:       # Breadcrumb trail

# Theme
theme:             # Theme configuration
theme.params:      # Theme-specific parameters
```

**Layout-Specific Variables:**

```yaml
# list.html
pages:             # List of child pages
paginator:         # Pagination object (if enabled)

# doc/single.html  
prev_page:         # Previous page in section
next_page:         # Next page in section
section:           # Parent section object

# home.html
featured_posts:    # Featured blog posts (if configured)
recent_posts:      # Recent blog posts
```

### Theme Structure Contract

```
themes/my-theme/
├── theme.yaml              # REQUIRED: Theme metadata
├── assets/
│   ├── css/
│   │   └── style.css       # REQUIRED: Main stylesheet
│   └── js/                  # Optional: Custom JS
├── templates/
│   ├── base.html           # REQUIRED: Base layout
│   ├── home.html           # REQUIRED: Homepage
│   ├── page.html           # REQUIRED: Generic page
│   ├── doc/
│   │   └── single.html     # REQUIRED: Documentation page
│   ├── blog/
│   │   └── list.html       # REQUIRED: Blog listing
│   └── partials/           # Optional: Reusable components
└── README.md               # REQUIRED: Theme documentation
```

**theme.yaml Schema:**

```yaml
name: "My Theme"
version: "1.0.0"
description: "A beautiful theme for Bengal"
author: "Your Name"
license: "MIT"
homepage: "https://github.com/you/bengal-theme-name"

# Bengal version compatibility
bengal:
  min_version: "1.0.0"

# Feature flags
features:
  dark_mode: true
  syntax_highlighting: true
  search: true

# Optional: Import Bengal aesthetic CSS
imports:
  - "bengal:aesthetic/code-blocks"  # Import default code styling
  # Or omit to use only base functional CSS

# Theme-specific configuration
params:
  accent_color: "#3b82f6"
  font_heading: "Inter"
```

### Theme Scaffolding

```bash
# Create new theme from template
bengal theme new my-theme

# Creates:
themes/my-theme/
├── theme.yaml              # Pre-filled template
├── assets/css/style.css    # Starter CSS with variable definitions
├── templates/              # Minimal working templates
└── README.md               # Theme author guide
```

### Theme Validator

```bash
# Validate theme before publishing
bengal theme validate themes/my-theme

# Checks:
✅ Required files present (theme.yaml, base.html, etc.)
✅ Required CSS variables defined
✅ Templates render without errors
✅ Directives display correctly (visual regression optional)
✅ Accessibility basics (color contrast, focus states)
✅ Dark mode works (if declared)
```

## Implementation Plan

### Phase 1: Foundation (Q1 2025)

**Week 1-2: Extract Directive Base CSS**
- [ ] Identify structural CSS in default theme (~500 lines)
- [ ] Create `bengal/assets/css/directives/*.css`
- [ ] Implement auto-include in asset pipeline
- [ ] Test with ink theme (should work with zero directive CSS)

**Week 3-4: CSS Variable Contract**
- [ ] Document required CSS variables
- [ ] Add fallbacks to directive base CSS
- [ ] Create CSS variable reference page

### Phase 2: Developer Experience (Q2 2025)

**Week 1-2: Theme Scaffolding**
- [ ] Implement `bengal theme new`
- [ ] Create starter template set
- [ ] Write theme author guide

**Week 3-4: Theme Validator**
- [ ] File structure validation
- [ ] CSS variable validation
- [ ] Template render testing
- [ ] Integration with CI

### Phase 3: Template API (Q2-Q3 2025)

**Per RFC-Template-Object-Model:**
- [ ] Phase 1: Add `page._source` alias
- [ ] Phase 2: Deprecation warnings
- [ ] Document template context contract

### Phase 4: Ecosystem (Q4 2025)

- [ ] Theme gallery/registry
- [ ] Community contribution guidelines
- [ ] Theme certification program (optional)

## Default Theme Migration

The default theme needs refactoring to fit the tier system:

### Current Structure
```
themes/default/assets/css/components/
├── tabs.css           # 528 lines (mixed structural + aesthetic)
├── admonitions.css    # 679 lines (mixed)
├── dropdowns.css      # 478 lines (mixed)
└── ... (~4,445 lines total)
```

### Target Structure
```
# Tier 1: Auto-included by Bengal
bengal/assets/css/directives/
├── tabs.css           # ~80 lines (structural only)
├── admonitions.css    # ~60 lines (structural only)
├── dropdowns.css      # ~40 lines (structural only)
└── ... (~400 lines total)

# Tier 2: Default theme aesthetic (optional for other themes)
themes/default/assets/css/components/
├── tabs.css           # ~450 lines (aesthetic: animations, palettes)
├── admonitions.css    # ~620 lines (aesthetic: glow, gradients)
└── ... (~4,000 lines of Bengal's signature style)
```

### Migration Strategy

1. **Don't break default theme** during extraction
2. **Extract structural CSS** to new location
3. **Keep aesthetic CSS** in default theme
4. **Test both themes** (default + ink) after each change

## Success Criteria

| Metric | Target |
|--------|--------|
| New theme creation time | < 2 hours for basic theme |
| Directive CSS needed by theme | 0 lines (functional) |
| Theme validation pass rate | > 90% for contributed themes |
| Community themes | 5+ within 6 months of launch |

## Risks

| Risk | Mitigation |
|------|------------|
| CSS cascade conflicts | Careful specificity design, thorough testing |
| Breaking default theme | Incremental migration, extensive test coverage |
| Variable naming conflicts | Clear namespacing, documentation |
| Community adoption | Good docs, starter templates, responsive support |

## Open Questions

1. **Should Bengal host a theme registry?**
   - Option A: GitHub-based (themes in repos, registry is JSON file)
   - Option B: npm-style registry
   - Option C: Just documentation, no registry

2. **Theme versioning and updates?**
   - How do users update themes?
   - Compatibility checking?

3. **Should aesthetic CSS (Tier 2) be importable?**
   - `@import "bengal:aesthetic/tabs"` lets themes cherry-pick effects
   - Adds complexity but enables gradual customization

## References

- RFC-Directive-Base-CSS
- RFC-Template-Object-Model
- Hugo Theme Components: https://gohugo.io/hugo-modules/theme-components/
- Tailwind Plugin System: https://tailwindcss.com/docs/plugins
