# Bengal Default Theme - Component Documentation

**Version:** 2.0  
**Date:** October 4, 2025  
**Status:** Complete

---

## 📚 Overview

This document provides comprehensive usage documentation for all components in the Bengal default theme.

---

## 🎨 Design System

### Design Tokens

The theme uses a two-tier token system:

#### Foundation Tokens (Primitives)
Raw values - **never use directly in HTML/templates**.

```css
/* Colors */
--blue-500: #2196f3;
--gray-900: #212121;

/* Spacing */
--size-4: 1rem;
--size-6: 1.5rem;

/* Typography */
--font-size-16: 1rem;
--font-weight-bold: 700;
```

#### Semantic Tokens (Purpose-Based)
**Use these in templates and custom styles.**

```css
/* Colors */
--color-primary: var(--blue-500);
--color-text-primary: var(--gray-900);
--color-bg-primary: var(--white);

/* Spacing */
--space-component-gap: var(--size-4);
--space-section-gap: var(--size-12);

/* Typography */
--text-body: var(--text-base);
--text-heading-1: var(--text-5xl);
```

### Using Tokens in Custom Styles

```css
/* ✅ Good - Uses semantic tokens */
.my-component {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
  padding: var(--space-component-gap);
  font-size: var(--text-body);
}

/* ❌ Bad - Uses foundation tokens directly */
.my-component {
  color: var(--gray-900);
  background: var(--gray-50);
  padding: var(--size-4);
  font-size: var(--font-size-16);
}
```

---

## 🧩 Layout Components

### Three-Column Documentation Layout

**Template:** `doc.html`

```yaml
---
title: "My Documentation Page"
template: doc.html
description: "Page description"
---
```

**Structure:**
```
┌─────────────────────────────────────┐
│           Header (Fixed)            │
├─────┬───────────────────┬───────────┤
│ Nav │   Main Content    │    TOC    │
│     │                   │           │
│ 250 │       Flex        │    250    │
│  px │                   │    px     │
└─────┴───────────────────┴───────────┘
```

**Features:**
- ✅ Responsive (collapses to single column on mobile)
- ✅ Sticky sidebar navigation
- ✅ Auto-generated TOC
- ✅ Active section highlighting

**Customization:**
```css
/* Adjust sidebar widths */
.docs-layout {
  --docs-nav-width: 280px;  /* Default: 250px */
  --toc-width: 280px;       /* Default: 250px */
}
```

### Standard Page Layout

**Template:** `page.html` (default)

Full-width content with standard header/footer.

```yaml
---
title: "My Page"
# template defaults to page.html
---
```

---

## 📦 Content Components

### 1. Admonitions (Callouts)

**Usage in Markdown:**

```markdown
!!! note
    This is a note admonition.

!!! tip "Custom Title"
    This is a tip with a custom title.

!!! warning
    This is a warning.

!!! danger
    This is a danger callout.

!!! example
    This is an example.
```

**Available Types:**
- `note` (blue) - Informational content
- `tip` (green) - Helpful suggestions
- `warning` (orange) - Caution/attention needed
- `danger` (red) - Critical warnings
- `example` (purple) - Code examples

**Styling:**
- Colored left border (4px)
- Matching background tint
- Icon (auto-generated)
- Elevation on hover

### 2. Code Blocks

**Features:**
- ✅ Syntax highlighting
- ✅ Language label
- ✅ Copy button
- ✅ Line numbers (optional)
- ✅ Filename header (optional)

**Usage:**

````markdown
```python
def hello_world():
    print("Hello, World!")
```

```python{title="example.py"}
# With title
def hello():
    return "Hello"
```
````

**Copy Button:**
- Auto-added to all code blocks
- SVG icons (copy → checkmark)
- 2-second success state
- Keyboard accessible

### 3. Content Cards

**Feature Card:**

```html
<div class="card feature-card">
  <div class="card-icon">
    <svg><!-- icon --></svg>
  </div>
  <h3 class="card-title">Feature Title</h3>
  <p class="card-description">Feature description goes here.</p>
  <a href="/learn-more" class="card-link">Learn More →</a>
</div>
```

**Callout Card:**

```html
<div class="card callout-card callout-info">
  <div class="callout-icon">💡</div>
  <div class="callout-content">
    <h4 class="callout-title">Quick Tip</h4>
    <p>This is a callout card for highlighting information.</p>
  </div>
</div>
```

**Callout Types:**
- `callout-info` (blue)
- `callout-success` (green)
- `callout-warning` (orange)
- `callout-danger` (red)

**Link Card:**

```html
<a href="/docs" class="card link-card">
  <h3 class="card-title">Documentation</h3>
  <p class="card-description">Read the full docs.</p>
  <span class="card-arrow">→</span>
</a>
```

**Stat Card:**

```html
<div class="card stat-card">
  <div class="stat-value">99.9%</div>
  <div class="stat-label">Uptime</div>
</div>
```

**Card Grid:**

```html
<div class="card-grid card-grid-2">
  <!-- 2 columns -->
  <div class="card">...</div>
  <div class="card">...</div>
</div>

<div class="card-grid card-grid-3">
  <!-- 3 columns -->
  <div class="card">...</div>
  <div class="card">...</div>
  <div class="card">...</div>
</div>

<div class="card-grid card-grid-4">
  <!-- 4 columns (auto-responsive) -->
  <div class="card">...</div>
  <!-- ... -->
</div>
```

### 4. Tabs

**HTML Structure:**

```html
<div class="tabs">
  <div class="tab-buttons">
    <button class="tab-button active" data-tab="tab1">Tab 1</button>
    <button class="tab-button" data-tab="tab2">Tab 2</button>
    <button class="tab-button" data-tab="tab3">Tab 3</button>
  </div>
  <div class="tab-contents">
    <div class="tab-content active" id="tab1">
      <p>Content for tab 1</p>
    </div>
    <div class="tab-content" id="tab2">
      <p>Content for tab 2</p>
    </div>
    <div class="tab-content" id="tab3">
      <p>Content for tab 3</p>
    </div>
  </div>
</div>
```

**Features:**
- Keyboard accessible (arrow keys)
- Smooth transitions
- ARIA attributes
- Mobile-friendly

### 5. Hero Sections

**Large Hero:**

```html
<div class="hero hero-large">
  <h1 class="hero-title">Welcome to Bengal SSG</h1>
  <p class="hero-subtitle">Fast & Fierce Static Sites</p>
  <div class="hero-actions">
    <a href="/docs" class="btn btn-primary">Get Started</a>
    <a href="/about" class="btn btn-secondary">Learn More</a>
  </div>
</div>
```

**Compact Hero:**

```html
<div class="hero hero-compact">
  <h1 class="hero-title">Documentation</h1>
  <p class="hero-subtitle">Everything you need to know</p>
</div>
```

**With Background Pattern:**

```html
<div class="hero hero-large hero-pattern">
  <!-- Content -->
</div>
```

---

## 🎯 Interactive Components

### 1. Back to Top Button

**Auto-enabled** on all pages.

**Features:**
- Appears after scrolling 300px
- Smooth scroll to top
- Fixed position (bottom-right)
- Mobile-responsive

**Customization:**

```css
#back-to-top {
  --offset: 20px; /* Distance from bottom/right */
}
```

### 2. Reading Progress Bar

**Auto-enabled** on all pages.

**Features:**
- Fixed at top of viewport
- Real-time progress tracking
- 4px height
- Primary color

**Customization:**

```css
#reading-progress {
  height: 3px; /* Adjust thickness */
  background: linear-gradient(90deg, blue, green); /* Custom gradient */
}
```

### 3. Copy Link Buttons

**Auto-enabled** on all headings with IDs.

**Features:**
- Appears on hover
- Click to copy anchor link
- Success feedback (2 seconds)
- Keyboard accessible

**Disable on specific heading:**

```html
<h2 id="my-heading" data-no-copy-link>
  No Copy Button
</h2>
```

### 4. Image Lightbox

**Auto-enabled** for images >400px.

**Features:**
- Click to enlarge
- Arrow keys to navigate
- Escape to close
- Mobile-friendly

**Enable/Disable:**

```html
<!-- Force enable -->
<img src="small.jpg" data-lightbox alt="Image">

<!-- Force disable -->
<img src="large.jpg" data-no-lightbox alt="Image">
```

**High-res version:**

```html
<img 
  src="thumb.jpg" 
  data-lightbox-src="full-res.jpg"
  alt="Image">
```

---

## 🎨 Utility Classes

### Spacing

```html
<!-- Margins -->
<div class="mt-4">Margin top (1rem)</div>
<div class="mb-6">Margin bottom (1.5rem)</div>
<div class="my-8">Margin vertical (2rem)</div>

<!-- Paddings -->
<div class="p-4">Padding all (1rem)</div>
<div class="px-6">Padding horizontal (1.5rem)</div>
<div class="py-8">Padding vertical (2rem)</div>
```

### Display

```html
<div class="hidden">Hidden on all sizes</div>
<div class="hidden-mobile">Hidden on mobile (<768px)</div>
<div class="visible-mobile">Visible only on mobile</div>
```

### Text Alignment

```html
<div class="text-left">Left aligned</div>
<div class="text-center">Center aligned</div>
<div class="text-right">Right aligned</div>
```

### Colors

```html
<p class="text-primary">Primary color text</p>
<p class="text-secondary">Secondary color text</p>
<p class="text-muted">Muted text</p>

<div class="bg-primary">Primary background</div>
<div class="bg-secondary">Secondary background</div>
```

### Typography

```html
<p class="text-sm">Small text</p>
<p class="text-base">Normal text</p>
<p class="text-lg">Large text</p>
<p class="text-xl">Extra large text</p>

<p class="font-normal">Normal weight</p>
<p class="font-medium">Medium weight</p>
<p class="font-bold">Bold weight</p>
```

---

## 🌓 Dark Mode

### Auto-Detection

Theme automatically detects system preference:

```javascript
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
```

### Manual Toggle

Theme toggle button in header:

```html
<button class="theme-toggle" aria-label="Toggle dark mode">
  <!-- SVG icons for sun/moon -->
</button>
```

### Persistent Storage

Theme preference saved to `localStorage`:

```javascript
localStorage.setItem('bengal-theme', 'dark'); // or 'light'
```

### Custom Styles for Dark Mode

```css
/* Light mode (default) */
.my-component {
  background: white;
  color: black;
}

/* Dark mode */
[data-theme="dark"] .my-component {
  background: #1a1a1a;
  color: white;
}
```

---

## ♿ Accessibility

### Skip to Content

Press **Tab** immediately after page load:

```html
<a href="#main-content" class="skip-link">
  Skip to main content
</a>
```

### Keyboard Navigation

- **Tab**: Navigate forward
- **Shift + Tab**: Navigate backward
- **Enter/Space**: Activate buttons
- **Escape**: Close modals/overlays
- **Arrow Keys**: Navigate tabs/lightbox

### Screen Reader Support

All components include proper ARIA attributes:

```html
<button aria-label="Close menu" aria-expanded="false">
<div role="dialog" aria-modal="true" aria-labelledby="title">
<nav role="navigation" aria-label="Main navigation">
```

### Focus Indicators

Clear focus outlines appear when navigating via keyboard:

```css
*:focus-visible {
  outline: 2px solid var(--color-border-focus);
  outline-offset: 2px;
}
```

### Color Contrast

All text meets WCAG 2.1 AA standards:
- Body text: 16.1:1 (AAA)
- Secondary text: 4.6:1 (AA)
- Links: 5.5:1 (AA)

### Reduced Motion

Respects user's motion preferences:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
    transition: none !important;
  }
}
```

---

## 📱 Responsive Design

### Breakpoints

```css
/* Mobile first approach */
.component { }

/* Tablet (768px+) */
@media (min-width: 768px) { }

/* Desktop (1024px+) */
@media (min-width: 1024px) { }

/* Large desktop (1280px+) */
@media (min-width: 1280px) { }
```

### Three-Column Layout Behavior

- **Mobile (<768px)**: Single column, stacked
- **Tablet (768-1024px)**: Content + TOC (nav in drawer)
- **Desktop (1024px+)**: Full three-column layout

---

## 🖨️ Print Styles

### Automatic Optimization

Print styles automatically:
- Hide interactive elements (buttons, navigation)
- Remove backgrounds and shadows
- Show link URLs
- Optimize spacing
- Use black text on white background

### Print-Specific Classes

```html
<!-- Hidden when printing -->
<div class="print-hidden">
  This won't print
</div>

<!-- Only visible when printing -->
<div class="print-only">
  This only appears in print
</div>
```

### Print Command

Users can print with:
- **Ctrl/Cmd + P**
- Browser print button
- Automatic PDF generation

---

## 🎯 Performance

### Lazy Loading Images

```html
<!-- Automatic lazy loading -->
<img src="image.jpg" loading="lazy" alt="Description">

<!-- With responsive images -->
<img 
  srcset="image-400.jpg 400w, image-800.jpg 800w"
  sizes="(max-width: 600px) 400px, 800px"
  loading="lazy"
  alt="Description">
```

### Performance Features

- ✅ Zero dependencies
- ✅ ~7 KB JavaScript (gzipped)
- ✅ GPU-accelerated animations
- ✅ Passive event listeners
- ✅ Debounced scroll handlers
- ✅ requestAnimationFrame

---

## 🔧 Customization

### Override Design Tokens

```css
/* custom.css */
:root {
  /* Brand colors */
  --color-primary: #your-brand-color;
  --color-secondary: #your-secondary-color;
  
  /* Typography */
  --font-sans: 'Your Font', sans-serif;
  --text-body: 1.125rem; /* Larger body text */
  
  /* Spacing */
  --space-component-gap: 2rem; /* More spacing */
}
```

### Custom Components

```css
/* my-component.css */
.my-component {
  /* Use semantic tokens */
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  padding: var(--space-component-gap);
  border-radius: var(--border-radius-medium);
  box-shadow: var(--elevation-card);
}

.my-component:hover {
  box-shadow: var(--elevation-card-hover);
}

/* Dark mode support */
[data-theme="dark"] .my-component {
  /* Tokens automatically adjust, but you can override */
}
```

### Template Override

Create your own template:

```html
<!-- templates/my-template.html -->
{% extends "base.html" %}

{% block content %}
  <div class="my-custom-layout">
    {{ content | safe }}
  </div>
{% endblock %}
```

Use in frontmatter:

```yaml
---
title: "Custom Page"
template: my-template.html
---
```

---

## 📚 Template Functions

### Available Functions

```jinja2
{# URL generation #}
{{ url_for(page) }}
{{ asset_url('css/style.css') }}
{{ canonical_url(page.url) }}

{# Image helpers #}
{{ og_image(page.metadata.image) }}

{# Navigation #}
{{ get_menu('main') }}

{# Tags & Categories #}
{{ popular_tags(10) }}

{# Content helpers #}
{{ meta_description(text, 160) }}
{{ meta_keywords(tags, 10) }}
{{ reading_time(content) }}

{# Date formatting #}
{{ page.date | date_format('%B %d, %Y') }}

{# Conditionals #}
{% if page | has_tag('featured') %}
{% if item.active %}
{% if item.active_trail %}
```

---

## 🎉 Best Practices

### 1. Always Use Semantic Tokens

```css
/* ✅ Good */
color: var(--color-text-primary);

/* ❌ Bad */
color: var(--gray-900);
color: #212121;
```

### 2. Mobile-First CSS

```css
/* ✅ Good - Mobile first */
.component {
  flex-direction: column;
}

@media (min-width: 768px) {
  .component {
    flex-direction: row;
  }
}

/* ❌ Bad - Desktop first */
.component {
  flex-direction: row;
}

@media (max-width: 767px) {
  .component {
    flex-direction: column;
  }
}
```

### 3. Accessibility First

```html
<!-- ✅ Good - Semantic, accessible -->
<button aria-label="Close menu" aria-expanded="false">
  <svg aria-hidden="true">...</svg>
</button>

<!-- ❌ Bad - No semantics -->
<div onclick="close()">
  <img src="close.png">
</div>
```

### 4. Progressive Enhancement

```html
<!-- ✅ Good - Works without JS -->
<a href="/docs" class="button">
  View Docs
</a>
<script>
  // Enhance with modal
  enhanceWithModal('.button');
</script>

<!-- ❌ Bad - Requires JS -->
<div onclick="showModal()">
  View Docs
</div>
```

---

## 🐛 Troubleshooting

### Component Not Styling Correctly

1. Check if correct class names are used
2. Verify `style.css` is loaded
3. Check browser console for errors
4. Ensure tokens are defined

### Dark Mode Not Working

1. Check `data-theme` attribute on `<html>`
2. Verify localStorage has correct value
3. Clear cache and reload
4. Check for CSS specificity issues

### Lightbox Not Opening

1. Ensure image is >400px
2. Check image is not inside `<a>` tag
3. Verify `lightbox.js` is loaded
4. Check browser console for errors

### Layout Breaking on Mobile

1. Test responsive breakpoints
2. Check for fixed widths
3. Use flexible units (rem, %, vw)
4. Test in actual devices, not just browser resize

---

## 📞 Support

### Resources

- **Documentation**: Full Bengal docs
- **Examples**: See `examples/quickstart/`
- **Issues**: GitHub Issues
- **Community**: Discord/Forum

### Quick Reference

- Design Tokens: `assets/css/tokens/`
- Components: `assets/css/components/`
- Templates: `templates/`
- JavaScript: `assets/js/`

---

**Component Documentation Complete! 🎉**

All components are documented, tested, and ready for production use.

