# Weight-Based Sorting Feature

**Date**: 2025-10-10  
**Status**: ✅ Completed

## Overview

Implemented the ability to sort files and directories by frontmatter `weight` field, allowing content authors to control the order in which pages and sections appear.

## Implementation

### 1. Core Changes

#### `bengal/core/section.py`
- Added `sorted_pages` property: Returns pages sorted by weight (ascending), then title
- Added `sorted_subsections` property: Returns subsections sorted by weight (ascending), then title
- Added `sort_children_by_weight()` method: Sorts pages and subsections in-place
- Updated `add_page()` to copy all metadata from index pages to section metadata (not just cascade)

#### `bengal/discovery/content_discovery.py`
- Added `_sort_all_sections()` method: Recursively sorts all sections after discovery
- Added `_sort_section_recursive()` method: Helper to recursively sort a section and its children
- Integrated sorting into the `discover()` workflow (called after content discovery completes)

#### `bengal/rendering/renderer.py`
- Updated template context to use `section.sorted_pages` and `section.sorted_subsections`
- Added documentation explaining pre-sorting during discovery

#### `bengal/themes/default/templates/partials/child-page-tiles.html`
- Updated comments to document that data is pre-sorted by weight during discovery
- Template continues to re-sort merged lists (for combining pages and sections)

## How It Works

### For Content Authors

Add a `weight` field to frontmatter to control ordering:

```yaml
---
title: "Getting Started"
weight: 1
---
```

- **Lower weights appear first** (ascending order)
- Pages/sections without a weight field are treated as `weight: 0`
- When weights are equal, items are sorted alphabetically by title
- Works for both pages and sections (via `_index.md`)

### Sorting Algorithm

1. **During Content Discovery**: After all pages and sections are discovered, `_sort_all_sections()` recursively sorts:
   - Pages within each section
   - Subsections within each section
   - Top-level sections

2. **Sort Key**: `(weight, title.lower())`
   - Primary: Weight (ascending, 0 if not specified)
   - Secondary: Title (case-insensitive alphabetical)

3. **In Templates**: Pre-sorted data is passed via `posts` and `subsections` variables

## Testing

Created comprehensive test content in `examples/showcase/content/demo-sorting-test/`:
- Pages with varying weights (1, 50, 100)
- Subsections with different weights (10, 200)
- Verified both pages and subsections sort correctly

**Test Results**:
```
✅ Pages ARE correctly sorted by weight (ascending)
✅ Subsections ARE correctly sorted by weight (ascending)

Expected Order:
  Pages:       A Page (1) → M Page (50) → Z Page (100)
  Subsections: Subsection B (10) → Subsection A (200)
```

## Examples

### Example 1: Blog Posts by Priority

```yaml
# content/blog/announcement.md
---
title: "Important Announcement"
weight: 1  # Appears first
---

# content/blog/tutorial.md
---
title: "Tutorial"
weight: 10  # Appears after announcements
---
```

### Example 2: Documentation Sections

```yaml
# content/docs/getting-started/_index.md
---
title: "Getting Started"
weight: 1  # First section
---

# content/docs/advanced/_index.md
---
title: "Advanced Topics"
weight: 100  # Last section
---
```

### Example 3: Mixed Content (Pages + Sections)

When a section has both child pages and subsections, they are merged and sorted together by weight in the template.

## API

### Section Properties

```python
section.sorted_pages        # Pages sorted by weight, then title
section.sorted_subsections  # Subsections sorted by weight, then title
section.sort_children_by_weight()  # Sort in-place (called during discovery)
```

### Template Variables

Templates receive pre-sorted data:
```jinja2
{% for page in posts %}           {# Already sorted by weight #}
{% for subsection in subsections %} {# Already sorted by weight #}
```

## Performance

- Sorting happens once during content discovery (O(n log n) per section)
- Pre-sorted data means no runtime sorting overhead in templates
- Properties (`sorted_pages`, `sorted_subsections`) re-sort on access (safe but slightly slower than using pre-sorted lists)

## Backwards Compatibility

- ✅ Fully backwards compatible
- Content without `weight` fields defaults to `weight: 0`
- Alphabetical sorting is preserved as secondary sort key
- Existing templates continue to work without modification

## Future Enhancements

Possible improvements:
- Add `sort_order` config option (ascending/descending)
- Support negative weights for "pinning to top"
- Add `sort_by` field to customize sort key (date, title, custom field)
- Cache sorted lists if performance becomes an issue

## Related Files

- `bengal/core/section.py` - Section sorting logic
- `bengal/discovery/content_discovery.py` - Discovery-time sorting
- `bengal/rendering/renderer.py` - Template context
- `bengal/themes/default/templates/partials/child-page-tiles.html` - Display component
- `examples/showcase/content/demo-sorting-test/` - Test content
- `examples/showcase/content/demo-tiles/` - Demo content

## Commit Message

```
feat: Add weight-based sorting for pages and sections

- Add sorted_pages and sorted_subsections properties to Section
- Sort content by weight during discovery (ascending order)
- Update templates to use pre-sorted data
- Support weight field in frontmatter for both pages and sections
- Default to weight=0 for content without explicit weight
- Secondary sort by title (alphabetically) when weights are equal

Closes: #XXX
```

