# Default Theme Component Library

This directory contains component manifests for the Bengal SSG default theme's component preview system.

## Overview

The default theme includes **14 reusable components** (template partials) with **42 test variants** for development and testing.

### What are Component Manifests?

Component manifests are YAML files that define:
- Which template to render
- Sample data (context) for testing different scenarios
- Variants to test edge cases (long titles, empty states, etc.)

**Key Point**: Manifests are dev/test fixtures only. Templates work perfectly without them.

## Component Preview System

Start the dev server to preview components in isolation:

```bash
cd examples/showcase  # or your project
bengal site serve
open http://localhost:5173/__bengal_components__/
```

### Features

- **Isolated rendering**: Test components without building the full site
- **Live reload**: Changes to templates/styles update instantly
- **Multiple variants**: Test edge cases and different data scenarios
- **No production impact**: Manifests are dev tools only

## Component Catalog

### Simple Components

| Component | Template | Variants | Description |
|-----------|----------|----------|-------------|
| **Breadcrumbs** | `partials/breadcrumbs.html` | 3 | Hierarchical navigation trail |
| **Page Navigation** | `partials/page-navigation.html` | 3 | Prev/next page links |
| **Pagination** | `partials/pagination.html` | 3 | Page number controls |
| **Tag List** | `partials/tag-list.html` | 3 | Tag badges (linkable/non-linkable) |
| **Popular Tags** | `partials/popular-tags.html` | 3 | Tag cloud widget |
| **Random Posts** | `partials/random-posts.html` | 3 | Random post suggestions |
| **Document Metadata** | `partials/docs-meta.html` | 3 | Date and reading time |

### Complex Components

| Component | Template | Variants | Description |
|-----------|----------|----------|-------------|
| **Article Card** | `partials/article-card.html` | 3 | Rich article preview card |
| **Child Page Tiles** | `partials/child-page-tiles.html` | 3 | Section/page listing with icons |
| **Documentation Nav** | `partials/docs-nav.html` | 3 | Full hierarchical sidebar |
| **TOC Sidebar** | `partials/toc-sidebar.html` | 3 | Table of contents with progress |
| **Section Navigation** | `partials/section-navigation.html` | 3 | Section statistics and subsections |

### Special Components

| Component | Template | Variants | Description |
|-----------|----------|----------|-------------|
| **Search** | `partials/search.html` | 3 | Full-text search with Lunr.js |
| **Docs Nav Section** | `partials/docs-nav-section.html` | 3 | Recursive nav section renderer |

## Using Components

### In Your Templates

All components are designed to be included with context:

```jinja
{# Simple include (uses implicit context) #}
{% include 'partials/breadcrumbs.html' %}

{# Include with explicit context #}
{% include 'partials/article-card.html' with {'article': post, 'show_image': true} %}

{# Include with additional variables #}
{% include 'partials/pagination.html' with {'current_page': 2, 'total_pages': 10, 'base_url': '/blog/'} %}
```

### Component Props

Each component documents its variables in the template header. Example:

```jinja
{#
  Article Card Component

  Variables:
    - article: Page object to display (required)
    - show_excerpt: Boolean (default: true)
    - show_image: Boolean (default: false)

  Usage:
    {% include 'partials/article-card.html' with {'article': page} %}
#}
```

## Customizing Components

### Using Swizzle

Copy a component to your project for customization:

```bash
# Copy a component template
bengal theme swizzle partials/article-card.html

# List swizzled components
bengal theme swizzle-list

# Update swizzled components (safe when unchanged)
bengal theme swizzle-update
```

Swizzled templates are tracked in `.bengal/themes/sources.json` with checksums for safe updates.

### Preview Your Changes

After swizzling, your customized component will appear in the component preview:

1. Swizzle: `bengal theme swizzle partials/pagination.html`
2. Edit: `templates/partials/pagination.html`
3. Preview: Visit `http://localhost:5173/__bengal_components__/`
4. See your changes with live reload!

## Creating New Components

### 1. Create the Template

```jinja
{# templates/partials/my-component.html #}
{#
  My Component

  Description of what it does.

  Variables:
    - title: Component title (required)
    - variant: Style variant (default: 'default')

  Usage:
    {% include 'partials/my-component.html' with {'title': 'Hello'} %}
#}

{% set variant = variant | default('default') %}

<div class="my-component my-component-{{ variant }}">
    <h3>{{ title }}</h3>
</div>
```

### 2. Create the Manifest

```yaml
# dev/components/my-component.yaml
name: "My Component"
template: "partials/my-component.html"
description: "Brief description for component gallery"
variants:
  - id: "default"
    name: "Default"
    context:
      title: "Hello World"
      variant: "default"

  - id: "alternate"
    name: "Alternate Style"
    context:
      title: "Alternate Example"
      variant: "alternate"
```

### 3. Preview It

Visit `http://localhost:5173/__bengal_components__/` and your component will appear in the gallery.

## Manifest Format

```yaml
name: "Component Name"              # Display name in gallery
template: "partials/component.html" # Template path (relative to templates/)
description: "Brief description"    # Optional, shows in gallery
variants:                           # List of test scenarios
  - id: "variant-id"               # Unique ID (used in URLs)
    name: "Variant Name"            # Display name
    context:                        # Template context (variables)
      variable1: "value"
      variable2: 123
      nested:
        key: "value"
```

## Best Practices

### Component Design

1. **Self-contained**: Components should work with minimal dependencies
2. **Documented props**: Always document variables in template header
3. **Sensible defaults**: Use `| default()` filter for optional props
4. **Graceful degradation**: Handle missing data elegantly
5. **Accessible**: Use semantic HTML and ARIA attributes

### Manifest Design

1. **Test edge cases**: Create variants for empty states, long content, etc.
2. **Realistic data**: Use plausible sample data that demonstrates the component
3. **Multiple scenarios**: Test different prop combinations
4. **Document limitations**: Note when components depend on global functions

### Example: Good Component Header

```jinja
{#
  Pagination Component

  Displays page number controls for paginated content.

  Variables:
    - current_page: Current page number (1-indexed, required)
    - total_pages: Total number of pages (required)
    - base_url: Base URL for pagination (e.g., '/blog/', required)

  Template Functions Used:
    - get_pagination_items(current_page, total_pages, base_url)

  Features:
    - Smart ellipsis for large page counts
    - Accessible with aria-current and aria-label
    - Disabled state for unavailable links

  Usage:
    {% include 'partials/pagination.html' with {'current_page': 2, 'total_pages': 10, 'base_url': '/blog/'} %}
#}
```

## Limitations

### Global Template Functions

Some components use global template functions that require full site context:

- `popular_tags()` - Queries all pages for tag frequencies
- `site.regular_pages | sample()` - Random page selection
- `get_breadcrumbs(page)` - Builds ancestor chain

These components will show UI structure in preview but may not have full functionality.

### Workaround

Add a `_preview_note` to your manifest context:

```yaml
context:
  site:
    config:
      title: "My Site"
  _preview_note: "This component uses popular_tags() which requires full site context"
```

## Troubleshooting

### Component doesn't appear in gallery

- Check YAML syntax (use YAML validator)
- Ensure `template` path is correct
- Restart dev server: `Ctrl+C` then `bengal site serve`

### Component renders blank/errors

- Check template syntax
- Verify context data matches template expectations
- Look for missing required variables

### Changes don't show up

- Live reload requires component preview to be open in browser
- Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
- Check browser console for errors

## Architecture Notes

### Source of Truth

**Templates are the source of truth.** Manifests are test fixtures only.

```
┌─────────────────┐
│  template.html  │ ← Source of truth (used in production)
└────────┬────────┘
         │ referenced by
         ↓
┌─────────────────┐
│ component.yaml  │ ← Test fixture (dev/preview only)
└─────────────────┘
```

### No Automatic Sync

If you change a template's props, manually update manifests:

```html
<!-- Changed template prop name -->
{% set item = item | default({}) %}  {# was 'article' #}
```

```yaml
# Update manifest context
context:
  item:  # was 'article'
    title: "Hello"
```

### Optional by Design

- Templates work without manifests
- Manifests don't affect production builds
- Delete outdated manifests without breaking anything
- Manifests are "living documentation"

## Further Reading

- [Swizzle & Component Preview Analysis](/plan/SWIZZLE_AND_COMPONENT_PREVIEW_ANALYSIS.md)
- [Theme Development Guide](/bengal/themes/default/README.md)
- [Bengal SSG Documentation](https://bengal-ssg.github.io/)

## Contributing

When adding new components to the default theme:

1. ✅ Create the template with standardized header
2. ✅ Create manifest with 2-3 test variants
3. ✅ Test in component preview
4. ✅ Document in this README
5. ✅ Add usage examples to showcase

---

**Total Components**: 14  
**Total Variants**: 42  
**Last Updated**: October 2025
