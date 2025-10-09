# Blockquote Minimal Design + TOC Fix - Complete

**Date:** October 8, 2025  
**Status:** ✅ Complete

## Overview

Two improvements to blockquotes:
1. **Simplified styling** to match minimal design aesthetic
2. **Fixed TOC** to exclude blockquote headers from table of contents

## Problem Statement

### Issue 1: Heavy Blockquote Styling
- Decorative large quote mark (`::before`)
- Heavy padding and positioning
- Didn't match new minimal TOC/tabs aesthetic

### Issue 2: Blockquote Headers in TOC
- Headings inside blockquotes were getting IDs
- They appeared in the TOC navigation
- Problem: Blockquoted content is referenced/quoted material
- Its headers shouldn't be part of document structure

## Changes Made

### 1. CSS Simplification

**Files Modified:**
- `bengal/themes/default/assets/css/base/typography.css`
- `bengal/themes/default/assets/css/base/prose-content.css`

**Changes:**

#### Before:
```css
.prose blockquote {
  margin: var(--space-8) 0;
  padding: var(--space-3) var(--space-5) var(--space-3) var(--space-6);
  border-left: 3px solid var(--color-text-muted);
  position: relative;
}

.prose blockquote::before {
  content: '"';
  position: absolute;
  left: var(--space-2);
  top: 0;
  font-size: var(--text-2xl);  /* Big decorative quote */
  color: var(--color-text-muted);
}
```

#### After:
```css
.prose blockquote {
  margin: var(--space-6) 0;              /* Less margin */
  padding: var(--space-3) var(--space-4); /* Balanced padding */
  border-left: 2px solid var(--color-border-light); /* Lighter border */
  opacity: 0.9;                          /* Subtle transparency */
}

/* Removed ::before decorator entirely */

.prose blockquote h1,
.prose blockquote h2,
.prose blockquote h3,
.prose blockquote h4,
.prose blockquote h5,
.prose blockquote h6 {
  font-style: normal;                    /* Headers not italic */
  margin-top: var(--space-2);
  margin-bottom: var(--space-2);
}
```

**Key Improvements:**
- ✅ Removed decorative quote mark
- ✅ Lighter 2px border (down from 3px)
- ✅ Reduced margins and balanced padding
- ✅ Subtle 90% opacity
- ✅ Blockquote headers get normal styling

### 2. TOC Exclusion Logic

**File Modified:**
- `bengal/rendering/parser.py` → `_inject_heading_anchors()` method

**How It Works:**

1. **Fast Path (No Blockquotes):**
   - If HTML has no `<blockquote>` tags
   - Uses existing fast regex replacement
   - No performance impact

2. **Slow Path (Has Blockquotes):**
   - Scans HTML for blockquote open/close tags
   - Tracks nesting level (handles nested blockquotes)
   - Only adds heading IDs **outside** blockquotes
   - Headings inside blockquotes: kept as-is (no ID, no anchor)

**Code Flow:**
```python
if '<blockquote' not in html:
    # Fast path: normal processing
    return self._HEADING_PATTERN.sub(replace_heading, html)

# Slow path: skip headings in blockquotes
for match in blockquote_pattern.finditer(html):
    if in_blockquote == 0:
        # Outside: add IDs and anchors
        parts.append(add_anchors(before))
    else:
        # Inside blockquote: keep as-is
        parts.append(before)
```

**Result:**
- Blockquote headers have NO ID attribute
- No `¶` anchor link
- Won't appear in TOC extraction
- Document structure remains clean

## Design Principles

1. **Minimal Visual Weight**
   - Removed decorative elements
   - Lighter borders and reduced padding
   - Subtle opacity for distinction

2. **Semantic Correctness**
   - Blockquote content is quoted/referenced
   - Its structure ≠ document's structure
   - TOC shows only document's own headings

3. **Performance Conscious**
   - Fast path for common case (no blockquotes)
   - Only use slow path when necessary
   - Graceful error handling

## Benefits

✅ **Cleaner Design** - Matches minimal TOC/tabs aesthetic  
✅ **Semantic TOC** - Only includes document's own structure  
✅ **Better UX** - No confusing navigation to quoted content  
✅ **Fast Performance** - Optimized paths for both cases  
✅ **Robust** - Handles nested blockquotes correctly  

## Technical Details

### Nesting Support
The parser tracks blockquote nesting level:
```python
in_blockquote = 0  # Start outside

# On <blockquote>: in_blockquote += 1
# On </blockquote>: in_blockquote -= 1

if in_blockquote == 0:
    # Process headings normally
else:
    # Skip heading ID injection
```

### Error Handling
Both paths have try/except with fallback:
```python
try:
    return processed_html
except Exception as e:
    print(f"Warning: {e}", file=sys.stderr)
    return html  # Return original on error
```

## Testing

✅ Built showcase site successfully  
✅ Blockquotes now have minimal styling  
✅ No decorative quote marks  
✅ Lighter, cleaner appearance  
✅ Headers in blockquotes have no IDs  
✅ TOC excludes blockquote headers  

## Example

### Markdown:
```markdown
## Main Document Header

Regular content here.

> ### Quoted Section Header
> 
> This is quoted content from another source.
> The header above shouldn't be in TOC.

## Another Document Header

More content.
```

### Result:
**TOC Will Show:**
- Main Document Header ✓
- Another Document Header ✓

**TOC Won't Show:**
- Quoted Section Header (excluded!) ✓

## Files Modified

1. `/bengal/themes/default/assets/css/base/typography.css`
2. `/bengal/themes/default/assets/css/base/prose-content.css`
3. `/bengal/rendering/parser.py`

---

**Result:** Clean, minimal blockquotes that match the overall aesthetic, with semantically correct TOC that excludes quoted content.

