# Documentation Layout Fixes

## Problem Summary

The documentation layout had two issues:

1. **Sidebar showing entire site tree**: The left sidebar navigation was displaying ALL sections from the entire site instead of just the docs section tree
2. **Child pages not inheriting layout**: Only the docs index page had the three-column docs layout, while child pages reverted to the default page template

## Solutions Implemented

### 1. Scoped Sidebar Navigation

**File**: `bengal/themes/default/templates/partials/docs-nav.html`

**Change**: Modified the navigation tree logic to detect the current page's section and show only that section's tree, rather than all top-level sections.

**How it works**:
- When a page is rendered, the template checks if it has a `_section` property
- It traverses up the section hierarchy to find the root section
- It then displays only that section's pages and subsections
- Falls back to showing all sections if no section is detected (backwards compatibility)

**Result**: When viewing any page in `/docs/`, the sidebar now shows only the docs tree, not posts, tutorials, etc.

### 2. Template Inheritance via Cascade

**File**: `examples/quickstart/content/docs/_index.md`

**Change**: Added cascade configuration to apply the `docs.html` template to all child pages:

```yaml
---
title: "Documentation"
description: "Complete documentation for Bengal SSG features and capabilities"
template: docs.html
cascade:
  template: docs.html
---
```

**How it works**:
- The `template: docs.html` ensures the index page itself uses the docs template
- The `cascade:` block applies `template: docs.html` to ALL descendant pages
- This is Bengal's built-in Hugo-style cascade feature for frontmatter inheritance
- Child pages can still override the template if needed by specifying their own `template:` value

**Result**: All pages under `/docs/` now automatically use the three-column documentation layout with:
- Left sidebar: Section navigation
- Center: Page content
- Right sidebar: Table of contents

## Verification

Build output shows successful generation:
```
✨ Built 83 pages in 1.3s
```

HTML structure verification confirms proper template usage:
- `docs-layout` - Three-column container
- `docs-sidebar` - Left navigation showing only docs tree
- `docs-main` - Center content area
- `docs-toc` - Right table of contents

## Usage Guidelines

### For Any Documentation Section

To apply this pattern to any section (e.g., `/api/`, `/guides/`):

1. Add cascade to the section's `_index.md`:
```yaml
---
title: "API Documentation"
template: docs.html
cascade:
  template: docs.html
---
```

2. The sidebar will automatically scope to that section's tree

### For Custom Template per Section

If you want different subsections to have different layouts:

```yaml
# content/api/_index.md
---
cascade:
  template: api-doc.html  # Custom template for API docs
---

# content/guides/_index.md  
---
cascade:
  template: guide.html  # Different template for guides
---
```

### Override for Specific Pages

A specific page can override the cascaded template:

```yaml
# content/docs/special-page.md
---
title: "Special Page"
template: custom.html  # Override the cascaded docs.html
---
```

## Benefits

1. **DRY Principle**: Define template once in `_index.md`, applies to all children
2. **Consistent UX**: All docs pages have the same navigation and layout
3. **Easy Maintenance**: Change template in one place to update entire section
4. **Smart Scoping**: Sidebar automatically shows only relevant section tree
5. **Flexible**: Can still override on a per-page basis when needed

## Technical Details

**Template Selection Priority** (from `bengal/rendering/renderer.py`):
1. Explicit page frontmatter `template:` (highest priority)
2. Cascaded template from parent section
3. Section-based auto-detection
4. Default fallback template

**Cascade Inheritance** (from `bengal/orchestration/content.py`):
- Cascades accumulate through section hierarchies
- Child cascade values merge with parent cascade values
- Page values override cascaded values
- Deeper cascades take precedence over shallower ones

