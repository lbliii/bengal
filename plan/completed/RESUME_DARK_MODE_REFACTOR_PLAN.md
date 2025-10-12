# Resume Template Dark Mode & CSS Refactoring

## Problem
The resume templates (`resume/list.html` and `resume/single.html`) currently have extensive inline CSS that:
1. Bypasses the theme's design token system
2. Contains hardcoded colors that don't respect dark mode
3. Violates the separation of concerns principle
4. Makes maintenance and consistency difficult

## Solution
Extract all resume CSS into a proper theme asset file that:
1. Uses the theme's semantic design tokens
2. Properly integrates with the existing dark mode system
3. Follows the CUBE CSS methodology already in use
4. Is maintainable and consistent with other layouts

## Implementation Plan

### Phase 1: Create Resume CSS Asset
**File**: `bengal/themes/default/assets/css/layouts/resume.css`

This file will contain:
- Base resume layout styles
- All resume component styles (header, timeline, skills, etc.)
- Dark mode overrides using `[data-theme="dark"]`
- System preference support via `@media (prefers-color-scheme: dark)`
- Responsive styles
- Print styles specific to resume

**Key Principles**:
- Use semantic tokens from `tokens/semantic.css` (e.g., `var(--color-text-primary)`)
- Never use foundation tokens directly (e.g., avoid `var(--gray-500)`)
- Follow existing dark mode patterns from other theme components
- Use spacing, typography, and color tokens consistently

### Phase 2: Update Main Stylesheet
**File**: `bengal/themes/default/assets/css/style.css`

Add import in the layouts section:
```css
@import url('layouts/resume.css');
```

### Phase 3: Update Resume Templates
**Files**:
- `bengal/themes/default/templates/resume/list.html`
- `bengal/themes/default/templates/resume/single.html`

Actions:
1. Remove all `<style>` blocks
2. Keep only the HTML structure
3. Ensure class names remain consistent
4. Templates should rely entirely on theme CSS

### Phase 4: Verify & Test
1. Check that styles load correctly
2. Verify dark mode toggle works
3. Test system preference detection
4. Ensure print styles work
5. Verify responsive behavior

## Design Token Mapping

### Current Hardcoded → Token Replacements

**Light Mode Base Colors**:
- `#1a1a1a` → `var(--color-text-primary)`
- `#111827` → `var(--color-text-primary)`
- `#4b5563` → `var(--color-text-secondary)`
- `#6b7280` → `var(--color-text-tertiary)`
- `#374151` → `var(--color-text-secondary)`

**Backgrounds**:
- `#f9fafb` → `var(--color-bg-secondary)`
- `white` → `var(--color-bg-primary)`
- `#e5e7eb` → `var(--color-border-light)`

**Borders**:
- `#e5e7eb` → `var(--color-border-light)`
- `#d1d5db` → `var(--color-border)`

**Brand Colors**:
- `#3b82f6` → `var(--color-primary)`
- `#2563eb` → `var(--color-primary-hover)`
- `#eff6ff` → Use with `var(--color-primary)` and adjust opacity

**Dark Mode** (will be handled automatically via theme tokens):
- Dark backgrounds → `var(--color-bg-primary)`, `var(--color-bg-secondary)`
- Dark text → `var(--color-text-primary)`, etc.
- Dark borders → `var(--color-border)`, `var(--color-border-light)`

## Benefits

1. **Consistency**: Resume styles match the rest of the theme
2. **Maintainability**: Single source of truth for resume styles
3. **Dark Mode**: Automatic support via theme system
4. **Performance**: CSS loaded once, cached properly
5. **Extensibility**: Easy to override in custom themes
6. **Token-based**: Changes to design tokens cascade properly

## File Structure After Refactor

```
bengal/themes/default/
├── assets/
│   └── css/
│       ├── layouts/
│       │   ├── footer.css
│       │   ├── grid.css
│       │   ├── header.css
│       │   └── resume.css       ← NEW
│       └── style.css             ← UPDATED (add import)
└── templates/
    └── resume/
        ├── list.html             ← UPDATED (remove inline CSS)
        └── single.html           ← UPDATED (remove inline CSS)
```

## Notes

- Resume templates are identical in structure (DRY violation, but separate issue)
- Both templates will benefit from this refactoring
- Consider whether resume should be in `layouts/` or `pages/` (recommend `layouts/` since it's a specialized layout system)
- Print styles are particularly important for resumes - maintain them carefully

## Next Steps

1. Create `resume.css` with proper token usage
2. Import in `style.css`
3. Clean up templates
4. Test thoroughly
5. Document any resume-specific CSS classes
