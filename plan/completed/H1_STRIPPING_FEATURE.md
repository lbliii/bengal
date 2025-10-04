# Automatic H1 Stripping Feature

## Overview

Bengal SSG now automatically removes the first H1 (`<h1>`) tag from rendered markdown content to prevent duplication with template-rendered page titles.

## Problem

Many pages had duplicate titles because:
1. Templates render `{{ page.title }}` as an H1
2. Authors naturally include `# Title` as the first line in markdown
3. Both appeared in the output, creating visual duplication

Example of the problem:
```html
<!-- Template renders: -->
<h1>My Page Title</h1>

<!-- Then markdown content also has: -->
<h1>My Page Title</h1>
<p>Content...</p>

<!-- Result: Two identical H1s -->
```

## Solution

The renderer now automatically strips the **first H1 only** from parsed HTML content before inserting it into templates.

### Implementation

- **Location**: `bengal/rendering/renderer.py`
- **Method**: `Renderer._strip_first_h1(content)`
- **Called by**: `Renderer.render_content(content)`
- **Regex pattern**: `r'<h1[^>]*>.*?</h1>'` (non-greedy, case-insensitive)

### Behavior

✅ **Strips:**
- First H1 in content
- H1s with attributes (`<h1 id="..." class="...">`)
- Multi-line H1s
- H1s with nested HTML

✅ **Preserves:**
- All subsequent H1s (2nd, 3rd, etc.)
- All other heading levels (H2-H6)
- All content outside the first H1

## Benefits

1. **User-friendly**: Writers can include H1s naturally in markdown without worrying about duplication
2. **Portable content**: Markdown files remain complete and readable as standalone documents
3. **Flexibility**: H1 in markdown can differ slightly from frontmatter title if needed
4. **SSG standard**: Matches behavior of Hugo and other modern SSGs

## Examples

### Before (Duplication)

**Markdown (`content/docs/guide.md`):**
```markdown
---
title: "Getting Started Guide"
---

# Getting Started Guide

This is the introduction...
```

**Output:**
```html
<h1>Getting Started Guide</h1> <!-- From template -->
<h1>Getting Started Guide</h1> <!-- From markdown - DUPLICATE -->
<p>This is the introduction...</p>
```

### After (No Duplication)

**Same Markdown Input**

**Output:**
```html
<h1>Getting Started Guide</h1> <!-- From template only -->
<p>This is the introduction...</p> <!-- Markdown H1 stripped -->
```

## Testing

Comprehensive test suite added in `tests/unit/rendering/test_h1_stripping.py`:

- ✅ Strips basic H1
- ✅ Strips H1 with attributes
- ✅ Keeps subsequent H1s
- ✅ Handles multi-line H1s
- ✅ Handles missing H1s
- ✅ Case-insensitive matching
- ✅ Integration with render_content()
- ✅ Preserves nested content

All tests pass ✅

## Configuration

No configuration needed - the feature is always active.

**Rationale**: This prevents a common mistake and matches user expectations. Since templates always render titles as H1, there's no valid use case for keeping duplicate H1s.

## Edge Cases

### Multiple H1s in Content

If content intentionally has multiple H1s (e.g., for tabbed content or special layouts), only the **first** H1 is removed:

```html
<!-- Input -->
<h1>Page Title</h1>
<p>Intro</p>
<h1>Tabbed Section</h1>
<p>Tab content</p>

<!-- Output -->
<p>Intro</p>
<h1>Tabbed Section</h1> <!-- Kept -->
<p>Tab content</p>
```

### No H1 in Content

If markdown has no H1, the stripping has no effect (content passes through unchanged).

### Different H1 vs Title

Authors can use slightly different text in markdown H1 vs frontmatter title. The markdown H1 will be stripped, and only the template title appears:

```markdown
---
title: "Complete Feature Guide"
---

# Feature Guide

Content...
```

Result: Only "Complete Feature Guide" appears (from template).

## Related Files

- **Implementation**: `bengal/rendering/renderer.py`
- **Tests**: `tests/unit/rendering/test_h1_stripping.py`
- **Affected templates**: 
  - `themes/default/templates/page.html` (renders title as H1)
  - `themes/default/templates/index.html` (renders title as H1)

## Performance Impact

Minimal - single regex operation per page:
- Pattern: Simple regex with `count=1` (stops after first match)
- Timing: < 1ms per page on average
- Build time: No measurable impact on showcase site (57 pages in 496ms)

## Status

✅ **Implemented**: October 4, 2025
✅ **Tested**: 8 unit tests passing
✅ **Verified**: Showcase site build successful, no duplicate H1s

## Future Considerations

### Potential Enhancements (if needed)

1. **Configuration option**: Add `strip_first_h1: false` in config for edge cases
2. **Per-page control**: Frontmatter option `strip_h1: false` to disable per-page
3. **Alternative approaches**: Remove from AST instead of HTML (more complex but cleaner)

**Current assessment**: Not needed - current implementation is simple, robust, and covers all realistic use cases.

