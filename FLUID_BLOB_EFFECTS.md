# Fluid Blob Effects for Bengal Theme

**Concept**: Subtle fluid/blob-like animations inspired by Bengal cat rosettes and spots. Very gentle, puddle-like movement that adds life without distraction.

---

## Design Philosophy

Bengal cats have distinctive rosettes and spots - patterns that are organic, fluid, and beautiful. These effects translate that into subtle UI animations:

- **Very subtle** - barely noticeable, but adds life
- **Organic** - blob-like, puddle-like, natural movement
- **Non-distracting** - doesn't interfere with reading
- **Theme-aware** - uses palette colors
- **Accessible** - respects `prefers-reduced-motion`

---

## Effect Types

### 1. Fluid Background Blob
**Large morphing background gradients that slowly shift**

- Large radial gradients that morph shape
- Very slow movement (20-25s cycles)
- Low opacity (4-8%)
- Best for: Feature cards, hero sections

### 2. Flowing Gradient Border
**Gradient that slowly flows along the border**

- Gradient position animates
- Creates a "flowing" effect
- Medium speed (8s cycles)
- Best for: Cards, code blocks

### 3. Floating Blob Spots
**Small floating spots that gently move (rosette-inspired)**

- Multiple small blob spots
- Independent floating animations
- Different sizes and speeds
- Best for: Background elements, subtle accents

### 4. Morphing Border Shape
**Border radius subtly changes like a puddle edge**

- Border radius morphs slightly
- Very subtle shape changes
- Slow movement (10-12s cycles)
- Best for: Cards, containers

### 5. Combined Effect
**Background blob + flowing border together**

- Most subtle version
- Both effects work together
- Perfect for documentation
- Best for: Main content cards

---

## Implementation

### CSS Variables

```css
:root {
  /* Blob animation durations */
  --blob-duration-slow: 20s;
  --blob-duration-medium: 12s;
  --blob-duration-fast: 8s;
  
  /* Blob opacity levels */
  --blob-opacity-subtle: 0.04;
  --blob-opacity-normal: 0.06;
  --blob-opacity-strong: 0.08;
  
  /* Blob colors (theme-aware) */
  --blob-color-1: rgba(var(--color-primary-rgb), var(--blob-opacity-normal));
  --blob-color-2: rgba(var(--color-accent-rgb), var(--blob-opacity-subtle));
}
```

### Component Classes

```html
<!-- Fluid background -->
<div class="card card-fluid-bg">...</div>

<!-- Flowing border -->
<div class="card card-fluid-border">...</div>

<!-- Floating spots -->
<div class="card card-blob-spots">...</div>

<!-- Morphing border -->
<div class="card card-morph-border">...</div>

<!-- Combined (recommended) -->
<div class="card card-combined">...</div>
```

---

## Usage Recommendations

### Documentation Sites
**Use**: Combined effect (most subtle)
- Adds life without distraction
- Professional but unique
- Works well for long-form content

### Feature Cards
**Use**: Fluid background blob
- More noticeable
- Draws attention appropriately
- Good for CTAs

### Code Blocks
**Use**: Flowing gradient border
- Subtle movement
- Doesn't interfere with code reading
- Adds visual interest

### Background Elements
**Use**: Floating blob spots
- Very subtle
- Adds texture
- Doesn't compete with content

---

## Performance Considerations

### Optimizations
- Use `transform` and `opacity` (GPU-accelerated)
- Keep animations simple (no complex calculations)
- Use `will-change` sparingly
- Limit number of animated elements per page

### Browser Support
- Modern browsers: Full support
- Older browsers: Graceful degradation (static gradients)
- Reduced motion: Animations disabled

---

## Accessibility

### Reduced Motion
All effects respect `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  .card-fluid-bg::before,
  .card-fluid-border::before {
    animation: none !important;
  }
}
```

### Visual Impact
- Low opacity ensures readability
- Doesn't affect text contrast
- Can be disabled via CSS if needed

---

## Theme Integration

### Palette-Aware Colors

Each palette gets its own blob colors:

```css
/* Blue Bengal */
[data-palette="blue-bengal"] {
  --blob-color-1: rgba(127, 163, 195, 0.06);
  --blob-color-2: rgba(105, 145, 181, 0.04);
}

/* Brown Bengal */
[data-palette="brown-bengal"] {
  --blob-color-1: rgba(212, 133, 15, 0.06);
  --blob-color-2: rgba(230, 154, 37, 0.04);
}
```

---

## Customization

### Adjust Speed
```css
.card-fluid-bg::before {
  animation: blob-morph 15s ease-in-out infinite; /* Faster */
  /* or */
  animation: blob-morph 30s ease-in-out infinite; /* Slower */
}
```

### Adjust Opacity
```css
.card-fluid-bg::before {
  background: radial-gradient(
    circle,
    rgba(59, 130, 246, 0.12) 0%, /* More visible */
    transparent 60%
  );
}
```

### Adjust Size
```css
.card-fluid-bg::before {
  width: 150%; /* Smaller */
  height: 150%;
  /* or */
  width: 250%; /* Larger */
  height: 250%;
}
```

---

## Testing Checklist

- [ ] Animations are subtle (not distracting)
- [ ] Respects `prefers-reduced-motion`
- [ ] Works in all palettes (blue, brown, silver, charcoal)
- [ ] Works in dark mode
- [ ] Performance is good (60fps)
- [ ] Doesn't affect readability
- [ ] Mobile-friendly (doesn't drain battery)

---

## Examples

See `demo-fluid-blob-effects.html` for live examples of all effect types.

---

## Next Steps

1. **Review** the demo
2. **Choose** which effects to use
3. **Test** with actual content
4. **Fine-tune** opacity and speed
5. **Implement** in production CSS

---

## Files

- **Demo**: `demo-fluid-blob-effects.html`
- **Documentation**: This file
- **Implementation**: (To be created in `components/` or `utilities/`)

