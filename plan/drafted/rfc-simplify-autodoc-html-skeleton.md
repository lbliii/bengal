# RFC: Simplify Autodoc HTML Skeleton

**Status**: Draft  
**Created**: 2025-12-17  
**Author**: AI Assistant  
**Confidence**: 85% 🟢

---

## Executive Summary

Simplify the autodoc HTML skeleton to reduce output verbosity by ~25% while retaining identical visual structure and functionality. Four targeted changes eliminate unnecessary wrapper elements, consolidate repetitive template logic, and externalize inline SVGs.

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

1. **Reduce HTML output size** by ~25% without visual/functional changes
2. **Simplify template logic** by consolidating repetitive patterns
3. **Improve consistency** by moving AI icons to the icon system
4. **Maintain accessibility** - all ARIA attributes preserved
5. **Preserve CSS class structure** - no breaking changes to selectors

## Non-Goals

- Visual redesign of autodoc pages
- Changing the information architecture
- Removing accessibility attributes
- Refactoring the icon system itself

---

## Proposed Changes

### Change 1: Flatten Navigation Toggle Wrapper

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

**CSS Changes Required**:
```css
/* Before: relied on wrapper for flex layout */
.docs-nav-group-toggle-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* After: apply flex to parent, use grid or subgrid for layout */
.docs-nav-group {
  display: grid;
  grid-template-columns: auto auto 1fr;
  grid-template-rows: auto auto;
  align-items: center;
  gap: var(--space-2);
}
.docs-nav-items {
  grid-column: 1 / -1;
}
```

**Savings**: ~20 bytes × ~50 nav groups = ~1KB per page

---

### Change 2: Externalize AI Assistant Icons

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

---

### Change 3: Consolidate Hero Stats with Filter

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

**New filter** (`bengal/rendering/filters.py`):
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

---

### Change 4: Merge Content Wrapper

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

---

## Implementation Plan

### Phase 1: Add Infrastructure (Low Risk)
1. Add AI icons to icon system
2. Add `get_element_stats` filter to filters.py
3. Create `_element-stats.html` partial

### Phase 2: Update Templates (Medium Risk)
1. Update `_share-dropdown.html` to use icon system
2. Update `element.html` to use new stats partial
3. Update `page-hero-api.html` (deprecated but still used)

### Phase 3: Flatten Navigation (Higher Risk)
1. Update `docs-nav-section.html` to remove wrapper
2. Update `layouts.css` with new grid-based layout
3. Test all navigation states (expanded/collapsed/active)

### Phase 4: Merge Content Wrapper (Low Risk)
1. Update all autodoc templates
2. Consolidate CSS selectors

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CSS breakage from nav flattening | Medium | High | Phase 3 last; comprehensive visual testing |
| Icon system doesn't support new icons | Low | Medium | Verify icon loading mechanism first |
| Filter not registered in Jinja env | Low | Low | Add to `AUTODOC_FILTERS` dict |
| Accessibility regression | Low | High | Automated a11y testing; preserve all ARIA |

---

## Testing Strategy

1. **Visual regression**: Screenshot comparison before/after
2. **Accessibility audit**: axe-core on sample pages
3. **File size comparison**: Measure HTML output size reduction
4. **Navigation functionality**: Expand/collapse all groups
5. **Share dropdown**: All AI links work correctly

---

## Success Criteria

- [ ] HTML output size reduced by ≥20%
- [ ] All visual regression tests pass
- [ ] All accessibility audits pass (0 new violations)
- [ ] Navigation expand/collapse works identically
- [ ] Share dropdown functions correctly
- [ ] No new template warnings/errors

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

---

## References

- Evidence: `bengal/themes/default/templates/partials/docs-nav-section.html:48-71`
- Evidence: `bengal/themes/default/templates/partials/page-hero/_share-dropdown.html:54-92`
- Evidence: `bengal/themes/default/templates/partials/page-hero-api.html:184-278`
- Evidence: `bengal/themes/default/templates/cli-reference/command-group.html:32-34`
