---
title: Theme Components
description: Macro-based components for building Bengal themes
weight: 50
toc: true
---

# Theme Components

Bengal's default theme provides a set of reusable macro-based components that make it easy to build consistent, maintainable templates.

## Why Macros?

Macros provide several advantages over traditional include-based patterns:

- **Explicit parameters** - Self-documenting function-like calls
- **Type safety** - Fails fast on missing required parameters
- **No scope pollution** - Parameters don't leak into parent scope
- **Default values** - Optional parameters with sensible defaults
- **Better errors** - Clear error messages in strict mode
- **Easy to refactor** - Change signature, get immediate feedback

## Component Libraries

### Navigation Components

Import from `partials/navigation-components.html`:

```jinja2
{% from 'partials/navigation-components.html' import breadcrumbs, pagination, page_navigation with context %}
```

#### `breadcrumbs(page)`

Displays hierarchical navigation showing the current page's location.

**Parameters:**
- `page` (required) - Current page object

**Example:**
```jinja2
{{ breadcrumbs(page) }}
```

**Output:**
```html
<nav class="breadcrumbs" aria-label="Breadcrumb">
  <ol>
    <li><a href="/">Home</a></li>
    <li aria-current="page">Theme Components</li>
  </ol>
</nav>
```

---

#### `pagination(current_page, total_pages, base_url)`

Displays page number controls for paginated content.

**Parameters:**
- `current_page` (required) - Current page number (1-indexed)
- `total_pages` (required) - Total number of pages
- `base_url` (required) - Base URL for pagination links

**Example:**
```jinja2
{{ pagination(current_page=2, total_pages=10, base_url='/blog/') }}
```

**Features:**
- Smart ellipsis for large page counts
- Accessible with aria-current
- SVG icons for prev/next buttons
- Disabled state for unavailable links

---

#### `page_navigation(page)`

Displays previous/next page links for sequential navigation.

**Parameters:**
- `page` (required) - Current page object with `prev` and `next` attributes

**Example:**
```jinja2
{{ page_navigation(page) }}
```

**Output:**
```html
<nav class="page-navigation">
  <div class="nav-links">
    <div class="nav-previous">
      <a href="/prev/" rel="prev">
        <span class="nav-subtitle">← Previous</span>
        <span class="nav-title">Previous Page Title</span>
      </a>
    </div>
    <div class="nav-next">
      <a href="/next/" rel="next">
        <span class="nav-subtitle">Next →</span>
        <span class="nav-title">Next Page Title</span>
      </a>
    </div>
  </div>
</nav>
```

---

#### `section_navigation(page)`

Displays statistics and subsection cards for exploring a section hierarchy.

**Parameters:**
- `page` (required) - Current section object

**Example:**
```jinja2
{{ section_navigation(page) }}
```

**Features:**
- Shows page counts
- Displays subsection grid with descriptions
- Recursive page counting

---

#### `toc(toc_items, toc, page)`

Interactive table of contents with progress tracking and metadata.

**Parameters:**
- `toc_items` (optional) - List of TOC items with id, title, level
- `toc` (optional) - HTML TOC fallback
- `page` (optional) - Current page object for metadata

**Example:**
```jinja2
{{ toc(toc_items=toc_items, toc=toc, page=page) }}
```

**Features:**
- Scroll progress indicator
- Collapsible H2 sections
- Active item highlighting
- Settings menu (expand all/collapse all)
- Page metadata display
- Edit on GitHub link

---

### Content Components

Import from `partials/content-components.html`:

```jinja2
{% from 'partials/content-components.html' import article_card, tag_list, child_page_tiles with context %}
```

#### `article_card(article, show_excerpt, show_image)`

Rich article preview card with metadata, tags, and optional image.

**Parameters:**
- `article` (required) - Page object to display
- `show_excerpt` (optional, default: `True`) - Show description/excerpt
- `show_image` (optional, default: `False`) - Show featured image

**Example:**
```jinja2
{{ article_card(post, show_image=True, show_excerpt=True) }}
```

**Features:**
- Responsive images with srcset
- Dynamic badges (featured, tutorial, new)
- Reading time calculation
- Relative time formatting
- Semantic HTML

---

#### `child_page_tiles(posts, subsections)`

Displays subsections and child pages as compact row-based items with icons.

**Parameters:**
- `posts` (optional) - List of child pages
- `subsections` (optional) - List of child sections

**Example:**
```jinja2
{{ child_page_tiles(posts=page.regular_pages, subsections=page.sections) }}
```

**Features:**
- Merged and sorted list
- Folder icon for sections
- Document icon for pages
- Page count metadata
- Weight-based sorting

---

#### `tag_list(tags, small, linkable)`

Displays tags as styled badges.

**Parameters:**
- `tags` (required) - List of tag strings
- `small` (optional, default: `False`) - Use smaller size
- `linkable` (optional, default: `True`) - Make tags clickable

**Example:**
```jinja2
{{ tag_list(page.tags) }}
{{ tag_list(post.tags, small=True) }}
{{ tag_list(['Python', 'Testing'], linkable=False) }}
```

**Features:**
- Locale-aware tag URLs
- Small variant for compact display
- Non-linkable mode for display-only

---

#### `popular_tags(limit)`

Tag cloud widget showing most frequently used tags.

**Parameters:**
- `limit` (optional, default: `10`) - Number of tags to show

**Example:**
```jinja2
{{ popular_tags(limit=20) }}
```

---

#### `random_posts(count)`

Random post discovery widget.

**Parameters:**
- `count` (optional, default: `3`) - Number of random posts to show

**Example:**
```jinja2
{{ random_posts(count=5) }}
```

---

## Migration Guide

### From Include to Macro

**Old pattern (deprecated):**
```jinja2
{# Set variables #}
{% set icon = '📦' %}
{% set title = page.title %}
{% include 'partials/breadcrumbs.html' %}
```

**New pattern (recommended):**
```jinja2
{# Import and use #}
{% from 'partials/navigation-components.html' import breadcrumbs with context %}
{{ breadcrumbs(page) }}
```

### Benefits of Migration

1. **Explicit Parameters** - No guessing what variables an include needs
2. **Fail Fast** - Errors on missing required parameters
3. **No Pollution** - Variables don't leak into parent scope
4. **Refactoring** - Change signature, get clear errors everywhere
5. **Documentation** - Self-documenting function-like calls

## Usage Patterns

### Import Multiple Components

```jinja2
{% from 'partials/navigation-components.html' import breadcrumbs, page_navigation with context %}
{% from 'partials/content-components.html' import article_card, tag_list with context %}

{{ breadcrumbs(page) }}

{% for post in posts %}
  {{ article_card(post, show_image=True) }}
{% endfor %}

{{ tag_list(page.tags, small=True) }}
{{ page_navigation(page) }}
```

### Conditional Rendering

```jinja2
{% from 'partials/navigation-components.html' import pagination with context %}

{% if total_pages > 1 %}
  {{ pagination(current_page, total_pages, base_url) }}
{% endif %}
```

### With Custom Parameters

```jinja2
{% from 'partials/content-components.html' import article_card with context %}

{# Show with image and excerpt #}
{{ article_card(post, show_image=True, show_excerpt=True) }}

{# Show without excerpt #}
{{ article_card(post, show_image=True, show_excerpt=False) }}

{# Minimal card #}
{{ article_card(post) }}
```

## Best Practices

### 1. Always Import with Context

Use `with context` to ensure macros have access to global template variables:

```jinja2
{% from 'partials/navigation-components.html' import breadcrumbs with context %}
```

### 2. Use Safe Dict Access

When accessing metadata, use `.get()` for strict mode compatibility:

```jinja2
{% if page.metadata.get('description') %}
  <p>{{ page.metadata.get('description') }}</p>
{% endif %}
```

### 3. Provide Required Parameters

Always provide required parameters explicitly:

```jinja2
{# Good #}
{{ breadcrumbs(page) }}

{# Bad - will error #}
{{ breadcrumbs() }}
```

### 4. Use Named Parameters

For clarity, use named parameters for optional arguments:

```jinja2
{# Good #}
{{ article_card(post, show_image=True, show_excerpt=True) }}

{# Less clear #}
{{ article_card(post, True, True) }}
```

## Strict Mode

All components are strict mode compatible. Enable strict mode for better error detection:

```bash
bengal site build --strict
```

This will catch:
- Undefined variables
- Missing required parameters
- Incorrect attribute access
- Typos in variable names

## Examples in This Site

See these components in action throughout this documentation:

- **Navigation**: Look at the breadcrumbs above and page navigation below
- **TOC**: The table of contents on the right side
- **Tags**: See the tag list at the bottom of blog posts
- **Cards**: Article cards on the blog list page

## Component Development

To create your own macros:

```jinja2
{#
  My Component

  Description of what this component does.

  Args:
    required_param: Description of required parameter
    optional_param: Description (default: 'value')

  Example:
    {{ my_component(required_param='foo') }}
#}
{% macro my_component(required_param, optional_param='default') %}
  <div class="my-component">
    <h2>{{ required_param }}</h2>
    <p>{{ optional_param }}</p>
  </div>
{% endmacro %}
```

## Further Reading

- [Jinja2 Macros Documentation](https://jinja.palletsprojects.com/en/3.0.x/templates/#macros)
- [Bengal Template Functions](/docs/templates/functions/)
- [Creating Custom Themes](/docs/themes/custom/)

## Deprecation Timeline

Old include-based templates are deprecated and will be removed in Bengal 1.0:

- ⚠️ **Now**: Old includes work but show deprecation warnings
- 🔜 **Bengal 1.0**: Old includes will be removed
- ✅ **Recommended**: Migrate to macros now for better experience
