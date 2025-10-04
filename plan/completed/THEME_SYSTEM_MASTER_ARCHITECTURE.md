# Bengal Theme System - Master Architecture

**Date:** October 3, 2025  
**Status:** Foundation Document  
**Goal:** Rock-solid, long-term architecture for Bengal's theme system

---

## Executive Summary

This document establishes the **master architecture** for Bengal's theme system, ensuring scalability, maintainability, and flexibility for years to come. It addresses:

1. **Design System Architecture** - Token-based design with clear hierarchies
2. **Component Architecture** - Modular, testable, documented components
3. **CSS Architecture** - Scalable methodology (CUBE CSS + Design Tokens)
4. **JavaScript Architecture** - Progressive enhancement with clear patterns
5. **Theme Variants** - Easy customization without forking
6. **Versioning & Upgrades** - Backward compatibility strategy
7. **Testing & Quality** - Theme testing framework
8. **Documentation** - Self-documenting patterns

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Design Token System](#design-token-system)
3. [CSS Architecture (CUBE CSS)](#css-architecture-cube-css)
4. [Component Architecture](#component-architecture)
5. [JavaScript Architecture](#javascript-architecture)
6. [Theme Structure Standards](#theme-structure-standards)
7. [Override & Customization Strategy](#override--customization-strategy)
8. [Versioning & Breaking Changes](#versioning--breaking-changes)
9. [Testing Framework](#testing-framework)
10. [Documentation Standards](#documentation-standards)
11. [Migration & Upgrade Path](#migration--upgrade-path)
12. [Validation Checklist](#validation-checklist)

---

## Core Principles

### 1. Progressive Enhancement

**Philosophy:** Start with semantic HTML, enhance with CSS, add JavaScript only when necessary.

```
Layer 1: Semantic HTML     → Works with CSS/JS disabled
Layer 2: CSS Enhancement   → Visual polish, layout
Layer 3: JS Enhancement    → Interactions, dynamic features
```

**Why:** Ensures accessibility, performance, and resilience.

### 2. Design Tokens First

**Philosophy:** All design decisions flow from a token system.

```
Tokens → Components → Templates → Pages
```

**Why:** Enables consistent theming, easy customization, and systematic design.

### 3. Composition Over Inheritance

**Philosophy:** Build complex components from simple, reusable pieces.

```html
<!-- Bad: Monolithic -->
<div class="article-card-with-image-and-meta-and-tags"></div>

<!-- Good: Composable -->
<div class="card">
  <img class="card-image" />
  <div class="card-body">
    <h3 class="card-title"></h3>
    <div class="card-meta"></div>
    <div class="card-tags"></div>
  </div>
</div>
```

**Why:** Flexibility, reusability, easier maintenance.

### 4. Convention Over Configuration

**Philosophy:** Sensible defaults with opt-in complexity.

```
Default behavior → Works out of the box
Advanced behavior → Explicit opt-in via frontmatter/config
```

**Why:** Lower barrier to entry, predictable behavior.

### 5. Zero Breaking Changes to Core API

**Philosophy:** Template functions, context variables, and core templates maintain backward compatibility.

**Strategy:**
- Deprecate with warnings (not removal)
- Add new APIs alongside old ones
- Document migration paths
- Maintain old behavior for 2+ major versions

**Why:** Users can upgrade Bengal without breaking their sites.

### 6. Performance Budget

**Hard Limits:**
- CSS: < 50KB (gzipped)
- JavaScript: < 20KB (gzipped)
- First Contentful Paint: < 1s
- Time to Interactive: < 2s
- Cumulative Layout Shift: < 0.1

**Why:** Fast sites = better UX and SEO.

---

## Design Token System

### Architecture

Design tokens are the **single source of truth** for all design decisions.

```
Foundation Tokens → Semantic Tokens → Component Tokens
```

### 1. Foundation Tokens (Primitives)

**Purpose:** Raw values (colors, sizes, fonts) - never used directly in components.

```css
/* assets/css/tokens/foundation.css */
:root {
  /* Color Primitives */
  --color-blue-50: #e3f2fd;
  --color-blue-100: #bbdefb;
  --color-blue-200: #90caf9;
  --color-blue-300: #64b5f6;
  --color-blue-400: #42a5f5;
  --color-blue-500: #2196f3;  /* Base blue */
  --color-blue-600: #1e88e5;
  --color-blue-700: #1976d2;
  --color-blue-800: #1565c0;
  --color-blue-900: #0d47a1;
  
  /* Gray Primitives */
  --color-gray-50: #fafafa;
  --color-gray-100: #f5f5f5;
  --color-gray-200: #eeeeee;
  --color-gray-300: #e0e0e0;
  --color-gray-400: #bdbdbd;
  --color-gray-500: #9e9e9e;
  --color-gray-600: #757575;
  --color-gray-700: #616161;
  --color-gray-800: #424242;
  --color-gray-900: #212121;
  
  /* Size Primitives (spacing scale) */
  --size-1: 0.25rem;   /* 4px */
  --size-2: 0.5rem;    /* 8px */
  --size-3: 0.75rem;   /* 12px */
  --size-4: 1rem;      /* 16px */
  --size-5: 1.25rem;   /* 20px */
  --size-6: 1.5rem;    /* 24px */
  --size-8: 2rem;      /* 32px */
  --size-10: 2.5rem;   /* 40px */
  --size-12: 3rem;     /* 48px */
  --size-16: 4rem;     /* 64px */
  --size-20: 5rem;     /* 80px */
  --size-24: 6rem;     /* 96px */
  
  /* Font Size Primitives */
  --font-size-12: 0.75rem;
  --font-size-14: 0.875rem;
  --font-size-16: 1rem;
  --font-size-18: 1.125rem;
  --font-size-20: 1.25rem;
  --font-size-24: 1.5rem;
  --font-size-30: 1.875rem;
  --font-size-36: 2.25rem;
  --font-size-48: 3rem;
  
  /* Font Weight Primitives */
  --font-weight-light: 300;
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  
  /* Line Height Primitives */
  --line-height-tight: 1.25;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;
  
  /* Border Radius Primitives */
  --radius-1: 0.125rem;  /* 2px */
  --radius-2: 0.25rem;   /* 4px */
  --radius-3: 0.5rem;    /* 8px */
  --radius-4: 0.75rem;   /* 12px */
  --radius-5: 1rem;      /* 16px */
  --radius-full: 9999px;
  
  /* Shadow Primitives */
  --shadow-1: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-2: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  --shadow-3: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-4: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-5: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  
  /* Transition Primitives */
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 350ms;
  
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
}
```

### 2. Semantic Tokens (Purpose-Based)

**Purpose:** Map foundation tokens to semantic purposes. Components use these.

```css
/* assets/css/tokens/semantic.css */
:root {
  /* Semantic Colors */
  --color-primary: var(--color-blue-500);
  --color-primary-hover: var(--color-blue-600);
  --color-primary-active: var(--color-blue-700);
  
  --color-text-primary: var(--color-gray-900);
  --color-text-secondary: var(--color-gray-600);
  --color-text-muted: var(--color-gray-500);
  --color-text-inverse: white;
  
  --color-bg-primary: white;
  --color-bg-secondary: var(--color-gray-50);
  --color-bg-tertiary: var(--color-gray-100);
  --color-bg-hover: var(--color-gray-100);
  
  --color-border: var(--color-gray-300);
  --color-border-light: var(--color-gray-200);
  --color-border-strong: var(--color-gray-400);
  
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: var(--color-blue-500);
  
  /* Semantic Spacing */
  --space-component-gap: var(--size-4);
  --space-section-gap: var(--size-12);
  --space-content-padding: var(--size-6);
  
  /* Semantic Typography */
  --text-heading-1: var(--font-size-48);
  --text-heading-2: var(--font-size-36);
  --text-heading-3: var(--font-size-30);
  --text-heading-4: var(--font-size-24);
  --text-body: var(--font-size-16);
  --text-small: var(--font-size-14);
  --text-tiny: var(--font-size-12);
  
  /* Semantic Elevation */
  --elevation-none: none;
  --elevation-card: var(--shadow-2);
  --elevation-dropdown: var(--shadow-3);
  --elevation-modal: var(--shadow-5);
  
  /* Semantic Transitions */
  --transition-quick: var(--duration-fast) var(--ease-out);
  --transition-smooth: var(--duration-normal) var(--ease-in-out);
  --transition-slow: var(--duration-slow) var(--ease-in-out);
}

/* Dark Mode Overrides */
[data-theme="dark"] {
  --color-text-primary: var(--color-gray-50);
  --color-text-secondary: var(--color-gray-400);
  --color-text-muted: var(--color-gray-500);
  --color-text-inverse: var(--color-gray-900);
  
  --color-bg-primary: #1a1a1a;
  --color-bg-secondary: #2d2d2d;
  --color-bg-tertiary: #3a3a3a;
  --color-bg-hover: #404040;
  
  --color-border: #404040;
  --color-border-light: #3a3a3a;
  --color-border-strong: #6c757d;
  
  /* Adjust shadows for dark mode */
  --shadow-1: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-2: 0 1px 3px 0 rgba(0, 0, 0, 0.4);
  --shadow-3: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
  --shadow-4: 0 10px 15px -3px rgba(0, 0, 0, 0.6);
  --shadow-5: 0 20px 25px -5px rgba(0, 0, 0, 0.7);
}
```

### 3. Component Tokens (Scoped)

**Purpose:** Component-specific values that can be customized per-component.

```css
/* assets/css/components/button.css */
.btn {
  /* Component tokens (customizable) */
  --btn-bg: var(--color-primary);
  --btn-color: var(--color-text-inverse);
  --btn-padding-x: var(--size-4);
  --btn-padding-y: var(--size-2);
  --btn-radius: var(--radius-2);
  --btn-shadow: var(--elevation-card);
  --btn-transition: var(--transition-quick);
  
  /* Apply tokens */
  background: var(--btn-bg);
  color: var(--btn-color);
  padding: var(--btn-padding-y) var(--btn-padding-x);
  border-radius: var(--btn-radius);
  box-shadow: var(--btn-shadow);
  transition: all var(--btn-transition);
}

/* Variants override tokens */
.btn-secondary {
  --btn-bg: var(--color-bg-secondary);
  --btn-color: var(--color-text-primary);
}

.btn-large {
  --btn-padding-x: var(--size-6);
  --btn-padding-y: var(--size-3);
}
```

**Benefits:**
1. **Consistency:** All values flow from system
2. **Customization:** Override at any level
3. **Maintainability:** Change once, update everywhere
4. **Documentation:** Self-documenting via naming

---

## CSS Architecture (CUBE CSS)

### Methodology: CUBE CSS

**CUBE** = Composition, Utility, Block, Exception

This is a **pragmatic, scalable** CSS methodology that fits Bengal's needs perfectly.

#### 1. **C**omposition (Layout)

**Purpose:** Structural relationships between elements.

```css
/* assets/css/composition/layouts.css */

/* Three-column docs layout */
.docs-layout {
  display: grid;
  grid-template-columns: [sidebar] 280px [content] 1fr [toc] 240px;
  gap: var(--space-section-gap);
  max-width: 1600px;
  margin: 0 auto;
  padding: var(--space-content-padding);
}

/* Responsive variants */
@media (max-width: 1280px) {
  .docs-layout {
    grid-template-columns: [sidebar] 260px [content] 1fr;
  }
}

/* Stack layout (flow) */
.stack {
  display: flex;
  flex-direction: column;
  gap: var(--stack-gap, var(--space-component-gap));
}

/* Cluster layout (horizontal flow) */
.cluster {
  display: flex;
  flex-wrap: wrap;
  gap: var(--cluster-gap, var(--space-component-gap));
  align-items: var(--cluster-align, center);
}

/* Grid layout */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--grid-min, 280px), 1fr));
  gap: var(--grid-gap, var(--space-component-gap));
}

/* Center layout */
.center {
  box-sizing: content-box;
  max-width: var(--center-max-width, 1200px);
  margin-inline: auto;
  padding-inline: var(--center-padding, var(--space-content-padding));
}
```

#### 2. **U**tility (Single Purpose)

**Purpose:** Single-responsibility classes for common patterns.

```css
/* assets/css/utilities/utilities.css */

/* Display */
.hidden { display: none; }
.block { display: block; }
.flex { display: flex; }
.grid { display: grid; }

/* Visibility (accessible hiding) */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Text alignment */
.text-left { text-align: left; }
.text-center { text-align: center; }
.text-right { text-align: right; }

/* Font weights */
.font-normal { font-weight: var(--font-weight-normal); }
.font-medium { font-weight: var(--font-weight-medium); }
.font-bold { font-weight: var(--font-weight-bold); }

/* Truncate */
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Spacing (use sparingly, prefer composition) */
.mt-0 { margin-top: 0; }
.mt-1 { margin-top: var(--size-1); }
.mt-2 { margin-top: var(--size-2); }
/* etc. */
```

**Rule:** Utilities are **escape hatches**, not the primary styling method.

#### 3. **B**lock (Components)

**Purpose:** Reusable UI components with clear boundaries.

```css
/* assets/css/components/card.css */

.card {
  /* Component structure */
  display: flex;
  flex-direction: column;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-3);
  box-shadow: var(--elevation-card);
  overflow: hidden;
  transition: box-shadow var(--transition-quick);
}

.card:hover {
  box-shadow: var(--elevation-dropdown);
}

/* Component parts (BEM-style) */
.card__image {
  width: 100%;
  height: auto;
  object-fit: cover;
}

.card__body {
  padding: var(--size-6);
  flex: 1;
}

.card__title {
  margin: 0 0 var(--size-2) 0;
  font-size: var(--text-heading-4);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.card__description {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

.card__footer {
  padding: var(--size-4) var(--size-6);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
}

/* Variants (modifiers) */
.card--interactive {
  cursor: pointer;
  transition: transform var(--transition-quick);
}

.card--interactive:hover {
  transform: translateY(-2px);
}

.card--horizontal {
  flex-direction: row;
}

.card--horizontal .card__image {
  width: 200px;
  height: auto;
}
```

**Naming Convention:** BEM (Block__Element--Modifier)
- **Block:** `.card`
- **Element:** `.card__body`
- **Modifier:** `.card--interactive`

#### 4. **E**xception (Overrides)

**Purpose:** Context-specific adjustments (use sparingly).

```css
/* assets/css/exceptions/exceptions.css */

/* Exception: Card in sidebar needs smaller padding */
.sidebar .card {
  padding: var(--size-4);
}

/* Exception: Last child no margin */
.stack > *:last-child {
  margin-bottom: 0;
}

/* Exception: Print styles */
@media print {
  .no-print {
    display: none !important;
  }
}
```

**Rule:** Exceptions are marked clearly and used only when composition/utilities don't fit.

### File Organization

```
assets/css/
├── tokens/
│   ├── foundation.css      # Primitive values
│   └── semantic.css        # Semantic mappings
├── base/
│   ├── reset.css           # Modern CSS reset
│   ├── typography.css      # Base typography
│   └── accessibility.css   # Focus states, sr-only
├── composition/
│   └── layouts.css         # Layout primitives (stack, cluster, grid)
├── utilities/
│   └── utilities.css       # Single-purpose classes
├── components/
│   ├── button.css
│   ├── card.css
│   ├── navigation.css
│   ├── toc.css
│   ├── code.css
│   ├── admonition.css
│   └── ...
├── exceptions/
│   └── exceptions.css      # Context-specific overrides
└── style.css               # Entry point (imports all)
```

**Import Order (in `style.css`):**

```css
/* 1. Tokens (variables first) */
@import url('tokens/foundation.css');
@import url('tokens/semantic.css');

/* 2. Base (resets, typography) */
@import url('base/reset.css');
@import url('base/typography.css');
@import url('base/accessibility.css');

/* 3. Composition (layout) */
@import url('composition/layouts.css');

/* 4. Utilities (single purpose) */
@import url('utilities/utilities.css');

/* 5. Components (blocks) */
@import url('components/button.css');
@import url('components/card.css');
/* ... all components ... */

/* 6. Exceptions (last, so they can override) */
@import url('exceptions/exceptions.css');
```

---

## Component Architecture

### Component Definition Standard

Every component must have:

1. **Purpose:** What problem does it solve?
2. **API:** What props/classes does it accept?
3. **States:** What visual states exist? (hover, active, disabled, etc.)
4. **Variants:** What variations are supported?
5. **Accessibility:** What ARIA attributes are required?
6. **Examples:** How is it used?

### Example: Button Component

```css
/**
 * Button Component
 * 
 * Purpose: Clickable action element
 * 
 * API:
 * - .btn (base class, required)
 * - .btn--primary, .btn--secondary, .btn--ghost (variants)
 * - .btn--small, .btn--large (sizes)
 * - .btn--block (full width)
 * 
 * States:
 * - :hover, :focus, :active (interactive)
 * - [disabled], .btn--disabled (disabled state)
 * 
 * Accessibility:
 * - Must have visible focus indicator
 * - Use <button> or <a role="button">
 * - Icon-only buttons need aria-label
 * 
 * Examples:
 * <button class="btn btn--primary">Primary Action</button>
 * <button class="btn btn--secondary btn--large">Large Secondary</button>
 * <button class="btn btn--ghost" disabled>Disabled</button>
 */

.btn {
  /* Base styles */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--size-2);
  padding: var(--size-2) var(--size-4);
  font-family: inherit;
  font-size: var(--text-body);
  font-weight: var(--font-weight-medium);
  line-height: 1.5;
  text-decoration: none;
  border: 1px solid transparent;
  border-radius: var(--radius-2);
  cursor: pointer;
  transition: all var(--transition-quick);
  
  /* Default variant */
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-primary);
}

.btn:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: var(--elevation-card);
}

.btn:active {
  transform: translateY(0);
}

.btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.btn:disabled,
.btn--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* Variants */
.btn--secondary {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border-color: var(--color-border);
}

.btn--secondary:hover {
  background: var(--color-bg-tertiary);
  border-color: var(--color-border-strong);
}

.btn--ghost {
  background: transparent;
  color: var(--color-primary);
  border-color: transparent;
}

.btn--ghost:hover {
  background: var(--color-bg-hover);
}

/* Sizes */
.btn--small {
  padding: var(--size-1) var(--size-3);
  font-size: var(--text-small);
}

.btn--large {
  padding: var(--size-3) var(--size-6);
  font-size: var(--text-heading-4);
}

/* Modifiers */
.btn--block {
  width: 100%;
}
```

### Template Component Standard

Every template partial should be documented:

```jinja2
{#
  Component: Article Card
  
  Purpose: Display article preview with image, title, excerpt, and metadata
  
  Context Variables:
  - article (Page): The page/post to display
  - show_image (bool, optional): Whether to show featured image (default: true)
  - show_excerpt (bool, optional): Whether to show excerpt (default: true)
  - excerpt_length (int, optional): Max excerpt length (default: 150)
  
  Example:
  {% include 'partials/article-card.html' with article=post %}
  {% include 'partials/article-card.html' with article=post, show_image=false %}
#}

<article class="card card--interactive">
  {% if show_image|default(true) and article.metadata.image %}
  <img 
    class="card__image"
    src="{{ image_url(article.metadata.image, width=400) }}"
    alt="{{ article.title }}"
    loading="lazy">
  {% endif %}
  
  <div class="card__body">
    <h3 class="card__title">
      <a href="{{ url_for(article) }}">{{ article.title }}</a>
    </h3>
    
    {% if show_excerpt|default(true) %}
    <p class="card__description">
      {{ article.content | excerpt(excerpt_length|default(150)) }}
    </p>
    {% endif %}
  </div>
  
  <footer class="card__footer">
    <div class="cluster cluster--small">
      {% if article.date %}
      <time datetime="{{ article.date | date_iso }}">
        {{ article.date | time_ago }}
      </time>
      {% endif %}
      
      {% if article.metadata.reading_time %}
      <span>{{ article.metadata.reading_time }} min read</span>
      {% endif %}
    </div>
  </footer>
</article>
```

---

## JavaScript Architecture

### Principles

1. **Progressive Enhancement:** Site works without JS
2. **No Build Step:** Vanilla JS (ES6+ modules OK)
3. **Modular:** Each feature is a self-contained module
4. **Event-Driven:** Use custom events for inter-module communication
5. **Performance:** Defer non-critical JS, use passive listeners

### Module Pattern

```javascript
// assets/js/modules/theme-toggle.js

/**
 * Theme Toggle Module
 * 
 * Purpose: Handle light/dark theme switching
 * Dependencies: None
 * Events Emitted: themechange
 */

(function() {
  'use strict';
  
  const MODULE_NAME = 'ThemeToggle';
  const STORAGE_KEY = 'bengal-theme';
  
  // Module state
  const state = {
    current: 'light',
    initialized: false
  };
  
  /**
   * Initialize module
   */
  function init() {
    if (state.initialized) return;
    
    // Get initial theme
    state.current = getStoredTheme() || getSystemTheme() || 'light';
    applyTheme(state.current);
    
    // Setup toggle button
    const toggleBtn = document.querySelector('[data-theme-toggle]');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggle);
    }
    
    // Watch for system theme changes
    watchSystemTheme();
    
    state.initialized = true;
    console.debug(`[${MODULE_NAME}] Initialized`);
  }
  
  /**
   * Toggle theme
   */
  function toggle() {
    const next = state.current === 'light' ? 'dark' : 'light';
    setTheme(next);
  }
  
  /**
   * Set theme
   */
  function setTheme(theme) {
    state.current = theme;
    applyTheme(theme);
    storeTheme(theme);
    
    // Emit event for other modules
    window.dispatchEvent(new CustomEvent('themechange', {
      detail: { theme }
    }));
  }
  
  /**
   * Apply theme to document
   */
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
  }
  
  /**
   * Get stored theme
   */
  function getStoredTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }
  
  /**
   * Store theme
   */
  function storeTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      console.warn(`[${MODULE_NAME}] Could not store theme`);
    }
  }
  
  /**
   * Get system theme preference
   */
  function getSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }
  
  /**
   * Watch for system theme changes
   */
  function watchSystemTheme() {
    if (!window.matchMedia) return;
    
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', (e) => {
      // Only update if user hasn't manually set a theme
      if (!getStoredTheme()) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    });
  }
  
  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  // Expose public API
  window.BengalTheme = {
    toggle,
    setTheme,
    getCurrent: () => state.current
  };
})();
```

### Module Communication

```javascript
// Module A emits event
window.dispatchEvent(new CustomEvent('themechange', {
  detail: { theme: 'dark' }
}));

// Module B listens
window.addEventListener('themechange', (e) => {
  console.log('Theme changed to:', e.detail.theme);
});
```

### File Organization

```
assets/js/
├── modules/
│   ├── theme-toggle.js
│   ├── mobile-nav.js
│   ├── toc-scroll.js
│   ├── code-copy.js
│   ├── tabs.js
│   └── ...
├── utils/
│   ├── debounce.js
│   ├── throttle.js
│   └── dom-helpers.js
└── main.js  (orchestrator, minimal)
```

---

## Theme Structure Standards

### Standard Theme Structure

```
themes/
  mytheme/
    ├── theme.toml              # Theme metadata
    ├── README.md               # Theme documentation
    ├── CHANGELOG.md            # Version history
    ├── templates/
    │   ├── base.html           # Master template
    │   ├── index.html          # Homepage
    │   ├── page.html           # Default page
    │   ├── post.html           # Blog post
    │   ├── doc.html            # Documentation page (optional)
    │   ├── archive.html        # Archive/list
    │   ├── tag.html            # Single tag
    │   ├── tags.html           # All tags
    │   ├── 404.html            # Error page
    │   └── partials/
    │       ├── header.html
    │       ├── footer.html
    │       ├── sidebar.html
    │       ├── toc.html
    │       ├── breadcrumbs.html
    │       ├── article-card.html
    │       ├── pagination.html
    │       └── ...
    ├── assets/
    │   ├── css/
    │   │   ├── tokens/
    │   │   │   ├── foundation.css
    │   │   │   └── semantic.css
    │   │   ├── base/
    │   │   │   ├── reset.css
    │   │   │   ├── typography.css
    │   │   │   └── accessibility.css
    │   │   ├── composition/
    │   │   │   └── layouts.css
    │   │   ├── utilities/
    │   │   │   └── utilities.css
    │   │   ├── components/
    │   │   │   └── *.css
    │   │   ├── exceptions/
    │   │   │   └── exceptions.css
    │   │   └── style.css       # Main entry point
    │   ├── js/
    │   │   ├── modules/
    │   │   │   └── *.js
    │   │   ├── utils/
    │   │   │   └── *.js
    │   │   └── main.js
    │   └── images/
    │       └── ...
    ├── screenshots/
    │   ├── desktop.png
    │   ├── mobile.png
    │   └── dark-mode.png
    └── examples/
        └── sample-content.md
```

### theme.toml Specification

```toml
[theme]
name = "Bengal Default"
version = "1.0.0"
author = "Bengal Team"
license = "MIT"
homepage = "https://github.com/bengal-ssg/bengal"
description = "Modern documentation theme with dark mode"
tags = ["documentation", "blog", "responsive", "dark-mode"]

# Minimum Bengal version required
min_bengal_version = "0.1.0"

# Features this theme supports
[theme.features]
dark_mode = true
responsive = true
toc = true
breadcrumbs = true
search_ready = true  # Ready for search integration
syntax_highlighting = true
i18n_ready = false

# Layouts provided
[theme.layouts]
default = "page.html"
blog = "post.html"
docs = "doc.html"

# Required template functions
[theme.requires]
template_functions = [
  "url_for",
  "asset_url",
  "get_menu",
  "excerpt",
  "time_ago",
  "related_posts"
]

# Configuration options for users
[theme.config]
# Example: Users can set these in their bengal.toml
# [theme.options]
# primary_color = "#2196f3"
# show_toc = true
```

---

## Override & Customization Strategy

### Three Levels of Customization

#### Level 1: Design Token Override (Easiest)

**Use Case:** Change colors, fonts, spacing without touching CSS.

```css
/* custom/assets/css/custom-tokens.css */
:root {
  /* Override semantic tokens */
  --color-primary: #8b5cf6;  /* Change to purple */
  --text-heading-1: 3.5rem;  /* Larger headings */
  --space-section-gap: 4rem; /* More spacing */
}
```

**Usage:**
```html
<!-- In custom templates/base.html -->
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
<link rel="stylesheet" href="{{ asset_url('css/custom-tokens.css') }}">
```

#### Level 2: Component Override (Moderate)

**Use Case:** Customize specific components.

```css
/* custom/assets/css/custom-components.css */
/* Override button component */
.btn {
  border-radius: var(--radius-full); /* Pill-shaped buttons */
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Override card component */
.card:hover {
  transform: scale(1.02); /* Different hover effect */
}
```

#### Level 3: Template Override (Full Control)

**Use Case:** Complete template replacement.

**Template Resolution Order:**
1. `custom/templates/page.html` (checked first)
2. `themes/mytheme/templates/page.html`
3. `bengal/themes/default/templates/page.html` (fallback)

**Example:**
```
mysite/
  templates/
    page.html        ← Overrides theme's page.html
    partials/
      header.html    ← Custom header
```

### Customization Matrix

| Need | Solution | Effort | Flexibility |
|------|----------|--------|-------------|
| Change colors | Token override | Low | Low |
| Change fonts | Token override | Low | Low |
| Tweak spacing | Token override | Low | Low |
| Modify button style | Component override | Medium | Medium |
| Change layout | Template override | High | High |
| New page type | New template | High | Complete |

---

## Versioning & Breaking Changes

### Semantic Versioning

Bengal themes follow **SemVer**:

```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes (template API changes)
MINOR: New features (backward compatible)
PATCH: Bug fixes
```

### Breaking Change Policy

**Definition:** A breaking change requires users to modify their code.

**Examples of Breaking Changes:**
- Removing a template block
- Renaming CSS classes used in documentation
- Removing a design token
- Changing template context variable names

**Non-Breaking Changes:**
- Adding new blocks
- Adding new CSS classes
- Adding new design tokens
- Adding new context variables

### Deprecation Process

1. **Announce:** Document deprecation in CHANGELOG
2. **Warn:** Add console warnings (if applicable)
3. **Wait:** Keep deprecated feature for 2+ major versions
4. **Remove:** Remove in major version bump

**Example:**

```
Version 1.5.0: Deprecate .old-button class
  - Still works
  - Console warning: "Warning: .old-button is deprecated, use .btn instead"
  
Version 2.0.0: Still supported with warning

Version 3.0.0: Removed
```

### Compatibility Table

| Bengal Version | Theme Version | Status |
|----------------|---------------|--------|
| 1.x | 1.x | Supported |
| 1.x | 2.x | Recommended |
| 2.x | 1.x | Compatible (with warnings) |
| 2.x | 2.x | Supported |

---

## Testing Framework

### Theme Testing Strategy

#### 1. Visual Regression Testing

**Tool:** Manual screenshots + automated (future)

**Test Matrix:**
- Light mode / Dark mode
- Desktop (1920px) / Tablet (768px) / Mobile (375px)
- All page types (index, page, post, archive, tag)
- All components (buttons, cards, nav, toc)

**Checklist:**
```
□ Homepage renders correctly
□ Blog post with TOC renders
□ Archive page with pagination
□ Tag pages work
□ 404 page displays
□ Navigation highlights active page
□ Dark mode toggles correctly
□ Mobile menu works
□ All components display correctly
□ No layout shift (CLS < 0.1)
```

#### 2. Accessibility Testing

**Tool:** axe DevTools, WAVE, manual keyboard testing

**Checklist:**
```
□ All interactive elements keyboard accessible
□ Focus indicators visible
□ Color contrast passes WCAG AA (4.5:1 text, 3:1 UI)
□ Skip links work
□ ARIA labels correct
□ Headings hierarchical
□ Images have alt text
□ Forms have labels
□ No keyboard traps
```

#### 3. Performance Testing

**Tool:** Lighthouse, WebPageTest

**Targets:**
```
□ Performance score > 95
□ Accessibility score = 100
□ Best Practices score > 95
□ SEO score > 95
□ First Contentful Paint < 1s
□ Time to Interactive < 2s
□ Cumulative Layout Shift < 0.1
□ Largest Contentful Paint < 2.5s
```

#### 4. Template Function Testing

**Tool:** Python unit tests

**Example:**
```python
def test_article_card_partial(site_with_content):
    """Test article-card partial renders correctly."""
    engine = TemplateEngine(site_with_content)
    
    page = site_with_content.pages[0]
    html = engine.render('partials/article-card.html', {
        'article': page,
        'show_image': True
    })
    
    assert page.title in html
    assert 'card' in html
    assert 'card__title' in html
```

---

## Documentation Standards

### Theme Documentation Template

```markdown
# Theme Name

Brief description (1-2 sentences).

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

```bash
# Copy theme to your project
cp -r themes/mytheme mysite/themes/
```

## Configuration

```toml
[site]
theme = "mytheme"

[theme.options]
primary_color = "#2196f3"
show_toc = true
```

## Customization

### Changing Colors

Override design tokens:

```css
/* custom/assets/css/custom.css */
:root {
  --color-primary: #8b5cf6;
}
```

### Custom Layouts

Create custom templates:

```
mysite/templates/
  page.html  ← Your custom page template
```

## Components

### Button

```html
<button class="btn btn--primary">Primary</button>
<button class="btn btn--secondary">Secondary</button>
```

[More components...]

## Browser Support

- Chrome/Edge: Last 2 versions
- Firefox: Last 2 versions
- Safari: Last 2 versions
- Mobile: iOS 13+, Android 8+

## License

MIT
```

---

## Migration & Upgrade Path

### From Default Theme to Enhanced Theme

**Step 1: Backup**
```bash
cp -r mysite/templates mysite/templates.backup
```

**Step 2: Update theme reference**
```toml
# bengal.toml
[site]
theme = "enhanced"  # Changed from "default"
```

**Step 3: Test**
```bash
bengal build
bengal serve
```

**Step 4: Adjust custom CSS**
- Review custom CSS for conflicts
- Update to use new design tokens
- Test all pages

### From Theme 1.x to 2.x

**Changelog Review:**
- Read CHANGELOG.md for breaking changes
- Note deprecated features
- Plan replacements

**Migration Guide Template:**
```markdown
# Migrating from Theme 1.x to 2.x

## Breaking Changes

### 1. Button Classes Renamed

**Old:**
```html
<button class="old-button">Click</button>
```

**New:**
```html
<button class="btn btn--primary">Click</button>
```

### 2. Token Names Changed

**Old:**
```css
:root {
  --primary-color: #2196f3;
}
```

**New:**
```css
:root {
  --color-primary: #2196f3;
}
```

## New Features

- Dark mode support
- TOC scroll tracking
- Code copy buttons

## Upgrade Steps

1. Update theme version in `theme.toml`
2. Search for deprecated classes
3. Replace with new classes
4. Test thoroughly
```

---

## Validation Checklist

Before releasing a theme or theme update:

### Design

- [ ] All design decisions use design tokens
- [ ] Color contrast passes WCAG AA
- [ ] Typography is readable (line-height, font-size)
- [ ] Spacing is consistent
- [ ] Dark mode works correctly

### Code Quality

- [ ] CSS follows CUBE methodology
- [ ] JavaScript modules are self-contained
- [ ] No inline styles (except dynamic)
- [ ] No !important (except utilities)
- [ ] Comments explain "why", not "what"

### Components

- [ ] All components documented
- [ ] All states defined (hover, focus, active, disabled)
- [ ] All variants tested
- [ ] Accessibility attributes present
- [ ] Examples provided

### Templates

- [ ] All templates have documentation comments
- [] Template inheritance clear
- [ ] Blocks well-named
- [ ] Context variables documented
- [ ] Error states handled

### Accessibility

- [ ] Keyboard navigation works
- [ ] Focus indicators visible
- [ ] ARIA labels correct
- [ ] Screen reader tested
- [ ] Color contrast sufficient
- [ ] Skip links present

### Performance

- [ ] CSS < 50KB (gzipped)
- [ ] JS < 20KB (gzipped)
- [ ] Images optimized
- [ ] No render-blocking resources
- [ ] Lighthouse score > 95

### Compatibility

- [ ] Works in last 2 versions of major browsers
- [ ] Mobile responsive
- [ ] Works without JavaScript (progressive enhancement)
- [ ] Print styles included

### Documentation

- [ ] README complete
- [ ] CHANGELOG updated
- [ ] Migration guide (if breaking changes)
- [ ] Examples provided
- [ ] Screenshots included

---

## Conclusion

This master architecture provides a **rock-solid foundation** for Bengal's theme system:

1. **Design Token System:** Consistent, customizable, scalable
2. **CUBE CSS Methodology:** Pragmatic, maintainable, performant
3. **Component Architecture:** Modular, documented, testable
4. **JavaScript Patterns:** Progressive, event-driven, modular
5. **Theme Standards:** Clear structure, versioning, documentation
6. **Customization Strategy:** Three levels of increasing complexity
7. **Testing Framework:** Visual, accessibility, performance
8. **Upgrade Path:** Smooth migrations, backward compatibility

**Key Success Factors:**

- ✅ **No Dependencies:** Everything uses web standards
- ✅ **Performance First:** Strict budgets, optimized delivery
- ✅ **Accessibility Built-In:** WCAG AA compliance from day one
- ✅ **Progressive Enhancement:** Works at every level
- ✅ **Backward Compatibility:** No breaking changes without clear path
- ✅ **Self-Documenting:** Clear naming, inline documentation
- ✅ **Testable:** Clear validation criteria
- ✅ **Flexible:** Customize without forking

**This architecture will serve Bengal for years to come.**

---

## Next Steps

1. **Review and approve** this architecture
2. **Implement Phase 1** from UX Enhancement Plan using this architecture
3. **Document as we build** using these standards
4. **Test continuously** against validation checklist
5. **Iterate and improve** based on real-world usage

Questions or concerns? This is the time to raise them!

