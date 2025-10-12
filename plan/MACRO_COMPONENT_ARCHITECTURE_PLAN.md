# Macro Component Architecture Plan

**Date:** 2025-10-12  
**Status:** 🎯 Planning

## Strategic Question

How should Bengal organize templates to support macro-based components while maintaining clarity for theme developers?

## Current Structure

```
themes/default/templates/
├── layouts/              # Base page structures
│   ├── base.html
│   ├── docs.html
│   └── minimal.html
├── partials/             # Reusable includes
│   ├── breadcrumbs.html
│   ├── docs-nav.html
│   ├── reference-header.html   # ← Old include pattern
│   └── reference-metadata.html # ← Old include pattern
├── api-reference/        # Section templates
│   ├── list.html
│   └── single.html
├── cli-reference/
├── blog/
└── ...
```

## Architecture Options

### Option A: Separate `components/` Directory ❌

```
templates/
├── layouts/          # Layouts (extends)
├── partials/         # Includes (old style)
├── components/       # Macros (new style)  ← NEW LAYER
└── [sections]/
```

**Pros:**
- Clear separation between old and new
- Obvious where components live

**Cons:**
- ❌ Adds a third conceptual layer
- ❌ More directories = more cognitive load
- ❌ Duplication during migration
- ❌ Where does something "become" a component?

### Option B: Single `partials/components.html` ❌

```
templates/
├── layouts/
├── partials/
│   ├── components.html           # ALL macros in one file
│   ├── breadcrumbs.html          # Old includes (deprecated)
│   └── reference-header.html     # Old includes (deprecated)
└── [sections]/
```

**Pros:**
- No new directory
- Clear that `components.html` is the new way

**Cons:**
- ❌ One giant file with all macros
- ❌ Hard to navigate/maintain
- ❌ Merge conflicts
- ❌ No logical grouping

### Option C: Domain-Grouped Component Files ✅ **RECOMMENDED**

```
templates/
├── layouts/
├── partials/
│   ├── reference-components.html     # Reference doc macros
│   ├── layout-components.html        # Layout/structure macros
│   ├── ui-components.html            # UI element macros
│   ├── navigation-components.html    # Nav/menu macros
│   │
│   ├── breadcrumbs.html              # Old include (to deprecate)
│   ├── reference-header.html         # Old include (to deprecate)
│   └── docs-nav.html                 # Old include (maybe keep)
└── [sections]/
```

**Pros:**
- ✅ Organized by domain
- ✅ Each component file is focused (~100-200 lines)
- ✅ Still in `partials/` (no new conceptual layer)
- ✅ Clear naming convention (`*-components.html` = macros)
- ✅ Easy to find related components
- ✅ Gradual migration path
- ✅ Scales with more components

**Cons:**
- Multiple files to potentially import from
- Need consistent naming convention

### Option D: Colocated Macros ❌

Put macro definition inside the include file itself:

```jinja2
{# partials/breadcrumbs.html #}

{# MACRO VERSION (preferred) #}
{% macro breadcrumbs(items, separator='/') %}
  <nav>...</nav>
{% endmacro %}

{# INCLUDE VERSION (backwards compat) #}
{% if items is not defined %}
  <nav>...</nav>  {# Duplicate HTML #}
{% endif %}
```

**Pros:**
- Everything in one place
- Backwards compatible

**Cons:**
- ❌ Duplicated HTML code
- ❌ Confusing dual-purpose files
- ❌ Not clear which pattern to use
- ❌ Harder to deprecate old pattern

## Recommended Architecture: Domain-Grouped Components

### Structure

```
themes/default/templates/
├── layouts/                          # Base page structures (extends)
│   ├── base.html
│   ├── docs.html
│   └── minimal.html
│
├── partials/                         # Reusable components & includes
│   │
│   ├── reference-components.html    # 📦 Reference documentation macros
│   ├── layout-components.html       # 📐 Layout/structure macros
│   ├── ui-components.html           # 🎨 UI element macros
│   ├── navigation-components.html   # 🧭 Navigation macros
│   ├── content-components.html      # 📝 Content display macros
│   │
│   ├── breadcrumbs.html             # [DEPRECATED] Use navigation-components
│   ├── docs-nav.html                # [KEEP] Complex navigation
│   └── footer.html                  # [KEEP] Large layout chunk
│
├── api-reference/                    # Section-specific templates
│   ├── list.html
│   └── single.html
│
├── cli-reference/
├── blog/
└── ...
```

### Component File Organization

#### `partials/reference-components.html`
All macros related to reference documentation:
- `reference_header()`
- `reference_metadata()`
- `api_signature()`
- `cli_usage()`

#### `partials/layout-components.html`
Layout and structure macros:
- `three_column_layout()`
- `sidebar()`
- `card()`
- `grid()`

#### `partials/ui-components.html`
UI element macros:
- `button()`
- `badge()`
- `alert()`
- `icon()`

#### `partials/navigation-components.html`
Navigation macros:
- `breadcrumbs()`
- `pagination()`
- `menu_item()`
- `toc()`

#### `partials/content-components.html`
Content display macros:
- `code_block()`
- `callout()`
- `table_of_contents()`
- `related_posts()`

## Naming Conventions

### File Naming
- **Macro files:** `{domain}-components.html`
- **Old includes:** `{name}.html` (no suffix)
- **Layouts:** `{name}.html` in `layouts/`

### Macro Naming
- **Snake case:** `reference_header()`, not `referenceHeader()`
- **Descriptive:** `api_signature()`, not `sig()`
- **Domain-prefixed if needed:** `api_parameter_list()`, `cli_option_list()`

### Import Pattern
```jinja2
{# Import specific macros you need #}
{% from 'partials/reference-components.html' import reference_header, reference_metadata %}
{% from 'partials/ui-components.html' import button, badge %}

{# Use in template #}
{{ reference_header(icon='📦', title=page.title) }}
{{ button(text='Click me', type='primary') }}
```

## Migration Strategy

### Phase 1: Core Components (Week 1)
**Goal:** Convert most-used includes to macros

1. ✅ `reference-components.html` (done)
   - ✅ `reference_header()`
   - ✅ `reference_metadata()`

2. `navigation-components.html`
   - `breadcrumbs(items, separator='/')`
   - `pagination(current, total, base_url)`
   - `toc(items, max_depth=3)`

3. `ui-components.html`
   - `button(text, url=None, type='default')`
   - `badge(text, color='default')`
   - `alert(message, type='info')`
   - `card(title, content, url=None)`

4. `layout-components.html`
   - `sidebar(content, position='left')`
   - `grid(items, columns=3)`

### Phase 2: Section Templates (Week 2)
**Goal:** Update all section templates to use new macros

1. ✅ `api-reference/single.html` (done)
2. ✅ `cli-reference/single.html` (done)
3. `blog/post.html`
4. `docs/single.html`
5. `blog/list.html`
6. `api-reference/list.html`

### Phase 3: Deprecation (Week 3)
**Goal:** Mark old includes as deprecated, add warnings

1. Add deprecation comments to old include files:
```jinja2
{# DEPRECATED: Use navigation-components.html breadcrumbs() macro instead
   This include-based pattern will be removed in Bengal 1.0

   Old:
     {% include 'partials/breadcrumbs.html' %}

   New:
     {% from 'partials/navigation-components.html' import breadcrumbs %}
     {{ breadcrumbs(items) }}
#}
```

2. Add console warnings (optional):
```python
# In template engine
if 'partials/breadcrumbs.html' in template_name:
    logger.warning("Using deprecated include pattern, use macro instead")
```

### Phase 4: Cleanup (Bengal 1.0)
**Goal:** Remove old includes

1. Delete deprecated include files
2. Update all bundled themes
3. Update documentation
4. Release as breaking change in Bengal 1.0

## When to Use Each Pattern

### Use Macros (Components) ✅ **DEFAULT**
- **Reusable UI elements:** buttons, badges, cards
- **Small isolated components:** breadcrumbs, pagination
- **Components with parameters:** anything that needs configuration
- **New code:** always prefer macros for new components

**Example:**
```jinja2
{% from 'partials/ui-components.html' import button, card %}
{{ button(text='Learn More', url='/docs/', type='primary') }}
```

### Use Includes ⚠️ **LIMITED CASES**
- **Large layout chunks:** entire sidebars, footers (>100 lines)
- **Complex context-dependent components:** main navigation with active states
- **Backwards compatibility:** during migration period

**Example:**
```jinja2
{# Complex navigation that relies on heavy context #}
{% include 'partials/docs-nav.html' %}
```

### Use Layouts (Extends) 📐 **STRUCTURE**
- **Base page structures:** overall HTML structure
- **Layout inheritance:** docs layout extends base layout

**Example:**
```jinja2
{% extends 'layouts/docs.html' %}
{% block content %}...{% endblock %}
```

## Documentation for Theme Developers

### Component Discovery

Create `themes/default/COMPONENTS.md`:

```markdown
# Bengal Default Theme Components

## Reference Components
`{% from 'partials/reference-components.html' import ... %}`

### reference_header(icon, title, description=None, type='default')
Display header for reference documentation.

**Parameters:**
- `icon` (required): Emoji or icon
- `title` (required): Page title
- `description` (optional): Lead text
- `type` (optional): 'api', 'cli', etc.

**Example:**
\```jinja2
{{ reference_header(icon='📦', title=page.title) }}
\```

## UI Components
`{% from 'partials/ui-components.html' import ... %}`

### button(text, url=None, type='default', size='medium')
...
```

### IDE Support

Create JSON schema for autocomplete:

```json
{
  "components": {
    "reference_header": {
      "params": {
        "icon": { "type": "string", "required": true },
        "title": { "type": "string", "required": true },
        "description": { "type": "string", "required": false },
        "type": { "type": "string", "required": false, "default": "default" }
      }
    }
  }
}
```

## Benefits of This Architecture

### For Theme Developers
1. ✅ Clear organization by domain
2. ✅ Easy to find related components
3. ✅ Self-documenting imports
4. ✅ No new conceptual layer to learn
5. ✅ Gradual migration path

### For Bengal Core
1. ✅ Scalable (can add more component files)
2. ✅ Maintainable (smaller, focused files)
3. ✅ Backwards compatible during migration
4. ✅ Clear deprecation path
5. ✅ Matches industry patterns

### For Users
1. ✅ Better error messages
2. ✅ Faster template compilation (less scope pollution)
3. ✅ More reliable builds (fewer silent failures)
4. ✅ Easier theme customization

## File Size Guidelines

Keep component files focused and manageable:

- **Small:** < 100 lines (ui-components.html)
- **Medium:** 100-300 lines (reference-components.html)
- **Large:** 300-500 lines (break into smaller files)
- **Too Large:** > 500 lines (definitely split)

If a component file grows too large, split by subdomain:
```
partials/
  ui-components.html          → Too large

  ui-buttons-components.html   → Split out
  ui-cards-components.html     → Split out
  ui-alerts-components.html    → Split out
```

## Decision: Use Domain-Grouped Components

**Rationale:**
1. No new conceptual layer (still in `partials/`)
2. Clear organization without over-engineering
3. Scales naturally as components grow
4. Easy to understand and discover
5. Gradual migration without disruption
6. Matches patterns from other ecosystems

**Implementation:**
- Put all macros in `partials/{domain}-components.html`
- Use clear naming: `*-components.html` = macros
- Keep complex includes during transition
- Deprecate old includes gradually
- Document component files clearly

This is the right long-term architecture for Bengal themes.
