# Option D: Theme-Aware Gradient Borders

**Enhanced version** that uses Bengal's palette color tokens to create unique gradients for each theme variant.

---

## Concept

Instead of a single gradient for all themes, Option D now leverages the theme's own color tokens:

- **Blue Bengal**: Soft powder blue → steel blue gradients
- **Brown Bengal**: Warm amber → golden gradients  
- **Silver Bengal**: Cool silver → steel gradients
- **Charcoal Bengal**: Rich dark → accent gradients

Each palette gets its own character while maintaining visual cohesion.

---

## How It Works

### 1. CSS Custom Properties

The gradient borders use CSS variables that reference theme tokens:

```css
--gradient-border: linear-gradient(
  135deg,
  var(--color-primary) 0%,
  var(--color-accent) 50%,
  var(--color-primary) 100%
);
```

When you switch palettes, the gradient automatically adapts!

### 2. Palette-Specific Overrides

Each palette can customize its gradient:

```css
[data-palette="blue-bengal"] {
  --gradient-border: linear-gradient(
    135deg,
    var(--color-primary) 0%,      /* Powder blue */
    var(--color-accent) 50%,      /* Steel blue */
    var(--color-primary-dark) 100% /* Darker blue */
  );
}

[data-palette="brown-bengal"] {
  --gradient-border: linear-gradient(
    135deg,
    var(--color-primary) 0%,      /* Amber */
    var(--color-accent) 50%,      /* Golden */
    var(--color-primary-dark) 100% /* Rich brown */
  );
}
```

### 3. Component Application

Apply gradient borders using utility classes or component-specific styles:

```html
<!-- Cards -->
<div class="card gradient-border">...</div>

<!-- Code blocks -->
<pre class="gradient-border"><code>...</code></pre>

<!-- Buttons -->
<button class="button gradient-border">Click me</button>

<!-- Forms -->
<input type="text" class="form-input gradient-border">
```

---

## Variants

### Default Gradient Border
```html
<div class="card gradient-border">...</div>
```
- Uses `--gradient-border` (primary → accent → primary)
- Opacity: 0.6 (normal), 1.0 (hover)

### Subtle Gradient Border
```html
<div class="card gradient-border-subtle">...</div>
```
- Uses `--gradient-border-subtle` (lighter colors)
- Opacity: 0.4 (normal), 0.7 (hover)
- Best for: Background elements, less prominent cards

### Strong Gradient Border
```html
<div class="card gradient-border-strong">...</div>
```
- Uses `--gradient-border-strong` (darker, more vibrant)
- Opacity: 0.8 (normal), 1.0 (hover)
- Best for: Feature cards, CTAs, important elements

---

## Implementation Strategy

### Phase 1: Add Gradient Border Utilities
1. Import `border-gradient-theme-aware.css` after palette tokens
2. Test gradient borders on a few elements
3. Verify each palette shows unique gradients

### Phase 2: Apply to Components
1. **Cards**: Add `.gradient-border` to `.card`, `.feature-card`
2. **Code blocks**: Add to `pre` elements
3. **Buttons**: Add to `.button` (except `.button-primary`)
4. **Forms**: Add to `.form-input`, `.form-textarea`
5. **Blockquotes**: Add to `.prose blockquote`
6. **Admonitions**: Add to `.admonition`

### Phase 3: Fine-Tune Per Palette
1. Adjust gradient stops for each palette
2. Tune opacity levels
3. Test dark mode variants

---

## Example Gradients by Palette

### Blue Bengal
```
Primary: #7FA3C3 (powder blue)
Accent: #6991B5 (steel blue)
Gradient: Soft blue → Steel → Powder blue
```

### Brown Bengal
```
Primary: #D4850F (amber)
Accent: #E69A25 (golden)
Gradient: Amber → Golden → Rich brown
```

### Silver Bengal
```
Primary: (silver tones)
Accent: (steel tones)
Gradient: Silver → Steel → Darker silver
```

### Charcoal Bengal
```
Primary: (charcoal tones)
Accent: (accent color)
Gradient: Charcoal → Accent → Darker charcoal
```

---

## Benefits

✅ **Theme Cohesion**: Gradients match each palette's character  
✅ **Automatic Adaptation**: Switch palettes, gradients update automatically  
✅ **Consistent API**: Same classes work across all palettes  
✅ **Flexible**: Can customize per-palette or use defaults  
✅ **Accessible**: Respects reduced motion, maintains contrast  

---

## Usage Examples

### Cards
```html
<!-- Regular card with gradient -->
<div class="card gradient-border">
  <h3>Card Title</h3>
  <p>Card content...</p>
</div>

<!-- Feature card with strong gradient -->
<div class="feature-card gradient-border-strong">
  <h3>Featured</h3>
  <p>Important content...</p>
</div>
```

### Code Blocks
```html
<pre class="gradient-border"><code>
def hello():
    print("Gradient borders!")
</code></pre>
```

### Forms
```html
<input 
  type="text" 
  class="form-input gradient-border" 
  placeholder="Enter text..."
>
```

### Buttons
```html
<!-- Outline button with gradient -->
<button class="button gradient-border">Click me</button>

<!-- Primary button (no gradient, already filled) -->
<button class="button button-primary">Primary</button>
```

---

## Customization

### Adjust Gradient Intensity

```css
/* In your palette file */
[data-palette="blue-bengal"] {
  --gradient-border: linear-gradient(
    135deg,
    var(--color-primary) 0%,
    var(--color-accent) 30%,  /* Earlier stop = more accent */
    var(--color-primary) 100%
  );
}
```

### Adjust Opacity

```css
/* Component-specific */
.card.gradient-border::before {
  opacity: 0.8; /* More visible */
}

pre.gradient-border::before {
  opacity: 0.3; /* More subtle */
}
```

### Custom Gradient Directions

```css
/* Vertical gradient */
--gradient-border-vertical: linear-gradient(
  180deg,
  var(--color-primary) 0%,
  var(--color-accent) 100%
);

/* Radial gradient */
--gradient-border-radial: radial-gradient(
  circle,
  var(--color-primary) 0%,
  var(--color-accent) 100%
);
```

---

## Browser Support

- **Modern browsers**: Full support (Chrome, Firefox, Safari, Edge)
- **Mask fallback**: Uses `border-image` for older browsers
- **Graceful degradation**: Falls back to solid border if gradients not supported

---

## Testing Checklist

- [ ] Blue Bengal palette shows blue gradients
- [ ] Brown Bengal palette shows amber/gold gradients
- [ ] Silver Bengal palette shows silver gradients
- [ ] Charcoal Bengal palette shows dark gradients
- [ ] Dark mode gradients are appropriately subtle
- [ ] Hover states work correctly
- [ ] Focus states maintain accessibility
- [ ] Reduced motion is respected
- [ ] Fallback works in older browsers

---

## Next Steps

1. **Review** `border-gradient-theme-aware.css`
2. **Test** with each palette variant
3. **Customize** gradients per palette if needed
4. **Apply** to components gradually
5. **Iterate** based on feedback

---

## Files

- **Implementation**: `bengal/themes/default/assets/css/experimental/border-gradient-theme-aware.css`
- **Demo**: `demo-option-d.html` (update to show palette switching)
- **Documentation**: This file

