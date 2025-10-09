# Anchor Link System Merge - Implementation Summary

**Date**: October 9, 2025
**Status**: ✅ Complete

## Problem
The site had two redundant anchor link systems creating visual clutter:
1. **Pilcrow (¶) symbol** - Always visible, unstyled, acted as permalink
2. **Chain link icon** - Hover to reveal, copied URL to clipboard

Both served similar purposes but were implemented separately, creating a distracting user experience.

## Solution Implemented
Merged both systems into a single smart anchor link that:
- Regular click: Copies URL to clipboard (existing behavior)
- Right-click/Ctrl+click: Works as native permalink (new)
- Maintains polished hover/focus states
- Proper accessibility with ARIA labels

## Changes Made

### 1. Parser Updates (`bengal/rendering/parser.py`)
**Removed pilcrow from heading injection (3 locations):**
- Lines 472-473: Fast path heading injection
- Lines 512-513: Blockquote path heading injection  
- Lines 546-547: Remaining content heading injection

Changed from:
```python
f'<{tag} id="{slug}"{attrs}>{content}'
f'<a href="#{slug}" class="headerlink" title="Permanent link">¶</a>'
f'</{tag}>'
```

To:
```python
f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'
```

**Updated TOC pattern (line 125-128):**
Changed regex from:
```python
r'<(h[234])\s+id="([^"]+)"[^>]*>(.*?)<a[^>]*>¶</a></\1>'
```

To:
```python
r'<(h[234])\s+id="([^"]+)"[^>]*>(.*?)</\1>'
```

**Disabled python-markdown pilcrow (line 81):**
```python
'permalink': False,  # Permalink handled by JavaScript copy-link
```

### 2. JavaScript Enhancement (`bengal/themes/default/assets/js/copy-link.js`)
**Converted button to anchor tag (lines 30-58):**
- Changed from `createElement('button')` to `createElement('a')`
- Added `href="#${id}"` attribute for native link behavior
- Smart click handler: intercepts left-click, preserves right-click/modifier keys
- Updated comments and console log messages

```javascript
// Create copy link (anchor tag for proper link semantics)
const link = document.createElement('a');
link.href = `#${id}`;
link.className = 'copy-link';

// Only intercept normal left-clicks without modifiers
link.addEventListener('click', function(e) {
  if (!e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) {
    e.preventDefault();
    const url = `${window.location.origin}${window.location.pathname}#${id}`;
    copyToClipboard(url, link);
  }
  // Otherwise let the browser handle it as a normal link
});
```

### 3. CSS Update (`bengal/themes/default/assets/css/components/interactive.css`)
**Added text-decoration property (line 136):**
```css
.copy-link {
  /* ... existing styles ... */
  text-decoration: none; /* Remove underline for anchor tags */
}
```

## Testing Results

### ✅ Parser Tests
```
Test 1 - Heading with ID (no pilcrow):
<h2 id="test-heading">Test Heading</h2>

Test 2 - TOC Generation:
<div class="toc">
  <li><a href="#first-section">First Section</a></li>
  <li><a href="#subsection">Subsection</a></li>
</div>

Test 3 - Blockquote handling: ✓
```

### ✅ Build Tests
- Full site build: 245 pages in 1.0s
- No linter errors
- Headings have clean IDs without pilcrow
- TOC correctly links to heading IDs

### ✅ Generated HTML Verification
Before:
```html
<h2 id="overview">Overview<a href="#overview" class="headerlink">¶</a></h2>
```

After:
```html
<h2 id="overview">Overview</h2>
```

TOC still works:
```html
<a href="#overview" class="toc-link">Overview</a>
```

## Benefits

### User Experience
- **Cleaner visual design** - No distracting pilcrow symbols
- **Better UX** - Single icon serves both purposes
- **Familiar interaction** - Hover to reveal, click to copy
- **Power user friendly** - Right-click/Ctrl+click for native link behavior

### Technical
- **Proper semantics** - Using `<a>` tag instead of `<button>`
- **Accessibility** - Works with keyboard navigation and screen readers
- **Performance** - No impact on build times or TOC generation
- **Maintainability** - Single system instead of two redundant ones

## Backward Compatibility
- ✅ TOC generation still works correctly
- ✅ Heading IDs are still generated
- ✅ All anchor links function properly
- ✅ Works with both Mistune and python-markdown parsers
- ✅ No breaking changes to templates or existing pages

## Files Modified
1. `bengal/rendering/parser.py` - Removed pilcrow injection, updated TOC regex
2. `bengal/themes/default/assets/js/copy-link.js` - Converted to anchor tag with smart click
3. `bengal/themes/default/assets/css/components/interactive.css` - Added text-decoration

## Next Steps
None required - implementation is complete and tested.

## Notes
The implementation properly handles both parser engines:
- **Mistune**: Pilcrow removed from `_inject_heading_anchors()` method
- **Python-markdown**: Pilcrow disabled via `'permalink': False` config

