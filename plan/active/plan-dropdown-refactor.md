# Plan: Refactor Navigation Dropdowns

**Status**: Draft  
**Parent RFC**: `rfc-premium-tactile-theme.md`  
**Created**: 2025-01-XX

## Problem Statement

Current nav dropdown implementation has multiple issues:
1. **Complex positioning calculations** - `calc(100% + var(--space-2))` accounts for multiple padding layers
2. **Hover gap hack** - Requires `::after` pseudo-element bridge to prevent flicker
3. **Fragile keyboard navigation** - `:focus-within` with `!important` overrides
4. **Alignment complexity** - `left: var(--space-4)` tries to match nav item padding

## Proposed Solution: Wrapper-Based Dropdown

### Approach: Position Relative to Nav Item (`<a>`)

Instead of positioning relative to `<li>`, position relative to the `<a>` element itself. This eliminates padding calculations.

**Benefits**:
- Simpler positioning: `top: 100%` directly below nav item
- No hover gap: Dropdown connects seamlessly
- Better alignment: `left: 0` aligns with nav item's left edge
- Cleaner CSS: No bridge hacks needed

### Alternative: JavaScript-Controlled (Like Theme Dropdown)

Use JavaScript to toggle `.open` class, similar to theme dropdown pattern.

**Benefits**:
- More reliable keyboard navigation
- No CSS `:focus-within` fragility
- Consistent with theme dropdown pattern
- Better control over timing/animations

## Implementation Options

### Option 1: CSS-Only Refactor (Position Relative to `<a>`)

**Changes**:
- Move positioning context from `<li>` to `<a>`
- Use `position: relative` on nav item `<a>` when it has submenu
- Dropdown positioned `top: 100%` directly below `<a>`
- Remove hover bridge hack

**Pros**: No JavaScript needed, simpler CSS  
**Cons**: Still relies on `:focus-within` for keyboard

### Option 2: JavaScript-Controlled (Recommended)

**Changes**:
- Add JavaScript to handle dropdown state
- Use `.open` class toggle (like theme dropdown)
- Position relative to `<a>` element
- Handle keyboard navigation in JS

**Pros**: More reliable, consistent pattern, better control  
**Cons**: Requires JavaScript

### Option 3: Hybrid Approach

**Changes**:
- CSS for hover (immediate feedback)
- JavaScript for keyboard navigation and state management
- Position relative to `<a>` element

**Pros**: Best of both worlds  
**Cons**: More complex

## Recommended: Option 2 (JavaScript-Controlled)

Matches theme dropdown pattern, more reliable, and eliminates CSS complexity.

## Implementation Steps

1. **Create dropdown JavaScript module** (`nav-dropdown.js`)
   - Handle click/hover on nav items with submenus
   - Toggle `.open` class
   - Keyboard navigation (Arrow keys, Escape)
   - Click outside to close

2. **Refactor CSS positioning**
   - Position relative to `<a>` instead of `<li>`
   - Remove hover bridge hack
   - Simplify positioning calculations
   - Use `.open` class for visibility

3. **Update HTML structure** (if needed)
   - Ensure nav items have proper structure
   - Add ARIA attributes for accessibility

4. **Test**
   - Mouse hover/click
   - Keyboard navigation
   - Mobile behavior
   - All 5 breed palettes

## Files to Modify

- `bengal/themes/default/assets/css/layouts/header.css` - Dropdown styles
- `bengal/themes/default/assets/js/nav-dropdown.js` - New JavaScript module
- `bengal/themes/default/templates/base.html` - Include JS module

## Success Criteria

- ✅ Dropdown starts exactly at bottom of nav item (no gap)
- ✅ No hover gap flicker
- ✅ Keyboard navigation works reliably
- ✅ Aligns with nav item's left edge
- ✅ Consistent with theme dropdown pattern
- ✅ No CSS hacks or workarounds

## Estimated Effort

- JavaScript module: 1-2 hours
- CSS refactor: 30 minutes
- Testing: 30 minutes
- **Total**: 2-3 hours

## Next Steps

1. Review and approve approach
2. Implement JavaScript module
3. Refactor CSS
4. Test across browsers/palettes
5. Update RFC with completion status



