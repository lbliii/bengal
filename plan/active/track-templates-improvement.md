# Track Templates Improvement Plan

**Status**: Draft  
**Created**: 2025-01-27  
**Goal**: Fix and enhance the track templates (list, single, navigation) to create an excellent learning experience

---

## Executive Summary

The track system provides structured learning paths, but the templates have several issues that impact usability, accessibility, and visual polish. This plan addresses formatting bugs, semantic HTML improvements, accessibility enhancements, and visual design refinements.

**Key Issues Identified**:
1. Formatting bug in `track_nav.html` (malformed comment)
2. Missing semantic HTML structure
3. Accessibility gaps (ARIA labels, skip links)
4. Visual hierarchy and spacing issues
5. Missing dedicated CSS for track components
6. Navigation UX improvements needed

---

## Current State Analysis

### Files Reviewed

1. **`bengal/themes/default/templates/tracks/list.html`** - Track listing page
2. **`bengal/themes/default/templates/tracks/single.html`** - Individual track page
3. **`bengal/themes/default/templates/partials/track_nav.html`** - Track navigation component
4. **`site/data/tracks.yaml`** - Track data structure
5. **`site/content/tracks/_index.md`** - Track index page

### Issues Found

#### 1. `track_nav.html` - Formatting Bug

**Location**: Line 10-11  
**Issue**: Malformed Jinja comment on same line as code
```jinja
{% set next_slug = track.items[current_index + 1] if current_index < (track.items|length - 1) else None %} {# Track
    Navigation Component #} <div class="track-navigation card mb-4">
```

**Impact**: Template renders but comment is visible in HTML output

**Fix**: Separate comment to its own line

---

#### 2. `tracks/single.html` - Semantic HTML & Accessibility

**Issues**:
- Missing semantic HTML (`<article>`, `<nav>`, `<section>`)
- Missing ARIA labels for navigation and progress
- Syllabus links use anchor navigation but no smooth scroll
- "Back to Top" link points to generic `#main-content`
- Missing breadcrumb navigation
- No skip links for lesson sections
- Progress tracking not visually prominent

**Impact**: Poor accessibility, SEO, and user experience

---

#### 3. `tracks/single.html` - Visual Hierarchy

**Issues**:
- Lesson sections lack clear visual separation
- Syllabus card could be more visually appealing
- Missing completion indicators
- No estimated total time for track
- Lesson numbering could be more prominent
- Footer navigation buttons could be better styled

**Impact**: Harder to scan and navigate

---

#### 4. `tracks/list.html` - Navigation Logic

**Issue**: "Start Track" button links to first lesson instead of track overview page

**Current**:
```jinja
<a href="{{ first_page.url }}" class="btn btn-primary stretched-link">
    Start Track &rarr;
</a>
```

**Expected**: Should link to track page (`/tracks/{track_id}`) to show syllabus first

**Impact**: Users skip the track overview and syllabus

---

#### 5. Missing CSS

**Issue**: No dedicated CSS file for track components

**Current**: Uses generic Bootstrap classes only

**Impact**: Limited customization, inconsistent styling, harder to maintain

**Needed**:
- Track-specific component styles
- Responsive design for mobile
- Print styles
- Dark mode support
- Animation/transitions

---

#### 6. `track_nav.html` - UX Improvements

**Issues**:
- Progress bar is too subtle (4px height)
- Missing visual indicator of current position
- Button text could be more descriptive
- Missing keyboard navigation hints

---

## Proposed Solutions

### Phase 1: Critical Fixes

#### 1.1 Fix `track_nav.html` Formatting

**File**: `bengal/themes/default/templates/partials/track_nav.html`

**Changes**:
- Separate comment to its own line
- Clean up indentation
- Add proper spacing

---

#### 1.2 Fix `tracks/list.html` Navigation

**File**: `bengal/themes/default/templates/tracks/list.html`

**Changes**:
- Change "Start Track" button to link to track page instead of first lesson
- Add track page URL construction logic
- Update button text if needed for clarity

---

### Phase 2: Semantic HTML & Accessibility

#### 2.1 Enhance `tracks/single.html` Structure

**File**: `bengal/themes/default/templates/tracks/single.html`

**Changes**:
- Wrap track content in `<article>` with proper ARIA
- Add `<nav>` for syllabus with ARIA label
- Use `<section>` for each lesson with IDs
- Add breadcrumb navigation
- Add skip links for lesson sections
- Improve "Back to Top" to scroll to track header
- Add ARIA labels to progress indicators
- Add `role="navigation"` to lesson footer

---

#### 2.2 Enhance `track_nav.html` Accessibility

**File**: `bengal/themes/default/templates/partials/track_nav.html`

**Changes**:
- Add ARIA labels to navigation buttons
- Improve progress bar accessibility
- Add `aria-current="page"` to current lesson indicator
- Add keyboard navigation hints

---

### Phase 3: Visual Design & UX

#### 3.1 Create Track CSS Component

**File**: `bengal/themes/default/assets/css/components/tracks.css` (new)

**Features**:
- Track card styles
- Lesson section styling
- Progress bar enhancements
- Navigation button styles
- Responsive breakpoints
- Print styles
- Dark mode support
- Smooth scroll behavior
- Hover/focus states

---

#### 3.2 Improve Visual Hierarchy

**Files**: `tracks/single.html`, `tracks/list.html`

**Changes**:
- Enhanced syllabus card design
- Better lesson section separation
- More prominent lesson numbering
- Completion indicators
- Estimated time display
- Improved spacing and typography
- Better button styling

---

#### 3.3 Enhance `track_nav.html` Visual Design

**File**: `bengal/themes/default/templates/partials/track_nav.html`

**Changes**:
- Larger, more visible progress bar
- Better button layout
- Visual indicator of current position
- Improved spacing

---

### Phase 4: Polish & Edge Cases

#### 4.1 Handle Edge Cases

**Files**: All track templates

**Edge Cases**:
- Empty tracks (no items)
- Missing pages in track
- Single-item tracks
- Very long track titles/descriptions
- Missing track data

---

#### 4.2 Add Track Metadata

**Enhancement**: Display additional track information

**Ideas**:
- Total estimated time
- Difficulty level
- Prerequisites
- Completion status (if user tracking added later)

---

## Implementation Plan

### Step 1: Critical Fixes (30 min)
1. Fix `track_nav.html` formatting bug
2. Fix `tracks/list.html` navigation logic
3. Test both fixes

### Step 2: Semantic HTML (45 min)
1. Refactor `tracks/single.html` with semantic HTML
2. Add ARIA labels and accessibility features
3. Add breadcrumb navigation
4. Test accessibility with screen reader

### Step 3: CSS Component (60 min)
1. Create `tracks.css` file
2. Add responsive styles
3. Add print styles
4. Test across devices

### Step 4: Visual Enhancements (45 min)
1. Update templates with new classes
2. Improve visual hierarchy
3. Enhance navigation components
4. Test visual design

### Step 5: Testing & Refinement (30 min)
1. Test all edge cases
2. Verify accessibility
3. Check responsive design
4. Validate HTML/CSS

**Total Estimated Time**: ~3.5 hours

---

## Success Criteria

### Functionality
- [ ] All templates render without errors
- [ ] Navigation works correctly (list → single → lessons)
- [ ] Track navigation component works on individual lesson pages
- [ ] All links resolve correctly

### Accessibility
- [ ] Semantic HTML structure
- [ ] ARIA labels on all interactive elements
- [ ] Keyboard navigation works
- [ ] Screen reader friendly
- [ ] WCAG 2.1 AA compliance

### Visual Design
- [ ] Clear visual hierarchy
- [ ] Consistent spacing and typography
- [ ] Responsive on mobile/tablet/desktop
- [ ] Print-friendly
- [ ] Dark mode support

### Code Quality
- [ ] Clean, maintainable templates
- [ ] Well-organized CSS
- [ ] No formatting bugs
- [ ] Proper comments

---

## Files to Modify

### Templates
1. `bengal/themes/default/templates/tracks/list.html`
2. `bengal/themes/default/templates/tracks/single.html`
3. `bengal/themes/default/templates/partials/track_nav.html`

### CSS (New)
4. `bengal/themes/default/assets/css/components/tracks.css`

### CSS Import
5. `bengal/themes/default/assets/css/style.css` (add import)

---

## Notes

- All template filters (`reading_time`, `demote_headings`, `slugify`) exist and work correctly
- Track data structure in `tracks.yaml` is sufficient
- Consider future enhancements: user progress tracking, completion certificates, track recommendations

---

## Related Documentation

- Track system: `site/content/guides/curated-tracks.md`
- Template functions: `bengal/rendering/template_functions/strings.py`
