# Bengal SSG - Mature Default Theme Planning

## Current State Analysis

### What We Have Now ✅
- Basic HTML structure (base.html)
- Minimal templates (page, post, index)
- Simple header/footer
- No CSS assets
- No JavaScript
- No partials/components
- No responsive design
- No accessibility features
- No theme configuration

### What's Missing ❌
- Complete CSS framework
- JavaScript functionality
- Component library
- Responsive design
- Accessibility (a11y)
- SEO optimization
- Performance features
- Dark mode support
- Typography system
- Color system
- Layout options
- Navigation components
- Search integration
- Code syntax highlighting
- Table of contents
- Breadcrumbs
- Pagination
- Archive pages
- Tag/category pages
- Social sharing
- Print styles

---

## Mature Theme Requirements

### 1. Visual Design System

#### Color Palette
```css
/* Primary Colors */
--primary: #3498db      /* Links, CTAs */
--secondary: #2ecc71    /* Success, highlights */
--accent: #e74c3c       /* Warnings, errors */

/* Neutral Colors */
--bg-primary: #ffffff
--bg-secondary: #f8f9fa
--bg-tertiary: #e9ecef
--text-primary: #212529
--text-secondary: #6c757d
--text-muted: #adb5bd

/* Dark Mode */
--dark-bg-primary: #1a1a1a
--dark-bg-secondary: #2d2d2d
--dark-text-primary: #f8f9fa
--dark-text-secondary: #adb5bd

/* Semantic Colors */
--success: #28a745
--warning: #ffc107
--error: #dc3545
--info: #17a2b8
```

#### Typography Scale
```css
/* Font Families */
--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-serif: Georgia, 'Times New Roman', serif;
--font-mono: 'SF Mono', Monaco, 'Cascadia Code', monospace;

/* Font Sizes (fluid typography) */
--text-xs: clamp(0.75rem, 0.7rem + 0.2vw, 0.8rem);
--text-sm: clamp(0.875rem, 0.8rem + 0.3vw, 0.95rem);
--text-base: clamp(1rem, 0.95rem + 0.3vw, 1.125rem);
--text-lg: clamp(1.125rem, 1rem + 0.5vw, 1.5rem);
--text-xl: clamp(1.25rem, 1.1rem + 0.7vw, 1.875rem);
--text-2xl: clamp(1.5rem, 1.3rem + 1vw, 2.25rem);
--text-3xl: clamp(1.875rem, 1.5rem + 1.5vw, 3rem);
--text-4xl: clamp(2.25rem, 1.8rem + 2vw, 3.75rem);

/* Line Heights */
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.75;

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

#### Spacing System
```css
/* Consistent spacing scale */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.5rem;    /* 24px */
--space-6: 2rem;      /* 32px */
--space-8: 3rem;      /* 48px */
--space-10: 4rem;     /* 64px */
--space-12: 6rem;     /* 96px */
--space-16: 8rem;     /* 128px */
```

### 2. Component Library

#### Navigation Components
```
partials/
├── nav-main.html         # Primary navigation
├── nav-mobile.html       # Mobile hamburger menu
├── nav-breadcrumbs.html  # Breadcrumb navigation
├── nav-pagination.html   # Page navigation
├── nav-toc.html          # Table of contents
└── nav-sidebar.html      # Sidebar navigation
```

#### Content Components
```
partials/
├── article-card.html     # Blog post preview card
├── article-meta.html     # Author, date, reading time
├── article-tags.html     # Tag list
├── article-share.html    # Social sharing buttons
├── article-related.html  # Related posts
├── article-comments.html # Comments section placeholder
└── article-author.html   # Author bio box
```

#### Layout Components
```
partials/
├── header.html           # Site header
├── footer.html           # Site footer
├── sidebar.html          # Sidebar with widgets
├── hero.html             # Hero section
├── cta.html              # Call-to-action blocks
└── section-header.html   # Section headers
```

#### Utility Components
```
partials/
├── alert.html            # Alert/notification boxes
├── code-block.html       # Syntax highlighted code
├── image.html            # Responsive images
├── video.html            # Video embeds
├── search.html           # Search box
└── theme-toggle.html     # Dark/light mode toggle
```

### 3. Template Types Needed

#### Core Templates
- ✅ `base.html` - Base layout (enhance existing)
- ✅ `index.html` - Homepage (enhance existing)
- ✅ `page.html` - Single page (enhance existing)
- ✅ `post.html` - Blog post (enhance existing)

#### Archive Templates
- ❌ `archive.html` - Blog archive/listing
- ❌ `archive-year.html` - Posts by year
- ❌ `archive-month.html` - Posts by month
- ❌ `tag.html` - Posts by tag
- ❌ `category.html` - Posts by category
- ❌ `author.html` - Posts by author

#### Special Templates
- ❌ `search.html` - Search results page
- ❌ `404.html` - Error page
- ❌ `sitemap-html.html` - Human-readable sitemap
- ❌ `portfolio.html` - Portfolio/project showcase
- ❌ `landing.html` - Landing page template
- ❌ `documentation.html` - Documentation layout

### 4. CSS Architecture

```
assets/css/
├── style.css              # Main stylesheet (imports all)
├── base/
│   ├── reset.css         # CSS reset/normalize
│   ├── variables.css     # CSS custom properties
│   ├── typography.css    # Font styles
│   └── utilities.css     # Utility classes
├── components/
│   ├── buttons.css       # Button styles
│   ├── cards.css         # Card components
│   ├── forms.css         # Form elements
│   ├── navigation.css    # Navigation styles
│   ├── tables.css        # Table styles
│   ├── code.css          # Code blocks
│   ├── alerts.css        # Alert/notification boxes
│   └── modals.css        # Modal dialogs
├── layouts/
│   ├── header.css        # Header layout
│   ├── footer.css        # Footer layout
│   ├── sidebar.css       # Sidebar layout
│   ├── grid.css          # Grid system
│   └── containers.css    # Container widths
├── pages/
│   ├── home.css          # Homepage specific
│   ├── post.css          # Blog post specific
│   ├── archive.css       # Archive pages
│   └── docs.css          # Documentation specific
├── themes/
│   ├── light.css         # Light mode
│   └── dark.css          # Dark mode
└── vendor/
    └── highlight.css     # Syntax highlighting theme
```

### 5. JavaScript Features

```
assets/js/
├── main.js               # Main entry point
├── modules/
│   ├── theme-toggle.js   # Dark/light mode switching
│   ├── mobile-nav.js     # Mobile menu
│   ├── search.js         # Client-side search
│   ├── toc.js            # Table of contents
│   ├── smooth-scroll.js  # Smooth scrolling
│   ├── copy-code.js      # Copy code button
│   ├── external-links.js # External link handling
│   ├── image-zoom.js     # Image lightbox
│   └── lazy-load.js      # Lazy load images
└── vendor/
    └── search-index.js   # Search library (lunr.js?)
```

### 6. Responsive Design

#### Breakpoint System
```css
/* Mobile First */
--breakpoint-sm: 640px;   /* Small tablets */
--breakpoint-md: 768px;   /* Tablets */
--breakpoint-lg: 1024px;  /* Laptops */
--breakpoint-xl: 1280px;  /* Desktops */
--breakpoint-2xl: 1536px; /* Large desktops */
```

#### Layout Patterns
1. **Single Column** (mobile)
   - Stack all content vertically
   - Full-width containers
   - Hamburger menu

2. **Two Column** (tablet)
   - Main content + sidebar
   - Collapsible sidebar
   - Tablet navigation

3. **Three Column** (desktop)
   - Left sidebar (nav)
   - Main content
   - Right sidebar (TOC/widgets)
   - Full navigation

### 7. Accessibility (a11y) Features

#### Required Elements
- ✅ Semantic HTML5 elements
- ✅ ARIA labels and roles
- ✅ Keyboard navigation
- ✅ Focus indicators
- ✅ Skip to content link
- ✅ Alt text for images
- ✅ Form labels
- ✅ Contrast ratios (WCAG AA)
- ✅ Screen reader friendly
- ✅ Reduced motion support

#### Implementation Checklist
```html
<!-- Skip to main content -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<!-- Proper heading hierarchy -->
<h1>Page Title</h1>
<h2>Section</h2>
<h3>Subsection</h3>

<!-- ARIA landmarks -->
<header role="banner">
<nav role="navigation" aria-label="Main">
<main id="main-content" role="main">
<aside role="complementary">
<footer role="contentinfo">

<!-- Focus management -->
<button aria-label="Open menu" aria-expanded="false">

<!-- Reduced motion -->
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; }
}
```

### 8. SEO Optimization

#### Meta Tags Template
```html
<!-- Essential Meta Tags -->
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{{ page.description }}">
<meta name="keywords" content="{{ page.tags | join(', ') }}">
<meta name="author" content="{{ page.author }}">

<!-- Open Graph / Facebook -->
<meta property="og:type" content="article">
<meta property="og:url" content="{{ page.url }}">
<meta property="og:title" content="{{ page.title }}">
<meta property="og:description" content="{{ page.description }}">
<meta property="og:image" content="{{ page.image }}">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:url" content="{{ page.url }}">
<meta name="twitter:title" content="{{ page.title }}">
<meta name="twitter:description" content="{{ page.description }}">
<meta name="twitter:image" content="{{ page.image }}">

<!-- Canonical URL -->
<link rel="canonical" href="{{ page.canonical_url }}">

<!-- RSS Feed -->
<link rel="alternate" type="application/rss+xml" 
      title="{{ site.title }}" 
      href="/rss.xml">

<!-- Favicon -->
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">

<!-- Schema.org Structured Data -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{{ page.title }}",
  "datePublished": "{{ page.date }}",
  "author": { "@type": "Person", "name": "{{ page.author }}" }
}
</script>
```

### 9. Performance Features

#### CSS Optimization
- Critical CSS inlining
- CSS minification
- Unused CSS removal
- CSS custom properties for theming

#### JavaScript Optimization
- Module bundling
- Code splitting
- Lazy loading
- Defer/async loading

#### Image Optimization
- Responsive images (srcset)
- WebP format support
- Lazy loading
- Image compression
- Proper sizing

#### Font Optimization
- Font subsetting
- WOFF2 format
- Font-display: swap
- System font fallbacks

#### Loading Performance
```html
<!-- Preload critical assets -->
<link rel="preload" href="/css/critical.css" as="style">
<link rel="preload" href="/fonts/main.woff2" as="font" crossorigin>

<!-- DNS prefetch for external resources -->
<link rel="dns-prefetch" href="https://fonts.googleapis.com">

<!-- Resource hints -->
<link rel="preconnect" href="https://cdn.example.com">
```

### 10. Theme Configuration

#### theme.toml
```toml
[theme]
name = "Bengal Default"
version = "1.0.0"
author = "Bengal Contributors"
license = "MIT"

[features]
dark_mode = true
search = true
toc = true
comments = false
analytics = false

[navigation]
show_breadcrumbs = true
show_pagination = true
show_related_posts = true
sticky_header = true

[sidebar]
enabled = true
position = "right"  # left, right, or both
show_toc = true
show_tags = true
show_recent = true

[footer]
show_social = true
show_copyright = true
show_powered_by = true

[colors]
primary = "#3498db"
secondary = "#2ecc71"
accent = "#e74c3c"

[typography]
body_font = "system-ui"
heading_font = "system-ui"
code_font = "monospace"
base_size = "16px"
```

### 11. Jinja2 Macros & Filters

#### Custom Macros
```jinja2
{# macros/components.html #}

{% macro button(text, url, style="primary") %}
<a href="{{ url }}" class="btn btn-{{ style }}">{{ text }}</a>
{% endmacro %}

{% macro card(title, content, image=none, url=none) %}
<div class="card">
  {% if image %}
  <img src="{{ image }}" alt="{{ title }}">
  {% endif %}
  <div class="card-body">
    <h3>{{ title }}</h3>
    <p>{{ content }}</p>
    {% if url %}
    <a href="{{ url }}">Read more →</a>
    {% endif %}
  </div>
</div>
{% endmacro %}

{% macro tag_list(tags) %}
<div class="tags">
  {% for tag in tags %}
  <a href="/tags/{{ tag | slugify }}/" class="tag">{{ tag }}</a>
  {% endfor %}
</div>
{% endmacro %}

{% macro reading_time(content) %}
{% set words = content | wordcount %}
{% set minutes = (words / 200) | round(0, 'ceil') %}
<span class="reading-time">{{ minutes }} min read</span>
{% endmacro %}
```

#### Custom Filters
```python
# In template_engine.py

def filter_reading_time(content):
    """Calculate reading time in minutes."""
    words = len(content.split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"

def filter_excerpt(content, length=150):
    """Generate excerpt from content."""
    if len(content) <= length:
        return content
    return content[:length].rsplit(' ', 1)[0] + '...'

def filter_toc(content):
    """Generate table of contents from headings."""
    # Parse headings and create TOC
    pass

env.filters['reading_time'] = filter_reading_time
env.filters['excerpt'] = filter_excerpt
env.filters['toc'] = filter_toc
```

### 12. Code Syntax Highlighting

#### Integration Options
1. **Pygments** (server-side, current)
   - Fast, no client-side JS
   - Many themes available
   - Good for static content

2. **Highlight.js** (client-side)
   - 193 languages
   - Automatic language detection
   - Smaller bundle than Prism

3. **Prism.js** (client-side)
   - 300+ languages
   - Plugin system
   - Line numbers, diff highlighting

#### Recommended: Hybrid Approach
```python
# Server-side highlighting with Pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

# Add copy button via JavaScript
# Add line numbers via CSS
```

### 13. Search Implementation

#### Client-Side Search (Recommended for Static)
```javascript
// Using Lunr.js or Fuse.js
// Build search index at build time
// Load index on search page
// No server required

// search.js
import lunr from 'lunr';

const searchIndex = lunr(function() {
  this.ref('id');
  this.field('title');
  this.field('content');
  this.field('tags');
  
  documents.forEach(doc => this.add(doc));
});

function search(query) {
  return searchIndex.search(query);
}
```

#### Build-Time Index Generation
```python
# In postprocess/search.py
class SearchIndexGenerator:
    def generate(self, site):
        index = []
        for page in site.pages:
            index.append({
                'id': page.slug,
                'title': page.title,
                'content': page.content,
                'tags': page.tags,
                'url': page.url
            })
        
        # Write to search-index.json
        output = site.output_dir / 'search-index.json'
        output.write_text(json.dumps(index))
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up CSS architecture
- [ ] Create design system (colors, typography, spacing)
- [ ] Build base styles and reset
- [ ] Create responsive grid system
- [ ] Implement dark mode toggle

### Phase 2: Core Components (Week 2)
- [ ] Enhanced header with navigation
- [ ] Footer with social links
- [ ] Article cards and meta
- [ ] Sidebar layout
- [ ] Mobile navigation
- [ ] Breadcrumbs
- [ ] Pagination

### Phase 3: Content Templates (Week 3)
- [ ] Enhanced post template
- [ ] Archive/listing templates
- [ ] Tag/category pages
- [ ] Search page
- [ ] 404 page
- [ ] Documentation layout

### Phase 4: JavaScript Features (Week 4)
- [ ] Theme toggle (dark/light)
- [ ] Mobile menu interactions
- [ ] Search functionality
- [ ] Copy code buttons
- [ ] Smooth scrolling
- [ ] Table of contents
- [ ] Lazy loading images

### Phase 5: Polish & Performance (Week 5)
- [ ] Accessibility audit
- [ ] Performance optimization
- [ ] SEO enhancements
- [ ] Print styles
- [ ] Browser testing
- [ ] Documentation

---

## File Structure (Complete Theme)

```
themes/default/
├── theme.toml                 # Theme configuration
├── README.md                  # Theme documentation
│
├── templates/
│   ├── base.html             # Base layout
│   ├── index.html            # Homepage
│   ├── page.html             # Single page
│   ├── post.html             # Blog post
│   ├── archive.html          # Archive listing
│   ├── tag.html              # Tag page
│   ├── search.html           # Search page
│   ├── 404.html              # Error page
│   │
│   ├── partials/
│   │   ├── head.html         # <head> content
│   │   ├── header.html       # Site header
│   │   ├── footer.html       # Site footer
│   │   ├── nav-main.html     # Main navigation
│   │   ├── nav-mobile.html   # Mobile menu
│   │   ├── sidebar.html      # Sidebar
│   │   ├── toc.html          # Table of contents
│   │   ├── breadcrumbs.html  # Breadcrumb nav
│   │   ├── pagination.html   # Page navigation
│   │   ├── article-card.html # Post preview
│   │   ├── article-meta.html # Post metadata
│   │   ├── tags.html         # Tag list
│   │   └── search-box.html   # Search input
│   │
│   └── macros/
│       ├── components.html   # Reusable components
│       ├── seo.html          # SEO meta tags
│       └── icons.html        # SVG icons
│
├── assets/
│   ├── css/
│   │   ├── style.css         # Main stylesheet
│   │   ├── base/
│   │   │   ├── reset.css
│   │   │   ├── variables.css
│   │   │   ├── typography.css
│   │   │   └── utilities.css
│   │   ├── components/
│   │   │   ├── buttons.css
│   │   │   ├── cards.css
│   │   │   ├── navigation.css
│   │   │   ├── code.css
│   │   │   └── ...
│   │   ├── layouts/
│   │   │   ├── header.css
│   │   │   ├── footer.css
│   │   │   ├── sidebar.css
│   │   │   └── grid.css
│   │   └── themes/
│   │       ├── light.css
│   │       └── dark.css
│   │
│   ├── js/
│   │   ├── main.js
│   │   └── modules/
│   │       ├── theme-toggle.js
│   │       ├── mobile-nav.js
│   │       ├── search.js
│   │       └── ...
│   │
│   └── images/
│       ├── logo.svg
│       ├── favicon.png
│       └── og-image.png
│
├── static/
│   ├── fonts/
│   │   └── ...
│   └── icons/
│       └── ...
│
└── config/
    └── default.toml          # Default theme config
```

---

## Success Metrics

### Performance Goals
- ✅ Lighthouse Score: 95+ (all categories)
- ✅ First Contentful Paint: < 1.5s
- ✅ Time to Interactive: < 3s
- ✅ Cumulative Layout Shift: < 0.1
- ✅ Total page weight: < 200KB (initial load)

### Accessibility Goals
- ✅ WCAG 2.1 Level AA compliance
- ✅ Keyboard navigable
- ✅ Screen reader compatible
- ✅ Contrast ratio: 4.5:1 (text)

### Browser Support
- ✅ Chrome/Edge (last 2 versions)
- ✅ Firefox (last 2 versions)
- ✅ Safari (last 2 versions)
- ✅ iOS Safari
- ✅ Android Chrome

---

## Next Steps

1. **Review & Prioritize**: Decide which features are MVP vs nice-to-have
2. **Design Mockups**: Create visual designs for key pages
3. **Start Implementation**: Begin with Phase 1 (Foundation)
4. **Iterate**: Build → Test → Refine
5. **Document**: Create theme documentation and examples

Would you like me to start implementing any specific phase?

