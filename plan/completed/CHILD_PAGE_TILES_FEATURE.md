# Child Page Tiles Feature Implementation

**Date:** 2025-10-10  
**Status:** ✅ Completed

## Summary

Implemented a reusable partial for displaying child pages and subsections as tiles on index pages, with the ability to disable this feature via frontmatter.

## Problem Statement

The user asked:
1. Do we have a partial for child page tiles?
2. Should it be added automatically to index pages, especially if they're empty?
3. Should it be disable-able from frontmatter?

## Solution

### 1. Created Reusable Partial

**File:** `bengal/themes/default/templates/partials/child-page-tiles.html`

- Displays subsections and pages in a **unified list** (no separate sections)
- **Weight-based sorting**: Orders by `weight` frontmatter (ascending)
- **Compact row-based layout** with icons (folder for sections, document for pages)
- Shows descriptions and smart metadata (page counts for sections, dates for pages)

### 2. Updated Templates

**Files:**
- `bengal/themes/default/templates/index.html` - Generic section indexes
- `bengal/themes/default/templates/doc/list.html` - Documentation list pages

Both templates now:
- Support `show_children` frontmatter option (defaults to `true`)
- Use the new `child-page-tiles.html` partial
- Have simplified markup by extracting repetitive code

### 3. Fixed Renderer Context

**File:** `bengal/rendering/renderer.py`

- Extended section context to include index pages and doc type pages
- Previously only reference documentation types got `posts` and `subsections` variables
- Now these page types have access to their section's child pages and subsections:
  - Index pages (`_index.md`, `index.md`)
  - Doc type pages (`type: doc`)
  - Reference pages (`api-reference`, `cli-reference`, `tutorial`)

### 4. Updated Documentation

**Files:**
- `bengal/themes/default/templates/README.md` - Added partial documentation
- `examples/child-page-tiles-demo.md` - Created comprehensive usage guide

### 5. Created Test Examples

**Files:**
- `examples/showcase/content/demo-tiles/` - Section with visible child tiles
  - `_index.md` - Index page with default behavior
  - `getting-started.md` - Sample child page
  - `advanced-features.md` - Sample child page

- `examples/showcase/content/demo-tiles-hidden/` - Section with hidden child tiles
  - `_index.md` - Index page with `show_children: false`
  - `hidden-page-1.md` - Sample hidden child page
  - `hidden-page-2.md` - Sample hidden child page

## Usage

### Default Behavior (Auto-Display)

```markdown
---
title: My Section
description: A section with child pages
---

# Welcome

Content here...

<!-- Child pages automatically appear below -->
```

### Disable Child Tiles

```markdown
---
title: My Section
show_children: false
---

# Custom Landing Page

Custom content without automatic child page tiles.
```

### Use Partial Directly

```jinja
{% include 'partials/child-page-tiles.html' %}

{# Or with options #}
{% include 'partials/child-page-tiles.html' with {
  'show_excerpt': false,
  'show_subsections': true
} %}
```

## Features

✅ **Automatic Display** - Child pages and subsections shown by default on index pages  
✅ **Disable via Frontmatter** - Set `show_children: false` to hide tiles  
✅ **Unified List** - Sections and pages displayed together (no artificial division)  
✅ **Weight-based Sorting** - Control order with `weight` frontmatter  
✅ **Compact Design** - Clean row-based layout instead of large cards  
✅ **Smart Icons** - Folder icon for sections, document icon for pages  
✅ **Reusable Partial** - Can be used in custom templates  
✅ **Semantic HTML** - Uses `<article>`, `<section>`, proper hierarchy  
✅ **Responsive Design** - Works on all screen sizes

## Technical Details

### Template Variables

The `child-page-tiles.html` partial expects:
- `posts` - List of child pages in the section
- `subsections` - List of child sections

### Sorting and Ordering

Items are automatically:
1. Merged into a unified list
2. Sorted by `weight` (ascending) - lower weight appears first
3. Items with same weight sorted alphabetically by title
4. Default weight is 0 if not specified

### Renderer Context

The renderer now adds section context for:
1. Generated pages (archives, tag pages)
2. Reference documentation (`api-reference`, `cli-reference`, `tutorial`)
3. **Index pages** (`_index.md`, `index.md`) ← NEW

This ensures `posts` and `subsections` variables are available in templates.

### Frontmatter Options

**For index pages:**
```yaml
---
title: My Section
show_children: false  # Disables automatic child tile display
---
```

**For ordering (all pages/sections):**
```yaml
---
title: Getting Started
weight: 1  # Lower weight = appears first
description: "Quick introduction"
---

---
title: Advanced Topics
weight: 10  # Higher weight = appears later  
---
```

## Benefits

1. **Better Navigation** - Users can easily discover child pages
2. **Flexible Control** - Can be disabled for custom landing pages  
3. **Weight-based Ordering** - Complete control over display order
4. **Unified Display** - No artificial division between sections and pages
5. **Compact Design** - More content visible without scrolling
6. **Consistent UI** - Reusable partial ensures consistent presentation
7. **Less Boilerplate** - Template code is simplified
8. **Maintainability** - Single source of truth for child page display logic

## Testing

✅ Built showcase example successfully (275 pages in 1.4s)  
✅ Verified child tiles render correctly on `/demo-tiles/`  
✅ Verified `show_children: false` works on `/demo-tiles-hidden/`  
✅ Verified child tiles render on doc list pages at `/docs/`  
✅ No linter errors  
✅ No template syntax errors

## Files Changed

1. ✅ `bengal/themes/default/templates/partials/child-page-tiles.html` (NEW)
2. ✅ `bengal/themes/default/templates/index.html` (UPDATED)
3. ✅ `bengal/themes/default/templates/doc/list.html` (UPDATED)
4. ✅ `bengal/themes/default/templates/README.md` (UPDATED)
5. ✅ `bengal/rendering/renderer.py` (UPDATED)
6. ✅ `examples/child-page-tiles-demo.md` (NEW)
7. ✅ `examples/showcase/content/demo-tiles/` (NEW - test cases)
8. ✅ `examples/showcase/content/demo-tiles-hidden/` (NEW - test cases)
9. ✅ `examples/showcase/content/docs/_index.md` (UPDATED - test doc list template)

## Future Enhancements

Possible future improvements:
- Add grid layout options (2-column, 3-column, etc.)
- Support custom sorting (by date, title, weight)
- Add filtering options (by tag, category)
- Support limiting number of displayed children
- Add "view all" link when children are limited

## Related Features

- `article-card.html` - Individual article card component
- `section-navigation.html` - Alternative section navigation with stats
- `docs-nav.html` - Hierarchical documentation navigation
- `breadcrumbs.html` - Breadcrumb navigation
