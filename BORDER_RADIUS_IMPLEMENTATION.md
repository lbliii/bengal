# Border Radius Implementation Guide

**Option A: Cohesive Roundedness** - Quick implementation guide

---

## Summary of Changes

Add consistent roundedness across all elements for a more modern, approachable feel.

**Current → Proposed**:
- Cards: `8px` → `12px`
- Code blocks: `12px` → `16px`
- Buttons: `4px` → `8px`
- Forms/Inputs: `4px` → `8px`
- Tabs: `4px` → `8px`
- Dropdowns: `4px` → `8px`
- **Blockquotes**: `0` → `8px` ⚠️ (currently sharp!)
- Images: `4px` → `8px` or `12px`
- Admonitions: Increase right-side radius

---

## File-by-File Changes

### 1. Cards (`components/cards.css`)

**Find**:
```css
.card {
  border-radius: var(--radius-lg);
}
```

**Change to**:
```css
.card {
  border-radius: var(--radius-xl); /* 12px instead of 8px */
}
```

**Also update**:
- `.article-card`: `var(--radius-lg)` → `var(--radius-xl)`
- `.feature-card`: `var(--border-radius-large)` → `var(--radius-xl)` (verify variable name)
- `.stat-card`: `var(--border-radius-large)` → `var(--radius-xl)`
- `.callout-card`: `var(--border-radius-medium)` → `var(--radius-lg)` or `var(--radius-xl)`

---

### 2. Code Blocks (`components/code.css`)

**Find**:
```css
pre {
  border-radius: var(--radius-xl);
}
```

**Change to**:
```css
pre {
  border-radius: var(--radius-2xl); /* 16px instead of 12px */
}
```

**Also check**:
- `.code-header`: Update `border-radius` to match
- Mobile breakpoints: May need to adjust `border-radius` for smaller screens

---

### 3. Buttons (`components/buttons.css`)

**Find**:
```css
.button {
  border-radius: var(--radius-md);
}
```

**Change to**:
```css
.button {
  border-radius: var(--radius-lg); /* 8px instead of 4px */
}
```

**Note**: `.button-pill` already uses `var(--radius-full)` - keep as is.

---

### 4. Forms (`components/forms.css`)

**Find**:
```css
.form-input,
.form-textarea,
.form-select {
  border-radius: var(--border-radius-medium);
}
```

**Change to**:
```css
.form-input,
.form-textarea,
.form-select {
  border-radius: var(--radius-lg); /* 8px instead of 4px */
}
```

---

### 5. Tabs (`components/tabs.css`)

**Find**:
```css
.tabs {
  border-radius: var(--radius-md);
}
```

**Change to**:
```css
.tabs {
  border-radius: var(--radius-lg); /* 8px instead of 4px */
}
```

---

### 6. Dropdowns (`components/dropdowns.css`)

**Find**:
```css
details.dropdown {
  border-radius: var(--radius-md);
}
```

**Change to**:
```css
details.dropdown {
  border-radius: var(--radius-lg); /* 8px instead of 4px */
}
```

---

### 7. Blockquotes (`base/typography.css`) ⚠️ IMPORTANT

**Find**:
```css
.prose blockquote {
  border-radius: 0;
}
```

**Change to**:
```css
.prose blockquote {
  border-radius: var(--radius-lg); /* 8px instead of 0 - adds rounding! */
}
```

**Note**: This is a significant change - blockquotes currently have sharp corners.

---

### 8. Images (`base/typography.css`)

**Find**:
```css
.prose img {
  border-radius: var(--radius-md);
}
```

**Change to**:
```css
.prose img {
  border-radius: var(--radius-lg); /* 8px instead of 4px */
  /* OR for more rounded: var(--radius-xl) */
}
```

**Mobile variant** (if exists):
```css
@media (max-width: 640px) {
  .prose img {
    border-radius: var(--radius-md); /* Keep smaller on mobile, or use var(--radius-lg) */
  }
}
```

---

### 9. Admonitions (`components/admonitions.css`)

**Find**:
```css
.admonition {
  border-radius: 0 var(--border-radius-large) var(--border-radius-large) 0;
}
```

**Change to**:
```css
.admonition {
  border-radius: 0 var(--radius-xl) var(--radius-xl) 0; /* 12px instead of current */
}
```

**Verify**: Check what `--border-radius-large` resolves to - may already be correct.

---

### 10. Tables (`components/data-table.css`)

**Find**:
```css
.bengal-data-table-wrapper {
  border-radius: var(--radius-md, 8px);
}
```

**Change to**:
```css
.bengal-data-table-wrapper {
  border-radius: var(--radius-lg, 8px); /* Keep 8px fallback, use --radius-lg */
}
```

**Or** (if you want larger):
```css
.bengal-data-table-wrapper {
  border-radius: var(--radius-xl, 12px); /* 12px for larger tables */
}
```

---

### 11. Interactive Elements (`components/interactive.css`)

**Check**:
- `.back-to-top`: Already uses `var(--border-radius-full)` - keep as is
- `.lightbox__image`: Uses `var(--border-radius-medium)` - consider `var(--radius-lg)`
- `.lightbox__close`: Uses `var(--border-radius-full)` - keep as is
- `.keyboard-shortcuts`: Uses `var(--border-radius-medium)` - consider `var(--radius-lg)`

---

## Verification Checklist

After making changes, verify:

- [ ] **Cards**: All card types have `12px` radius
- [ ] **Code blocks**: `16px` radius
- [ ] **Buttons**: `8px` radius (except pill buttons)
- [ ] **Forms**: All inputs have `8px` radius
- [ ] **Tabs**: `8px` radius
- [ ] **Dropdowns**: `8px` radius
- [ ] **Blockquotes**: **Now have rounding!** `8px` radius
- [ ] **Images**: `8px` or `12px` radius
- [ ] **Admonitions**: Right-side radius increased
- [ ] **Tables**: Consistent radius

---

## Testing

1. **Visual Check**:
   - Browse site with changes
   - Look for any elements that look "off" with new rounding
   - Check nested elements (cards in cards, etc.)

2. **Dark Mode**:
   - Verify all rounded elements look good in dark mode
   - Check contrast on rounded corners

3. **Mobile**:
   - Test on mobile devices
   - Verify rounded corners don't cause layout issues
   - Check touch targets still work well

4. **Edge Cases**:
   - Code blocks with headers
   - Cards with images
   - Forms with validation states
   - Long content in rounded containers

---

## Rollback Plan

If issues arise, you can quickly revert by:

1. Git revert the changes
2. Or manually change back:
   - Cards: `var(--radius-xl)` → `var(--radius-lg)`
   - Code: `var(--radius-2xl)` → `var(--radius-xl)`
   - Everything else: `var(--radius-lg)` → `var(--radius-md)`
   - Blockquotes: `var(--radius-lg)` → `0`

---

## Expected Visual Impact

**Before**: Sharp, minimal, "boxy" feel
**After**: Softer, more modern, approachable feel

**Benefits**:
- More cohesive visual language
- Modern, friendly appearance
- Better for documentation (less harsh)
- Still professional and clean

**Risks**:
- Very low - just increasing existing radius values
- Easy to revert if needed
- No breaking changes

---

## Next Steps (Optional Enhancements)

After implementing cohesive roundedness, consider:

1. **Asymmetric borders** on cards (Bengal-inspired)
2. **Corner accents** on feature cards
3. **Gradient borders** for special elements
4. **Soft shadows** instead of borders

See `BORDER_STYLE_PROPOSAL.md` for details on these enhancements.

