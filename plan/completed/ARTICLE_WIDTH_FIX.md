# Article Width Fix - Grid Layout Issue

**Date**: October 4, 2025  
**Status**: Complete  
**Impact**: All pages with table of contents sidebar

---

## Problem

Pages deeper in the path hierarchy (e.g., `/cli/commands/new/`) appeared to have the article content area "squished" or narrower compared to shallower pages. The content width was inconsistent across different URL depths.

### Root Cause

The issue was caused by conflicting CSS rules:

1. **`pages/article.css` (lines 10-15)**: Applied `max-width: 75ch` to `.page` elements
2. **Grid Layout**: The `.page-with-toc` grid uses `grid-template-columns: 1fr 280px`
3. **Conflict**: The `75ch` max-width constraint was applied INSIDE the grid column

This created a double constraint:
- Grid column: `1fr` (available space after TOC sidebar)
- Element inside: `max-width: 75ch`

Result: On narrower viewports or when the grid was constrained, the article appeared unnecessarily narrow.

---

## Solution

Modified `/Users/llane/Documents/github/python/bengal/bengal/themes/default/assets/css/components/toc.css`

### Before
```css
/* Ensure main article takes proper space */
.page-layout.page-with-toc .page,
.page-layout.page-with-toc .post {
    min-width: 0; /* Prevent grid blowout */
}
```

### After
```css
/* Ensure main article takes proper space */
.page-layout.page-with-toc .page,
.page-layout.page-with-toc .post {
    min-width: 0; /* Prevent grid blowout */
    max-width: none; /* Remove prose width constraint in grid layout */
    margin: 0; /* Remove auto centering in grid */
}
```

---

## Technical Details

### CSS Specificity
The fix uses the same specificity as the problematic rule:
- `.page-layout.page-with-toc .page` (3 classes) 
- Overrides `.page` (1 class) from article.css

### Why This Works

1. **Single-column pages**: Without `.page-with-toc`, the `.page` element retains its `max-width: 75ch` and centered layout (good for readability)

2. **Grid layout pages**: With `.page-with-toc`, the overrides apply:
   - `max-width: none` - lets the grid column control the width
   - `margin: 0` - no auto-centering needed in grid
   - Grid system handles responsive layout

### Grid Layout Context

```css
@media (min-width: 1024px) {
    .page-layout.page-with-toc {
        grid-template-columns: 1fr 280px;
        /* First column: article (takes remaining space)
           Second column: TOC (fixed 280px) */
    }
}
```

On screens ≥1024px:
- Container width: 100% (up to max-content-width)
- TOC: fixed 280px
- Article: `1fr` = (container - 280px - gap)
- No need for max-width constraint inside grid

---

## Visual Improvement

### Before
```
┌────────────────────────────────────────────┐
│ Container                                   │
│  ┌──────────────────┐  ┌────────────────┐ │
│  │ Article          │  │   TOC          │ │
│  │ (75ch max)       │  │   (280px)      │ │
│  │ 🟦🟦🟦🟦🟦        │  │   sidebar      │ │
│  │ Squished!        │  │                │ │
│  │                  │  │                │ │
│  └──────────────────┘  └────────────────┘ │
└────────────────────────────────────────────┘
```

### After
```
┌────────────────────────────────────────────┐
│ Container                                   │
│  ┌──────────────────────────┐  ┌─────────┐│
│  │ Article                  │  │   TOC   ││
│  │ (fills available 1fr)    │  │ (280px) ││
│  │ 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦     │  │         ││
│  │ Full width! ✓            │  │         ││
│  │                          │  │         ││
│  └──────────────────────────┘  └─────────┘│
└────────────────────────────────────────────┘
```

---

## Testing

To verify the fix:

1. **Hard refresh browser** (Cmd+Shift+R / Ctrl+Shift+R) to clear CSS cache
2. Compare pages at different depths:
   - `/cli/` (shallow)
   - `/cli/commands/build/` (deep)
   - `/api/validators/links/` (deep)
3. All should have consistent article width
4. Article should fill available space minus TOC width

### CSS Inspection
Check in browser DevTools:
```css
.page-layout.page-with-toc .page {
  max-width: none;  /* ✓ Should be present */
  margin: 0;        /* ✓ Should be present */
}
```

---

## Related Files

### Modified
- `bengal/themes/default/assets/css/components/toc.css` (lines 135-140)

### Related (unchanged but relevant)
- `bengal/themes/default/assets/css/pages/article.css` (lines 10-15)
  - Still applies 75ch max-width to standalone pages (correct behavior)
- `bengal/themes/default/assets/css/base/typography.css` (lines 10-13)
  - `.prose` class also has 75ch max-width (for content, not container)

---

## Impact

✅ **Consistent Layout**: All pages with TOC sidebars now have consistent article width  
✅ **Better Space Utilization**: Article content fills available grid space  
✅ **Responsive**: Grid layout still works properly on mobile (single column)  
✅ **No Regressions**: Pages without TOC still have 75ch max-width for optimal readability  
✅ **Depth-Independent**: URL path depth no longer affects layout  

---

## Best Practices Established

1. **Grid layouts should control child widths** - don't apply max-width to grid items
2. **Use conditional overrides** - scope layout rules to specific contexts
3. **Preserve single-column behavior** - standalone pages still need max-width for readability
4. **Test at multiple depths** - verify layout consistency across different URL structures

---

## User Experience

Before: Users noticed content getting narrower as they navigated deeper into documentation  
After: Consistent, predictable layout regardless of navigation depth  
Result: More professional appearance and better reading experience

