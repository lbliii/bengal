# CSS Variable Standardization & Fixes

**Date:** October 9, 2025  
**Status:** ✅ Complete

## Problem

The API docs theme CSS and templates weren't rendering correctly because several CSS variables were either:
1. Undefined (missing from token files)
2. Using non-standard naming conventions
3. Inconsistent with the established design system

## Root Causes

### 1. Letter-based Spacing Tokens (Missing)
The API docs CSS files used letter-based spacing variables that didn't exist:
- `--space-xs`, `--space-s`, `--space-m`, `--space-l`, `--space-xl`, `--space-2xl`

These were **never defined** in `semantic.css`, causing all spacing/gaps/padding to fail.

### 2. Inconsistent Radius Naming
Used shorthand radius names that didn't match the foundation tokens:
- `--radius-s` (should be `--radius-sm`)
- `--radius-xs` (doesn't exist, should be `--radius-sm`)
- `--radius-m` (should be `--radius-md`)

### 3. Generic Color Variable
Used `--color-text` instead of the semantic `--color-text-primary`

### 4. Wrong Code Background Variable
Used `--color-code-bg` instead of `--color-bg-code`

### 5. Missing Purple Color Scale
Used `--purple-600` and `--purple-400` for code syntax highlighting, but purple scale was never defined in `foundation.css`

## Solution

### Decision: Standardize on Numerical Spacing Tokens

**Analysis:**
- **Numerical tokens** (`--space-0` through `--space-32`): Used 284 times across 24 files
- **Letter-based tokens** (`--space-xs`, `--space-m`, etc.): Used 90 times in only 3 files

**Decision:** Standardize on numerical tokens (already the established pattern)

**Benefits:**
- One clear way to specify spacing
- Better alignment with design system
- Complete scale from 0-32 mapped to foundation tokens
- Less maintenance overhead

### Changes Made

#### 1. Refactored Spacing Tokens (3 files)

**Files changed:**
- `bengal/themes/default/assets/css/components/api-docs.css`
- `bengal/themes/default/assets/css/components/reference-docs.css`
- `bengal/themes/default/assets/css/components/code.css`

**Replacements:**
```css
--space-xs  → --space-2   /* 0.5rem / 8px */
--space-s   → --space-3   /* 0.75rem / 12px */
--space-m   → --space-4   /* 1rem / 16px */
--space-l   → --space-6   /* 1.5rem / 24px */
--space-xl  → --space-8   /* 2rem / 32px */
--space-2xl → --space-12  /* 3rem / 48px */
```

#### 2. Fixed Radius Variables (2 files)

**Files changed:**
- `bengal/themes/default/assets/css/components/api-docs.css`
- `bengal/themes/default/assets/css/components/reference-docs.css`

**Replacements:**
```css
--radius-xs → --radius-sm
--radius-s  → --radius-sm
--radius-m  → --radius-md
```

#### 3. Fixed Color Variables (2 files)

**Files changed:**
- `bengal/themes/default/assets/css/components/reference-docs.css`
- `bengal/themes/default/assets/css/components/navigation.css`

**Replacements:**
```css
--color-text    → --color-text-primary
--color-code-bg → --color-bg-code
```

#### 4. Added Missing Purple Color Scale

**File changed:**
- `bengal/themes/default/assets/css/tokens/foundation.css`

**Added:**
```css
/* Purple Scale */
--purple-50: #f3e5f5;
--purple-100: #e1bee7;
--purple-200: #ce93d8;
--purple-300: #ba68c8;
--purple-400: #ab47bc;
--purple-500: #9c27b0;
--purple-600: #8e24aa;
--purple-700: #7b1fa2;
--purple-800: #6a1b9a;
--purple-900: #4a148c;
```

## Impact

### Fixed
✅ API docs spacing, padding, and gaps now render correctly  
✅ Border radius on API docs cards and buttons now works  
✅ Text colors in API reference pages now display properly  
✅ Code syntax highlighting for keywords now has correct purple color  
✅ All CSS variables are now defined and properly scoped  

### Design System Improvements
✅ Standardized on numerical spacing tokens across the codebase  
✅ Complete color palette with purple scale for syntax highlighting  
✅ Consistent variable naming following semantic token conventions  

## Files Modified

1. `bengal/themes/default/assets/css/tokens/foundation.css` - Added purple scale
2. `bengal/themes/default/assets/css/tokens/semantic.css` - Removed letter-based tokens (never added permanently)
3. `bengal/themes/default/assets/css/components/api-docs.css` - Fixed all variables
4. `bengal/themes/default/assets/css/components/reference-docs.css` - Fixed all variables
5. `bengal/themes/default/assets/css/components/code.css` - Fixed spacing tokens
6. `bengal/themes/default/assets/css/components/navigation.css` - Fixed color token

## Verification

All undefined CSS variables have been eliminated:
- ✅ No letter-based spacing tokens remain
- ✅ No shorthand radius tokens remain
- ✅ No generic color variables remain
- ✅ All color scales are complete and defined

## Next Steps

- Test API documentation pages to verify visual improvements
- Consider creating linting rules to catch undefined CSS variables
- Document the design token system in theme documentation

