# CSS Modernization Plan - Bleeding-Edge Features

**Goal**: Make Bengal's CSS embrace all modern CSS features and APIs  
**Priority**: High  
**Status**: Planning → Implementation

---

## 🎯 Modern CSS Features to Implement

### Phase 1: Container Queries (Highest Impact)

**Status**: ❌ Not implemented  
**Browser Support**: ✅ All modern browsers (2023+)  
**Impact**: High - Component-level responsiveness

**Implementation Targets**:
- [ ] Card grids (respond to container, not viewport)
- [ ] Navigation menus
- [ ] Sidebar components
- [ ] Code blocks
- [ ] Tables
- [ ] Form layouts

**Example**:
```css
.card-container {
  container-type: inline-size;
  container-name: card-grid;
}

@container card-grid (min-width: 400px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@container card-grid (min-width: 600px) {
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

---

### Phase 2: Grid Template Areas (Readability)

**Status**: ❌ Not implemented  
**Browser Support**: ✅ All browsers  
**Impact**: Medium - Better code readability

**Implementation Targets**:
- [ ] Docs layout (sidebar, content, toc)
- [ ] Header layout
- [ ] Footer layout
- [ ] Card layouts
- [ ] Form layouts

**Example**:
```css
.docs-layout {
  display: grid;
  grid-template-areas:
    "sidebar content toc";
  grid-template-columns: minmax(240px, 280px) minmax(0, 1fr) minmax(200px, 260px);
  gap: 2rem;
}

.docs-sidebar { grid-area: sidebar; }
.docs-main { grid-area: content; }
.docs-toc { grid-area: toc; }
```

---

### Phase 3: Subgrid (Nested Grids)

**Status**: ❌ Not implemented  
**Browser Support**: ✅ Firefox, Chrome 117+, Safari 16+  
**Impact**: Medium - Cleaner nested grids

**Implementation Targets**:
- [ ] Card grids with nested content
- [ ] Table layouts
- [ ] Form layouts
- [ ] Navigation menus

**Example**:
```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.card {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: span 3;
}
```

---

### Phase 4: Aspect Ratio (All Images/Cards)

**Status**: ⚠️ Partial (12 instances)  
**Browser Support**: ✅ All modern browsers  
**Impact**: High - Consistent sizing

**Implementation Targets**:
- [ ] All card images
- [ ] Hero images
- [ ] Blog post images
- [ ] Code block containers
- [ ] Video embeds
- [ ] Icon containers

**Example**:
```css
.card-image {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

.hero-image {
  aspect-ratio: 21 / 9;
  object-fit: cover;
}
```

---

### Phase 5: :has() Selector (Conditional Styling)

**Status**: ⚠️ Limited (only api-docs.css)  
**Browser Support**: ✅ All modern browsers  
**Impact**: High - Cleaner conditional styles

**Implementation Targets**:
- [ ] Cards with/without images
- [ ] Lists with icons
- [ ] Forms with errors
- [ ] Navigation with active items
- [ ] Tables with headers

**Example**:
```css
/* Card with image gets different layout */
.card:has(.card-image) {
  grid-template-rows: auto 1fr auto;
}

.card:not(:has(.card-image)) {
  padding: 2rem;
}

/* Form field with error */
.form-group:has(.error) {
  border-color: var(--color-error);
}
```

---

### Phase 6: CSS Layers (@layer)

**Status**: ⚠️ Partial (utilities layer)  
**Browser Support**: ✅ All modern browsers  
**Impact**: Medium - Better cascade control

**Implementation Targets**:
- [ ] Organize all CSS into layers
- [ ] Replace `!important` with layer ordering
- [ ] Create layer hierarchy

**Example**:
```css
@layer reset, base, components, utilities, overrides;

@layer base {
  /* Base styles */
}

@layer components {
  /* Component styles */
}

@layer utilities {
  /* Utility classes */
}
```

---

### Phase 7: Logical Properties

**Status**: ⚠️ Partial  
**Browser Support**: ✅ All modern browsers  
**Impact**: Medium - Better RTL support

**Implementation Targets**:
- [ ] Replace `left/right` with `inline-start/inline-end`
- [ ] Replace `top/bottom` with `block-start/block-end`
- [ ] Replace `width/height` with `inline-size/block-size`
- [ ] Replace `margin/padding` with logical equivalents

**Example**:
```css
/* Before */
.card {
  padding-left: 1rem;
  padding-right: 1rem;
  margin-top: 2rem;
}

/* After */
.card {
  padding-inline: 1rem;
  margin-block-start: 2rem;
}
```

---

### Phase 8: Color Functions (Modern)

**Status**: ⚠️ Partial  
**Browser Support**: ✅ All modern browsers  
**Impact**: Low - Better color manipulation

**Implementation Targets**:
- [ ] Use `color-mix()` for hover states
- [ ] Use `oklch()` for better color spaces
- [ ] Use `relative-color-syntax`

**Example**:
```css
.button:hover {
  background: color-mix(in srgb, var(--color-primary) 90%, black);
}

:root {
  --color-primary: oklch(60% 0.2 250);
}
```

---

### Phase 9: View Transitions API

**Status**: ❌ Not implemented  
**Browser Support**: ⚠️ Chrome 111+, Firefox 127+  
**Impact**: High - Smooth page transitions

**Implementation Targets**:
- [ ] Page transitions
- [ ] Modal open/close
- [ ] Tab switching
- [ ] Image lightbox

**Example**:
```css
@view-transition {
  navigation: auto;
}

::view-transition-old(root),
::view-transition-new(root) {
  animation-duration: 0.3s;
}
```

---

### Phase 10: Scroll-Driven Animations

**Status**: ❌ Not implemented  
**Browser Support**: ⚠️ Chrome 115+  
**Impact**: Medium - Modern scroll effects

**Implementation Targets**:
- [ ] Parallax effects
- [ ] Progress indicators
- [ ] Fade-in on scroll
- [ ] Sticky headers

**Example**:
```css
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fade-in linear;
  animation-timeline: scroll();
  animation-range: entry 0% entry 50%;
}
```

---

### Phase 11: Anchor Positioning

**Status**: ❌ Not implemented  
**Browser Support**: ⚠️ Chrome 125+  
**Impact**: Medium - Better tooltips/popovers

**Implementation Targets**:
- [ ] Tooltips
- [ ] Dropdowns
- [ ] Popovers
- [ ] Context menus

**Example**:
```css
.tooltip {
  position-anchor: --anchor;
  position: absolute;
  top: anchor(bottom);
  left: anchor(center);
}
```

---

### Phase 12: Content Visibility

**Status**: ❌ Not implemented  
**Browser Support**: ✅ All modern browsers  
**Impact**: High - Performance optimization

**Implementation Targets**:
- [ ] Long blog post lists
- [ ] Documentation navigation
- [ ] Search results
- [ ] Table rows

**Example**:
```css
.blog-post-list > * {
  content-visibility: auto;
  contain-intrinsic-size: 200px;
}
```

---

### Phase 13: CSS Nesting

**Status**: ❌ Not implemented  
**Browser Support**: ✅ All modern browsers (2024+)  
**Impact**: Medium - Cleaner code

**Implementation Targets**:
- [ ] All component files
- [ ] Reduce selector repetition
- [ ] Better organization

**Example**:
```css
.card {
  padding: 1rem;
  
  &:hover {
    transform: translateY(-4px);
  }
  
  .card-title {
    font-size: 1.25rem;
    
    a {
      color: inherit;
    }
  }
}
```

---

### Phase 14: @scope

**Status**: ❌ Not implemented  
**Browser Support**: ⚠️ Chrome 118+  
**Impact**: Medium - Better style scoping

**Implementation Targets**:
- [ ] Component isolation
- [ ] Theme variants
- [ ] Reduce specificity conflicts

**Example**:
```css
@scope (.card) {
  .title {
    /* Only applies to .title inside .card */
  }
}
```

---

### Phase 15: @starting-style

**Status**: ❌ Not implemented  
**Browser Support**: ⚠️ Chrome 117+  
**Impact**: Low - Better initial animations

**Implementation Targets**:
- [ ] Modal open animations
- [ ] Drawer animations
- [ ] List item animations

**Example**:
```css
.modal {
  opacity: 1;
  transform: scale(1);
  
  @starting-style {
    opacity: 0;
    transform: scale(0.95);
  }
  
  transition: opacity 0.3s, transform 0.3s;
}
```

---

## 📊 Implementation Priority

| Feature | Browser Support | Impact | Effort | Priority |
|---------|----------------|--------|--------|----------|
| Container Queries | ✅ Universal | High | Medium | 🔴 P0 |
| Aspect Ratio | ✅ Universal | High | Low | 🔴 P0 |
| :has() Selector | ✅ Universal | High | Low | 🔴 P0 |
| Content Visibility | ✅ Universal | High | Low | 🔴 P0 |
| CSS Nesting | ✅ Universal | Medium | Medium | 🟡 P1 |
| Grid Template Areas | ✅ Universal | Medium | Low | 🟡 P1 |
| Logical Properties | ✅ Universal | Medium | High | 🟡 P1 |
| CSS Layers | ✅ Universal | Medium | High | 🟡 P1 |
| Subgrid | ⚠️ Modern | Medium | Medium | 🟢 P2 |
| View Transitions | ⚠️ Chrome/Firefox | High | Medium | 🟢 P2 |
| Scroll Animations | ⚠️ Chrome | Medium | Medium | 🟢 P2 |
| Color Functions | ✅ Universal | Low | Low | 🟢 P2 |
| @scope | ⚠️ Chrome | Medium | Low | 🟢 P3 |
| @starting-style | ⚠️ Chrome | Low | Low | 🟢 P3 |
| Anchor Positioning | ⚠️ Chrome | Medium | Medium | 🟢 P3 |

---

## 🚀 Implementation Strategy

### Phase 1: Universal Support (P0)
**Target**: Features supported in all modern browsers
1. Container Queries
2. Aspect Ratio (expand usage)
3. :has() Selector (expand usage)
4. Content Visibility

**Timeline**: Week 1-2

### Phase 2: High Value (P1)
**Target**: Features with high impact
1. CSS Nesting
2. Grid Template Areas
3. Logical Properties (gradual migration)
4. CSS Layers (organize existing)

**Timeline**: Week 3-4

### Phase 3: Modern Features (P2)
**Target**: Features with good browser support
1. Subgrid
2. View Transitions API
3. Scroll-Driven Animations
4. Color Functions

**Timeline**: Week 5-6

### Phase 4: Experimental (P3)
**Target**: Cutting-edge features
1. @scope
2. @starting-style
3. Anchor Positioning

**Timeline**: Week 7+ (with feature detection)

---

## 📋 Implementation Checklist

### Container Queries
- [ ] Card grids
- [ ] Navigation menus
- [ ] Sidebar components
- [ ] Code blocks
- [ ] Tables
- [ ] Form layouts

### Aspect Ratio
- [ ] All card images
- [ ] Hero images
- [ ] Blog post images
- [ ] Code block containers
- [ ] Video embeds

### :has() Selector
- [ ] Cards with/without images
- [ ] Forms with errors
- [ ] Navigation with active items
- [ ] Tables with headers
- [ ] Lists with icons

### Content Visibility
- [ ] Blog post lists
- [ ] Documentation navigation
- [ ] Search results
- [ ] Table rows

### CSS Nesting
- [ ] Refactor all component files
- [ ] Reduce selector repetition
- [ ] Better organization

### Grid Template Areas
- [ ] Docs layout
- [ ] Header layout
- [ ] Footer layout
- [ ] Card layouts

---

## 🎯 Success Metrics

**Measure Progress**:
- Container queries: Target 10+ implementations
- Aspect ratio: Target 100% of images
- :has() selector: Target 20+ use cases
- Content visibility: Target all long lists
- CSS nesting: Target 100% of components
- Grid template areas: Target all complex layouts

---

## 🔍 Feature Detection Strategy

For features with limited browser support:

```css
/* Feature detection */
@supports (container-type: inline-size) {
  /* Container queries */
}

@supports (subgrid) {
  /* Subgrid */
}

@supports (view-transition-name: root) {
  /* View Transitions */
}

/* Fallbacks */
.card-grid {
  /* Fallback grid */
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

@supports (container-type: inline-size) {
  .card-container {
    container-type: inline-size;
  }
  
  @container (min-width: 400px) {
    .card-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}
```

---

## 📚 Resources

- [MDN CSS Reference](https://developer.mozilla.org/en-US/docs/Web/CSS)
- [Can I Use](https://caniuse.com/)
- [CSS-Tricks Modern CSS](https://css-tricks.com/)
- [Web.dev Modern CSS](https://web.dev/learn/css/)

---

## 🎓 Learning & Documentation

As we implement each feature:
1. Document usage patterns
2. Create examples
3. Add to component library
4. Update style guide
5. Share learnings

---

**Next Steps**: Start with Phase 1 (P0) features - Container Queries, Aspect Ratio, :has(), and Content Visibility.

