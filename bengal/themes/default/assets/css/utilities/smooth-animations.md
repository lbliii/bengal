# Smooth Animations System

**Inspired by**: Fern's Ask AI panel smooth expansion  
**Purpose**: GPU-accelerated, buttery-smooth animations for drawers, panels, and UI elements

---

## Quick Start

### Drawer/Panel (Bottom Slide)
```html
<div class="smooth-drawer smooth-drawer-bottom" data-open="false">
  <!-- Panel content -->
</div>
```

```javascript
// Open drawer
drawer.setAttribute('data-open', 'true');

// Close drawer
drawer.setAttribute('data-open', 'false');
```

### Slide Animations
```html
<div class="smooth-slide-up">
  <!-- Content slides up smoothly -->
</div>
```

```javascript
// Show element
element.classList.add('is-visible');
// or
element.setAttribute('data-visible', 'true');
```

---

## Available Classes

### Drawer/Panel Classes

- `.smooth-drawer` - Base drawer class (adds touch-action, will-change, transition)
- `.smooth-drawer-bottom` - Slides from bottom
- `.smooth-drawer-top` - Slides from top
- `.smooth-drawer-left` - Slides from left
- `.smooth-drawer-right` - Slides from right

**Usage**:
```html
<div class="smooth-drawer smooth-drawer-bottom" data-open="false">
  <div class="smooth-overlay" data-open="false"></div>
  <!-- Content -->
</div>
```

### Slide Animation Classes

- `.smooth-slide-up` - Slides up with fade
- `.smooth-slide-down` - Slides down with fade
- `.smooth-slide-left` - Slides left with fade
- `.smooth-slide-right` - Slides right with fade

**Usage**:
```html
<div class="smooth-slide-up">
  <!-- Hidden by default -->
</div>

<script>
  // Show element
  element.classList.add('is-visible');
</script>
```

### Other Classes

- `.smooth-overlay` - Backdrop overlay with smooth fade
- `.smooth-fade-scale` - Fade + scale animation (for modals)
- `.smooth-raise` - GPU-accelerated hover raise effect

---

## How It Works

### The 4 Techniques (Fern-inspired)

1. **GPU Acceleration**: Uses `translate3d()` instead of `translateY()`
2. **Will-Change Hint**: Browser optimizes in advance
3. **Custom Easing**: `cubic-bezier(0.32, 0.72, 0, 1)` for natural motion
4. **Touch Action Control**: Prevents scroll interference

### CSS Variables

```css
--ease-smooth: cubic-bezier(0.32, 0.72, 0, 1);
--transition-smooth: 500ms var(--ease-smooth);
```

---

## Examples

### Example 1: Side Panel
```html
<div class="smooth-drawer smooth-drawer-right" data-open="false">
  <div class="smooth-overlay" data-open="false"></div>
  <div class="panel-content">
    <h2>Side Panel</h2>
    <p>Content here</p>
  </div>
</div>
```

### Example 2: Modal with Backdrop
```html
<div class="smooth-overlay" data-open="false"></div>
<div class="smooth-fade-scale modal" data-visible="false">
  <h2>Modal Title</h2>
  <p>Modal content</p>
</div>
```

### Example 3: Staggered List Items
```html
<ul class="stagger-children">
  <li class="smooth-slide-up">Item 1</li>
  <li class="smooth-slide-up">Item 2</li>
  <li class="smooth-slide-up">Item 3</li>
</ul>
```

---

## Performance Notes

- **will-change** is automatically removed after animation completes
- **GPU acceleration** via `translate3d()` ensures 60fps
- **Reduced motion** is respected (animations disabled)
- **Mobile optimized** (will-change removed on mobile for hover effects)

---

## Integration with Existing Code

The smooth animation system integrates seamlessly with Bengal's existing:
- Motion utilities (`utilities/motion.css`)
- Design tokens (`tokens/foundation.css`, `tokens/semantic.css`)
- Reduced motion preferences
- Existing component styles

---

## Browser Support

- **translate3d()**: All modern browsers
- **will-change**: Safari 9+, Chrome 36+, Firefox 36+
- **backdrop-filter**: Safari 9+, Chrome 76+, Firefox 103+

Fallbacks are included for older browsers.
