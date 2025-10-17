# Bengal Default Theme

**Version:** 2.0  
**Last Updated:** October 10, 2025  
**License:** MIT

---

## Overview

The Bengal Default Theme is a modern, accessible, and highly customizable theme for Bengal Static Site Generator. It provides a complete foundation for documentation sites, blogs, API references, and more.

## Features

### 🎨 Design System
- **Semantic design tokens** with foundation → semantic → component layers
- **Dark mode** with automatic system preference detection
- **Accessible** WCAG 2.1 AA compliant with focus management
- **Responsive** mobile-first design with breakpoints
- **Print-optimized** styles for documentation

### 📐 CSS Architecture
- **Scoped CSS** preventing style conflicts (see [CSS_SCOPING_RULES.md](assets/css/CSS_SCOPING_RULES.md))
- **Token-based** design with ~200 semantic CSS variables
- **Component-driven** modular CSS structure
- **Performance-focused** minimal CSS footprint

### 🧩 Components

#### Content Components
- **Prose Typography** - Beautiful long-form content styling
- **Code Blocks** - Syntax highlighting with copy buttons
- **Admonitions** - Callout boxes (info, warning, success, error)
- **Tabs** - Tabbed content with keyboard navigation
- **Dropdowns** - Collapsible content sections
- **Cards** - Flexible card layouts with grids

#### Documentation Components
- **TOC (Table of Contents)** - Sticky sidebar with scroll spy
- **Docs Navigation** - Hierarchical sidebar navigation
- **API Documentation** - Specialized styling for API refs
- **CLI Reference** - Command documentation layouts
- **Breadcrumbs** - Navigation trail
- **Page Navigation** - Prev/Next links

#### UI Components
- **Hero Sections** - Eye-catching landing sections
- **Search** - Full-text search with Lunr.js
- **Appearance** - Dropdown for Mode (System/Light/Dark) and Brand/Palette
- **Mobile Navigation** - Responsive menu with hamburger
- **Pagination** - Page number navigation
- **Tags & Badges** - Content categorization

#### Interactive Features
- **Back to Top** - Smooth scroll to top button
- **Reading Progress** - Progress bar for long articles
- **Lightbox** - Image zoom gallery
- **Copy Links** - Heading anchor link copying
- **Smooth Scroll** - Enhanced anchor navigation

### 🔧 Component Library & Development Tools

The default theme includes a comprehensive **component library** with development tools for rapid iteration:

#### Component Preview System

All 14 template partials have **component manifests** for isolated testing and development:

```bash
# Start dev server
bengal serve

# Preview components in browser
open http://localhost:5173/__bengal_components__/
```

**Features:**
- **Isolated rendering** - Test components without full site build
- **42 test variants** - Edge cases, empty states, long content
- **Live reload** - Instant updates on template/style changes
- **Variant testing** - Multiple scenarios per component

#### Swizzle: Safe Template Customization

Copy theme templates for customization with provenance tracking:

```bash
# Copy a component to your project
bengal theme swizzle partials/article-card.html

# List swizzled components
bengal theme swizzle-list

# Update swizzled files (safe when unchanged)
bengal theme swizzle-update
```

Swizzled templates are tracked in `.bengal/themes/sources.json` with checksums for safe updates.

#### Component Catalog

All 14 partials are documented with:
- **Standardized headers** documenting props and usage
- **Test manifests** with 2-3 variants each
- **Component preview** for visual testing

See [Component Library Documentation](dev/components/README.md) for complete details.

**Quick Links:**
- 📚 [Component Library README](dev/components/README.md)
- 🎨 [Component Preview](http://localhost:5173/__bengal_components__/) (dev server required)
- 🔀 [Swizzle Documentation](/plan/SWIZZLE_AND_COMPONENT_PREVIEW_ANALYSIS.md)

### 📂 File Structure

```
default/
├── assets/
│   ├── css/
│   │   ├── tokens/           # Design tokens (foundation + semantic)
│   │   ├── base/             # Resets, typography, accessibility
│   │   ├── composition/      # Layout primitives
│   │   ├── components/       # UI components
│   │   ├── layouts/          # Page layouts (header, footer, grid)
│   │   ├── pages/            # Page-specific styles
│   │   ├── utilities/        # Utility classes
│   │   ├── style.css         # Main entry point
│   │   ├── README.md         # CSS architecture docs
│   │   ├── CSS_SCOPING_RULES.md      # Scoping guidelines
│   │   └── CSS_QUICK_REFERENCE.md    # Quick reference card
│   │
│   └── js/
│       ├── main.js           # Main JavaScript entry point
│       ├── theme-toggle.js   # Dark mode functionality
│       ├── toc.js            # Table of contents behavior
│       ├── search.js         # Search functionality
│       ├── tabs.js           # Tab component behavior
│       ├── lightbox.js       # Image lightbox
│       ├── interactive.js    # Interactive features
│       ├── mobile-nav.js     # Mobile navigation
│       ├── copy-link.js      # Copy link functionality
│       └── lunr.min.js       # Search library
│
├── templates/
│   ├── base.html             # Base template
│   ├── home.html             # Homepage template
│   ├── page.html             # Generic page template
│   ├── doc/                  # Documentation templates
│   ├── blog/                 # Blog templates
│   ├── api-reference/        # API reference templates
│   ├── cli-reference/        # CLI reference templates
│   ├── tutorial/             # Tutorial templates
│   └── partials/             # Reusable template fragments (14 components)
│
├── dev/
│   └── components/           # Component manifests (42 variants)
│       ├── README.md         # Component library documentation
│       ├── *.yaml            # Component test manifests
│
└── README.md                 # This file
```

---

## Getting Started

### Using This Theme

The default theme is automatically included with Bengal. To use it:

```toml
# bengal.toml
[theme]
name = "default"
```

### Customizing Colors

Override semantic tokens in your site's CSS:

```css
:root {
  --color-primary: #3b82f6;
  --color-text-primary: #1f2937;
  --color-bg-primary: #ffffff;
}

[data-theme="dark"] {
  --color-text-primary: #f3f4f6;
  --color-bg-primary: #1a1a1a;
}
```

### Adding Custom Components

1. Create `assets/css/custom.css` in your project
2. Import after theme styles:
   ```css
   @import '../themes/default/assets/css/style.css';
   @import 'custom.css';
   ```

### Overriding Templates

Create a template with the same name in your project's `templates/` directory:

```
your-project/
├── templates/
│   └── page.html      # Overrides default theme's page.html
```

---

## CSS Architecture

### Design Token System

**Two-layer approach:**

1. **Foundation Tokens** (`tokens/foundation.css`)
   - Raw primitive values (colors, sizes, fonts)
   - Never use directly in components
   - Example: `--blue-500`, `--size-4`

2. **Semantic Tokens** (`tokens/semantic.css`)
   - Purpose-based naming
   - Maps foundation tokens to semantic use
   - **Always use these in components**
   - Example: `--color-primary`, `--space-4`, `--text-lg`

### Scoping Rules

**Every CSS selector must be scoped** to prevent conflicts. See [CSS_SCOPING_RULES.md](assets/css/CSS_SCOPING_RULES.md) for details.

**Key principles:**
- ✅ `.prose.api-content ul` - Content-type scoped
- ✅ `.dropdown-content ul` - Component scoped
- ✅ `.has-prose-content ul` - Utility class
- ❌ `.prose ul` - Too broad
- ❌ `ul` - Never bare elements in components

### File Organization

**Import order matters:**

```css
/* 1. Tokens (variables) */
@import 'tokens/foundation.css';
@import 'tokens/semantic.css';

/* 2. Base (element resets) */
@import 'base/reset.css';
@import 'base/typography.css';

/* 3. Composition (layout primitives) */
@import 'composition/layouts.css';

/* 4. Components (most specific) */
@import 'components/*.css';

/* 5. Pages (page-specific) */
@import 'pages/*.css';
```

---

## JavaScript Architecture

### Module Structure

All JavaScript is vanilla ES6+ with no framework dependencies:

```javascript
// Standard module pattern
(function() {
  'use strict';

  // Private functions
  function privateFunction() { }

  // Public init
  function init() { }

  // Auto-initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

### Key Features

- **Progressive Enhancement** - Works without JavaScript
- **Accessibility First** - Keyboard navigation, ARIA
- **Performance** - Lazy loading, debouncing
- **No Dependencies** (except Lunr.js for search)

### Main Modules

| File | Purpose |
|------|---------|
| `main.js` | Entry point, coordinates all modules |
| `theme-toggle.js` | Appearance control (mode + brand) with persistence |
| `toc.js` | Table of contents with scroll spy |
| `search.js` | Full-text search with Lunr.js |
| `tabs.js` | Tab component with keyboard nav |
| `lightbox.js` | Image zoom gallery |
| `interactive.js` | Back-to-top, reading progress, smooth scroll |
| `mobile-nav.js` | Responsive hamburger menu |
| `copy-link.js` | Copy heading anchor links |

---

## Templates

### Template Hierarchy

Bengal uses a template resolution order:

1. Page-specific template (e.g., `doc/single.html`)
2. Type-specific template (e.g., `page.html`)
3. Base template (`base.html`)

### Available Templates

#### Core Templates
- `base.html` - Base layout with header/footer
- `home.html` - Homepage
- `page.html` - Generic pages
- `404.html` - Error page

#### Content Type Templates
- `doc/list.html` - Documentation list
- `doc/single.html` - Documentation page
- `blog/list.html` - Blog index
- `blog/single.html` - Blog post
- `post.html` - Simple blog post

#### Reference Templates
- `api-reference/list.html` - API reference index
- `api-reference/single.html` - API documentation page
- `cli-reference/list.html` - CLI reference index
- `cli-reference/single.html` - CLI command page
- `tutorial/list.html` - Tutorial list
- `tutorial/single.html` - Tutorial page

#### Special Templates
- `archive.html` - Archive pages
- `tag.html` - Tag page
- `tags.html` - Tags index
- `search.html` - Search results

### Partials (Component Library)

**14 reusable template components** in `partials/` with full documentation:

**Simple Components:**
- `breadcrumbs.html` - Breadcrumb navigation
- `page-navigation.html` - Prev/Next links
- `pagination.html` - Page number navigation
- `tag-list.html` - Tag badges
- `popular-tags.html` - Tag cloud widget
- `random-posts.html` - Random post suggestions
- `docs-meta.html` - Date and reading time

**Complex Components:**
- `article-card.html` - Article preview card with images
- `child-page-tiles.html` - Section/page listing
- `docs-nav.html` - Full documentation sidebar
- `toc-sidebar.html` - Table of contents with progress
- `section-navigation.html` - Section statistics

**Special Components:**
- `search.html` - Full-text search UI
- `docs-nav-section.html` - Recursive nav renderer

Each component includes:
- ✅ Standardized header with prop documentation
- ✅ Test manifests with 2-3 variants
- ✅ Component preview support
- ✅ Swizzle compatibility

**Component Library:** See [dev/components/README.md](dev/components/README.md) for detailed documentation

### Template Variables

All templates have access to:

```jinja
{{ site }}              # Site configuration
{{ page }}              # Current page object
{{ content }}           # Rendered page content
{{ pages }}             # All pages
{{ sections }}          # All sections
{{ menu }}              # Navigation menu
{{ config }}            # Full configuration
```

---

## Customization Guide

### 1. Colors & Branding

**Override semantic tokens:**

```css
/* assets/css/custom.css */
:root {
  --color-primary: #your-brand-color;
  --color-primary-hover: #darker-shade;
  --font-sans: 'Your Font', system-ui;
}
```

### 2. Layout

**Adjust container widths:**

```css
:root {
  --container-xl: 1400px;  /* Default: 1280px */
  --prose-width: 800px;     /* Default: 65ch */
}
```

### 3. Typography

**Change font scale:**

```css
:root {
  --text-base: 1.125rem;    /* Default: 1rem */
  --text-lg: 1.25rem;
  /* ... other sizes */
}
```

### 4. Components

**Disable or customize components:**

```css
/* Hide back-to-top button */
.back-to-top {
  display: none;
}

/* Customize TOC */
.toc-sidebar {
  position: static;  /* Remove sticky */
}
```

### 5. JavaScript Features

**Disable specific features:**

```html
<!-- In your base template override -->
<script>
// Disable smooth scroll
window.Bengal = window.Bengal || {};
window.Bengal.disableSmoothScroll = true;
</script>
```

---

## Browser Support

### Supported Browsers

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- iOS Safari 14+
- Android Chrome 90+

### Progressive Enhancement

**Core features work everywhere:**
- Content is always readable
- Navigation always functional
- No JavaScript required for basic usage

**Enhanced features (with JavaScript):**
- Search
- Appearance control (mode + brand)
- Interactive components
- Smooth scrolling
- Back to top

---

## Accessibility

### WCAG 2.1 AA Compliance

- ✅ **Keyboard Navigation** - All interactive elements
- ✅ **Focus Indicators** - Visible focus states
- ✅ **Color Contrast** - 4.5:1 minimum
- ✅ **ARIA Labels** - Screen reader support
- ✅ **Semantic HTML** - Proper heading hierarchy
- ✅ **Skip Links** - Skip to main content

### Testing

```bash
# Run accessibility audit
npm install -g pa11y
pa11y http://localhost:5173
```

---

## Performance

### Optimization Techniques

- **CSS** (~50KB minified)
  - Design tokens reduce duplication
  - Component-based loading
  - Print styles separated

- **JavaScript** (~30KB minified)
  - Vanilla JS, no frameworks
  - Lazy loading for search
  - Event delegation

- **Images**
  - Lazy loading with native `loading="lazy"`
  - Responsive images with `srcset`
  - WebP with fallbacks

### Lighthouse Scores

Target scores for documentation sites:

- **Performance:** 95+
- **Accessibility:** 100
- **Best Practices:** 100
- **SEO:** 100

---

## Development

### Local Development

```bash
# Watch CSS changes
cd bengal/themes/default/assets/css
# Use your preferred CSS processor or edit directly

# Test JavaScript
cd bengal/themes/default/assets/js
# Open test.html in browser
```

### CSS Development

**Follow the scoping rules:**

1. Read [CSS_SCOPING_RULES.md](assets/css/CSS_SCOPING_RULES.md)
2. Use [CSS_QUICK_REFERENCE.md](assets/css/CSS_QUICK_REFERENCE.md) while coding
3. Always scope selectors to prevent conflicts
4. Use semantic tokens, never foundation tokens

### JavaScript Development

**Best practices:**

```javascript
// ✅ Good: Scoped module
(function() {
  'use strict';

  function myFeature() {
    // Feature code
  }

  document.addEventListener('DOMContentLoaded', myFeature);
})();

// ❌ Bad: Global pollution
function myFeature() {
  // Conflicts with other code
}
```

---

## Testing

### Manual Testing Checklist

- [ ] Light and dark modes
- [ ] All breakpoints (mobile, tablet, desktop)
- [ ] Keyboard navigation
- [ ] Screen reader (VoiceOver/NVDA)
- [ ] Print preview
- [ ] Cross-browser (Chrome, Firefox, Safari)

### Automated Testing

```bash
# Accessibility
pa11y http://localhost:5173

# Performance
lighthouse http://localhost:5173

# Visual regression
# TODO: Add backstop.js config
```

---

## Migration Guide

### Upgrading from v1.0

**Breaking changes:**

1. **CSS Variables** - All variables renamed to semantic system
2. **Template Variables** - Some page attributes renamed
3. **JavaScript** - Event names changed for consistency

**Migration steps:**

```bash
# 1. Update bengal.toml
[theme]
name = "default"
version = "2.0"

# 2. Update custom CSS to use semantic tokens
# Old: --primary-color
# New: --color-primary

# 3. Update template overrides
# Check template variable changes in CHANGELOG
```

---

## Contributing

### Adding New Components

1. **CSS Component** (`assets/css/components/new-component.css`)
   ```css
   .new-component {
     /* Use semantic tokens */
     padding: var(--space-4);
     color: var(--color-text-primary);
   }
   ```

2. **Import in style.css**
   ```css
   @import 'components/new-component.css';
   ```

3. **JavaScript (if needed)** (`assets/js/new-component.js`)
   ```javascript
   (function() {
     'use strict';
     function init() { /* ... */ }
     document.addEventListener('DOMContentLoaded', init);
   })();
   ```

4. **Template** (`templates/components/new-component.html`)
   ```html
   <div class="new-component">
     {{ content }}
   </div>
   ```

### Code Style

- **CSS:** BEM-like naming, alphabetical properties
- **JavaScript:** ESLint Standard, 2-space indent
- **Templates:** Jinja2, 2-space indent

---

## Troubleshooting

### Common Issues

**Q: Dark mode not persisting**
```javascript
// Check localStorage
console.log(localStorage.getItem('theme'));
// Should be 'light', 'dark', or null
```

**Q: TOC not highlighting**
```javascript
// Check scroll spy initialization
console.log('TOC headings:', document.querySelectorAll('.prose h2, .prose h3'));
```

**Q: Search not working**
```javascript
// Check search index
console.log('Search index:', window.searchIndex);
// Should be an object with documents array
```

**Q: Styles not applying**
```html
<!-- Check CSS import order in base.html -->
<link rel="stylesheet" href="{{ url_for('assets/css/style.css') }}">
```

### Debug Mode

```html
<!-- Add to base template -->
<script>
window.Bengal = window.Bengal || {};
window.Bengal.debug = true;
</script>
```

---

## Resources

### Documentation
- [CSS Architecture](assets/css/README.md)
- [CSS Scoping Rules](assets/css/CSS_SCOPING_RULES.md)
- [CSS Quick Reference](assets/css/CSS_QUICK_REFERENCE.md)
- [Bengal Documentation](https://bengal-ssg.org/docs/)

### Design Systems
- [Semantic Design Tokens](https://design-tokens.github.io/community-group/format/)
- [CUBE CSS Methodology](https://cube.fyi/)
- [Every Layout](https://every-layout.dev/)

### Accessibility
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM](https://webaim.org/)

---

## License

MIT License - See [LICENSE](../../../LICENSE) for details

---

## Changelog

### v2.1.0 (October 2025)
- **Component Library** - 14 components with 42 test variants
- **Component Preview System** - Storybook-like isolated component testing
- **Swizzle Support** - Safe template overriding with provenance tracking
- **Standardized Documentation** - All components have comprehensive headers
- **Component Manifests** - YAML test fixtures for all partials

### v2.0.0 (October 2025)
- Semantic design token system
- Strict CSS scoping rules
- Improved accessibility (WCAG 2.1 AA)
- Dark mode enhancements
- Component-based architecture

### v1.0.0 (Initial release)
- Basic theme structure
- Core components
- Responsive design
