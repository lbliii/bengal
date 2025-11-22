# Gradient Borders & Fluid Blobs - Usage Guide

**Implementation complete!** Here's how to use the new theme-aware gradient borders and fluid blob effects.

---

## What's Been Implemented

✅ **Cohesive Roundedness** - All elements now have increased border radius:
- Cards: 8px → 12px
- Code blocks: 12px → 16px
- Buttons/Forms/Tabs: 4px → 8px
- Blockquotes: 0px → 8px (added rounding!)
- Images: 4px → 8px
- Admonitions: Increased right-side radius

✅ **Theme-Aware Gradient Borders** - Gradients adapt to each palette
✅ **Fluid Blob Effects** - Subtle animations inspired by Bengal rosettes

---

## Usage

### Gradient Borders

Add `.gradient-border` class to any element:

```html
<!-- Cards -->
<div class="card gradient-border">...</div>
<div class="feature-card gradient-border">...</div>

<!-- Code blocks -->
<pre class="gradient-border"><code>...</code></pre>

<!-- Buttons (outline style) -->
<button class="button gradient-border">Click me</button>

<!-- Forms -->
<input type="text" class="form-input gradient-border">

<!-- Blockquotes -->
<blockquote class="gradient-border">...</blockquote>

<!-- Admonitions -->
<div class="admonition note gradient-border">...</div>
```

**Variants**:
- `.gradient-border` - Default (opacity 0.6)
- `.gradient-border-subtle` - More subtle (opacity 0.4)
- `.gradient-border-strong` - More visible (opacity 0.8)

### Fluid Blob Effects

Add fluid effect classes:

```html
<!-- Fluid background blob -->
<div class="card fluid-bg">...</div>

<!-- Flowing gradient border -->
<div class="card fluid-border">...</div>

<!-- Floating blob spots (rosette-inspired) -->
<div class="card blob-spots">...</div>

<!-- Combined effect (recommended) -->
<div class="card fluid-combined">...</div>
```

**Combined Usage** (Gradient + Fluid):

```html
<!-- Card with gradient border AND fluid background -->
<div class="card gradient-border fluid-combined">...</div>

<!-- Feature card with strong gradient and fluid bg -->
<div class="feature-card gradient-border-strong fluid-bg">...</div>
```

---

## Palette Behavior

Gradients automatically adapt to the active palette:

- **Blue Bengal**: Soft powder blue → Steel blue gradients
- **Brown Bengal**: Warm amber → Golden gradients
- **Silver Bengal**: Cool silver → Steel gradients
- **Charcoal Bengal**: Rich dark → Accent gradients

Switch palettes and gradients update automatically!

---

## Examples

### Feature Card with Full Effects

```html
<div class="feature-card gradient-border fluid-combined">
  <div class="feature-card__icon">...</div>
  <h3 class="feature-card__title">Feature Name</h3>
  <p class="feature-card__description">Description...</p>
</div>
```

### Code Block with Flowing Border

```html
<pre class="gradient-border fluid-border"><code>
def hello():
    print("Bengal theme!")
</code></pre>
```

### Button with Gradient

```html
<!-- Outline button with gradient border -->
<button class="button gradient-border">Learn More</button>

<!-- Primary button (uses gradient background) -->
<button class="button button-primary">Get Started</button>
```

---

## Customization

### Adjust Opacity

```css
/* In your custom CSS */
.card.gradient-border::before {
  opacity: 0.8; /* More visible */
}

pre.gradient-border::before {
  opacity: 0.3; /* More subtle */
}
```

### Adjust Animation Speed

```css
/* Faster blob movement */
.fluid-bg::before {
  animation: blob-morph 15s ease-in-out infinite;
}

/* Slower blob movement */
.fluid-bg::before {
  animation: blob-morph 30s ease-in-out infinite;
}
```

### Disable for Specific Elements

```css
/* Remove gradient border */
.no-gradient-border.gradient-border::before {
  display: none;
}

/* Remove fluid effects */
.no-fluid.fluid-combined::before,
.no-fluid.fluid-combined::after {
  display: none;
}
```

---

## Accessibility

✅ **Reduced Motion**: All animations respect `prefers-reduced-motion`  
✅ **Focus States**: Gradient borders maintain focus indicators  
✅ **Contrast**: Low opacity ensures readability  
✅ **Performance**: Uses GPU-accelerated properties

---

## Browser Support

- **Modern browsers**: Full support (Chrome, Firefox, Safari, Edge)
- **Mask fallback**: Uses `border-image` for older browsers
- **Color-mix fallback**: Uses rgba() for browsers without color-mix support
- **Graceful degradation**: Falls back to solid borders if gradients not supported

---

## Files Modified

### New Files
- `utilities/gradient-borders.css` - Gradient border utilities
- `utilities/fluid-blobs.css` - Fluid blob effect utilities

### Updated Files
- `style.css` - Added utility imports
- `components/cards.css` - Increased radius, added gradient support
- `components/code.css` - Increased radius, added gradient support
- `components/buttons.css` - Increased radius, added gradient support
- `components/forms.css` - Increased radius, added gradient support
- `components/tabs.css` - Increased radius, added gradient support
- `components/dropdowns.css` - Increased radius
- `base/typography.css` - Added blockquote rounding, increased image radius
- `components/admonitions.css` - Increased radius, added gradient support

---

## Next Steps

1. **Test** with your actual content
2. **Apply** classes to elements you want enhanced
3. **Customize** opacity/speed if needed
4. **Iterate** based on feedback

---

## Tips

- **Start subtle**: Use `.gradient-border-subtle` and `.fluid-combined` for documentation
- **Feature cards**: Use `.gradient-border-strong` + `.fluid-bg` for more impact
- **Code blocks**: `.gradient-border` + `.fluid-border` works well
- **Don't overuse**: Apply to key elements, not everything

---

## Questions?

- See `BORDER_STYLE_PROPOSAL.md` for design rationale
- See `FLUID_BLOB_EFFECTS.md` for blob effect details
- See `OPTION_D_THEME_AWARE.md` for gradient border details

