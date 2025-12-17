# RFC: Simplify Autodoc HTML Skeleton

**Status**: Draft  
**Created**: 2025-12-17  
**Author**: AI Assistant  
**Confidence**: 85% 🟢

---

## Executive Summary

Simplify the autodoc HTML skeleton to reduce output verbosity by ~15-20% while retaining identical visual structure and functionality. Four targeted changes: externalize inline SVGs, consolidate repetitive template logic, merge content wrappers, and optionally flatten navigation structure.

**Recommendation**: Implement Changes 2-4 immediately (low risk, high value). Defer Change 1 (navigation flattening) pending cost-benefit review due to significant JS/CSS refactoring requirements.

---

## Problem Statement

The current autodoc HTML output is more verbose than necessary. Analysis of a typical CLI command group page (`/cli/bengal/`) reveals:

| Metric | Current | Issue |
|--------|---------|-------|
| Navigation wrapper divs | 2 per group | 1 is unnecessary |
| Inline SVGs in share dropdown | 4 × ~8 lines each | Should be icon system |
| Hero stats conditionals | 4 separate blocks | Repetitive template logic |
| Content wrapper nesting | 3 levels | 1 can be merged |

**Evidence**: `bengal/themes/default/templates/partials/docs-nav-section.html:48-71` shows the toggle wrapper pattern duplicated across all nav groups.

**Impact**:
- Larger HTML file sizes (~5-10KB per page)
- More complex DOM for browser parsing
- Template maintenance burden (4 stats blocks to update)
- Inconsistent icon handling (SVG inline vs `{{ icon() }}` system)

---

## Goals

1. **Reduce HTML output size** by ~15-20% without visual/functional changes
2. **Simplify template logic** by consolidating repetitive patterns
3. **Improve consistency** by moving AI icons to the icon system
4. **Maintain accessibility** - all ARIA attributes preserved
5. **Minimize JS/CSS churn** - prefer changes with low coupling

## Non-Goals

- Visual redesign of autodoc pages
- Changing the information architecture
- Removing accessibility attributes
- Major refactoring of navigation JavaScript

---

## Proposed Changes

### Change 1: Flatten Navigation Toggle Wrapper ⚠️ HIGH EFFORT

> **Note**: This change has significant downstream impact. Consider implementing Changes 2-4 first, then re-evaluate ROI.

**Location**: `partials/docs-nav-section.html`

**Before** (lines 48-71):
```html
<div class="docs-nav-group" data-depth="0">
  <div class="docs-nav-group-toggle-wrapper">
    <button class="docs-nav-group-toggle" aria-expanded="false" aria-controls="...">
      {{ icon('caret-right', size=14) }}
    </button>
    <span class="docs-nav-icon">
      {{ icon('folder', size=16) }}
    </span>
    <a href="..." class="docs-nav-group-link">Section Name</a>
  </div>
  <div class="docs-nav-group-items" id="...">
    <!-- children -->
  </div>
</div>
```

**After**:
```html
<div class="docs-nav-group" data-depth="0">
  <button class="docs-nav-toggle" aria-expanded="false" aria-controls="...">
    {{ icon('caret-right', size=14) }}
  </button>
  <span class="docs-nav-icon">
    {{ icon('folder', size=16) }}
  </span>
  <a href="..." class="docs-nav-link">Section Name</a>
  <div class="docs-nav-items" id="...">
    <!-- children -->
  </div>
</div>
```

#### JavaScript Changes Required

**File**: `bengal/themes/default/assets/js/enhancements/interactive.js`

The navigation JS relies on DOM structure for expand/collapse and active state propagation. Removing the wrapper requires rewriting the traversal logic.

**Affected code** (lines 306-369):

| Current | After | Lines |
|---------|-------|-------|
| `.docs-nav-group-toggle` | `.docs-nav-toggle` | 306, 343, 360 |
| `.docs-nav-group-toggle-wrapper` | **REMOVED** | 342, 359 |
| `.docs-nav-group-link` | `.docs-nav-link` | 335, 340 |
| `.docs-nav-group-items` | `.docs-nav-items` | 345, 355 |

**Before** (lines 340-365):
```javascript
// Current: relies on wrapper for sibling traversal
if (activeLink.classList.contains('docs-nav-group-link')) {
  const wrapper = activeLink.parentElement;
  if (wrapper && wrapper.classList.contains('docs-nav-group-toggle-wrapper')) {
    const toggle = wrapper.querySelector('.docs-nav-group-toggle');
    const items = wrapper.nextElementSibling;
    if (toggle && items && items.classList.contains('docs-nav-group-items')) {
      toggle.setAttribute('aria-expanded', 'true');
      items.classList.add('expanded');
    }
  }
}

// Walk up DOM using previousElementSibling
let parent = activeLink.parentElement;
while (parent) {
  if (parent.classList.contains('docs-nav-group-items')) {
    const wrapper = parent.previousElementSibling;
    if (wrapper && wrapper.classList.contains('docs-nav-group-toggle-wrapper')) {
      const toggle = wrapper.querySelector('.docs-nav-group-toggle');
      // ...
    }
  }
  parent = parent.parentElement;
}
```

**After**:
```javascript
// Simplified: use closest() instead of sibling traversal
if (activeLink.classList.contains('docs-nav-link')) {
  const group = activeLink.closest('.docs-nav-group');
  if (group) {
    const toggle = group.querySelector(':scope > .docs-nav-toggle');
    const items = group.querySelector(':scope > .docs-nav-items');
    if (toggle && items) {
      toggle.setAttribute('aria-expanded', 'true');
      items.classList.add('expanded');
    }
  }
}

// Walk up using closest() - cleaner than sibling traversal
let parent = activeLink.parentElement;
while (parent) {
  if (parent.classList.contains('docs-nav-items')) {
    const group = parent.closest('.docs-nav-group');
    if (group) {
      const toggle = group.querySelector(':scope > .docs-nav-toggle');
      if (toggle) {
        toggle.setAttribute('aria-expanded', 'true');
        parent.classList.add('expanded');
      }
    }
  }
  parent = parent.parentElement;
}
```

#### CSS Changes Required

**File**: `bengal/themes/default/assets/css/components/docs-nav.css` (770 lines)

**Impact Assessment**: 60+ CSS rules reference affected classes

| Class | Occurrences | Complexity |
|-------|-------------|------------|
| `.docs-nav-group-toggle-wrapper` | 28 | High (pseudo-elements, `:has()`) |
| `.docs-nav-group-toggle` | 12 | Medium |
| `.docs-nav-group-link` | 16 | Medium |
| `.docs-nav-group-items` | 10 | Low |

**Rules requiring updates**:
- Neumorphic hover states (lines 88-114)
- Pseudo-element positioning `::before`, `::after` (lines 56-86)
- `:has()` selectors for active state propagation (lines 188-218, 443-468)
- Dark mode overrides (lines 412-468)
- Glow animations (lines 575-614)
- Alignment calculations (lines 333-355)

**CSS Migration**:
```css
/* Before: wrapper handled flex layout and hover states */
.docs-nav-group-toggle-wrapper {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  /* + 28 more rules for hover, active, ::before, ::after */
}

/* After: grid on parent, move styles to .docs-nav-group */
.docs-nav-group {
  display: grid;
  grid-template-columns: auto auto 1fr;
  grid-template-rows: auto auto;
  align-items: center;
  gap: 0.25rem;
  /* Migrate all wrapper styles here */
}

.docs-nav-items {
  grid-column: 1 / -1;
}

/* Update all :has() selectors */
/* Before: .docs-nav-group-toggle-wrapper:has(.docs-nav-group-link.active) */
/* After:  .docs-nav-group:has(> .docs-nav-link.active) */
```

**Savings**: ~20 bytes × ~50 nav groups = ~1KB per page

**Effort**: ~4-6 hours (JS rewrite + CSS migration + testing)

---

### Change 2: Externalize AI Assistant Icons ✅ LOW EFFORT

**Location**: `partials/page-hero/_share-dropdown.html`

**Before** (lines 54-92): Inline SVGs for Claude, ChatGPT, Gemini, Copilot

**After**: Add icons to the icon system and use `{{ icon() }}`

**New icons to add** (`bengal/themes/default/assets/icons/`):
- `ai-claude.svg`
- `ai-chatgpt.svg`
- `ai-gemini.svg`
- `ai-copilot.svg`

**Template change**:
```jinja
{# Before #}
<a href="..." class="page-hero__share-item page-hero__share-ai" data-ai="claude">
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48..." />
    <circle cx="12" cy="12" r="3" />
  </svg>
  <span>Ask Claude</span>
</a>

{# After #}
<a href="..." class="page-hero__share-item page-hero__share-ai" data-ai="claude">
  {{ icon('ai-claude', size=16) }}
  <span>Ask Claude</span>
</a>
```

**Savings**: ~120 lines → ~20 lines in template

**Effort**: ~30 minutes

---

### Change 3: Consolidate Hero Stats with Filter ✅ LOW EFFORT

**Location**: `partials/page-hero-api.html` (deprecated) and `partials/page-hero/element.html`

**Before** (lines 184-278 in page-hero-api.html): Four separate conditional blocks:
```jinja
{# Stats for modules #}
{% if classes | length > 0 or functions | length > 0 %}
<div class="page-hero__stats">
  {% if classes | length > 0 %}
  <span class="page-hero__stat">...</span>
  {% endif %}
  ...
</div>
{% endif %}

{# Stats for classes #}
{% if methods | length > 0 %}
<div class="page-hero__stats">...</div>
{% endif %}

{# Stats for CLI command groups #}
{% if commands | length > 0 or command_groups | length > 0 %}
<div class="page-hero__stats">...</div>
{% endif %}

{# Stats for CLI commands #}
{% if options | length > 0 or arguments | length > 0 %}
<div class="page-hero__stats">...</div>
{% endif %}
```

**After**: Single unified partial with Python filter

**New filter** (add to autodoc filters):
```python
def get_element_stats(element: DocElement) -> list[dict]:
    """Extract display stats from a DocElement based on its type."""
    if not element or not element.children:
        return []

    children = element.children
    stats = []

    # Count by element type
    type_counts = {}
    for child in children:
        etype = child.element_type
        type_counts[etype] = type_counts.get(etype, 0) + 1

    # Map to display labels (singular/plural)
    type_labels = {
        'class': ('Class', 'Classes'),
        'function': ('Function', 'Functions'),
        'method': ('Method', 'Methods'),
        'command': ('Command', 'Commands'),
        'command-group': ('Group', 'Groups'),
        'option': ('Option', 'Options'),
        'argument': ('Argument', 'Arguments'),
    }

    for etype, count in type_counts.items():
        if count > 0 and etype in type_labels:
            singular, plural = type_labels[etype]
            stats.append({
                'value': count,
                'label': singular if count == 1 else plural
            })

    return stats
```

**New partial** (`partials/page-hero/_element-stats.html`):
```jinja
{% set stats = element | get_element_stats %}
{% if stats %}
<div class="page-hero__stats">
  {% for stat in stats %}
  <span class="page-hero__stat">
    <span class="page-hero__stat-value">{{ stat.value }}</span>
    <span class="page-hero__stat-label">{{ stat.label }}</span>
  </span>
  {% endfor %}
</div>
{% endif %}
```

**Savings**: ~100 lines → ~15 lines in templates, plus centralized logic

**Effort**: ~1 hour

---

### Change 4: Merge Content Wrapper ✅ LOW EFFORT

**Location**: `cli-reference/command-group.html` and similar templates

**Before**:
```html
<article class="prose {% if page.metadata.get('css_class') %}{{ page.metadata.get('css_class') }}{% endif %}">
  <div class="docs-content">
    <div class="autodoc-explorer">
      ...
    </div>
  </div>
</article>
```

**After**:
```html
<article class="prose docs-content {% if page.metadata.get('css_class') %}{{ page.metadata.get('css_class') }}{% endif %}">
  <div class="autodoc-explorer">
    ...
  </div>
</article>
```

**CSS Changes Required**:
```css
/* Merge .docs-content styles into .prose context */
.prose.docs-content {
  /* existing .docs-content styles */
}
```

**Savings**: Minor (~10 bytes × pages), but cleaner DOM

**Effort**: ~30 minutes

---

## Implementation Plan

### Phase 1: Quick Wins (Low Risk) — ~2 hours
1. Add AI icons to icon system (`ai-claude.svg`, etc.)
2. Update `_share-dropdown.html` to use `{{ icon() }}` calls
3. Add `get_element_stats` filter to autodoc filters
4. Create `_element-stats.html` partial
5. Update `element.html` and `page-hero-api.html` to use new stats partial

### Phase 2: Content Wrapper (Low Risk) — ~1 hour
1. Update all autodoc templates to merge `.docs-content` into `<article>`
2. Consolidate CSS selectors (`.prose.docs-content`)

### Phase 3: Navigation Flattening (High Risk) — ~4-6 hours ⚠️ OPTIONAL
> **Decision Point**: Evaluate ROI after Phases 1-2 are complete

1. Update `docs-nav-section.html` to remove wrapper
2. Rewrite `interactive.js` navigation logic (lines 306-369)
3. Migrate `docs-nav.css` (60+ rules)
4. Test all navigation states (expanded/collapsed/active)
5. Test dark mode and animations
6. Run visual regression tests

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **JS breakage from nav flattening** | High | High | Phase 3 last; comprehensive functional testing |
| **CSS breakage from nav flattening** | High | High | Phase 3 last; visual regression testing |
| Icon system doesn't support new icons | Low | Medium | Verify icon loading mechanism first |
| Filter not registered in Jinja env | Low | Low | Add to autodoc filters dict |
| Accessibility regression | Low | High | Automated a11y testing; preserve all ARIA |

---

## Testing Strategy

1. **Visual regression**: Screenshot comparison before/after (Percy or Playwright)
2. **Accessibility audit**: axe-core on sample pages
3. **File size comparison**: Measure HTML output size reduction
4. **Navigation functionality**: Test expand/collapse all groups
5. **Navigation active state**: Test active page highlighting and parent expansion
6. **Share dropdown**: Verify all AI links work correctly
7. **Dark mode**: Test all changes in both themes

### Phase 3 Specific Tests
- [ ] Click expand/collapse on all nav groups
- [ ] Navigate to nested page, verify parent groups auto-expand
- [ ] Test keyboard navigation (Tab, Enter, Space)
- [ ] Test `:has()` CSS selectors in Safari (partial support)
- [ ] Test reduced-motion preference

---

## Success Criteria

### Phase 1-2 (Required)
- [ ] HTML output size reduced by ≥10%
- [ ] All visual regression tests pass
- [ ] All accessibility audits pass (0 new violations)
- [ ] Share dropdown functions correctly
- [ ] No new template warnings/errors

### Phase 3 (Optional)
- [ ] Additional ~5% HTML reduction
- [ ] Navigation expand/collapse works identically
- [ ] Active state propagation works
- [ ] All JS tests pass

---

## Alternatives Considered

### Alternative A: CSS-only Simplification
Keep HTML structure, optimize CSS delivery instead.

**Rejected**: Doesn't address template maintenance burden or DOM complexity.

### Alternative B: Complete Template Rewrite
Redesign autodoc templates from scratch with minimal HTML.

**Rejected**: Too risky; high chance of regressions; not necessary for goal.

### Alternative C: Move to Web Components
Replace complex partials with custom elements.

**Rejected**: Adds JS dependency; overkill for static site generator.

### Alternative D: Rename Classes Without Restructuring
Keep the wrapper div but rename classes for consistency:
- `.docs-nav-group-toggle-wrapper` → `.docs-nav-header`
- `.docs-nav-group-toggle` → `.docs-nav-toggle`
- `.docs-nav-group-link` → `.docs-nav-title`
- `.docs-nav-group-items` → `.docs-nav-items`

**Considered**: Lower risk than flattening, improves naming consistency, but doesn't reduce HTML size. Could be a stepping stone before full flattening.

---

## Cost-Benefit Summary

| Change | Effort | HTML Savings | Risk | Recommendation |
|--------|--------|--------------|------|----------------|
| 2: AI Icons | 30 min | ~400 bytes | Low | ✅ Do first |
| 3: Stats Filter | 1 hour | ~200 bytes | Low | ✅ Do first |
| 4: Content Wrapper | 30 min | ~100 bytes | Low | ✅ Do first |
| 1: Nav Flattening | 4-6 hours | ~1KB | High | ⚠️ Evaluate ROI |

**Total (Phase 1-2)**: ~2 hours effort for ~700 bytes + cleaner templates
**Total (All phases)**: ~8 hours effort for ~1.7KB + cleaner templates

---

## References

- Evidence: `bengal/themes/default/templates/partials/docs-nav-section.html:48-71`
- Evidence: `bengal/themes/default/templates/partials/page-hero/_share-dropdown.html:54-92`
- Evidence: `bengal/themes/default/templates/partials/page-hero-api.html:184-278`
- Evidence: `bengal/themes/default/templates/cli-reference/command-group.html:32-34`
- Evidence: `bengal/themes/default/assets/js/enhancements/interactive.js:306-369`
- Evidence: `bengal/themes/default/assets/css/components/docs-nav.css:46-114,188-218,412-468`
