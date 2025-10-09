# Autodoc Sidebar Navigation Implementation

**Status**: ✅ Completed  
**Date**: 2025-10-09  
**Type**: UX Enhancement

## Overview

Added three-column layout with left sidebar navigation to API and CLI reference documentation pages, matching the experience of the docs template. This provides consistent navigation patterns across all reference documentation.

## Problem Statement

Previously:
- **Docs pages**: Had full three-column layout (left nav + content + right TOC)
- **API/CLI list pages**: Had single-column grid layout (no sidebars)
- **API/CLI single pages**: Used default `page.html` with only right TOC, no left navigation

This inconsistency meant users had to go back to the list page to navigate between modules/commands, making it harder to explore large API surfaces.

## Solution

Created new single-page templates for API and CLI reference that reuse the existing docs layout system:

### Files Created

1. **`api-reference/single.html`** - Main API single page template
2. **`cli-reference/single.html`** - Main CLI single page template  
3. **`api/single.html`** - Alias for sections named "api"
4. **`cli/single.html`** - Alias for sections named "cli"

### Design Decisions

#### ✅ Reused Existing Infrastructure

- **CSS Classes**: Reused `docs-*` classes (`.docs-layout`, `.docs-sidebar`, etc.)
  - Semantic enough: "docs" = documentation = reference docs
  - Zero CSS changes needed
  - Consistent styling across all reference types
  - Mobile-responsive drawer already works

- **Navigation Partial**: Reused `partials/docs-nav.html`
  - Already scope-aware: uses `page._section.root` to show only current section tree
  - Works automatically with API/CLI section hierarchies
  - Shows packages → modules or command groups → commands
  - Active page highlighting, collapsible sections, keyboard accessible

- **TOC Partial**: Reused `partials/toc-sidebar.html`
  - Right sidebar table of contents
  - Quick navigation within long reference pages

#### Template Structure

Both templates follow the same three-column pattern:

```jinja2
<div class="docs-layout">
  {# Left Sidebar: Navigation #}
  <aside class="docs-sidebar" id="docs-sidebar">
    {% include 'partials/docs-nav.html' %}
  </aside>
  
  {# Main Content #}
  <div class="docs-main">
    {% include 'partials/breadcrumbs.html' %}
    <article class="prose api-reference-page">
      {# Page-specific header with icon, metadata #}
      {# Main content #}
    </article>
    {% include 'partials/page-navigation.html' %}
  </div>
  
  {# Right Sidebar: TOC #}
  <aside class="docs-toc">
    {% include 'partials/toc-sidebar.html' %}
  </aside>
</div>
```

### CSS Additions

Added styles to `components/reference-docs.css`:

#### API Page Styles
- `.api-reference-page .api-header-top` - Icon + title layout
- `.api-reference-page .api-page-icon` - Module emoji/icon
- `.api-reference-page .api-meta` - Module metadata box (source file, module path)
- `.api-reference-page .api-meta-item` - Individual metadata items

#### CLI Page Styles
- `.cli-reference-page .cli-header-top` - Icon + title layout
- `.cli-reference-page .cli-page-icon` - Command emoji/icon
- `.cli-reference-page .cli-usage-header` - Command usage box
- `.cli-reference-page .cli-usage-header pre` - Usage code block

All styles integrate with existing design system variables and support dark mode.

## How It Works

### Template Selection

Enhanced Bengal's template selection logic (in `bengal/rendering/renderer.py`):

For regular pages (non-index), tries in order:
1. Explicit `template:` in frontmatter
2. **Type-based selection** (NEW):
   - Check section's `content_type` → try `{content_type}/single.html`
   - Check page's `type` field → map to content type → try `{content_type}/single.html`
   - Mappings: `python-module` → `api-reference`, `cli-command` → `cli-reference`
3. Section-based selection:
   - `{section_name}/single.html` 
   - `{section_name}/page.html`
   - `{section_name}.html`
4. Fallback: `page.html`

This means autodoc-generated pages with `type: python-module` automatically use `api-reference/single.html`!

### Section Name Detection

From `bengal/orchestration/section.py`:

- **API sections**: `api`, `reference`, `api-reference`, `api-docs` → `api-reference` type
- **CLI sections**: `cli`, `commands`, `cli-reference`, `command-line` → `cli-reference` type

### Alias Templates

To support both naming conventions:
- Sections named `api` → use `api/single.html` → extends `api-reference/single.html`
- Sections named `cli` → use `cli/single.html` → extends `cli-reference/single.html`

No code changes needed—templates work for any naming pattern.

## Features

### Left Sidebar Navigation
- Shows hierarchical structure (packages, modules, commands)
- Active page highlighting with border accent
- Collapsible sections with expand/collapse
- Scoped to current section tree (doesn't show entire site)
- Sticky positioning on desktop
- Mobile drawer with overlay on mobile

### Right Sidebar TOC
- Quick navigation within long pages
- Classes, functions, options sections
- Sticky positioning on desktop
- Hidden on tablet/mobile

### Responsive Behavior
- **Desktop (>1280px)**: Three columns (nav + content + TOC)
- **Tablet (768-1280px)**: Two columns (nav + content, TOC hidden)
- **Mobile (<768px)**: Single column, nav becomes drawer with toggle button

### Mobile Features
- Floating toggle button (bottom-left)
- Slide-in drawer animation
- Semi-transparent overlay
- Close on: overlay click, ESC key, link click
- Prevents body scroll when open

## Benefits

1. **Consistency**: All reference documentation now has same navigation pattern
2. **Discoverability**: Easy to explore related modules/commands without going back
3. **Context**: Always see where you are in the API/CLI structure
4. **Efficiency**: Faster navigation for large APIs with many modules
5. **Mobile-Friendly**: Same great experience on all devices
6. **Zero Breaking Changes**: Only adds templates, no existing behavior changed

## Testing Recommendations

1. **Build with API docs**: Run `bengal autodoc` then `bengal build`
2. **Check navigation**: Verify left sidebar shows module hierarchy
3. **Check active state**: Current page should be highlighted
4. **Test mobile**: Resize browser, check drawer functionality
5. **Test both names**: Try sections named `api` and `api-reference`
6. **CLI docs**: Same tests with CLI reference sections

## Future Enhancements

Potential improvements:
- Auto-expand active section in navigation
- Search within API/CLI docs
- Version switcher in sidebar
- Copy module import path button
- Link to source code on GitHub

## Code Changes

### Template Selection Enhancement

**File**: `bengal/rendering/renderer.py`  
**Method**: `_get_template_name()`

Added type-based template selection that checks:
1. Section's `content_type` metadata (set by `SectionOrchestrator`)
2. Page's `type` field with mappings:
   - `python-module` → `api-reference/single.html`
   - `cli-command` → `cli-reference/single.html`

This allows autodoc-generated pages to automatically use the sidebar templates without requiring explicit `template:` in frontmatter.

## Related Files

### Templates
- `bengal/themes/default/templates/api-reference/single.html`
- `bengal/themes/default/templates/cli-reference/single.html`
- `bengal/themes/default/templates/api/single.html`
- `bengal/themes/default/templates/cli/single.html`
- `bengal/themes/default/templates/doc.html` (reference template)

### CSS
- `bengal/themes/default/assets/css/components/reference-docs.css`
- `bengal/themes/default/assets/css/composition/layouts.css` (docs-layout)
- `bengal/themes/default/assets/css/components/docs-nav.css`

### Partials
- `bengal/themes/default/templates/partials/docs-nav.html`
- `bengal/themes/default/templates/partials/docs-nav-section.html`
- `bengal/themes/default/templates/partials/toc-sidebar.html`

## Notes

- The navigation partial is truly reusable—it works for any hierarchical section structure
- The `docs-*` CSS classes are generic enough for all documentation types
- No backend changes needed—pure template/CSS enhancement
- Backward compatible—existing customizations will continue to work

