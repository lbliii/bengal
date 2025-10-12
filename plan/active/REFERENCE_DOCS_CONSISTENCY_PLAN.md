# Reference Documentation Consistency Plan

**Date:** 2025-10-12  
**Status:** 🎯 Planning

## Problem Analysis

### Current Inconsistencies

**1. Duplicate Class Names:**
```css
/* API-specific */
.api-header-top
.api-page-icon
.api-meta
.api-meta-item
.api-content

/* CLI-specific */
.cli-header-top
.cli-page-icon
.cli-meta-item      /* exists but unused! */
.cli-content
```

**2. Duplicate HTML Structure:**
Both templates have nearly identical structure:
- Three-column layout
- Header with icon + title
- Metadata box
- Content wrapper
- Same sidebar/navigation

**3. Scoped Styling:**
```css
.api-reference-page .api-meta { ... }  /* Only works for API */
```

CLI template uses `.api-meta` but has no specific styling, so it inherits generic styles.

**4. No Shared Components:**
Each template duplicates 90% of the HTML with only minor variations (icon, class names).

## Root Cause

**Lack of abstraction** - Each reference type was built independently without a shared foundation.

## Solution: Unified Reference Documentation System

### Phase 1: Create Shared Partials ✅

**1. `partials/reference-header.html`**
- Renders icon + title
- Accepts: `icon`, `title`, `type` (api/cli/openapi/etc.)

**2. `partials/reference-metadata.html`**
- Renders metadata box (source, module, etc.)
- Accepts: metadata dict with flexible key-value pairs
- Generic enough for any reference type

**3. Benefits:**
- Single source of truth for structure
- Easy to add new reference types (OpenAPI, GraphQL, etc.)
- Consistent styling automatically

### Phase 2: Unified CSS Classes ✅

**Replace specific classes with generic ones:**

```css
/* OLD - Type-specific */
.api-header-top, .cli-header-top
.api-page-icon, .cli-page-icon
.api-meta, .cli-meta
.api-content, .cli-content

/* NEW - Generic reference classes */
.reference-header
.reference-icon
.reference-metadata
.reference-metadata-item
.reference-content
```

**Allow type-specific variations:**
```css
/* Base styles for all reference docs */
.reference-metadata { ... }

/* Type-specific overrides only when needed */
.reference-page--api .reference-metadata { ... }
.reference-page--cli .reference-metadata { ... }
```

### Phase 3: Template Refactoring ✅

**Before:**
```jinja2
{# api-reference/single.html - 105 lines #}
<article class="prose api-reference-page">
  <header class="docs-header">
    <div class="api-header-top">
      <span class="api-page-icon">📦</span>
      <h1>{{ page.title }}</h1>
    </div>
    <div class="api-meta">
      <div class="api-meta-item">...</div>
    </div>
  </header>
  <div class="docs-content api-content">...</div>
</article>

{# cli-reference/single.html - 109 lines, 90% duplicate #}
<article class="prose cli-reference-page">
  <header class="docs-header">
    <div class="cli-header-top">
      <span class="cli-page-icon">⌨️</span>
      <h1>{{ page.title }}</h1>
    </div>
    <div class="api-meta">
      <div class="api-meta-item">...</div>
    </div>
  </header>
  <div class="docs-content cli-content">...</div>
</article>
```

**After:**
```jinja2
{# api-reference/single.html - ~40 lines #}
{% set ref_type = 'api' %}
{% set icon = '📦' %}
{% extends 'partials/reference-base.html' %}

{# cli-reference/single.html - ~40 lines #}
{% set ref_type = 'cli' %}
{% set icon = '⌨️' %}
{% extends 'partials/reference-base.html' %}
```

Or using includes:
```jinja2
{# Both templates use shared partials #}
{% set icon = '📦' %}
{% set title = page.title %}
{% set type = 'api' %}
{% include 'partials/reference-header.html' %}

{% set metadata = {
  'Module': page.metadata.module_path,
  'Source': page.metadata.source_file
} %}
{% include 'partials/reference-metadata.html' %}
```

## Implementation Plan

### Step 1: Create Partials (Non-breaking) ✅

Create new partials without changing existing templates:

1. **`partials/reference-header.html`**
   ```jinja2
   {# Set variables before including:
      {% set icon = '📦' %}
      {% set title = page.title %}
   #}
   <div class="reference-header">
     <span class="reference-icon">{{ icon | default('📄') }}</span>
     <h1>{{ title }}</h1>
   </div>
   ```

2. **`partials/reference-metadata.html`**
   ```jinja2
   {% if metadata %}
   <div class="reference-metadata">
     {% for label, value in metadata.items() %}
     {% if value %}
     <div class="reference-metadata-item">
       <strong>{{ label }}:</strong>
       <code>{{ value }}</code>
     </div>
     {% endif %}
     {% endfor %}
   </div>
   {% endif %}
   ```

### Step 2: Add Generic CSS (Backwards Compatible) ✅

Add new classes alongside existing ones:

```css
/* ============================================
   Reference Documentation - Unified Base
   ============================================ */

/* Header */
.reference-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
}

.reference-icon {
    font-size: var(--text-3xl);
    line-height: 1;
}

/* Metadata Box */
.reference-metadata {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    margin: var(--space-4) 0;
    padding: var(--space-4);
    background: var(--color-surface);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
}

.reference-metadata-item {
    display: flex;
    gap: var(--space-2);
    font-size: var(--text-sm);
    line-height: 1.5;
}

.reference-metadata-item strong {
    color: var(--color-text-primary-muted);
    font-weight: 600;
    min-width: 60px;
}

.reference-metadata-item code {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    background: var(--color-bg-code);
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-sm);
    color: var(--color-code-text);
}

/* Content */
.reference-content {
    /* Generic content styles */
}

/* Type-specific variations (only if needed) */
.reference-page--api .reference-icon {
    /* API-specific icon styling if needed */
}

.reference-page--cli .reference-metadata {
    /* CLI-specific metadata styling if needed */
}
```

### Step 3: Migrate Templates ✅

**Option A: Using Partials (Recommended)**
- More flexible
- Easier to customize per-type
- Better for maintainability

**Option B: Using Base Template**
- More DRY
- Less flexibility
- Better if all types are truly identical

**Recommended: Option A with partials**

### Step 4: Deprecate Old Classes ✅

1. Add deprecation comments to old classes
2. Add console warnings in dev mode
3. Remove in next major version

## Benefits

### For Users
- **Consistent experience** across all reference docs
- **Familiar patterns** - learn once, use everywhere
- **Better visual hierarchy** - same structure = easier scanning

### For Developers
- **DRY principle** - one place to update
- **Easy to extend** - add new reference types quickly
- **Maintainable** - less duplicate code

### For Theme Builders
- **Clear patterns** - obvious how to style reference docs
- **Generic classes** - easy to override
- **Predictable structure** - consistent HTML

## Success Metrics

- [ ] All reference types use same base classes
- [ ] No duplicate HTML structure
- [ ] CSS reduced by ~40% for reference docs
- [ ] New reference type can be added in <50 lines
- [ ] Visual consistency across API, CLI, OpenAPI, etc.

## Migration Path

### For Existing Users

**Phase 1: Add (No breaking changes)**
- New partials coexist with old templates
- New CSS classes added alongside old ones
- No user action required

**Phase 2: Migrate (Backwards compatible)**
- Templates updated to use new partials
- Old classes still work (aliased to new ones)
- Deprecation warnings in console

**Phase 3: Remove (Major version)**
- Old classes removed
- Old template patterns deprecated
- Clean, unified system

## Future: Extended Reference Types

With this foundation, adding new reference types is trivial:

```jinja2
{# openapi-reference/single.html #}
{% set icon = '🔌' %}
{% set title = page.title %}
{% set type = 'openapi' %}
{% include 'partials/reference-header.html' %}

{% set metadata = {
  'Endpoint': page.metadata.endpoint,
  'Method': page.metadata.method,
  'Schema': page.metadata.schema_file
} %}
{% include 'partials/reference-metadata.html' %}
```

```jinja2
{# graphql-reference/single.html #}
{% set icon = '⚡' %}
{% set title = page.title %}
{% set type = 'graphql' %}
{% include 'partials/reference-header.html' %}

{% set metadata = {
  'Type': page.metadata.gql_type,
  'Schema': page.metadata.schema_file
} %}
{% include 'partials/reference-metadata.html' %}
```

## Next Steps

1. ✅ Create partials
2. ✅ Add generic CSS
3. ✅ Migrate API template
4. ✅ Migrate CLI template
5. ✅ Test consistency
6. ✅ Document pattern for new types
