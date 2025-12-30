# RFC: Shared Directive Base CSS

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2024-12-30 |
| **Updated** | 2024-12-30 |
| **Author** | Bengal Team |
| **Scope** | Non-Breaking Enhancement |
| **Goal** | Enable community-driven themes |

## Summary

Create a minimal, **opinion-free** CSS layer for Bengal directives that handles universal functional requirements (show/hide, accessibility, prose contamination fixes). Themes—including the default theme—retain full control over layout and aesthetics.

## Motivation

### The Problem

Bengal directives output semantic HTML with CSS classes:

```html
<!-- tab-set outputs: -->
<div class="tabs" data-bengal="tabs">
  <ul class="tab-nav">...</ul>
  <div class="tab-content">
    <div class="tab-pane active">...</div>
  </div>
</div>

<!-- dropdown outputs: -->
<details class="dropdown">
  <summary>Title</summary>
  <div class="dropdown-content">...</div>
</details>
```

**But themes must implement CSS for every directive class.** The default theme has:

```
themes/default/assets/css/components/
├── tabs.css           # 528 lines
├── tabs-native.css    # 259 lines  
├── dropdowns.css      # 478 lines
├── admonitions.css    # 679 lines
├── cards.css          # 1,492 lines
├── steps.css          # 205 lines
└── ...                # ~4,445 lines total for directives
```

New themes (like `ink`) ship with **zero directive styles**, causing:
- Tabs render as plain divs (panes don't hide/show)
- Dropdowns have no styling
- Admonitions look like regular text
- Tab navigation gets bullet points from prose styles

### Strategic Goal: Community-Driven Themes

Bengal aims to enable a community theme ecosystem. For this to work:
- Theme authors shouldn't need to write thousands of lines of CSS for basic functionality
- Directives should "just work" in any theme
- Themes should focus on aesthetics, not reimplementing show/hide logic

### Impact

| Stakeholder | Current Pain | After RFC |
|-------------|--------------|-----------|
| Theme authors | Write ~4,000 lines to support directives | Write ~200 lines for basic styling |
| Users | Directives "don't work" in new themes | Directives work in all themes |
| Maintenance | Bug fixes duplicated across themes | Fix once in base, benefits all |

## Design

### Core Principle: Opinion-Free Functional Base

**Base CSS handles ONLY universal requirements that ALL themes need:**
- Show/hide logic (`.tab-pane { display: none }`)
- Prose contamination fixes (list resets)
- Accessibility (focus-visible, reduced-motion)

**Base CSS does NOT handle:**
- Layout decisions (flex vs. grid vs. relative positioning)
- Colors, borders, backgrounds
- Typography, spacing
- Animations, transitions
- Any aesthetic choices

**Why opinion-free matters:** The default theme uses `position: relative` on `.tabs`. If base CSS forced `display: flex; flex-direction: column`, it would break the default theme's layout.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 3: Theme Styles                                       │
│  themes/*/assets/css/style.css                              │
│  - Layout (flex, grid, positioning)                         │
│  - Colors, borders, backgrounds                             │
│  - Typography and spacing                                   │
│  - Animations and effects                                   │
│  - Dark mode, responsive variants                           │
└─────────────────────────────────────────────────────────────┘
                              ↑ overrides (CSS cascade)
┌─────────────────────────────────────────────────────────────┐
│  Tier 1: Directive Base CSS (Auto-included)                 │
│  bengal/assets/css/directives/                              │
│  - Show/hide (.tab-pane, .dropdown-content)                 │
│  - List resets (prose contamination fix)                    │
│  - Accessibility (focus-visible, reduced-motion)            │
│  - ~40 lines per directive, ~200 lines total                │
└─────────────────────────────────────────────────────────────┘
```

**Note:** There is no "Tier 2". The default theme is a Tier 3 theme like any other. It consumes base CSS and provides its own complete aesthetic.

### Directive Base CSS Location

```
bengal/
├── assets/
│   └── css/
│       └── directives/
│           ├── _index.css      # Imports all (~200 lines total)
│           ├── tabs.css        # ~40 lines
│           ├── dropdowns.css   # ~30 lines
│           ├── admonitions.css # ~40 lines
│           ├── cards.css       # ~20 lines
│           ├── code-blocks.css # ~30 lines
│           ├── tables.css      # ~20 lines
│           └── steps.css       # ~20 lines
```

### What Base CSS Contains

| Directive | Base CSS Provides | Themes Provide |
|-----------|-------------------|----------------|
| `tabs` | Show/hide panes, list reset, focus-visible | Container layout, nav layout, colors, animations |
| `dropdown` | (Native `<details>` handles show/hide) | Borders, colors, icons, animations |
| `admonition` | None (no universal requirements) | Everything (layout, colors, icons) |
| `cards` | None | Grid layout, shadows, hover effects |
| `code-blocks` | None | Background, borders, toolbar |
| `steps` | Counter reset | Layout, connector lines, colors |

**Key insight:** Most directives need zero base CSS. Tabs are the main exception due to the show/hide requirement and prose contamination bug.

### Example: Tabs Base CSS

```css
/* bengal/assets/css/directives/tabs.css */
/* ~40 lines - handles ONLY universal requirements */

/* ==========================================================================
   FUNCTIONAL: Show/Hide Tab Panes
   ========================================================================== */

.tab-pane {
  display: none;
}

.tab-pane.active {
  display: block;
}

/* ==========================================================================
   FUNCTIONAL: List Reset (prose contamination fix)
   Without this, tabs inside .prose get bullet points and margins.
   ========================================================================== */

.tab-nav,
.tab-nav li {
  list-style: none;
  margin: 0;
  padding: 0;
}

/* Higher specificity for prose containers */
.prose .tab-nav,
.prose .tab-nav li,
.content .tab-nav,
.content .tab-nav li {
  list-style: none;
  margin: 0;
  padding: 0;
}

/* ==========================================================================
   FUNCTIONAL: Accessibility
   ========================================================================== */

.tab-nav a:focus-visible {
  outline: 2px solid var(--color-primary, var(--color-accent, currentColor));
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .tab-nav a,
  .tab-pane {
    transition: none !important;
    animation: none !important;
  }
}
```

### Token Contract (Soft Convention)

Base CSS uses semantic tokens **with fallbacks**. Themes are encouraged but not required to define them.

**How it works:**
```css
/* Base CSS - uses tokens with fallback chain */
.tab-nav a:focus-visible {
  outline: 2px solid var(--color-primary, var(--color-accent, currentColor));
}

.admonition.note {
  /* If theme defines --color-info, use it; else try --color-primary; else blue */
  border-left-color: var(--color-info, var(--color-primary, #3b82f6));
}
```

**Token compatibility:**

| Token | Default Theme | Ink Theme | Base CSS Uses |
|-------|---------------|-----------|---------------|
| `--color-primary` | ✅ `var(--blue-500)` | ❌ | First choice |
| `--color-accent` | ✅ `var(--orange-500)` | ✅ `#0c4a6e` | Fallback |
| `--color-info` | ✅ Defined | ❌ | For admonitions |
| `--color-border` | ✅ `var(--gray-300)` | ✅ `#e7e5e4` | For borders |

**Result:** Both themes work. No tokens are required.

### Theme Integration: Auto-Include

Bengal automatically includes directive base CSS in all builds:

```python
# bengal/assets/pipeline.py
def collect_base_css() -> str:
    """Include directive base CSS in every build."""
    base_css = Path(__file__).parent / "css" / "directives" / "_index.css"
    return base_css.read_text()
```

**Loading order:**
1. Base CSS injected first (~200 lines)
2. Theme CSS loaded second (full theme)
3. Same specificity → theme wins (CSS cascade)

Themes don't need to do anything—directives just work.

## Default Theme Migration

The default theme is treated as a customer of base CSS, like any community theme.

### What Default Theme Removes

```css
/* REMOVE from themes/default/assets/css/components/tabs.css */

/* These lines move to base CSS (~40 lines): */
.tab-pane { display: none; }
.tab-pane.active { display: block; }
.tab-nav, .tab-nav li { list-style: none; margin: 0; padding: 0; }
.prose .tab-nav { list-style: none; ... }
```

### What Default Theme Keeps (100% of aesthetics)

```css
/* KEEP: ALL layout and aesthetic decisions (~490 lines) */
.tabs {
  position: relative;  /* Theme's layout choice */
  margin: var(--space-6) 0;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  background-color: var(--color-bg-primary);
}

.tab-nav {
  display: flex;  /* Theme's layout choice */
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-light);
}

/* Signature Bengal effect - glowing active tab edge */
.tab-nav li.active a::after {
  animation: tab-accent-glow 8s ease-in-out infinite;
  /* ... */
}

/* All dark mode, palette variants, code-tabs, badges, responsive... */
```

### What Default Theme Gains

The default theme is **missing** `.tab-nav a:focus-visible`. Base CSS adds this accessibility feature.

| Feature | Before | After |
|---------|--------|-------|
| Tab focus-visible | ❌ Missing | ✅ Added by base |
| Reduced-motion (tabs) | Partial | ✅ Comprehensive |
| Prose list contamination | ✅ Has it | ✅ Redundant (can remove) |

### Net Change

| Directive | Lines Removed | Lines Kept | Change |
|-----------|---------------|------------|--------|
| tabs.css | ~40 | ~488 | -7% |
| admonitions.css | ~0 | ~679 | 0% |
| dropdowns.css | ~20 | ~458 | -4% |
| **Total** | ~100 | ~4,345 | -2% |

**Default theme keeps 98% of its CSS.** Visual output is identical (plus accessibility improvements).

## Community Theme Experience

### Minimal Theme (~40 lines for working tabs)

```css
/* Community theme - just the aesthetics */
.tabs {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin: 1.5rem 0;
}

.tab-nav {
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem;
  background: var(--color-bg-alt);
  border-bottom: 1px solid var(--color-border);
}

.tab-nav a {
  padding: 0.5rem 1rem;
  text-decoration: none;
  color: var(--color-text-muted);
  border-radius: var(--radius-sm);
}

.tab-nav li.active a {
  color: var(--color-primary);
  background: var(--color-surface);
}

.tab-content {
  padding: 1rem;
}
```

**Theme author didn't need to:**
- Figure out `.tab-pane` show/hide
- Handle prose list contamination
- Add focus-visible states
- Add reduced-motion support

## Implementation Plan

### Phase 1: Extract Base CSS (3-4 days)

1. Create `bengal/assets/css/directives/` directory
2. Extract functional CSS for tabs (~40 lines)
3. Extract functional CSS for other directives as needed
4. Create `_index.css` that imports all

### Phase 2: Pipeline Integration (2-3 days)

1. Implement auto-include in asset pipeline
2. Ensure base CSS loads before theme CSS
3. Test with default theme (no visual changes)
4. Test with ink theme (tabs now work)

### Phase 3: Default Theme Cleanup (1-2 days)

1. Remove redundant lines from default theme
2. Verify visual regression tests pass
3. Document what was removed

### Phase 4: Documentation (2-3 days)

1. Document token contract for theme authors
2. Create "Styling Directives" guide
3. Update theme creation documentation
4. Add examples to theme starter template

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Default theme unchanged visually | Screenshot comparison before/after |
| Default theme gains accessibility | Focus-visible on tabs, comprehensive reduced-motion |
| Ink theme has working directives | Tabs show/hide correctly, no prose contamination |
| Base CSS is minimal | < 200 lines total, < 2KB gzipped |
| No layout opinions | Base CSS has zero `display: flex/grid`, zero `position` |
| Theme override works | Any theme rule wins over base (same specificity, later load) |

### Validation Tests

```bash
# 1. Default theme visual regression
bengal build --theme default
# Percy/Playwright screenshot comparison

# 2. Ink theme functional test
bengal build --theme ink
# Verify: tabs switch, dropdowns expand, no bullet points in tab-nav

# 3. Base CSS audit
grep -E "display:\s*(flex|grid)|position:" bengal/assets/css/directives/*.css
# Should return zero matches (no layout opinions)

# 4. Size check
cat bengal/assets/css/directives/_index.css | wc -l  # < 200 lines
```

## Alternatives Considered

### Alternative A: Layout-Opinionated Base CSS

Include `display: flex` on containers, spacing, basic borders.

**Rejected because:**
- Default theme uses different layout (`position: relative`)
- Forces all themes into one structural approach
- Themes must fight CSS specificity to override

### Alternative B: No Base CSS

Themes bring everything, including show/hide logic.

**Rejected because:**
- Every theme must rediscover `.tab-pane { display: none }`
- Prose contamination bug hits every theme
- Accessibility features are forgotten

### Alternative C: Web Components / Shadow DOM

Encapsulate directive styles completely.

**Rejected because:**
- Requires JavaScript
- Much harder to customize
- SSR complexity
- Overkill for the problem

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1: Extract | 3-4 days | `bengal/assets/css/directives/*.css` |
| 2: Integrate | 2-3 days | Auto-include in pipeline, tests |
| 3: Cleanup | 1-2 days | Default theme migration |
| 4: Docs | 2-3 days | Theme author guide, examples |
| **Total** | ~2 weeks | |

## References

- [CSS Custom Properties Guide](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [Inclusive Components](https://inclusive-components.design/)
- [prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- Default theme: `bengal/themes/default/assets/css/components/`
- Ink theme: `bengal/themes/ink/assets/css/style.css`

### Working Examples

See `plan/examples/` for concrete implementations:

| File | Description |
|------|-------------|
| `directive-base-tabs.css` | What base CSS contains (~50 lines) |
| `default-theme-tabs.css` | What default theme keeps (~490 lines) |
| `minimal-theme-tabs.css` | What a community theme writes (~40 lines) |
| `token-contract.css` | Soft token convention documentation |
| `css-loading-explanation.md` | How CSS layers interact |
