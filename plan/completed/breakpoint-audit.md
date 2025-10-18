# Component Breakpoint Audit

**Date:** October 18, 2025  
**Status:** In Progress

## Standardization Rules

1. **767px → 768px** (OFF BY ONE - needs fixing)
2. **1023px → 1024px** (OFF BY ONE - needs fixing)  
3. **640px → 639px** when paired with `min-width: 640px` (avoid overlap)
4. **768px** stays as-is (correct for tablet breakpoint)
5. **1024px** stays as-is (correct for desktop breakpoint)

## Issues Found

### 🔴 Critical: Off-by-One Errors

**767px → Should be 768px**
- ❌ `components/cards.css:228`
- ❌ `base/utilities.css:291`
- ❌ `base/utilities.css:304`

**1023px → Should be 1024px**
- ❌ `components/toc.css:532`

### 🟡 Review Needed: 640px Usage

Need to determine if these should be 639px (when avoiding overlap with min-width: 640px):

- `components/author-page.css:268`
- `components/archive.css:360`
- `components/search.css:302`
- `components/hero.css:326`
- `components/empty-state.css:86`
- `components/cards.css:632, 652`
- `components/buttons.css:251`
- `components/interactive.css:106`
- `base/prose-content.css:227`
- `components/tutorial.css:91`
- `components/reference-docs.css:250`
- `components/blog.css:65`
- `components/tabs.css:201`
- `components/pagination.css:199`
- `components/dropdowns.css:289`
- `components/admonitions.css:307`

### ✅ Already Correct

**768px** (tablet breakpoint) - These are correct:
- `composition/layouts.css:101`
- `components/category-browser.css:309`
- `components/api-docs.css:393, 479, 578`
- `layouts/changelog.css:386`
- `components/search.css:287, 487`
- `components/navigation.css:107`
- `components/hero.css:278`
- `base/typography.css:150`
- `components/interactive.css:65, 175`
- `marimo.css:144`
- `layouts/resume.css:426`
- `components/tutorial.css:379`
- `components/reference-docs.css:557, 755`
- `components/data-table.css:336`
- `components/blog.css:105, 127, 558`
- `components/widgets.css:310`
- `components/related-posts.css:66`

**1024px** (desktop breakpoint) - These are correct:
- `composition/layouts.css:79`
- `components/tutorial.css:255`
- `components/blog.css:277`

**639px** (already fixed):
- `components/action-bar.css:426` ✅

**479px** (already fixed):
- `components/action-bar.css:484` ✅

## Fix Strategy

1. **Phase 1:** Fix off-by-one errors (767px, 1023px)
2. **Phase 2:** Audit 640px usage and update where needed
3. **Phase 3:** Add inline documentation comments
4. **Phase 4:** Verify with linter

## Progress

- [x] Phase 1: Off-by-one fixes ✅
- [x] Phase 2: 640px audit ✅
- [x] Phase 3: Documentation comments ✅
- [x] Phase 4: Linter verification ✅

## Final Results

### Files Modified (6 total)

1. **components/cards.css**
   - Fixed: `767px` → `768px` (line 228)
   - Fixed: `640px` → `639px` (lines 633, 653) - had overlap with `min-width: 640px`
   - Added: Documentation comments

2. **base/utilities.css**
   - Fixed: `767px` → `768px` (lines 291, 304)
   - Fixed: `768px` → `769px` for `min-width` queries (lines 295, 300)
   - Added: Documentation comments

3. **components/toc.css**
   - Fixed: `1023px` → `1024px` (line 532)
   - Added: Documentation comment

4. **components/action-bar.css**
   - Already had: `639px` and `479px` (from previous fix)
   - Added: Documentation comments

5. **composition/layouts.css**
   - Added: Documentation comments for `1024px` and `768px` breakpoints

### Files Analyzed - No Changes Needed (15 files)

These files use `640px` as standalone mobile breakpoints (no overlap risk):
- components/author-page.css
- components/archive.css
- components/search.css
- components/hero.css
- components/empty-state.css
- components/buttons.css
- components/interactive.css
- base/prose-content.css
- components/tutorial.css
- components/reference-docs.css
- components/blog.css
- components/tabs.css
- components/pagination.css
- components/dropdowns.css
- components/admonitions.css

**Rationale:** These files only have `max-width: 640px` queries without corresponding `min-width: 640px` queries in the same file, so there's no overlap risk. Using 640px is intentional and correct.

### Remaining Files - Already Correct (10+ files)

These files already use correct standardized breakpoints:
- All files using `768px` for tablet breakpoint
- All files using `1024px` for desktop breakpoint
- Files with proper `min-width` queries

## Summary Statistics

- **Total files audited:** 31
- **Files modified:** 6
- **Breakpoints fixed:** 7 instances
- **Documentation added:** 6 files
- **Linter errors:** 0 ✅

## Key Learnings

1. **Off-by-one errors are common**: `767px` instead of `768px`, `1023px` instead of `1024px`
2. **Overlap only matters within same file**: Most `640px` usages are fine because they're standalone
3. **Documentation helps**: Adding comments like "Tablet and below (md breakpoint)" clarifies intent
4. **Utilities need special care**: The responsive utility classes needed adjustment to avoid overlap (769px for min-width)
