# Motion & Micro‑Interactions Strategy

Date: 2025‑10‑17
Status: Proposal (Active)
Scope: Default theme (CSS only)

## Goals
- Add polished, consistent micro‑interactions across components using existing tokens
- Respect user preferences (`prefers-reduced-motion`) via semantic tokens
- Keep implementation small: utilities + light component hooks

## Principles
- Subtle by default (≤ 200ms, small distances, low opacity shifts)
- Purposeful: motion conveys state, hierarchy, or affordance
- Accessible: all motion gated by semantic transition tokens; zeroed when reduced motion
- Composable: prefer utilities and data‑attributes over deep selectors

## Token Review (Existing)
- Durations: `--duration-75/100/150/200/300/500/700/1000`
- Easing: `--ease-out`, `--ease-in`, `--ease-in-out`
- Semantic transitions: `--transition-fast`, `--transition-base`, `--transition-slow`, `--transition-slower`
- Reduced‑motion mapping already zeroes durations and transitions in `tokens/semantic.css`

## Proposed Token Additions (Semantic)
Add only semantic aliases; keep primitives unchanged.

- Motion categories
  - `--motion-distance-1: 2px;`  // micro nudge
  - `--motion-distance-2: 4px;`  // small slide/raise
  - `--motion-distance-3: 8px;`  // larger content reveal
  - `--motion-blur-1: 6px;`      // small backdrop blur pop
  - `--motion-scale-up: 1.02;`   // subtle scale for hover
  - `--motion-scale-down: 0.98;` // press feedback

- Timing aliases (compositions on existing durations)
  - `--motion-fast: var(--duration-150) var(--ease-out);`
  - `--motion-medium: var(--duration-200) var(--ease-out);`
  - `--motion-slow: var(--duration-300) var(--ease-in-out);`

These map to existing primitives so reduced‑motion overrides keep working.

## Utility Classes (New)
Minimal, reusable utilities to standardize micro interactions.

- Hover/press affordances
  - `.ux-raise` → translateY(-var(--motion-distance-2)) + shadow to `--elevation-card-hover)
  - `.ux-press` → scale(var(--motion-scale-down))
  - `.ux-scale` → scale(var(--motion-scale-up)) on hover

- Fades/slides
  - `.fade-in` → opacity transition in
  - `.slide-in-up` → transform: translateY(var(--motion-distance-3)) to 0
  - `.slide-in-down` → translateY(-var(--motion-distance-3)) to 0

- Focus/active
  - `.focus-glow` → transition box-shadow to focus ring using `--color-border-focus`

- Stagger helpers
  - `.stagger-children > *` with nth-child transition‑delay steps of 30ms

All should be wrapped in existing reduced‑motion media query to disable animations and use only opacity/color where needed.

## Component Recipes
Apply small, coherent touches per component using utilities + local tweaks:

- Buttons (`components/buttons.css`)
  - Default: transition `background, color, border-color` with `--motion-medium`
  - Hover: `.ux-raise` for secondary/ghost; primary uses subtle `filter: brightness(1.03)`
  - Active: `.ux-press` (scale down), reduce shadow

- Cards (`components/cards.css`)
  - Card hover: `.ux-raise` + elevate to `--elevation-card-hover`
  - Link‑card: underline slide‑in on title using background‑size animation (no layout shift)

- Navigation (`components/navigation.css`, `layouts/header.css`)
  - Hover underline from center (scaleX) using `transform-origin: center` and `--motion-fast`
  - Active item: color transition only (no translate to avoid nav shift)

- Dropdowns/Popovers (`components/dropdowns.css`)
  - Open: `.slide-in-down` + slight fade; origin top
  - Close: reverse; ensure `will-change: opacity, transform`

- TOC/Sidebars (`components/toc.css`, `components/docs-nav.css`)
  - Current item: color + subtle left border grow via width transition

- Search/Modals (`components/interactive.css`)
  - Backdrop fade only; dialog uses `.slide-in-up` 8px

- Tags/Badges (`components/tags.css`)
  - Hover: background tint and subtle scale to 1.02

## Accessibility & Safety
- Honor `prefers-reduced-motion`: utilities degrade to instant state changes
- Avoid parallax, large translations, continuous attention‑seeking motion
- Keep transforms on GPU‑friendly properties (transform, opacity)
- Provide adequate focus styles independent of motion

## Implementation Plan
1) Add semantic tokens to `tokens/semantic.css` (under transitions block)
2) Create `utilities/motion.css` with utilities above; import in `style.css` under `@layer utilities`
3) Apply utilities in components with minimal selector changes
4) QA: light/dark, mobile, keyboard nav, reduced‑motion

## Examples (CSS snippets)
```css
/* tokens/semantic.css */
:root {
  --motion-distance-1: 2px;
  --motion-distance-2: 4px;
  --motion-distance-3: 8px;
  --motion-blur-1: 6px;
  --motion-scale-up: 1.02;
  --motion-scale-down: 0.98;
  --motion-fast: var(--duration-150) var(--ease-out);
  --motion-medium: var(--duration-200) var(--ease-out);
  --motion-slow: var(--duration-300) var(--ease-in-out);
}
```

```css
/* utilities/motion.css (new) */
@layer utilities {
  .ux-raise { transition: transform var(--motion-medium), box-shadow var(--motion-medium); }
  .ux-raise:hover { transform: translateY(calc(-1 * var(--motion-distance-2))); box-shadow: var(--elevation-card-hover); }

  .ux-press { transition: transform var(--motion-fast); }
  .ux-press:active { transform: scale(var(--motion-scale-down)); }

  .ux-scale { transition: transform var(--motion-medium); }
  .ux-scale:hover { transform: scale(var(--motion-scale-up)); }

  .fade-in { opacity: 0; transform: translateY(var(--motion-distance-1)); transition: opacity var(--motion-medium), transform var(--motion-medium); }
  .fade-in.is-visible { opacity: 1; transform: none; }

  .slide-in-up { transform: translateY(var(--motion-distance-3)); opacity: 0; transition: transform var(--motion-medium), opacity var(--motion-medium); }
  .slide-in-up.is-visible { transform: none; opacity: 1; }

  .slide-in-down { transform: translateY(calc(-1 * var(--motion-distance-3))); opacity: 0; transition: transform var(--motion-medium), opacity var(--motion-medium); }
  .slide-in-down.is-visible { transform: none; opacity: 1; }

  .focus-glow { transition: box-shadow var(--motion-fast); }
  .focus-glow:focus-visible { box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-border-focus) 25%, transparent); }

  .stagger-children > * { transition: opacity var(--motion-medium), transform var(--motion-medium); }
  .stagger-children > *:nth-child(1) { transition-delay: 0ms; }
  .stagger-children > *:nth-child(2) { transition-delay: 30ms; }
  .stagger-children > *:nth-child(3) { transition-delay: 60ms; }
  .stagger-children > *:nth-child(4) { transition-delay: 90ms; }
}

@media (prefers-reduced-motion: reduce) {
  @layer utilities {
    .ux-raise, .ux-press, .ux-scale, .fade-in, .slide-in-up, .slide-in-down, .stagger-children > * { transition: none !important; transform: none !important; }
  }
}
```

## Rollout
- Phase 1: Add tokens + utilities, wire into buttons/cards/nav with low risk
- Phase 2: Extend to dropdowns, popovers, modals, search
- Phase 3: Evaluate component‑specific refinements from user feedback

## Risks
- Overuse of translate/scale on layout‑sensitive elements → visual shift
- Stagger delays accumulating on large lists → perceived latency

## Success Criteria
- Visual polish without distraction
- No layout jank, no CLS regressions
- Reduced‑motion users see instant state changes
