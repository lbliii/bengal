# Child Page Tiles Demonstration

This example demonstrates the child page tiles feature in Bengal SSG.

## Overview

The `child-page-tiles.html` partial automatically displays child pages and subsections as compact rows on index pages. Features include:

- **Unified List**: Sections and pages displayed together (no artificial division)
- **Weight-based Sorting**: Control order with `weight` frontmatter (lower = higher priority)
- **Compact Design**: Clean row-based layout with icons
- **Smart Metadata**: Shows page counts for sections, dates for pages

## Basic Usage

By default, index pages (`_index.md`) automatically show child page tiles:

```markdown
---
title: My Section
description: A section with child pages
---

# Welcome to My Section

This is the main content of the section.

<!-- Child pages will automatically appear below -->
```

## Disabling Child Tiles

To hide child page tiles (useful when you want a custom landing page):

```markdown
---
title: My Section
description: A custom landing page
show_children: false
---

# Welcome to My Section

This section has custom content without showing child pages.
You might want to manually link to specific pages or create
a completely custom layout.
```

## Use Cases

### 1. Documentation Section with Auto-Navigation

```markdown
---
title: API Documentation
description: Complete API reference
# show_children defaults to true
---

Browse our API documentation:

<!-- Child pages automatically displayed as tiles -->
```

### 2. Marketing Landing Page

```markdown
---
title: Features
description: Product features overview
show_children: false
---

# Amazing Features

<hero content here>

<custom feature grid>

<!-- No child tiles, fully custom content -->
```

### 3. Control Ordering with Weight

```markdown
---
title: Getting Started
weight: 1
---

# Getting Started

Lower weight = appears first in list.
```

```markdown
---
title: Advanced Topics  
weight: 10
---

# Advanced Topics

Higher weight = appears later in list.
```

Pages/sections without weight default to 0.

## What Gets Displayed

The child page tiles partial shows sections and pages in a unified, sorted list:

**All Items Display:**
- Icon (folder for sections, document for pages)
- Title (linked)
- Description (if available)
- Metadata:
  - For sections: page count
  - For pages: date (shown as "time ago")

**Ordering:**
Items are sorted by `weight` (ascending), then alphabetically by title. This gives you complete control over the display order.

## Empty Index Pages

If an index page has no content and no children:
- An empty state message is shown
- Helpful guidance for adding content is displayed
- Suggestions for creating pages and subsections

## Technical Details

### Template Variables

The partial uses these variables:
- `posts` - List of child pages
- `subsections` - List of child sections

### Frontmatter Options

**For index pages:**
- `show_children: false` - Disables automatic child tile display

**For all pages/sections:**
- `weight: <number>` - Controls sort order (lower appears first)
- `description: "text"` - Shown in the tile

### How Sorting Works

1. Items merged into unified list
2. Sorted by `weight` (ascending)
3. Items with same weight sorted alphabetically by title
4. Default weight is 0 if not specified

### Customization

Simple include in any template:

```jinja
{% include "partials/child-page-tiles.html" %}
```

## Best Practices

1. **Use for navigation** - Great for section landing pages
2. **Disable for marketing** - Turn off for custom landing pages
3. **Combine with content** - Works well with intro text above tiles
4. **Keep descriptions short** - Write concise section descriptions
5. **Use metadata** - Add descriptions and images to child pages

## Related Features

- `article-card.html` - Individual article card component
- `section-navigation.html` - Alternative section navigation with stats
- `docs-nav.html` - Hierarchical documentation navigation

