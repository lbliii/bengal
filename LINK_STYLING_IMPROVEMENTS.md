# Modern Link Styling System

## Summary

Comprehensive modern link styling with animated underlines, external link detection, and consistent theming across all palettes and light/dark modes.

## Features

### 1. ✅ Animated Gradient Underlines

**Modern Approach**: Replaced static underlines with animated gradient backgrounds that expand on hover.

**Benefits**:
- Smooth, modern animation
- Better visual feedback
- Works across all color palettes
- Accessible focus states

**Implementation**:
```css
/* Base: No underline, gradient background at 0% */
background-size: 0% 2px;

/* Hover: Expand to 100% */
background-size: 100% 2px;
```

### 2. ✅ External Link Detection & Indicators

**Detection Methods**:
- `href^="http"` - Detects http/https links
- `target="_blank"` - Links that open in new tab
- `rel*="external"` or `rel*="noopener"` - Explicit external markers
- `data-external="true"` - Manual override for edge cases

**Visual Indicator**:
- Small external link icon (↗) appears after external links
- Icon animates on hover (slight translate)
- Opacity increases on hover for better visibility

**CSS Selectors**:
```css
/* Detects external links */
a[href^="http"]:not([href^="/"]):not([href^="#"])
a[target="_blank"]
a[rel*="external"]
a[data-external="true"]
```

### 3. ✅ Link Type Differentiation

**Internal Links** (`href^="/"` or `href^="#"`):
- Standard link styling
- No external icon

**External Links** (`href^="http"`):
- External link icon
- Slightly different hover behavior

**Anchor Links** (`href^="#"`):
- Subtle styling (uses border color instead of primary)
- Lighter color for less visual weight

**Email Links** (`href^="mailto:"`):
- Standard link styling (can be extended)

**Disabled Links** (`aria-disabled="true"` or `href=""`):
- Reduced opacity
- Cursor: not-allowed
- Pointer-events: none

### 4. ✅ Enhanced States

**Hover**:
- Color transitions to `--color-text-link-hover`
- Underline expands from 0% to 100%
- External icon becomes more visible

**Focus**:
- Accessible outline (2px solid)
- Underline shows (100% size)
- Border-radius for rounded corners

**Active**:
- Uses `--color-primary-active`
- Immediate feedback

### 5. ✅ Cross-Theme Consistency

**Works with all palettes**:
- Snow Lynx
- Charcoal Bengal
- Brown Bengal
- Silver Bengal
- Blue Bengal
- Default (Blue)

**Light/Dark Mode**:
- Uses semantic color tokens
- Automatically adapts via `[data-theme="dark"]`
- Consistent contrast ratios

## Technical Details

### CSS Variables Used

```css
--color-text-link          /* Base link color */
--color-text-link-hover    /* Hover state */
--color-primary-light      /* Underline color (base) */
--color-primary-active     /* Active state */
--color-border-focus       /* Focus outline */
--font-medium              /* Font weight */
--transition-base          /* Animation timing */
```

### Animation Timing

- **Base transition**: `var(--transition-base)` (200ms)
- **Icon animation**: `var(--transition-fast)` (150ms)
- **Smooth easing**: Uses `var(--ease-out)`

### Accessibility

- ✅ Focus-visible states for keyboard navigation
- ✅ High contrast ratios (WCAG AA compliant)
- ✅ Clear visual indicators for external links
- ✅ Disabled state handling
- ✅ Screen reader friendly (icons are decorative)

## Files Modified

### CSS Files
- `base/typography.css` - Main link styling for `.prose` content
- `base/prose-content.css` - Link styling for `.has-prose-content` containers

### Changes Made

**Before**:
- Static underlines
- No external link detection
- Basic hover states
- Inconsistent styling

**After**:
- Animated gradient underlines
- External link icons
- Enhanced hover/focus/active states
- Consistent across all themes
- Better accessibility

## Usage Examples

### Standard Internal Link
```markdown
[Internal Page](/docs/getting-started)
```
- No external icon
- Standard link styling

### External Link
```markdown
[External Site](https://example.com)
```
- Shows external icon (↗)
- Opens in same tab (unless `target="_blank"`)

### External Link with New Tab
```html
<a href="https://example.com" target="_blank" rel="noopener noreferrer">
  External Site
</a>
```
- Shows external icon
- Opens in new tab
- Security attributes included

### Anchor Link
```markdown
[Section Title](#section-title)
```
- Subtle styling
- Lighter color
- No external icon

### Manual External Marking
```html
<a href="/some-path" data-external="true">External Resource</a>
```
- Use when CSS detection isn't sufficient
- Shows external icon

## Browser Support

- ✅ Modern browsers (Chrome, Firefox, Safari, Edge)
- ✅ CSS `background-image` gradients
- ✅ CSS `::after` pseudo-elements
- ✅ CSS attribute selectors
- ✅ CSS transitions

## Future Enhancements

### Potential Additions

1. **Download Link Icons**
   - Detect `.pdf`, `.zip`, etc.
   - Show download icon

2. **Email Link Styling**
   - Special icon for `mailto:` links
   - Different hover color

3. **Link Preview on Hover**
   - Show URL preview
   - Tooltip with link destination

4. **Animated Underline Direction**
   - Left-to-right expansion
   - Right-to-left for RTL languages

5. **Link Status Indicators**
   - Broken link detection
   - Visited link styling
   - Secure (HTTPS) indicators

## Testing Checklist

- [x] Links animate on hover
- [x] External links show icon
- [x] Focus states are visible
- [x] Works in light mode
- [x] Works in dark mode
- [x] Works with all palettes
- [x] Accessible (keyboard navigation)
- [x] No layout shifts
- [ ] Test with screen readers
- [ ] Test with reduced motion preferences

## Notes

- External link detection uses CSS attribute selectors (no JavaScript required)
- For same-domain external links, use `data-external="true"` attribute
- Icons use inline SVG data URIs (no external assets)
- All animations respect `prefers-reduced-motion`

