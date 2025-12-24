# Bengal Motion & Transitions Design System

## Philosophy

Bengal's motion design follows these principles:

1. **Purposeful** - Motion should guide attention, not distract
2. **Subtle** - Micro-interactions over dramatic effects
3. **Consistent** - Same timing/easing across similar interactions
4. **Accessible** - Respect `prefers-reduced-motion`

## Two Animation Systems

Bengal uses two distinct animation systems that should NOT overlap:

### 1. View Transitions API (Page Navigation)
- **Scope:** Cross-document/page navigation only
- **File:** `base/transitions.css`
- **Elements:** Only `main-content` has a view-transition-name
- **Duration:** 180ms crossfade (default)
- **Key Rule:** Header, footer, sidebars stay stable (no view-transition-name)

### 2. CSS Transitions (In-Page Interactions)
- **Scope:** Hover, focus, open/close, state changes
- **Files:** Individual component CSS files
- **Tokens:** Use semantic motion tokens (see below)

## Motion Tokens

### Duration Scale
```css
--duration-75: 75ms;     /* Micro: checkbox, toggle */
--duration-100: 100ms;   /* Quick: button press feedback */
--duration-150: 150ms;   /* Fast: hover states, small reveals */
--duration-200: 200ms;   /* Base: standard interactions */
--duration-300: 300ms;   /* Slow: larger reveals, panels */
--duration-500: 500ms;   /* Smooth: drawers, modals */
```

### Easing Functions
```css
--ease-out: cubic-bezier(0, 0, 0.2, 1);      /* Decelerate: entering elements */
--ease-in: cubic-bezier(0.4, 0, 1, 1);       /* Accelerate: exiting elements */
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1); /* Symmetric: state toggles */
--ease-smooth: cubic-bezier(0.32, 0.72, 0, 1); /* Fern-inspired: drawers/panels */
```

### Semantic Transition Tokens
```css
--transition-fast: 150ms ease-out;    /* Hover, focus, small state changes */
--transition-base: 200ms ease-out;    /* Standard interactions */
--transition-slow: 300ms ease-in-out; /* Larger state changes */
--transition-smooth: 500ms ease-smooth; /* Drawers, panels, overlays */
```

### Motion Tokens
```css
--motion-fast: 150ms ease-out;
--motion-medium: 200ms ease-out;
--motion-slow: 300ms ease-in-out;

--motion-distance-1: 2px;   /* Micro nudge */
--motion-distance-2: 4px;   /* Small raise/slide */
--motion-distance-3: 8px;   /* Content reveal */
--motion-scale-up: 1.02;    /* Subtle hover scale */
--motion-scale-down: 0.98;  /* Press feedback */
```

## Interaction Patterns

### Hover States
- **Cards/Buttons:** `--transition-fast` with `--motion-distance-2` translateY
- **Links:** `--transition-fast` color change only
- **Icons:** `--motion-fast` with subtle scale

### Focus States
- **Duration:** Instant outline appearance (no transition on outline)
- **Style:** 2px solid `--color-border-focus`, 2px offset

### Open/Close (Dropdowns, Modals)
- **Opening:** `--transition-fast` with translateY(-8px) → 0
- **Closing:** Slightly faster, same easing
- **Backdrop:** `--transition-slow` opacity

### Dialogs & Modals
- **Enter:** `--transition-fast` scale(0.95) → scale(1) + opacity
- **Exit:** `--transition-fast` reverse
- **Backdrop:** `--transition-slow` blur + opacity

### Page Navigation (View Transitions)
- **Default (crossfade):** 180ms pure opacity fade
- **Fade-slide:** 150ms opacity + 10px translateY
- **Slide:** 200ms horizontal slide
- **None:** Instant

## Component-Specific Guidelines

### Header
- Nav item hover: `--transition-fast`
- Submenu reveal: `--transition-fast` with translateY
- Mobile menu: `--transition-smooth` (500ms drawer)

### Search Modal
- Open: 150ms scale + opacity
- Result highlight: `--transition-fast`
- Close: Slightly faster than open

### Sidebar/TOC
- Section expand: `--transition-smooth`
- Active item: `--transition-fast`
- Scroll indicator: 100ms linear (tracks scroll precisely)

### Cards
- Hover lift: `--motion-medium` with `--motion-distance-2`
- Click: 50ms scale feedback
- Focus: Instant outline

## Reduced Motion

All animations respect `prefers-reduced-motion: reduce`:

```css
@media (prefers-reduced-motion: reduce) {
  /* View transitions */
  ::view-transition-group(*),
  ::view-transition-old(*),
  ::view-transition-new(*) {
    animation: none !important;
  }

  /* CSS transitions */
  * {
    transition-duration: 0ms !important;
    animation-duration: 0ms !important;
  }
}
```

## Anti-Patterns (Don't Do)

1. ❌ Multiple view-transition-names that morph between different layouts
2. ❌ Hardcoded timing values instead of tokens
3. ❌ Long animations (>500ms) for frequent interactions
4. ❌ Animation on page load for above-the-fold content
5. ❌ `will-change` left on elements permanently
6. ❌ Transitions on layout properties (width, height, top, left)
7. ❌ Different timing for enter vs exit (unless intentional)

## Performance Guidelines

1. **Use transform/opacity only** - GPU accelerated
2. **Add will-change sparingly** - Remove after animation completes
3. **Use translate3d()** - Forces GPU layer
4. **Avoid animating during scroll** - Use passive listeners
5. **Keep durations short** - <300ms for most interactions
