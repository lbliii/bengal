# Component Update Plan - Fern/Mintlify Enhancements

**Status**: Ready for implementation  
**Priority**: High → Medium → Low

---

## ✅ Already Updated Components

1. **Mobile Navigation** (`layouts/header.css`)
   - ✅ Smooth drawer animation with GPU acceleration
   - ✅ Touch-action controls
   - ✅ Will-change optimizations

2. **Dropdowns** (`components/dropdowns.css`)
   - ✅ GPU-accelerated slideDown animation
   - ✅ Will-change optimizations

3. **Lightbox** (`components/interactive.css`)
   - ✅ Smooth fade-scale animation
   - ✅ Backdrop blur
   - ✅ Will-change optimizations

4. **Code Blocks** (`components/code.css`)
   - ✅ Backdrop blur on copy buttons
   - ✅ Better mobile scrolling
   - ✅ Break out of container padding

5. **Buttons** (`components/buttons.css`)
   - ✅ Touch-action controls
   - ✅ Better touch targets

6. **Action Bar** (`components/action-bar.css`)
   - ✅ Touch-action on share trigger
   - ✅ Mobile optimizations

7. **Cards** (`components/cards.css`)
   - ✅ Smooth transitions (cubic-bezier)
   - ✅ Disable transforms on mobile
   - ⚠️ Still uses `translateY()` instead of `translate3d()`

---

## 🔄 Components Needing Updates

### HIGH PRIORITY

#### 1. **Cards Component** (`components/cards.css`)
**Current Issue**: Uses `translateY()` instead of `translate3d()`  
**Enhancement**: Replace with `.smooth-raise` class or update to `translate3d()`

**Current**:
```css
.card:hover {
  transform: translateY(calc(-1 * var(--motion-distance-2)));
}
```

**Should Be**:
```css
.card:hover {
  transform: translate3d(0, calc(-1 * var(--motion-distance-2)), 0);
}
```

**Or use**:
```html
<div class="card smooth-raise">
```

---

#### 2. **Search Modal** (`components/search.css`)
**Current**: Basic search input, no modal  
**Enhancement**: If search modal exists, add smooth animations

**Should Use**:
- `.smooth-overlay` for backdrop
- `.smooth-fade-scale` for modal content
- Better touch targets for mobile

**Action**: Check if search modal exists, add smooth animations if present

---

#### 3. **Tabs Component** (`components/tabs.css`)
**Current**: Basic transitions  
**Enhancement**: Add smooth transitions with GPU acceleration

**Current**:
```css
.tab-nav a {
  transition: all var(--transition-fast) var(--ease-out);
}
```

**Should Add**:
- GPU-accelerated transitions
- Smooth tab content switching
- Better touch targets on mobile

---

#### 4. **Pagination** (`components/pagination.css`)
**Current**: Basic hover with `translateY()`  
**Enhancement**: Use `translate3d()` and better touch targets

**Current**:
```css
.pagination a:hover {
  transform: translateY(-1px);
}
```

**Should Be**:
```css
.pagination a {
  touch-action: manipulation;
  transition: all var(--transition-base) cubic-bezier(0.4, 0, 0.2, 1);
}

.pagination a:hover {
  transform: translate3d(0, -1px, 0);
}
```

---

### MEDIUM PRIORITY

#### 5. **Docs Navigation** (`components/docs-nav.css`)
**Current**: Basic expand/collapse  
**Enhancement**: Add smooth slide animations for expand/collapse

**Should Add**:
- Smooth slide animations for nav groups
- GPU-accelerated transforms
- Better touch targets for mobile

---

#### 6. **Table of Contents** (`components/toc.css`)
**Current**: Basic sticky sidebar  
**Enhancement**: Add smooth animations for mobile drawer version

**Should Add**:
- If mobile drawer exists, use `.smooth-drawer`
- Smooth scroll animations
- Better touch interactions

---

#### 7. **Badges** (`components/badges.css`)
**Current**: Basic styling  
**Enhancement**: Add smooth hover transitions

**Should Add**:
- Smooth transitions
- GPU-accelerated hover effects

---

#### 8. **Tags** (`components/tags.css`)
**Current**: Basic styling  
**Enhancement**: Add smooth hover transitions

**Should Add**:
- Smooth transitions
- Better touch targets

---

#### 9. **Admonitions** (`components/admonitions.css`)
**Current**: Basic expand/collapse (if accordion-style)  
**Enhancement**: Add smooth slide animations

**Should Add**:
- Smooth expand/collapse animations
- GPU-accelerated transforms

---

### LOW PRIORITY (Polish)

#### 10. **Share Component** (`components/share.css`)
**Enhancement**: Add smooth transitions, better touch targets

#### 11. **Navigation** (`components/navigation.css`)
**Enhancement**: Add smooth transitions, GPU acceleration

#### 12. **Hero** (`components/hero.css`)
**Enhancement**: Add smooth fade-in animations

---

## 📋 Implementation Checklist

### Phase 1: High Priority (Core UX)
- [ ] Update cards to use `translate3d()` or `.smooth-raise`
- [ ] Update pagination to use `translate3d()` and touch-action
- [ ] Update tabs to use smooth transitions
- [ ] Add smooth animations to search modal (if exists)

### Phase 2: Medium Priority (Content Components)
- [ ] Add smooth animations to docs-nav expand/collapse
- [ ] Add smooth animations to TOC mobile drawer (if exists)
- [ ] Add smooth transitions to badges
- [ ] Add smooth transitions to tags
- [ ] Add smooth animations to admonitions (if accordion-style)

### Phase 3: Low Priority (Polish)
- [ ] Add smooth transitions to share component
- [ ] Add smooth transitions to navigation
- [ ] Add smooth fade-in to hero

---

## 🎯 Quick Wins (Easy Updates)

### 1. Replace translateY with translate3d
**Files**: `cards.css`, `pagination.css`, any component with hover transforms

**Pattern**:
```css
/* Before */
transform: translateY(-2px);

/* After */
transform: translate3d(0, -2px, 0);
```

### 2. Add Touch-Action to Interactive Elements
**Files**: `pagination.css`, `tabs.css`, `badges.css`, `tags.css`

**Pattern**:
```css
.interactive-element {
  touch-action: manipulation;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
```

### 3. Use Smooth Transition Token
**Files**: All components with transitions

**Pattern**:
```css
/* Before */
transition: all var(--transition-fast);

/* After (for smooth animations) */
transition: transform var(--transition-smooth), opacity var(--transition-smooth);
```

---

## 📊 Summary

**Total Components**: 28  
**Already Updated**: 7 ✅  
**Need Updates**: 12 🔄  
**Quick Wins Available**: 8+ ⚡

**Estimated Impact**:
- High Priority: 4 components (core UX)
- Medium Priority: 5 components (content)
- Low Priority: 3 components (polish)

