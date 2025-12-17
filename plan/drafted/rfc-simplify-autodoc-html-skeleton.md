# RFC: Simplify Autodoc HTML/CSS Architecture

**Status**: Implemented  
**Created**: 2025-12-17  
**Author**: AI Assistant  
**Confidence**: 85% 🟢

---

## Executive Summary

The autodoc system's HTML/CSS complexity has reached a point where **basic fixes are impossible**. Multiple attempts to fix CLI body content styling have failed due to:

- **2,629 lines** in `api-explorer.css` alone
- **~1,200 CSS rules** targeting `.api-*`, `.autodoc-*`, `.prose`, `.docs-content`
- **12 separate CSS files** in `autodoc/` directory
- **3 nested wrapper divs** before reaching content (`<article>` → `.docs-content` → `.autodoc-explorer`)
- **Cascading specificity wars** between component systems

This RFC proposes a phased approach: quick template cleanups first, followed by a systematic CSS consolidation that makes the system maintainable again.

---

## Problem Statement

### The Real Pain Point

> "I cannot easily fix the CLI autodoc body content. It's impossible and we've tried several times."

The current architecture blocks bug fixes because:

1. **CSS Sprawl**: Autodoc styling is spread across 12+ files totaling ~6,000 lines
2. **Specificity Conflicts**: `.prose .autodoc-explorer .api-section .api-table` vs `.docs-content .api-table` — which wins?
3. **Duplicated Tokens**: CSS custom properties defined in multiple places with inconsistent values
4. **Unclear Ownership**: Is table styling in `_table.css`, `api-explorer.css`, `api-docs.css`, or `reference-docs.css`?

### Evidence

| File | Lines | Purpose |
|------|-------|---------|
| `api-explorer.css` | 2,629 | Main autodoc styling |
| `api-docs.css` | 913 | API documentation |
| `reference-docs.css` | 838 | Reference pages |
| `autodoc/_base.css` | 641 | Base autodoc styles |
| `autodoc/_card.css` | ~200 | Card components |
| `autodoc/_table.css` | ~150 | Table components |
| **Total** | **~6,000** | For one feature area |

### Symptom: CLI Body Content Unfixable

**Actual rendered output** (`site/public/cli/bengal/build/index.html`):

```html
<article class="prose">                              <!-- Layer 1: Typography -->
  <div class="docs-content">                         <!-- Layer 2: Layout context -->
    <div class="autodoc-explorer">                   <!-- Layer 3: Autodoc tokens -->
      <div class="api-usage">                        <!-- Layer 4: Usage block -->
        <h3 class="api-label">Usage</h3>
        <div class="code-block-wrapper">             <!-- Layer 5: Code wrapper -->
          <div class="code-header-inline">           <!-- Layer 6: Code header -->
            <span class="code-language">Bash</span>
          </div>
          <pre><code class="language-bash">bengal.build [OPTIONS]</code></pre>
        </div>
      </div>

      <section class="api-section api-section--options">
        <h2 class="api-section__title">Options</h2>
        <table class="api-table api-table--compact">
          <thead>...</thead>
          <tbody>
            <tr>
              <td class="api-table__name"><code>--parallel</code></td>
              <td class="api-table__type"><code>boolean</code></td>
              <td class="api-table__default"><code>True</code></td>
              <td class="api-table__desc">Enable parallel processing...</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</article>
```

**6 levels of nesting** before reaching the code block. **5 levels** before the table.

**CSS specificity nightmare** — all of these could apply to the table:
```css
.prose table { }                                      /* 0,0,1,1 */
.docs-content table { }                               /* 0,0,1,1 */
.autodoc-explorer table { }                           /* 0,0,1,1 */
.api-section table { }                                /* 0,0,1,1 */
.api-table { }                                        /* 0,0,1,0 — LOSES to above! */
.api-table--compact { }                               /* 0,0,1,0 */
.prose .autodoc-explorer .api-table { }               /* 0,0,3,1 */
.prose .docs-content .autodoc-explorer table { }      /* 0,0,4,1 */
```

**Result**: The BEM class `.api-table` has *lower* specificity than generic element selectors like `.prose table`. Any fix requires overriding 4+ parent contexts.

---

## Goals

1. **Enable bug fixes** — make styling changes predictable and isolated
2. **Reduce CSS surface area** — fewer files, clearer ownership
3. **Simplify HTML structure** — fewer wrappers, clearer semantics
4. **Maintain visual design** — no regressions, same look

## Non-Goals

- Visual redesign
- JavaScript refactoring (unless blocking)
- Changing information architecture

---

## Proposed Changes

### Phase 1: Template Cleanup (Low Risk) — ~2 hours

Quick wins that reduce complexity without touching the CSS architecture.

#### Change 1.1: Externalize AI Icons

**Location**: `partials/page-hero/_share-dropdown.html:54-92`

Move inline SVGs to icon system:
```jinja
{# Before: inline SVG #}
<a href="..." class="page-hero__share-ai" data-ai="claude">
  <svg viewBox="0 0 24 24">...</svg>
  <span>Ask Claude</span>
</a>

{# After: icon system #}
<a href="..." class="page-hero__share-ai" data-ai="claude">
  {{ icon('ai-claude', size=16) }}
  <span>Ask Claude</span>
</a>
```

**Files**:
- Add `ai-claude.svg`, `ai-chatgpt.svg`, `ai-gemini.svg`, `ai-copilot.svg` to icons/
- Update `_share-dropdown.html`

**Effort**: 30 min

#### Change 1.2: Consolidate Hero Stats

**Location**: `partials/page-hero-api.html:184-278`

Replace 4 conditional blocks with single filter-driven partial:

```python
# New filter
def get_element_stats(element: DocElement) -> list[dict]:
    """Extract display stats based on element type."""
    ...
```

```jinja
{# New partial: _element-stats.html #}
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

**Effort**: 1 hour

#### Change 1.3: Merge Content Wrapper

**Location**: `cli-reference/*.html` templates

```html
{# Before #}
<article class="prose">
  <div class="docs-content">
    <div class="autodoc-explorer">

{# After #}
<article class="prose autodoc-explorer">
  <div class="api-content">
```

This removes one wrapper level and eliminates the `.docs-content` middleman.

**Effort**: 30 min

---

### Phase 2: CSS Consolidation (Medium Risk) — ~4 hours

The real fix. Consolidate autodoc CSS into a single, well-organized file.

#### Goal: Single Source of Truth

Merge these files into one `autodoc.css`:
- `api-explorer.css` (2,629 lines)
- `autodoc/_*.css` (12 files, ~1,000 lines)
- Relevant parts of `api-docs.css` and `reference-docs.css`

#### Strategy: Namespace + Reset

```css
/* autodoc.css — Single file for all autodoc styling */

/* ============================================
   AUTODOC RESET - Override inherited styles
   ============================================ */
.autodoc-explorer {
  /* Reset prose styles that interfere */
  & table { all: revert; }
  & code { all: revert; }

  /* Set autodoc baseline */
  font-family: var(--font-sans);
  font-size: var(--text-base);
}

/* ============================================
   TOKENS - All autodoc custom properties
   ============================================ */
.autodoc-explorer {
  --api-window-bg: var(--color-bg-elevated);
  --api-window-border: var(--color-border-light);
  --api-section-gap: var(--space-8);
  /* ... consolidate all tokens here */
}

/* ============================================
   COMPONENTS - Flat structure, no nesting
   ============================================ */

/* Sections */
.api-section { ... }
.api-section__title { ... }

/* Tables */
.api-table { ... }
.api-table--compact { ... }

/* Cards */
.api-card { ... }
.api-card--command { ... }

/* ... etc ... */
```

#### Key Principles

1. **Flat selectors**: `.api-table` not `.autodoc-explorer .api-section .api-table`
2. **Single file**: All autodoc CSS in one place
3. **Explicit resets**: Override inherited styles explicitly at container level
4. **BEM naming**: `block__element--modifier` throughout

#### Migration Path

1. Create `autodoc.css` with consolidated styles
2. Update import order (autodoc.css after prose.css)
3. Delete redundant files one by one
4. Test each deletion

**Effort**: 4 hours

---

### Phase 3: Navigation Flattening (High Risk) — ~4-6 hours

> **Decision Point**: Only proceed if Phases 1-2 don't resolve the maintainability issues.

Remove the `.docs-nav-group-toggle-wrapper` div, flattening nav structure.

**Current**:
```html
<div class="docs-nav-group">
  <div class="docs-nav-group-toggle-wrapper">
    <button class="docs-nav-group-toggle">...</button>
    <a class="docs-nav-group-link">...</a>
  </div>
  <div class="docs-nav-group-items">...</div>
</div>
```

**After**:
```html
<div class="docs-nav-group">
  <button class="docs-nav-toggle">...</button>
  <a class="docs-nav-link">...</a>
  <div class="docs-nav-items">...</div>
</div>
```

**Requires**:
- JS rewrite (`interactive.js:306-369`)
- CSS migration (60+ rules in `docs-nav.css`)

**See previous RFC version for detailed JS/CSS changes.**

---

## Implementation Plan

### Week 1: Template Cleanup
- [ ] Change 1.1: AI icons (30 min)
- [ ] Change 1.2: Stats filter (1 hour)
- [ ] Change 1.3: Content wrapper (30 min)
- [ ] Test all CLI autodoc pages

### Week 2: CSS Consolidation
- [ ] Create `autodoc.css` scaffold
- [ ] Migrate tokens from `_tokens.css`
- [ ] Migrate table styles from `_table.css` + `api-explorer.css`
- [ ] Migrate card styles
- [ ] Migrate section styles
- [ ] Delete redundant files
- [ ] Full regression test

### Week 3 (if needed): Navigation
- [ ] Evaluate if nav changes are still needed
- [ ] If yes, implement Phase 3

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CSS consolidation breaks pages | Medium | High | Incremental migration, test each file deletion |
| Specificity issues after merge | Medium | Medium | Explicit resets, flat selectors |
| Missing styles after consolidation | Low | Medium | Diff before/after rendered output |
| JS nav breakage (Phase 3 only) | High | High | Only if needed; comprehensive testing |

---

## Success Criteria

### Phase 1-2 (Required)
- [ ] Can successfully modify CLI table styling without breaking other pages
- [ ] Autodoc CSS reduced to <2,000 lines total
- [ ] Single file contains all autodoc styling
- [ ] No visual regressions

### Phase 3 (Optional)
- [ ] Navigation wrapper removed
- [ ] HTML output size reduced ~1KB/page

---

## Alternatives Considered

### Alternative A: Keep Current Structure, Add More Specificity
Add `!important` or longer selectors to force overrides.

**Rejected**: Makes problem worse over time. Technical debt accumulates.

### Alternative B: CSS-in-JS / Tailwind
Rewrite with utility classes or scoped styles.

**Rejected**: Major architectural change. Too disruptive for the benefit.

### Alternative C: Complete Template Rewrite
Start from scratch with minimal HTML.

**Rejected**: High risk of regressions. Months of work.

### Alternative D: CSS Modules / Scoping
Use CSS modules or shadow DOM for isolation.

**Rejected**: Requires build tooling changes. Overkill for static site.

---

## References

**CSS Files**:
- `bengal/themes/default/assets/css/components/api-explorer.css` (2,629 lines)
- `bengal/themes/default/assets/css/components/autodoc/` (12 files)
- `bengal/themes/default/assets/css/components/api-docs.css` (913 lines)
- `bengal/themes/default/assets/css/components/reference-docs.css` (838 lines)

**Templates**:
- `bengal/themes/default/templates/cli-reference/command.html`
- `bengal/themes/default/templates/cli-reference/command-group.html`
- `bengal/themes/default/templates/partials/page-hero/_share-dropdown.html`
- `bengal/themes/default/templates/partials/page-hero-api.html`

**JS**:
- `bengal/themes/default/assets/js/enhancements/interactive.js:306-369`
