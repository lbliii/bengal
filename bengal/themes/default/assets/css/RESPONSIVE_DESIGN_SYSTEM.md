# Responsive Design System

**Last Updated:** October 18, 2025  
**Purpose:** Standardized responsive breakpoints and component behavior patterns

---

## Overview

Bengal uses a **mobile-first, semantic breakpoint system** with standardized component behavior patterns to ensure consistent responsive design across all components.

## Breakpoint Values

### Standard Breakpoints

```css
/* CSS Variables (for JS reference only - cannot be used in @media) */
--breakpoint-xxs: 400px;  /* Very small phones; use 399px in CSS media */
--breakpoint-sm: 640px;   /* Landscape phones, portrait tablets */
--breakpoint-md: 768px;   /* Tablets */
--breakpoint-lg: 1024px;  /* Laptops, small desktops */
--breakpoint-xl: 1280px;  /* Large desktops */
--breakpoint-2xl: 1536px; /* Extra large displays */
```

### Device Mappings

| Breakpoint | Width | Devices | Use Case |
|------------|-------|---------|----------|
| **xs** (default) | 0-639px | Phones (portrait) | Mobile-first base styles |
| **sm** | 640px+ | Phones (landscape), small tablets | Expanded mobile layouts |
| **md** | 768px+ | Tablets, small laptops | Tablet optimizations |
| **lg** | 1024px+ | Laptops, desktops | Desktop layouts |
| **xl** | 1280px+ | Large desktops | Wide screen enhancements |
| **2xl** | 1536px+ | Ultra-wide displays | Maximum content width |

### Additional Utility Breakpoints

For fine-grained control when needed:

```css
--breakpoint-xs: 480px;   /* Small phones (landscape) */
--breakpoint-3xl: 1920px; /* 4K displays */
```

---

## Mobile-First Philosophy

**Always start with mobile styles, then progressively enhance:**

```css
/* ✅ GOOD - Mobile first */
.component {
  padding: 0.5rem;        /* Mobile (default) */
  font-size: 0.875rem;
}

@media (min-width: 640px) {
  .component {
    padding: 1rem;        /* Tablet+ */
  }
}

@media (min-width: 1024px) {
  .component {
    padding: 1.5rem;      /* Desktop+ */
    font-size: 1rem;
  }
}

/* ❌ BAD - Desktop first */
.component {
  padding: 1.5rem;
  font-size: 1rem;
}

@media (max-width: 1024px) {
  .component { padding: 1rem; }
}
```

**Why mobile-first?**
- Smaller CSS footprint on mobile (no overrides)
- Forces you to think about content hierarchy
- Easier to progressively enhance than degrade

---

## Responsive Behavior Patterns

### 1. Stack → Side-by-Side

**Use case:** Layout that stacks on mobile, becomes horizontal on larger screens

```css
.layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (min-width: 768px) {
  .layout {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}
```

**Examples:** Action bars, navigation, card grids

### 2. Compress → Expand

**Use case:** Content that compresses/truncates on mobile, expands on desktop

```css
.content {
  /* Mobile: Aggressive compression */
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.875rem;
  padding: 0.5rem;
}

@media (min-width: 768px) {
  .content {
    max-width: 250px;
    font-size: 1rem;
    padding: 1rem;
  }
}

@media (min-width: 1024px) {
  .content {
    max-width: none; /* No truncation */
  }
}
```

**Examples:** Breadcrumbs, table cells, navigation labels

### 3. Inline → Wrap

**Use case:** Keep items inline as long as possible, wrap when necessary

```css
.container {
  display: flex;
  flex-wrap: nowrap; /* Stay inline on mobile */
  gap: 0.5rem;
  overflow-x: auto; /* Scroll if needed */
}

@media (min-width: 640px) {
  .container {
    flex-wrap: wrap; /* Allow wrapping on tablet+ */
    overflow-x: visible;
    gap: 1rem;
  }
}
```

**Examples:** Tag lists, filter chips, action buttons

### 4. Hide → Show

**Use case:** Progressive disclosure - hide non-critical content on small screens

```css
.secondary-content {
  display: none; /* Hidden on mobile */
}

@media (min-width: 768px) {
  .secondary-content {
    display: block;
  }
}

/* For items that should ONLY show on mobile */
.mobile-only {
  display: block;
}

@media (min-width: 768px) {
  .mobile-only {
    display: none;
  }
}
```

**Use sparingly:** Hiding content should be a last resort

### 5. Reduce → Elaborate

**Use case:** Simplify interactions on mobile, add enhancements on desktop

```css
.interactive {
  /* Mobile: Essential interactions only */
  cursor: pointer;
  transition: background 0.15s ease;
}

.interactive:active {
  background: var(--color-bg-tertiary);
}

@media (min-width: 768px) {
  .interactive:hover {
    background: var(--color-bg-secondary);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
}
```

**Examples:** Hover effects, tooltips, animations

---

## Component Responsive Guidelines

### Navigation

```css
/* Stack vertically on mobile, horizontal on tablet+ */
@media (max-width: 767px) { /* Note: max-width for mobile-specific */ }
@media (min-width: 768px) { /* Desktop navigation */ }
```

### Content Grids

```css
.grid {
  display: grid;
  grid-template-columns: 1fr; /* Mobile: 1 column */
  gap: 1rem;
}

@media (min-width: 640px) {
  .grid { grid-template-columns: repeat(2, 1fr); } /* Tablet: 2 cols */
}

@media (min-width: 1024px) {
  .grid { grid-template-columns: repeat(3, 1fr); } /* Desktop: 3 cols */
}

@media (min-width: 1280px) {
  .grid { grid-template-columns: repeat(4, 1fr); } /* Wide: 4 cols */
}
```

### Action Bars / Toolbars

**Three-tier responsive strategy:**

```css
/* Mobile (640px and below): Compress aggressively, stay inline */
@media (max-width: 640px) {
  .action-bar {
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
  }

  .action-bar-nav {
    max-width: calc(100% - 80px); /* Reserve space for actions */
  }
}

/* Very small mobile (480px and below): Stack if absolutely necessary */
@media (max-width: 480px) {
  .action-bar {
    flex-wrap: wrap;
  }

  .action-bar-nav {
    flex: 1 1 100%;
  }
}
```

### Dropdowns & Modals

```css
.dropdown {
  position: absolute;
  right: 0;
  min-width: 240px;
}

/* Center on mobile for better UX */
@media (max-width: 640px) {
  .dropdown {
    left: 50%;
    right: auto;
    transform: translateX(-50%);
    min-width: 280px;
    max-width: 90vw;
  }
}
```

### Tables

```css
/* Card layout on mobile */
@media (max-width: 767px) {
  .table-responsive {
    display: block;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch; /* Smooth scroll on iOS */
  }
}
```

---

## Breakpoint Decision Tree

**When choosing a breakpoint, ask:**

1. **Does content need to change?**
   - Yes → Use closest standard breakpoint
   - No → Don't add media query

2. **Which breakpoint?**
   - **640px** (sm) - First major layout shift from phone → tablet
   - **768px** (md) - Tablet optimization, common nav breakpoint
   - **1024px** (lg) - Desktop layouts, multi-column grids
   - **480px** (xs) - Only for very small phone edge cases

3. **Mobile-first or desktop-first?**
   - Default: Mobile-first (`min-width`)
   - Exception: Mobile-specific overrides (`max-width`)

---

## Sass Mixins (Optional)

If using Sass preprocessor, define reusable mixins:

```scss
// Mobile-first breakpoints
@mixin sm { @media (min-width: 640px) { @content; } }
@mixin md { @media (min-width: 768px) { @content; } }
@mixin lg { @media (min-width: 1024px) { @content; } }
@mixin xl { @media (min-width: 1280px) { @content; } }

// Desktop-first (rare)
@mixin mobile-only { @media (max-width: 639px) { @content; } }
@mixin tablet-down { @media (max-width: 767px) { @content; } }

// Usage
.component {
  padding: 0.5rem;

  @include md {
    padding: 1rem;
  }

  @include lg {
    padding: 1.5rem;
  }
}
```

---

## Testing Checklist

When building responsive components, test at:

- [ ] **320px** - iPhone SE (smallest common viewport)
- [ ] **375px** - iPhone 12/13 (most common)
- [ ] **390px** - iPhone 14 Pro
- [ ] **768px** - iPad (portrait)
- [ ] **1024px** - iPad (landscape), small laptop
- [ ] **1280px** - Desktop
- [ ] **1920px** - Large desktop

**Browser DevTools:**
- Chrome: Device toolbar (Cmd+Shift+M)
- Firefox: Responsive Design Mode (Cmd+Option+M)
- Safari: Enter Responsive Design Mode

---

## Common Responsive Patterns by Component Type

| Component | Mobile | Tablet (768px+) | Desktop (1024px+) |
|-----------|--------|-----------------|-------------------|
| **Navigation** | Hamburger menu | Collapsed | Full horizontal |
| **Action Bar** | Compressed inline → Stack (480px) | Full inline | Full inline |
| **Cards Grid** | 1 column | 2 columns | 3-4 columns |
| **Sidebar** | Hidden/overlay | Side-by-side (narrow) | Side-by-side (wide) |
| **Table** | Horizontal scroll | Responsive columns | Full table |
| **Search** | Full width | Compact inline | Inline with filters |
| **Breadcrumbs** | Truncate heavily | Show more | Show all |

---

## Anti-Patterns

### ❌ Don't: Arbitrary breakpoints

```css
@media (max-width: 850px) { } /* Why 850? */
@media (max-width: 767px) { } /* Off by one from standard */
```

### ❌ Don't: Too many breakpoints

```css
/* Overly complex */
@media (max-width: 1200px) { }
@media (max-width: 992px) { }
@media (max-width: 768px) { }
@media (max-width: 576px) { }
@media (max-width: 480px) { }
@media (max-width: 320px) { }
```

Keep it simple: usually 2-3 breakpoints per component is enough.

### ❌ Don't: Hiding critical content

```css
/* Bad: Essential feature hidden on mobile */
@media (max-width: 767px) {
  .search-box { display: none; }
}
```

### ❌ Don't: Desktop-first for new components

```css
/* Bad: Forces mobile devices to override everything */
.component {
  padding: 3rem;
  font-size: 1.5rem;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}
```

---

## Resources

- [MDN: Using media queries](https://developer.mozilla.org/en-US/docs/Web/CSS/Media_Queries/Using_media_queries)
- [Web.dev: Responsive design patterns](https://web.dev/patterns/layout/)
- [CSS-Tricks: Complete Guide to CSS Media Queries](https://css-tricks.com/a-complete-guide-to-css-media-queries/)

---

## Quick Reference

### Standard Media Query Templates

```css
/* ===== Mobile-first (preferred) ===== */

/* Base: Mobile (0-639px) */
.component { }

/* Tablet up (640px+) */
@media (min-width: 640px) { }

/* Desktop up (1024px+) */
@media (min-width: 1024px) { }

/* ===== Desktop-first (rare) ===== */

/* Mobile-specific overrides */
@media (max-width: 639px) { }

/* Tablet and below */
@media (max-width: 767px) { }

/* Very small devices only */
@media (max-width: 480px) { }
```

**Note:** Use `max-width: 639px` (not 640px) and `max-width: 767px` (not 768px) to avoid overlap with min-width queries.

---

## Implementation Notes

### Why CSS Variables Can't Be Used in Media Queries

```css
/* ❌ This doesn't work */
@media (min-width: var(--breakpoint-md)) {
  /* ... */
}
```

CSS custom properties (variables) **cannot be used in media queries** because:
- Media queries are evaluated before CSS is parsed
- Variables are runtime values, media queries are static
- This is a CSS specification limitation

**Solution:** Use standard hardcoded breakpoint values consistently across all components, and keep CSS variables as documentation/reference for JavaScript.

### JavaScript Integration

Access breakpoints in JavaScript:

```javascript
const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  xxl: 1536
};

// Or read from CSS
const style = getComputedStyle(document.documentElement);
const breakpointMd = parseInt(style.getPropertyValue('--breakpoint-md'));

// Check current viewport
const isMobile = window.matchMedia('(max-width: 767px)').matches;
```

---

**Last Updated:** October 18, 2025  
**Maintainer:** Bengal Theme Team
