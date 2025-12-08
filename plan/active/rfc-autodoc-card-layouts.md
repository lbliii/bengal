# RFC: Autodoc Card-Based Layouts

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-01-08  
**Related**: `bengal/autodoc/`, `bengal/themes/default/assets/css/components/cards.css`

---

## Executive Summary

The current autodoc-generated API documentation pages have **three critical UX issues**:

1. **Low-value module listings** - Plain `<ul><li>` lists with just module names, no context
2. **Missing descriptions** - Links have no descriptions, making it hard to find what you need
3. **Poor visual design** - No visual hierarchy, no cards, no use of existing theme capabilities

This RFC proposes **card-based layouts** that leverage Bengal's existing card system to create rich, informative API documentation pages inspired by modern design patterns.

---

## Problem Analysis

### Current State

The API index page (`/api/`) outputs:

```html
<div class="api-section-index">
  <h2>Packages</h2>
  <ul>
    <li><a href="/api/analysis/">Analysis</a></li>
    <li><a href="/api/assets/">Assets</a></li>
    <!-- ... 20 more identical links ... -->
  </ul>
  <h2>Modules</h2>
  <ul>
    <li><a href="/api/__main__/">__main__</a></li>
    <li><a href="/api/analysis/">analysis</a></li>
    <!-- ... 20 more identical links ... -->
  </ul>
</div>
```

**Problems:**
- No descriptions - users must click to learn what each module does
- No visual differentiation - all items look identical
- Duplicated content - Packages and Modules often overlap
- No statistics - no indication of module size/importance
- Wastes existing card CSS - Bengal has a beautiful card system that isn't used

### What Users Need

When browsing API docs, users want to:
1. **Quickly scan** to find the right module
2. **Understand purpose** without clicking through
3. **See complexity** (is this a large module with many classes?)
4. **Navigate efficiently** to the most important entry points

---

## Proposed Solution

### 1. Card-Based Module Index

Replace flat lists with card grids populated from `DocElement` data:

```markdown
::::{cards}
:columns: 1-2-3
:gap: medium
:variant: api-module

:::{card} Core
:link: /api/core/
:icon: cube

Core domain models for Bengal SSG including Page, Site, Section, and Asset.

`5 classes` · `12 functions`
:::

:::{card} Orchestration
:link: /api/orchestration/
:icon: flow-arrow

Build coordination and multi-phase orchestration.

`3 classes` · `8 functions`
:::

<!-- ... more cards ... -->
::::
```

**Key Features:**
- **Description preview** - First sentence of module docstring
- **Statistics badges** - Count of classes, functions, constants
- **Icon support** - Visual differentiation by module type
- **Hover effects** - Existing card CSS provides beautiful interactions

### 2. Module Page Improvements

Within module pages, show class/function summaries as cards:

```markdown
## Classes

::::{card-grid}
:columns: 2
:variant: api-class

:::{card} Page
:link: #page
:badge: Dataclass

Represents a single content page in the site.

**Properties:** title, url, content, metadata
:::

:::{card} Site
:link: #site

Root container for all site data and configuration.

**Properties:** pages, sections, config, theme
:::
::::
```

### 3. Low-Value Page Filtering

Add configuration to filter out low-value pages:

```yaml
# autodoc.yaml
autodoc:
  python:
    # Minimum requirements for a module to get a standalone page
    min_public_members: 1  # Must have at least 1 public class/function
    
    # Modules with no docstring get "stub" treatment
    stub_modules: collapse  # Options: collapse, hide, show
    
    # Private module handling
    private_pattern: "^_"
    show_private: false
```

**Low-value indicators:**
- No module docstring (`*No module description provided.*)
- No public classes or functions
- Only re-exports (no original content)
- Internal/private modules (`_internal`, `__pycache__`)

---

## Implementation Plan

### Phase 1: Template Changes (2-3 hours)

**New Templates:**

1. **`python/partials/module_index_cards.md.jinja2`** - Card-based module listing

```jinja2
{# Module Index Cards - replaces flat ul/li lists #}
{% from 'macros/safe_macros.md.jinja2' import safe_section %}

{% set submodules = element.children | selectattr('element_type', 'equalto', 'module') | list %}
{% set packages = submodules | selectattr('metadata.is_package', 'equalto', true) | list %}

{% if packages %}
::::{card-grid}
:columns: 1-2-3
:gap: medium
:variant: api-module

{% for pkg in packages %}
{% set class_count = pkg.children | selectattr('element_type', 'equalto', 'class') | list | length %}
{% set func_count = pkg.children | selectattr('element_type', 'equalto', 'function') | list | length %}
{% set desc_preview = pkg.description | default('') | truncate(120, true) %}

:::{card} {{ pkg.name | title }}
:link: {{ pkg.qualified_name | module_to_url }}
:icon: {{ pkg.metadata.icon | default('folder') }}

{{ desc_preview if desc_preview else '*No description*' }}

{% if class_count or func_count %}
`{{ class_count }} classes` · `{{ func_count }} functions`
{% endif %}
:::
{% endfor %}

::::
{% endif %}
```

2. **`python/partials/class_summary_cards.md.jinja2`** - Card grid for classes

3. **`python/partials/function_summary_cards.md.jinja2`** - Card grid for functions

### Phase 2: CSS Additions (1-2 hours)

**New styles in `components/api-reference.css`:**

```css
/* API Module Cards */
.card-grid[data-variant="api-module"] .card {
  --card-accent-color: var(--color-api-module);
}

.card-grid[data-variant="api-class"] .card {
  --card-accent-color: var(--color-api-class);
}

.card-grid[data-variant="api-function"] .card {
  --card-accent-color: var(--color-api-function);
}

/* Stats badges in cards */
.card .api-stats {
  display: flex;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: auto;
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border-light);
}

.card .api-stats code {
  background: var(--color-bg-tertiary);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
}
```

### Phase 3: Filter Logic (1-2 hours)

**Add to `bengal/autodoc/generator.py`:**

```python
def should_generate_page(element: DocElement, config: AutodocConfig) -> bool:
    """Determine if element warrants a standalone page."""
    # Always generate for packages with content
    if element.metadata.get('is_package'):
        return True
    
    # Check minimum member threshold
    public_members = [
        c for c in element.children 
        if not c.name.startswith('_')
    ]
    if len(public_members) < config.min_public_members:
        return False
    
    # Skip internal modules
    if element.name.startswith('_') and not config.show_private:
        return False
    
    return True

def get_description_preview(element: DocElement, max_length: int = 120) -> str:
    """Extract first sentence or truncate description."""
    desc = element.description or ''
    
    # Try to get first sentence
    if '. ' in desc:
        first_sentence = desc.split('. ')[0] + '.'
        if len(first_sentence) <= max_length:
            return first_sentence
    
    # Truncate if needed
    if len(desc) > max_length:
        return desc[:max_length-3].rsplit(' ', 1)[0] + '...'
    
    return desc
```

### Phase 4: Template Filters (30 min)

**Add to `bengal/autodoc/template_config.py`:**

```python
def setup_autodoc_filters(env: Environment) -> None:
    """Add autodoc-specific template filters."""
    
    def module_to_url(qualified_name: str) -> str:
        """Convert module path to URL path."""
        return '/api/' + qualified_name.replace('.', '/') + '/'
    
    def count_public(children: list, element_type: str) -> int:
        """Count public children of a type."""
        return len([
            c for c in children 
            if c.element_type == element_type and not c.name.startswith('_')
        ])
    
    def description_preview(desc: str, max_length: int = 120) -> str:
        """Get description preview."""
        return get_description_preview_text(desc, max_length)
    
    env.filters['module_to_url'] = module_to_url
    env.filters['count_public'] = count_public
    env.filters['description_preview'] = description_preview
```

---

## Visual Design Reference

### Inspiration: Search Modal Aesthetic

The Bengal search modal has a clean, modern aesthetic with:
- Subtle background gradients
- Smooth hover transitions
- Clear visual hierarchy
- Icon integration

Apply similar patterns to API cards:

```css
/* API Card - Search-inspired aesthetic */
.api-card {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-4) var(--space-5);
  
  /* Subtle gradient overlay on hover */
  position: relative;
  overflow: hidden;
}

.api-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--color-primary) 5%, transparent) 0%,
    transparent 50%
  );
  opacity: 0;
  transition: opacity var(--transition-base);
}

.api-card:hover::before {
  opacity: 1;
}

/* Card icon with accent background */
.api-card-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: var(--radius-lg);
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
}
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Python Source Code                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Python Extractor                             │
│  - Parse AST                                                    │
│  - Extract docstrings                                           │
│  - Count public members                                         │
│  - Build DocElement tree                                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Filter Logic (NEW)                           │
│  - Check min_public_members threshold                           │
│  - Identify stub modules                                        │
│  - Mark low-value pages for collapse/hide                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Jinja2 Templates (UPDATED)                   │
│  - module_index_cards.md.jinja2 (NEW)                           │
│  - class_summary_cards.md.jinja2 (NEW)                          │
│  - Enhanced filters (count_public, description_preview)         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Card CSS (LEVERAGE EXISTING)                 │
│  - .card-grid with data-variant="api-module"                    │
│  - Existing card hover effects                                  │
│  - Color variants for types (class, function, module)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration Schema

```yaml
# autodoc.yaml additions
autodoc:
  python:
    # Existing config...
    
    # NEW: Display options
    display:
      # Use card layout for module index (default: true)
      card_layout: true
      
      # Columns for card grid (responsive: mobile-tablet-desktop)
      card_columns: "1-2-3"
      
      # Show statistics in cards (class/function counts)
      show_stats: true
      
      # Description preview length
      preview_length: 120
      
    # NEW: Filtering options  
    filtering:
      # Minimum public members for standalone page
      min_public_members: 1
      
      # How to handle modules without docstrings
      # Options: show (default), collapse (into parent), hide
      undocumented_modules: show
      
      # Skip internal modules (starting with _)
      skip_private: true
      
      # Modules to always show regardless of filters
      always_include:
        - "bengal.core"
        - "bengal.cli"
```

---

## Before/After Comparison

### Before: API Index Page

```
┌─────────────────────────────────────────────────────────────────┐
│  API Reference                                                  │
│                                                                 │
│  Packages                                                       │
│  • Analysis                                                     │
│  • Assets                                                       │
│  • Autodoc                                                      │
│  • Cache                                                        │
│  • ...                                                          │
│                                                                 │
│  Modules                                                        │
│  • __main__                                                     │
│  • analysis                                                     │
│  • ...                                                          │
└─────────────────────────────────────────────────────────────────┘
```

### After: API Index Page

```
┌─────────────────────────────────────────────────────────────────┐
│  API Reference                                                  │
│                                                                 │
│  Browse Bengal's Python API documentation by package.           │
│                                                                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ 📦 Core         │ │ 🔄 Orchestration│ │ 🎨 Rendering    │   │
│  │                 │ │                 │ │                 │   │
│  │ Domain models   │ │ Build coord... │ │ Template and... │   │
│  │ for Bengal SSG. │ │                 │ │                 │   │
│  │                 │ │ 3 classes       │ │ 2 classes       │   │
│  │ 5 classes       │ │ 8 functions     │ │ 15 functions    │   │
│  │ 12 functions    │ │                 │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ 💾 Cache        │ │ ✓ Health        │ │ ⌨️ CLI          │   │
│  │                 │ │                 │ │                 │   │
│  │ Caching infra...│ │ Validation and..│ │ Command-line... │   │
│  │                 │ │                 │ │                 │   │
│  │ 8 classes       │ │ 4 classes       │ │ 2 classes       │   │
│  │ 5 functions     │ │ 12 functions    │ │ 25 functions    │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

1. **Improved scannability** - Users can identify relevant modules in <10 seconds
2. **Reduced clicks** - Description previews eliminate need to click through
3. **Visual hierarchy** - Important modules stand out, internal modules de-emphasized
4. **Consistent aesthetic** - Cards match Bengal's existing theme/search modal style
5. **Configurable** - Site authors can customize thresholds and display options

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Large card grids on big codebases | Pagination or grouped sections |
| Missing descriptions look empty | Show "No description" with visual indicator |
| Performance with many modules | Lazy-load card content, limit initial display |
| Breaking existing autodoc output | Feature flag (`card_layout: true/false`) |

---

## Open Questions

1. **Grouping strategy** - Should packages be grouped by subsystem (core, rendering, cache)?
2. **Search integration** - Should card grid support filtering/search?
3. **Deprecation styling** - How to visually indicate deprecated modules?
4. **Versioning** - How to handle multi-version API docs?

---

## Next Steps

1. [ ] Review and approve RFC
2. [ ] Implement Phase 1: Template changes
3. [ ] Implement Phase 2: CSS additions
4. [ ] Implement Phase 3: Filter logic
5. [ ] Implement Phase 4: Template filters
6. [ ] Test with Bengal's own API docs
7. [ ] Document configuration options
8. [ ] Update autodoc guide

---

## References

- [DocElement model](bengal/autodoc/base.py:16-83)
- [Existing card CSS](bengal/themes/default/assets/css/components/cards.css)
- [Current module template](bengal/autodoc/templates/python/module.md.jinja2)
- [Search modal design](bengal/themes/default/assets/css/components/search.css)

