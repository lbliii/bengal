# Documentation Theme UX Enhancement Plan

**Date:** October 3, 2025  
**Status:** Strategic Planning  
**Goal:** Elevate Bengal's default theme to compete with modern documentation platforms like Mintlify, Docusaurus, and GitBook without adding new dependencies

---

## Executive Summary

Bengal SSG has a solid foundation with a well-architected theme system, comprehensive template functions, and excellent performance characteristics. This plan outlines how to take the current default theme to the next level by applying modern documentation UX patterns and visual design principles observed in leading platforms like Mintlify.

**Key Insight:** Most improvements can be achieved through CSS enhancements, layout refinements, and better use of existing template functions—no new dependencies required.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Competitive Analysis](#competitive-analysis)
3. [UX Enhancement Strategy](#ux-enhancement-strategy)
4. [Visual Design Improvements](#visual-design-improvements)
5. [Layout & Navigation Enhancements](#layout--navigation-enhancements)
6. [Content Experience Upgrades](#content-experience-upgrades)
7. [Interactive Elements](#interactive-elements)
8. [Accessibility & Performance](#accessibility--performance)
9. [Implementation Roadmap](#implementation-roadmap)

---

## Current State Analysis

### Strengths 💪

1. **Solid Foundation**
   - Clean, modular CSS architecture with CSS custom properties
   - Responsive design with mobile-first approach
   - Dark mode support with system preference detection
   - Semantic HTML with ARIA labels
   - 75 template functions for rich functionality

2. **Performance First**
   - No heavy JavaScript frameworks
   - Minimal dependencies
   - Fast build times (incremental builds)
   - Efficient asset pipeline

3. **Developer-Friendly Architecture**
   - Well-organized component structure
   - Clear separation of concerns
   - Template inheritance system
   - Extensible through template overrides

4. **Content Features**
   - Table of contents (TOC) with auto-generation
   - Breadcrumbs navigation
   - Page navigation (prev/next)
   - Related posts
   - Tag system
   - RSS/Sitemap generation

5. **Documentation-Ready Components**
   - Admonitions (note, warning, tip, etc.)
   - Code blocks with syntax highlighting
   - Tabs for multi-language examples
   - Dropdowns for collapsible content

### Gaps & Opportunities 🎯

1. **Visual Polish**
   - Basic styling needs more sophistication
   - Limited use of modern CSS techniques (backdrop-filter, gradients, etc.)
   - Could benefit from micro-interactions
   - Typography scale is good but needs better rhythm

2. **Layout Sophistication**
   - Single-column focused design (good start)
   - Missing: Three-column layout option (sidebar + content + TOC)
   - No persistent left sidebar for docs navigation
   - Limited grid variety for landing pages

3. **Navigation Experience**
   - Basic menu system works but lacks polish
   - No keyboard shortcuts
   - Search is missing (opportunity for future enhancement)
   - No quick navigation patterns (command palette inspiration)

4. **Content Discoverability**
   - Could use better visual hierarchy
   - Limited callouts/highlights for important content
   - No "quick links" or "on this page" preview cards
   - Related content could be more visually prominent

5. **Documentation-Specific Features**
   - No copy-to-clipboard for code blocks
   - API reference layouts not optimized
   - No version switcher (could be template-based)
   - No feedback mechanism ("Was this helpful?")

---

## Competitive Analysis

### Mintlify (https://www.mintlify.com/docs)

**What They Do Well:**

1. **Visual Design**
   - Clean, modern aesthetic with excellent contrast
   - Generous white space
   - Subtle shadows and borders create depth
   - Color-coded sections for quick scanning
   - Beautiful gradients on hero sections

2. **Layout**
   - Three-column layout: sidebar navigation + content + TOC/metadata
   - Persistent left sidebar with collapsible sections
   - Sticky TOC on the right
   - Content max-width optimized for readability (~70ch)

3. **Typography**
   - Clear hierarchy with multiple heading levels
   - Excellent line-height and letter spacing
   - Code snippets visually distinct
   - Consistent font sizing system

4. **Navigation**
   - Sidebar with nested items, expandable sections
   - Active state clearly indicated with color bar
   - Search prominently placed
   - Breadcrumbs at top
   - Keyboard shortcuts (Cmd+K for search)

5. **Interactive Elements**
   - Copy button on all code blocks
   - Expandable code examples
   - Tabs for multi-language code samples
   - Smooth scroll to sections
   - "On this page" TOC with active highlighting

6. **Content Components**
   - Callouts with icons (tip, warning, info)
   - Cards for feature grids
   - Accordion/FAQ components
   - API playground (interactive, but out of scope for us)

### Docusaurus

**Notable Patterns:**

1. Versioned documentation support
2. Doc-only mode with sidebar
3. Blog integration
4. Announcement bar
5. Last updated timestamp
6. Edit this page on GitHub link

### GitBook

**Notable Patterns:**

1. Clean, minimal interface
2. Excellent search with filtering
3. Page outline on hover
4. Emoji support for visual variety
5. Inline comments (collaboration feature)

### Nextra

**Notable Patterns:**

1. Built on Next.js (similar SSG approach to ours)
2. Beautiful syntax highlighting themes
3. Inline TOC with smooth scroll
4. File tree component for code structure
5. Callout components with customization

---

## UX Enhancement Strategy

### Core Principles

1. **Progressive Enhancement**: Start with semantic HTML, enhance with CSS, add minimal JavaScript for interactions
2. **No New Dependencies**: Use only CSS, HTML, and vanilla JavaScript
3. **Performance First**: Keep build times fast, don't bloat the theme
4. **Accessibility**: WCAG 2.1 AA compliance minimum
5. **Flexibility**: Users can override any part of the theme

### Design Philosophy

- **Content First**: Typography and readability are paramount
- **Scannable**: Clear hierarchy, visual anchors, predictable patterns
- **Delightful**: Subtle animations, smooth transitions, attention to detail
- **Professional**: Clean, modern, trustworthy aesthetic

---

## Visual Design Improvements

### 1. Enhanced Color System

**Current State:**
- Basic primary/secondary/accent colors
- Good dark mode support
- Limited semantic colors

**Enhancements:**

```css
/* Add nuanced color scales for better hierarchy */
:root {
  /* Primary scale (for documentation, blue is trust) */
  --color-primary-50: #e3f2fd;
  --color-primary-100: #bbdefb;
  --color-primary-200: #90caf9;
  --color-primary-300: #64b5f6;
  --color-primary-400: #42a5f5;
  --color-primary-500: #2196f3;  /* Main primary */
  --color-primary-600: #1e88e5;
  --color-primary-700: #1976d2;
  --color-primary-800: #1565c0;
  --color-primary-900: #0d47a1;
  
  /* Semantic colors with better contrast */
  --color-success-bg: #d1f4e0;
  --color-success-border: #50c878;
  --color-success-text: #0f5132;
  
  --color-warning-bg: #fff4e5;
  --color-warning-border: #ff9800;
  --color-warning-text: #663c00;
  
  --color-error-bg: #fdecea;
  --color-error-border: #f44336;
  --color-error-text: #842029;
  
  --color-info-bg: #e3f2fd;
  --color-info-border: #2196f3;
  --color-info-text: #014361;
  
  /* Surface colors for cards and panels */
  --color-surface-1: var(--color-bg-secondary);
  --color-surface-2: var(--color-bg-tertiary);
  --color-surface-elevated: var(--color-bg-primary);
}
```

### 2. Refined Typography

**Enhancements:**

```css
/* Better font stack with modern system fonts */
:root {
  --font-sans: 
    -apple-system, BlinkMacSystemFont, 
    "Segoe UI Variable", "Segoe UI",
    system-ui, ui-sans-serif,
    "Inter", "Helvetica Neue", 
    Arial, sans-serif,
    "Apple Color Emoji", "Segoe UI Emoji";
    
  /* Improved prose styling */
  --prose-line-height: 1.75;
  --prose-paragraph-spacing: 1.25em;
  --prose-heading-spacing: 1.5em;
}

/* Better heading hierarchy */
.prose h1 { 
  font-size: clamp(2rem, 4vw, 2.5rem);
  font-weight: 700;
  line-height: 1.2;
  margin-top: 0;
  margin-bottom: 1rem;
  letter-spacing: -0.02em;
}

.prose h2 {
  font-size: clamp(1.5rem, 3vw, 1.875rem);
  font-weight: 600;
  line-height: 1.3;
  margin-top: 2em;
  margin-bottom: 0.75rem;
  letter-spacing: -0.01em;
  border-bottom: 1px solid var(--color-border-light);
  padding-bottom: 0.5rem;
}

.prose h3 {
  font-size: clamp(1.25rem, 2.5vw, 1.5rem);
  font-weight: 600;
  line-height: 1.4;
  margin-top: 1.6em;
  margin-bottom: 0.6rem;
}
```

### 3. Depth & Elevation

**Add subtle depth with shadows and borders:**

```css
/* Elevation system */
:root {
  --elevation-0: none;
  --elevation-1: 
    0 1px 2px 0 rgba(0, 0, 0, 0.05),
    0 1px 3px 0 rgba(0, 0, 0, 0.05);
  --elevation-2: 
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --elevation-3: 
    0 10px 15px -3px rgba(0, 0, 0, 0.1),
    0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --elevation-4: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

/* Apply to cards, modals, dropdowns */
.card {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--elevation-1);
  transition: box-shadow 0.2s ease;
}

.card:hover {
  box-shadow: var(--elevation-2);
}
```

### 4. Modern CSS Techniques

**Add polish with backdrop filters, gradients:**

```css
/* Glass morphism for header (subtle) */
header {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px) saturate(180%);
  border-bottom: 1px solid var(--color-border-light);
}

[data-theme="dark"] header {
  background: rgba(26, 26, 26, 0.85);
}

/* Gradient accents */
.hero-section {
  background: 
    linear-gradient(135deg, 
      var(--color-primary-500) 0%, 
      var(--color-primary-700) 100%
    );
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(circle at 30% 20%, 
      rgba(255, 255, 255, 0.1) 0%, 
      transparent 50%
    );
}

/* Smooth focus states */
:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
  border-radius: 4px;
}
```

---

## Layout & Navigation Enhancements

### 1. Three-Column Documentation Layout

**Add a persistent left sidebar for docs:**

```html
<!-- templates/doc.html (new layout) -->
{% extends "base.html" %}

{% block content %}
<div class="docs-layout">
  <!-- Left Sidebar: Navigation -->
  <aside class="docs-sidebar">
    <nav aria-label="Documentation navigation">
      <!-- Auto-generated from section structure -->
      {% include 'partials/docs-nav.html' %}
    </nav>
  </aside>
  
  <!-- Main Content -->
  <main class="docs-main">
    {% include 'partials/breadcrumbs.html' %}
    
    <article class="prose">
      <header>
        <h1>{{ page.title }}</h1>
        {% if page.metadata.description %}
        <p class="lead">{{ page.metadata.description }}</p>
        {% endif %}
      </header>
      
      {{ content | safe }}
      
      <!-- Page navigation at bottom -->
      {% include 'partials/page-navigation.html' %}
    </article>
  </main>
  
  <!-- Right Sidebar: TOC & Metadata -->
  <aside class="docs-toc">
    {% include 'partials/toc-sidebar.html' %}
  </aside>
</div>
{% endblock %}
```

**CSS:**

```css
/* Three-column layout */
.docs-layout {
  display: grid;
  grid-template-columns: 
    [sidebar-start] minmax(240px, 280px) 
    [content-start] minmax(0, 1fr) 
    [toc-start] minmax(200px, 240px) [end];
  gap: 2rem;
  max-width: 1600px;
  margin: 0 auto;
  padding: 2rem;
}

/* Responsive: tablet */
@media (max-width: 1280px) {
  .docs-layout {
    grid-template-columns: 
      [sidebar-start] minmax(240px, 260px) 
      [content-start] minmax(0, 1fr) [end];
  }
  
  .docs-toc {
    display: none; /* Hide on tablet */
  }
}

/* Responsive: mobile */
@media (max-width: 768px) {
  .docs-layout {
    grid-template-columns: 1fr;
  }
  
  .docs-sidebar {
    /* Convert to collapsible menu */
    position: fixed;
    top: 60px;
    left: 0;
    bottom: 0;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    background: var(--color-bg-primary);
    border-right: 1px solid var(--color-border);
    z-index: var(--z-sticky);
    overflow-y: auto;
  }
  
  .docs-sidebar.open {
    transform: translateX(0);
  }
}

/* Sticky sidebars */
.docs-sidebar,
.docs-toc {
  position: sticky;
  top: 80px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
```

### 2. Enhanced Sidebar Navigation

**Collapsible sections with active highlighting:**

```html
<!-- partials/docs-nav.html -->
<div class="docs-nav">
  {% for section in site.sections_recursive %}
  <div class="docs-nav-section">
    <button 
      class="docs-nav-toggle"
      aria-expanded="false"
      data-section="{{ section.url | slugify }}">
      <svg class="icon-chevron" width="16" height="16">
        <path d="M6 9l3 3 3-3"/>
      </svg>
      {{ section.title }}
    </button>
    
    <ul class="docs-nav-items">
      {% for page in section.regular_pages %}
      <li>
        <a 
          href="{{ url_for(page) }}"
          class="{% if page.url == current_page.url %}active{% endif %}">
          {{ page.title }}
        </a>
      </li>
      {% endfor %}
    </ul>
  </div>
  {% endfor %}
</div>
```

**CSS:**

```css
/* Sidebar navigation */
.docs-nav {
  font-size: 0.875rem;
}

.docs-nav-section {
  margin-bottom: 0.5rem;
}

.docs-nav-toggle {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: none;
  border: none;
  font-weight: 600;
  color: var(--color-text-primary);
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s ease;
}

.docs-nav-toggle:hover {
  background: var(--color-bg-hover);
}

.docs-nav-toggle .icon-chevron {
  margin-right: 0.5rem;
  transition: transform 0.2s ease;
  stroke: currentColor;
  fill: none;
}

.docs-nav-toggle[aria-expanded="true"] .icon-chevron {
  transform: rotate(180deg);
}

.docs-nav-items {
  list-style: none;
  padding-left: 1.5rem;
  margin: 0;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.docs-nav-toggle[aria-expanded="true"] + .docs-nav-items {
  max-height: 1000px; /* Large enough for any section */
}

.docs-nav-items a {
  display: block;
  padding: 0.375rem 0.75rem;
  color: var(--color-text-secondary);
  text-decoration: none;
  border-radius: 4px;
  border-left: 2px solid transparent;
  margin-left: -2px;
  transition: all 0.15s ease;
}

.docs-nav-items a:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.docs-nav-items a.active {
  color: var(--color-primary);
  background: var(--color-primary-50);
  border-left-color: var(--color-primary);
  font-weight: 500;
}

[data-theme="dark"] .docs-nav-items a.active {
  background: rgba(33, 150, 243, 0.1);
}
```

### 3. Improved TOC Sidebar

**Enhanced table of contents with progress indicator:**

```html
<!-- partials/toc-sidebar.html -->
<div class="toc-sidebar">
  <div class="toc-header">
    <h3>On This Page</h3>
  </div>
  
  <nav class="toc-nav" aria-label="Table of contents">
    <!-- Progress bar -->
    <div class="toc-progress">
      <div class="toc-progress-bar" style="height: 0%"></div>
    </div>
    
    <!-- TOC items -->
    <ul class="toc-items">
      {% for item in toc_items %}
      <li class="toc-item toc-level-{{ item.level }}">
        <a href="#{{ item.id }}" data-toc-item>
          {{ item.title }}
        </a>
      </li>
      {% endfor %}
    </ul>
  </nav>
  
  <!-- Metadata section -->
  <div class="page-metadata">
    {% if page.date %}
    <div class="metadata-item">
      <span class="metadata-label">Last updated</span>
      <time datetime="{{ page.date | date_iso }}">
        {{ page.date | dateformat('%B %d, %Y') }}
      </time>
    </div>
    {% endif %}
    
    {% if page.metadata.edit_url %}
    <a href="{{ page.metadata.edit_url }}" class="edit-link">
      <svg width="16" height="16" fill="currentColor">
        <path d="M11 4l3 3-8 8H3v-3l8-8z"/>
      </svg>
      Edit this page
    </a>
    {% endif %}
  </div>
</div>
```

**JavaScript for scroll tracking:**

```javascript
// assets/js/toc-scroll.js
(function() {
  const tocItems = document.querySelectorAll('[data-toc-item]');
  const progressBar = document.querySelector('.toc-progress-bar');
  
  if (!tocItems.length) return;
  
  // Get all heading targets
  const headings = Array.from(tocItems).map(item => {
    const id = item.getAttribute('href').slice(1);
    return document.getElementById(id);
  }).filter(Boolean);
  
  // Update active item and progress on scroll
  function updateActive() {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = (scrollTop / docHeight) * 100;
    
    // Update progress bar
    if (progressBar) {
      progressBar.style.height = `${progress}%`;
    }
    
    // Find active heading
    let activeIndex = 0;
    for (let i = headings.length - 1; i >= 0; i--) {
      const heading = headings[i];
      if (heading.offsetTop <= scrollTop + 100) {
        activeIndex = i;
        break;
      }
    }
    
    // Update active class
    tocItems.forEach((item, index) => {
      item.classList.toggle('active', index === activeIndex);
    });
  }
  
  // Smooth scroll to heading
  tocItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const id = item.getAttribute('href').slice(1);
      const target = document.getElementById(id);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        history.pushState(null, '', `#${id}`);
      }
    });
  });
  
  // Throttled scroll handler
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateActive();
        ticking = false;
      });
      ticking = true;
    }
  });
  
  // Initial update
  updateActive();
})();
```

---

## Content Experience Upgrades

### 1. Enhanced Code Blocks

**Add copy button and language label:**

```html
<!-- Update rendering/renderer.py to wrap code blocks -->
<div class="code-block">
  <div class="code-header">
    <span class="code-language">{{ language }}</span>
    <button class="code-copy" aria-label="Copy code">
      <svg class="icon-copy" width="16" height="16">
        <path d="M8 2a1 1 0 011 1v1h3a2 2 0 012 2v8a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h3V3a1 1 0 011-1z"/>
      </svg>
      <svg class="icon-check" width="16" height="16" style="display:none">
        <path d="M5 13l-3-3 1-1 2 2 6-6 1 1z"/>
      </svg>
    </button>
  </div>
  <pre><code class="language-{{ language }}">{{ code }}</code></pre>
</div>
```

**JavaScript:**

```javascript
// assets/js/code-copy.js
(function() {
  document.querySelectorAll('.code-copy').forEach(button => {
    button.addEventListener('click', async () => {
      const codeBlock = button.closest('.code-block').querySelector('code');
      const code = codeBlock.textContent;
      
      try {
        await navigator.clipboard.writeText(code);
        
        // Visual feedback
        const iconCopy = button.querySelector('.icon-copy');
        const iconCheck = button.querySelector('.icon-check');
        iconCopy.style.display = 'none';
        iconCheck.style.display = 'block';
        button.classList.add('copied');
        
        setTimeout(() => {
          iconCopy.style.display = 'block';
          iconCheck.style.display = 'none';
          button.classList.remove('copied');
        }, 2000);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    });
  });
})();
```

**CSS:**

```css
.code-block {
  position: relative;
  margin: 1.5rem 0;
  border-radius: 8px;
  background: var(--color-bg-code);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: var(--color-bg-tertiary);
  border-bottom: 1px solid var(--color-border);
  font-size: 0.75rem;
}

.code-language {
  text-transform: uppercase;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.05em;
}

.code-copy {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.code-copy:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.code-copy.copied {
  background: var(--color-success-bg);
  border-color: var(--color-success-border);
  color: var(--color-success-text);
}

.code-block pre {
  margin: 0;
  padding: 1rem;
  overflow-x: auto;
}

.code-block code {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  line-height: 1.6;
}
```

### 2. Enhanced Callouts/Admonitions

**Improve visual design with icons:**

```css
/* Enhanced admonitions */
.admonition {
  margin: 1.5rem 0;
  padding: 1rem 1.25rem;
  border-left: 4px solid;
  border-radius: 0 8px 8px 0;
  background: var(--admonition-bg);
  border-color: var(--admonition-border);
  box-shadow: var(--elevation-1);
}

.admonition-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--admonition-title-color);
}

.admonition-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

/* Note (blue) */
.admonition.note {
  --admonition-bg: var(--color-info-bg);
  --admonition-border: var(--color-info-border);
  --admonition-title-color: var(--color-info-text);
}

/* Tip (green) */
.admonition.tip {
  --admonition-bg: var(--color-success-bg);
  --admonition-border: var(--color-success-border);
  --admonition-title-color: var(--color-success-text);
}

/* Warning (orange) */
.admonition.warning {
  --admonition-bg: var(--color-warning-bg);
  --admonition-border: var(--color-warning-border);
  --admonition-title-color: var(--color-warning-text);
}

/* Danger (red) */
.admonition.danger {
  --admonition-bg: var(--color-error-bg);
  --admonition-border: var(--color-error-border);
  --admonition-title-color: var(--color-error-text);
}

/* Add subtle animation on scroll */
@media (prefers-reduced-motion: no-preference) {
  .admonition {
    animation: fadeInUp 0.4s ease-out;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### 3. Content Cards

**For feature grids and quick links:**

```html
<!-- partials/content-card.html -->
<div class="content-card">
  {% if icon %}
  <div class="card-icon">
    {{ icon | safe }}
  </div>
  {% endif %}
  
  <h3 class="card-title">
    {% if url %}
    <a href="{{ url }}">{{ title }}</a>
    {% else %}
    {{ title }}
    {% endif %}
  </h3>
  
  {% if description %}
  <p class="card-description">{{ description }}</p>
  {% endif %}
  
  {% if cta %}
  <a href="{{ url }}" class="card-cta">
    {{ cta }} →
  </a>
  {% endif %}
</div>
```

```css
/* Content cards */
.content-card {
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  transition: all 0.2s ease;
  height: 100%;
}

.content-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--elevation-2);
  transform: translateY(-2px);
}

.card-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 1rem;
  color: var(--color-primary);
}

.card-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.card-title a {
  color: var(--color-text-primary);
  text-decoration: none;
}

.card-title a:hover {
  color: var(--color-primary);
}

.card-description {
  flex: 1;
  margin: 0 0 1rem 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.card-cta {
  display: inline-flex;
  align-items: center;
  color: var(--color-primary);
  font-weight: 500;
  text-decoration: none;
  transition: gap 0.2s ease;
}

.card-cta:hover {
  gap: 0.25rem;
}

/* Grid layout for cards */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin: 2rem 0;
}
```

### 4. Search Placeholder

**While we don't add search now, prepare the UI:**

```html
<!-- In header -->
<div class="search-trigger">
  <button class="search-button" aria-label="Search documentation">
    <svg width="20" height="20" fill="none" stroke="currentColor">
      <circle cx="10" cy="10" r="7"/>
      <path d="M15 15l5 5"/>
    </svg>
    <span>Search...</span>
    <kbd class="search-kbd">⌘K</kbd>
  </button>
</div>
```

```css
.search-trigger {
  margin-left: auto;
  margin-right: 1rem;
}

.search-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 200px;
}

.search-button:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-primary);
}

.search-kbd {
  margin-left: auto;
  padding: 0.125rem 0.375rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
```

---

## Interactive Elements

### 1. Smooth Scrolling & Anchor Links

```javascript
// assets/js/smooth-scroll.js
(function() {
  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#') return;
      
      e.preventDefault();
      const target = document.querySelector(href);
      
      if (target) {
        const offsetTop = target.offsetTop - 80; // Account for fixed header
        window.scrollTo({
          top: offsetTop,
          behavior: 'smooth'
        });
        
        // Update URL without jumping
        history.pushState(null, '', href);
      }
    });
  });
})();
```

### 2. Back to Top Button

```html
<!-- Add to base.html before </body> -->
<button class="back-to-top" aria-label="Back to top" title="Back to top">
  <svg width="20" height="20" fill="none" stroke="currentColor">
    <path d="M5 15l5-5 5 5"/>
    <path d="M5 10l5-5 5 5"/>
  </svg>
</button>
```

```javascript
// assets/js/back-to-top.js
(function() {
  const button = document.querySelector('.back-to-top');
  if (!button) return;
  
  // Show/hide based on scroll position
  window.addEventListener('scroll', () => {
    if (window.scrollY > 400) {
      button.classList.add('visible');
    } else {
      button.classList.remove('visible');
    }
  });
  
  // Scroll to top on click
  button.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();
```

```css
.back-to-top {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  width: 48px;
  height: 48px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 50%;
  box-shadow: var(--elevation-3);
  cursor: pointer;
  opacity: 0;
  visibility: hidden;
  transform: translateY(20px);
  transition: all 0.3s ease;
  z-index: var(--z-fixed);
}

.back-to-top.visible {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.back-to-top:hover {
  background: var(--color-primary-dark);
  box-shadow: var(--elevation-4);
  transform: translateY(-2px);
}

.back-to-top:active {
  transform: translateY(0);
}
```

### 3. Keyboard Navigation

```javascript
// assets/js/keyboard-nav.js
(function() {
  // Global keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Cmd/Ctrl + K: Focus search (when implemented)
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      const searchButton = document.querySelector('.search-button');
      if (searchButton) searchButton.click();
    }
    
    // Alt + Left/Right: Previous/Next page
    if (e.altKey && e.key === 'ArrowLeft') {
      const prevLink = document.querySelector('.page-nav-prev');
      if (prevLink) prevLink.click();
    }
    if (e.altKey && e.key === 'ArrowRight') {
      const nextLink = document.querySelector('.page-nav-next');
      if (nextLink) nextLink.click();
    }
    
    // Escape: Close mobile nav
    if (e.key === 'Escape') {
      const mobileNav = document.querySelector('.mobile-nav');
      if (mobileNav && mobileNav.classList.contains('open')) {
        mobileNav.classList.remove('open');
      }
    }
  });
})();
```

---

## Accessibility & Performance

### 1. Accessibility Enhancements

**Skip links:**

```html
<!-- Already in base.html, but enhance styling -->
<a href="#main-content" class="skip-link">Skip to main content</a>
<a href="#docs-sidebar" class="skip-link">Skip to navigation</a>
```

```css
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  padding: 0.75rem 1rem;
  background: var(--color-primary);
  color: white;
  text-decoration: none;
  font-weight: 600;
  z-index: var(--z-modal);
  transition: top 0.2s ease;
}

.skip-link:focus {
  top: 0;
  outline: 2px solid white;
  outline-offset: -2px;
}
```

**ARIA labels and landmarks:**

```html
<!-- Ensure all navigation has proper labels -->
<nav aria-label="Primary navigation">...</nav>
<nav aria-label="Documentation navigation">...</nav>
<nav aria-label="Table of contents">...</nav>
<nav aria-label="Page navigation">...</nav>
```

### 2. Performance Optimizations

**Critical CSS:**

```html
<!-- In base.html <head> -->
<style>
  /* Critical CSS: Above-the-fold styles */
  :root { 
    --color-bg-primary: #ffffff;
    --color-text-primary: #212529;
    /* ... essential variables only ... */
  }
  
  body {
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.5;
    color: var(--color-text-primary);
    background: var(--color-bg-primary);
  }
  
  header {
    position: sticky;
    top: 0;
    z-index: 1000;
  }
  
  /* ... minimal layout styles ... */
</style>

<!-- Load full CSS asynchronously -->
<link rel="preload" href="{{ asset_url('css/style.css') }}" as="style">
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}" media="print" onload="this.media='all'">
```

**JavaScript loading:**

```html
<!-- Defer non-critical scripts -->
<script src="{{ asset_url('js/theme-toggle.js') }}"></script>
<script defer src="{{ asset_url('js/mobile-nav.js') }}"></script>
<script defer src="{{ asset_url('js/tabs.js') }}"></script>
<script defer src="{{ asset_url('js/smooth-scroll.js') }}"></script>
<script defer src="{{ asset_url('js/code-copy.js') }}"></script>
<script defer src="{{ asset_url('js/toc-scroll.js') }}"></script>
<script defer src="{{ asset_url('js/back-to-top.js') }}"></script>
<script defer src="{{ asset_url('js/keyboard-nav.js') }}"></script>
```

**Image optimization (use template functions):**

```html
<!-- Use responsive images -->
<img 
  src="{{ image_url(page.metadata.image, width=800) }}"
  srcset="{{ image_srcset(page.metadata.image, [400, 800, 1200]) }}"
  sizes="(max-width: 768px) 100vw, 800px"
  alt="{{ image_alt(page.metadata.image) | default(page.title) }}"
  loading="lazy"
  width="800"
  height="450">
```

---

## Implementation Roadmap

### Phase 1: Visual Polish (Week 1)

**Priority: High | Effort: Low | Impact: High**

- [ ] Enhanced color system with scales
- [ ] Refined typography and hierarchy
- [ ] Elevation system (shadows)
- [ ] Modern CSS techniques (backdrop-filter, gradients)
- [ ] Improved focus states
- [ ] Enhanced admonitions with icons
- [ ] Code block styling improvements

**Deliverables:**
- Updated `base/variables.css`
- Enhanced `components/admonitions.css`
- Enhanced `components/code.css`
- New `components/cards.css` improvements

### Phase 2: Layout & Navigation (Week 2)

**Priority: High | Effort: Medium | Impact: High**

- [ ] Three-column documentation layout
- [ ] New `doc.html` template
- [ ] Persistent left sidebar navigation
- [ ] Collapsible nav sections
- [ ] Enhanced TOC sidebar
- [ ] TOC scroll progress
- [ ] Page metadata section
- [ ] Mobile sidebar improvements

**Deliverables:**
- New `templates/doc.html`
- New `partials/docs-nav.html`
- Enhanced `partials/toc-sidebar.html`
- Updated `layouts/grid.css`
- New `components/docs-layout.css`
- New `js/sidebar-toggle.js`

### Phase 3: Content Experience (Week 3)

**Priority: Medium | Effort: Medium | Impact: High**

- [ ] Code block copy buttons
- [ ] Language labels on code blocks
- [ ] Enhanced callout designs
- [ ] Content card component
- [ ] Search UI placeholder
- [ ] Better page navigation styling
- [ ] Breadcrumb improvements

**Deliverables:**
- Updated code block rendering
- New `js/code-copy.js`
- Enhanced `partials/content-card.html`
- Updated `components/navigation.css`
- Search placeholder in header

### Phase 4: Interactive Elements (Week 4)

**Priority: Medium | Effort: Low | Impact: Medium**

- [ ] Smooth scrolling
- [ ] Back to top button
- [ ] Keyboard navigation shortcuts
- [ ] TOC active highlighting
- [ ] Hover states polish
- [ ] Micro-interactions

**Deliverables:**
- New `js/smooth-scroll.js`
- New `js/back-to-top.js`
- New `js/keyboard-nav.js`
- Enhanced `js/toc-scroll.js`

### Phase 5: Accessibility & Performance (Week 5)

**Priority: High | Effort: Low | Impact: Medium**

- [ ] Enhanced skip links
- [ ] ARIA labels audit
- [ ] Keyboard navigation testing
- [ ] Screen reader testing
- [ ] Critical CSS extraction
- [ ] JavaScript loading optimization
- [ ] Image lazy loading
- [ ] Performance audit

**Deliverables:**
- Accessibility audit report
- Performance benchmark report
- Critical CSS inline
- Optimized asset loading

### Phase 6: Documentation & Examples (Week 6)

**Priority: Medium | Effort: Medium | Impact: Medium**

- [ ] Theme documentation
- [ ] Layout examples
- [ ] Component showcase
- [ ] Migration guide from default to enhanced
- [ ] Customization guide
- [ ] Best practices guide

**Deliverables:**
- Theme documentation site
- Example templates
- Customization guide
- Migration scripts

---

## Success Metrics

### User Experience Metrics

1. **Visual Appeal**
   - Modern, professional aesthetic
   - Consistent with leading documentation platforms
   - Good color contrast (WCAG AA minimum)

2. **Navigation Efficiency**
   - Users can find content within 3 clicks
   - Clear visual hierarchy
   - Active state always visible

3. **Content Readability**
   - Optimal line length (65-75 characters)
   - Good line height (1.6-1.8 for body text)
   - Scannable headings

4. **Interactive Feedback**
   - All interactions have visual feedback
   - Smooth transitions (where appropriate)
   - Loading states for async actions

### Technical Metrics

1. **Performance**
   - First Contentful Paint < 1s
   - Time to Interactive < 2s
   - Lighthouse score > 95

2. **Accessibility**
   - WCAG 2.1 AA compliance
   - Keyboard navigation support
   - Screen reader compatible
   - Color contrast ratios pass

3. **Bundle Size**
   - CSS < 50KB (gzipped)
   - JavaScript < 20KB (gzipped)
   - No layout shift (CLS < 0.1)

---

## Conclusion

This plan provides a comprehensive roadmap to elevate Bengal's theme to compete with modern documentation platforms like Mintlify, Docusaurus, and GitBook. The key advantages of this approach:

1. **No New Dependencies**: Everything uses CSS, HTML, and vanilla JavaScript
2. **Progressive Enhancement**: Works without JavaScript, better with it
3. **Performance First**: Maintains Bengal's fast build times and lightweight output
4. **Accessible**: WCAG 2.1 AA compliant from the start
5. **Flexible**: Users can override any component
6. **Maintainable**: Clean, modular code that's easy to understand

The phased implementation allows for iterative improvements while maintaining a working theme at each stage. Each phase delivers tangible value and can be deployed independently.

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize phases** based on current needs
3. **Create issues** for each phase in GitHub
4. **Start with Phase 1** (Visual Polish) for quick wins
5. **Iterate based on feedback** from actual users

---

## References

- [Mintlify Documentation](https://www.mintlify.com/docs)
- [Docusaurus](https://docusaurus.io/)
- [Nextra](https://nextra.site/)
- [GitBook](https://www.gitbook.com/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Web.dev Performance](https://web.dev/performance/)
- [MDN Web Docs: Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)

