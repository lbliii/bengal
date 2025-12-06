---
title: "Enhanced Neumorphic Components"
description: "Prototype implementation of enhanced neumorphic shadows with multi-layer depth"
layout: doc
---

# Enhanced Neumorphic Components

Prototype implementation of enhanced neumorphic shadows with multi-layer depth, refined borders, and softer shapes while preserving Bengal's distinctive tactile feel.

## Overview

This prototype explores enhancing Bengal's existing neumorphic style by incorporating:

- **Multi-layer shadow depth** - Border-defining shadows + depth layers
- **Refined borders** - Softer opacity (0.08 vs 0.1) for cleaner edges
- **Enhanced border radius** - Softer shapes (16-20px for code blocks, 12-16px for cards)
- **Preserved tactile feel** - All neumorphic inset/outset characteristics maintained

## Demo

Open the prototype demo:

```bash
# Start dev server
bengal site serve

# Open demo in browser
open http://localhost:5173/themes/default/assets/css/experimental/enhanced-neumorphic-demo.html
```

Or view the demo file directly:
- **Demo HTML**: `bengal/themes/default/assets/css/experimental/enhanced-neumorphic-demo.html`
- **Prototype CSS**: `bengal/themes/default/assets/css/experimental/enhanced-neumorphic-prototype.css`

## Components

### Code Blocks

Enhanced code blocks feature:
- Refined border: `rgba(0, 0, 0, 0.08)` (softer than current 0.1)
- Enhanced border radius: `20px` (vs current 16px)
- Multi-layer shadows: Border-defining + depth layers
- Enhanced neumorphic base shadow

```css
.enhanced-code-block {
  border: var(--border-refined-base);
  border-radius: var(--radius-soft-2xl); /* 20px */
  box-shadow: var(--neumorphic-enhanced-base);
}
```

### Cards

Enhanced cards feature:
- Refined border with softer opacity
- Enhanced border radius: `16px` (vs current 12px)
- Enhanced neumorphic subtle shadow
- Smooth hover transitions

```css
.enhanced-card {
  border: var(--border-refined-base);
  border-radius: var(--radius-soft-xl); /* 16px */
  box-shadow: var(--neumorphic-enhanced-subtle);
}
```

### Buttons

Enhanced button variant (optional):
- Refined border
- Enhanced border radius: `12px` (vs current 8px)
- Enhanced neumorphic shadows
- Maintains tactile feel

### Form Inputs

Enhanced inputs feature:
- Refined borders
- Enhanced border radius: `8px`
- Enhanced neumorphic subtle shadows
- Focus states with enhanced shadows

### Badges & Tags

Enhanced badges feature:
- Refined borders
- Enhanced border radius: `8px`
- Enhanced neumorphic subtle shadows

### Alerts

Enhanced alerts feature:
- Refined borders with left accent
- Enhanced border radius: `12px`
- Enhanced neumorphic shadows

## Design Tokens

### Enhanced Neumorphic Shadows

```css
/* Base - multi-layer depth with border-defining shadow */
--neumorphic-enhanced-base:
  /* Neumorphic layers (tactile feel) */
  inset 0 0 0 1px rgba(255, 255, 255, 0.35),
  inset 0.5px 0.5px 1px rgba(255, 255, 255, 0.4),
  inset -0.5px -0.5px 1px rgba(0, 0, 0, 0.1),
  /* Border-defining shadow */
  0 0 0 1px rgba(0, 0, 0, 0.06),
  /* Depth layers */
  0 1px 2px rgba(0, 0, 0, 0.04),
  0 2px 4px rgba(0, 0, 0, 0.03),
  /* Neumorphic highlight */
  -0.5px -0.5px 1px rgba(255, 255, 255, 0.3);

/* Hover - enhanced raised effect */
--neumorphic-enhanced-hover: /* ... */

/* Subtle - for smaller elements */
--neumorphic-enhanced-subtle: /* ... */
```

### Refined Border Tokens

```css
--border-refined-subtle: 1px solid rgba(0, 0, 0, 0.06);
--border-refined-base: 1px solid rgba(0, 0, 0, 0.08);
--border-refined-strong: 1px solid rgba(0, 0, 0, 0.1);
```

### Soft Border Radius Variants

```css
--radius-soft-sm: 0.375rem;   /* 6px */
--radius-soft-md: 0.5rem;      /* 8px */
--radius-soft-lg: 0.75rem;    /* 12px */
--radius-soft-xl: 1rem;       /* 16px */
--radius-soft-2xl: 1.25rem;   /* 20px */
--radius-soft-3xl: 1.5rem;    /* 24px */
```

## Comparison: Standard vs Enhanced

The prototype includes side-by-side comparisons showing:

- **Standard**: Current neumorphic styling
- **Enhanced**: Enhanced neumorphic with multi-layer depth

Key differences:
- Softer border opacity (0.08 vs 0.1)
- Enhanced border radius (softer shapes)
- Multi-layer shadow depth (border-defining + depth layers)
- Preserved tactile neumorphic feel

## Dark Mode Support

All enhanced tokens include dark mode variants:

```css
[data-theme="dark"] {
  --neumorphic-enhanced-base: /* dark mode variant */
  --border-refined-base: 1px solid rgba(255, 255, 255, 0.08);
}
```

## Usage

### Apply Enhanced Styles

```html
<!-- Enhanced code block -->
<div class="enhanced-code-block">
  <pre><code>const example = "enhanced styling";</code></pre>
</div>

<!-- Enhanced card -->
<div class="enhanced-card">
  <div class="enhanced-card-header">
    <h3>Card Title</h3>
  </div>
  <div class="enhanced-card-body">
    <p>Card content</p>
  </div>
</div>

<!-- Enhanced button -->
<button class="enhanced-button enhanced-button-primary">
  Click Me
</button>
```

### Use Design Tokens Directly

```css
.my-component {
  border: var(--border-refined-base);
  border-radius: var(--radius-soft-xl);
  box-shadow: var(--neumorphic-enhanced-base);
}

.my-component:hover {
  border-color: var(--border-refined-strong);
  box-shadow: var(--neumorphic-enhanced-hover);
}
```

## Related

- **RFC**: `plan/rfc-flat-dimensional-aesthetic.md` - Full design rationale and implementation plan
- **Tokens**: `bengal/themes/default/assets/css/tokens/semantic.css` - Enhanced neumorphic token definitions

## Status

**Prototype** - This is an experimental implementation for testing and feedback. Not yet integrated into main theme.

:::{warning}
**Experimental** - These styles are prototypes and may change. Use with caution in production.
:::

