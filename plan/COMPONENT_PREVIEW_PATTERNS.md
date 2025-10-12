# Component Preview Patterns & Best Practices

**Date:** 2025-10-12  
**Status:** Documentation Complete

## Overview

Not all components preview equally well. Understanding component patterns helps set expectations for what component preview can and cannot show.

## The Four Component Types

### 1. Pure Template/Macro Components ✅

**Best Preview Experience**

These components render different visual output based solely on template parameters. Perfect for static preview.

**Examples:**
- `breadcrumbs(page)` - Different pages = different breadcrumbs
- `pagination(current, total, url)` - Different pages = different controls
- `article_card(article, show_excerpt, show_image)` - Different params = different layouts
- `tag_list(tags, small, linkable)` - Different tags = different displays

**Why They Work Well:**
- ✅ Pure functions: Same inputs → Same outputs
- ✅ No external dependencies
- ✅ No JavaScript required
- ✅ Self-contained rendering
- ✅ Easily testable with mock data

**Preview Quality:** ✅ **Excellent**

**Recommendation:** Create 3-5 variants showing edge cases:
```yaml
variants:
  - id: "default"
    params: {page: {...}}
  - id: "edge-case-1"
    params: {page: {...}}
  - id: "empty-state"
    params: {page: {...}}
```

---

### 2. Template Function Components ⚠️

**Good Preview with Mock Data**

Components that call template functions requiring full site context. Can work well in preview with proper mocking.

**Examples:**
- `popular_tags_widget(limit)` - Calls `popular_tags()` function
- `random_posts(count)` - Calls `site.regular_pages | sample()`
- Components using `get_breadcrumbs()`, `get_related()`, etc.

**Why They Need Help:**
- Template functions need real site data
- Preview runs in isolation without full site
- Can work if functions handle missing data gracefully

**Preview Quality:** ⚠️ **Good with mock data**

**Recommendation:** Provide mock data or test in dev server:
```yaml
context:
  site:
    config:
      title: "My Site"
  _mock_tags:
    - name: "python"
      count: 15
  _preview_note: "Using mock data for preview"
```

---

### 3. JavaScript-Driven Components ⚠️

**Limited Static Preview**

Components where behavior is controlled by JavaScript at runtime. Preview shows only initial HTML.

**Examples:**
- `search` - All states (loading, results, errors) require JS
- Interactive filters - State changes need JS execution
- Live charts/graphs - Data visualization needs JS
- Real-time widgets - Updates need JS polling

**Why Preview is Limited:**
- ❌ Component preview renders static HTML only
- ❌ Cannot execute JavaScript
- ❌ Cannot simulate user interactions
- ❌ Cannot trigger state changes

**What Preview Shows:**
- Initial HTML structure
- Default/empty state
- CSS styling
- Static markup

**What Preview Cannot Show:**
- Loading states
- Search results
- Error states
- Interaction feedback
- State transitions

**Preview Quality:** ❌ **Limited (initial state only)**

**The Issue:**

All these variants look identical in preview because they're all the same initial HTML:

```yaml
# ❌ These all render the same in static preview
variants:
  - id: "default"
    name: "Empty State"
  - id: "with-results"
    name: "With Results"     # ← Needs JS to show results
  - id: "error"
    name: "Error State"      # ← Needs JS to show error
```

**Recommendation:** Use 1 variant with clear documentation:

```yaml
name: "Search"
template: "partials/search.html"
note: |
  ⚠️ JavaScript-Driven Component

  Preview shows only initial HTML structure. Runtime states (loading, results,
  errors) require JavaScript execution and cannot be previewed statically.

  To test functionality:
  - Run: bengal serve
  - Visit: http://localhost:5173/search/

  For theme developers: To preview states, create a separate preview-only
  template that conditionally renders based on context variables.
variants:
  - id: "default"
    name: "Initial State (JS-driven)"
    context: {...}
```

**Testing Instead:**
```bash
# Start dev server to test JS functionality
bengal serve

# Visit the actual page
open http://localhost:5173/search/
```

---

### 4. Complex Nested Components ⚠️

**Partial Preview**

Components with recursive structure or heavy context dependencies. Difficult to mock fully.

**Examples:**
- `docs-nav` - Recursive navigation tree
- Hierarchical menus - Deep nesting with state
- Section builders - Complex site structure dependencies

**Why They're Challenging:**
- Require specific site structure
- May have recursive logic
- Depend on navigation state
- Hard to mock comprehensively

**Preview Quality:** ⚠️ **Partial (shows structure)**

**Recommendation:** Create 1-2 example variants, test in full site:
```yaml
variants:
  - id: "simple-example"
    context:
      # Simplified structure for preview
      section:
        pages: [...]
```

---

## Decision Matrix

When creating component manifests, use this guide:

| Component Type | Create Variants? | Best Test Method | Preview Value |
|----------------|------------------|------------------|---------------|
| **Pure Template/Macro** | ✅ Yes (3-5) | Component preview | ⭐⭐⭐⭐⭐ Excellent |
| **Template Functions** | ⚠️ Yes (2-3 with mocks) | Preview + dev server | ⭐⭐⭐⭐ Good |
| **JS-Driven** | ❌ No (1 only) | Dev server | ⭐⭐ Limited |
| **Complex Nested** | ⚠️ Maybe (1-2 examples) | Full site build | ⭐⭐ Limited |

## Real-World Examples

### ✅ Excellent Preview: breadcrumbs

```yaml
id: breadcrumbs
name: "Breadcrumbs"
macro: "navigation-components.breadcrumbs"
variants:
  - id: "home"
    params:
      page:
        breadcrumbs: []  # Shows: "Home"

  - id: "nested"
    params:
      page:
        breadcrumbs:    # Shows: "Home > Docs > Guide"
          - {title: "Home", url: "/"}
          - {title: "Docs", url: "/docs/"}
```

**Why it works:** Different params = visually different breadcrumb trails.

### ⚠️ Limited Preview: search

```yaml
id: search
name: "Search"
template: "partials/search.html"
note: "⚠️ JS-driven. Preview shows initial HTML only. Test in dev server."
variants:
  - id: "default"
    name: "Initial State (JS-driven)"
    context: {...}
```

**Why it's limited:** All states require JavaScript to render.

## For Theme Developers

### Extending JS Component Preview (Advanced)

If you want better previews for JS-driven components, you can create preview-specific templates:

```jinja2
{# partials/search-preview.html - Preview-only template #}
{% if _preview_state == "results" %}
  {# Show mocked results #}
  <div class="search-results">
    {% for result in _mock_results %}
      <article>{{ result.title }}</article>
    {% endfor %}
  </div>
{% elif _preview_state == "loading" %}
  <div class="search-loading">Loading...</div>
{% elif _preview_state == "error" %}
  <div class="search-error">Error loading search</div>
{% else %}
  {# Include actual search component #}
  {% include 'partials/search.html' %}
{% endif %}
```

Then reference it in your manifest:

```yaml
name: "Search"
template: "partials/search.html"
preview_template: "partials/search-preview.html"  # Custom!
variants:
  - id: "results"
    context:
      _preview_state: "results"
      _mock_results: [...]
```

**Note:** This is opt-in. Bengal's default theme keeps it simple - just showing the initial state.

## Philosophy

> "Component preview is for **structure**, not **behavior**. For JS-driven components, show the structure and test behavior in the browser."

**Keep it simple:**
- ✅ Create multiple variants for pure template components
- ⚠️ Create 1-2 variants with mocks for function-dependent components  
- ❌ Don't create fake variants for JS-driven components (they'll all look the same)
- 📝 Document limitations clearly in manifest `note` fields

## Summary

| Pattern | Preview Value | Recommendation |
|---------|---------------|----------------|
| Pure templates/macros | ⭐⭐⭐⭐⭐ | Multiple variants, great for preview |
| Template functions | ⭐⭐⭐⭐ | Mock data, test in dev server |
| JavaScript-driven | ⭐⭐ | 1 variant with note, test in browser |
| Complex nested | ⭐⭐ | Simple example, test in full site |

**Golden Rule:** If different "variants" would look identical in static HTML, don't create separate variants. Document the limitation instead.

---

**Related Documentation:**
- `bengal/themes/default/dev/components/README.md` - Full component catalog
- `plan/COMPONENT_PREVIEW_MACRO_UPDATE.md` - Macro system integration
- `plan/MACROS_COMPONENT_PREVIEW_BENEFITS.md` - Why macros are perfect for preview
