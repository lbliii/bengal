# Bengal Default Theme - CSS Architecture

**Last Updated:** October 18, 2025  
**Architecture:** Semantic Design Token System + Scoping Rules + Responsive Design System

---

## ⚠️ Important: CSS Scoping Rules

**Bengal follows strict CSS scoping rules to prevent conflicts.**

**📖 Read before writing CSS:**
- [CSS Scoping Rules](./CSS_SCOPING_RULES.md) - Full documentation
- [Quick Reference](./CSS_QUICK_REFERENCE.md) - Keep this handy!

**Key principles:**
1. All selectors must be scoped (no bare elements in components)
2. Use `.has-prose-content` utility for user content
3. Content-type specific styles use `.prose.api-content`, etc.
4. Test with nested components

---

## 📱 Responsive Design System

**Bengal uses standardized breakpoints and responsive patterns.**

**📖 Essential reading for component development:**
- [Responsive Design System](./RESPONSIVE_DESIGN_SYSTEM.md) - Complete guide

**Key principles:**
1. **Mobile-first approach** - Start with mobile, enhance for larger screens
2. **Standard breakpoints** - 640px (sm), 768px (md), 1024px (lg), 1280px (xl)
3. **Semantic patterns** - Stack→Side-by-side, Compress→Expand, Hide→Show
4. **Avoid overlap** - Use `max-width: 639px` (not 640px) with `min-width: 640px`
5. **Test at key sizes** - 375px (iPhone), 768px (tablet), 1280px (desktop)

---

## Overview

This theme uses a **two-layer design token system** following modern CSS architecture best practices:

```
Foundation Tokens → Semantic Tokens → Components
(primitives)       (purpose-based)    (UI elements)
```

## File Structure

```
css/
├── tokens/
│   ├── foundation.css    # Primitive values (colors, sizes, fonts)
│   ├── typography.css    # Typography tokens
│   ├── semantic.css      # Purpose-based tokens (THE source of truth)
│   └── palettes/         # Color palette presets (user-switchable)
├── base/
│   ├── reset.css         # CSS reset
│   ├── typography.css    # Text styling
│   ├── utilities.css     # Utility classes
│   ├── interactive-patterns.css  # Common interactive patterns (extracted)
│   ├── accessibility.css # A11y styles
│   └── print.css         # Print styles
├── components/           # UI components (buttons, cards, etc.) - MODULAR
│   ├── buttons.css       # Button component (408 lines)
│   ├── cards.css         # Card component (1,338 lines)
│   ├── forms.css         # Form component
│   └── ... (45 files total, modular architecture)
├── layouts/              # Layout patterns (header, footer, grid)
├── composition/          # Layout primitives
├── pages/                # Page-specific styles
└── style.css             # Main entry point (imports all)
```

**📖 Why Modular CSS?** See [MODULAR_CSS_RATIONALE.md](./MODULAR_CSS_RATIONALE.md) for detailed explanation of why we keep components separate instead of consolidating.

## Design Token Layers

### 1. Foundation Tokens (`tokens/foundation.css`)

**Purpose:** Raw, primitive values  
**Usage:** Never use directly in components

Provides:
- Color scales (blue-50 to blue-900, etc.)
- Size primitives (--size-0 to --size-32)
- Font size primitives (--font-size-12 to --font-size-72)
- Base values for transitions, shadows, etc.

**Example:**
```css
--blue-500: oklch(65.82% 0.1690 248.8);  /* color primitives are authored in OKLCH */
--size-4: 1rem;
--font-size-16: 1rem;
```

### 2. Semantic Tokens (`tokens/semantic.css`)

**Purpose:** Purpose-based, meaningful names  
**Usage:** ALWAYS use these in components

Maps foundation tokens to semantic purposes:

**Colors:**
- `--color-primary`, `--color-secondary`, `--color-accent`
- `--color-text-primary`, `--color-text-secondary`, `--color-text-muted`
- `--color-bg-primary`, `--color-bg-secondary`, `--color-bg-hover`
- `--color-border`, `--color-border-light`, `--color-border-dark`
- `--color-success`, `--color-warning`, `--color-error`, `--color-info`

**Spacing:**
- `--space-0` through `--space-32` (maps to --size-*)
- `--space-component-gap`, `--space-section-gap`

**Typography:**
- `--text-xs`, `--text-sm`, `--text-base`, `--text-lg`, `--text-xl`, etc.
- `--text-heading-1` through `--text-heading-6`
- `--font-light`, `--font-normal`, `--font-medium`, `--font-semibold`, `--font-bold`
- `--leading-tight`, `--leading-normal`, `--leading-relaxed`
- `--tracking-tight`, `--tracking-normal`, `--tracking-wide`

**Shadows & Borders:**
- `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-xl`
- `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-xl`

**Transitions:**
- `--transition-fast`, `--transition-base`, `--transition-slow`
- `--ease-in`, `--ease-out`, `--ease-in-out`

**Layout:**
- `--container-sm`, `--container-md`, `--container-lg`, `--container-xl`
- `--prose-width`, `--content-width`
- `--breakpoint-sm`, `--breakpoint-md`, `--breakpoint-lg`

**Z-Index:**
- `--z-dropdown`, `--z-sticky`, `--z-fixed`, `--z-modal`, `--z-tooltip`

### 3. Components

**Rule:** ONLY use semantic tokens, never foundation tokens or hardcoded values.

**Good:**
```css
.button {
  padding: var(--space-4);
  background: var(--color-primary);
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
}
```

**Bad:**
```css
.button {
  padding: 16px;                    /* ❌ Hardcoded */
  background: var(--blue-500);      /* ❌ Foundation token */
  border-radius: 0.25rem;           /* ❌ Hardcoded */
}
```

## Dark Mode

Dark mode is handled automatically in `semantic.css`:

```css
[data-theme="dark"] {
  --color-text-primary: var(--gray-50);
  --color-bg-primary: #1a1a1a;
  /* ... other overrides */
}

/* System preference support */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    /* Same overrides */
  }
}
```

## Adding New Tokens

### For New Colors:
1. Add primitive to `foundation.css` (if needed)
2. Map to semantic purpose in `semantic.css`
3. Add dark mode override if needed

### For New Components:
1. Create file in appropriate directory (`components/`, `layouts/`, etc.)
2. Use ONLY semantic tokens
3. Import in `style.css`

## Migration from Legacy

The legacy `base/variables.css` file has been removed (October 2025). All variables are now in the semantic token system. No breaking changes - all variable names still work.

## Best Practices

✅ **Do:**
- Use semantic tokens exclusively
- Follow the cascade: Foundation → Semantic → Component
- Add dark mode overrides for new color tokens
- Use CSS custom properties for dynamic values

❌ **Don't:**
- Use foundation tokens directly in components
- Hardcode values (colors, sizes, etc.)
- Create component-specific variables in foundation.css
- Mix semantic and hardcoded values

## Performance

- **Total CSS Variables:** ~200 semantic tokens
- **File Size:** ~10KB (tokens only)
- **Build Impact:** Minimal (~5ms)
- **Runtime:** Optimized CSS custom property cascade

## Resources

- [CSS Custom Properties (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [Design Tokens (W3C)](https://design-tokens.github.io/community-group/format/)
- [CUBE CSS Methodology](https://cube.fyi/)

## Questions?

See `plan/completed/CSS_ARCHITECTURE_ANALYSIS.md` for the full migration history and rationale.
