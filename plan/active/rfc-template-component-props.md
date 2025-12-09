# RFC: Template Component Props & Layering System

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-06  
**Priority**: MEDIUM  
**Depends On**: rfc-shareable-site-skeletons.md (Component Model)

---

## Summary

Extend the Component Model to **template partials** with two key mechanisms:
1.  **Explicit Props**: Typed configuration for components (e.g., `show_reading_time=true`) via Jinja2 macros.
2.  **Atomic Layering**: Decompose complex components into reusable, overridable parts ("Atoms" and "Molecules").

**Key Insight**: By decomposing large partials (like `page-hero`) into smaller "atoms" (like `hero_title`) and "molecules" (like `share_widget`), we allow themers to customize specific parts via the theme chain without rewriting the entire component. This enables "Swizzling"—overriding just the part you need.

---

## The Problem

### Current State: Dispatcher Anti-Pattern

The `page-hero.html` partial is a dispatcher that routes to 4 different implementations. The `magazine` variant is particularly problematic:

```html
<!-- page-hero-magazine.html -->
<div class="page-hero">
   <!-- ... 150 lines of mixed layout, title logic, and complex share dropdown ... -->
</div>
```

Problems:
1.  **Monolithic**: The "Share with AI" dropdown logic is trapped inside the hero. You can't use it in the footer.
2.  **Rigidity**: A themer cannot change the date format without copying the entire 150-line file, shielding them from future bug fixes to the share widget.
3.  **Duplication**: Similar logic is repeated across `editorial` and `magazine`.
4.  **Drift**: Templates like `api-reference` have drifted from `doc` because the dispatcher is too rigid to reuse.

---

## The Solution: Atomic Components & Layering

### 1. Mental Model: Atomic Design

We apply **Atomic Design** principles to Jinja macros:

*   **Atoms**: Basic building blocks (e.g., `hero_title`, `hero_meta`).
*   **Molecules**: Functional units composed of atoms (e.g., `share_widget` - the complex AI dropdown).
*   **Organisms**: Complex sections composed of molecules/atoms (e.g., `page_hero`).

### 2. Props Convention & Explicit Context

Every component accepts typed props. **Crucially**, we pass explicit arguments to avoid "Context Traps" (Jinja2 scoping issues).

```jinja2
{# partials/components/page-hero.html #}

{% from 'partials/components/share-widget.html' import share_widget %}
{% from 'partials/components/atoms/hero-title.html' import hero_title %}

{% macro page_hero(
    page,
    show_share=true,
    title_tag='h1',
    extra_classes="",
    **overrides
) %}
    <header class="page-hero {{ extra_classes }}">

        {# Explicitly pass data to atoms - SAFE #}
        {{ hero_title(title=page.title, tag=title_tag) }}

        {% if show_share %}
            <div class="page-hero__actions">
                {# Pass class_prefix to adapt BEM styling #}
                {{ share_widget(page=page, class_prefix='page-hero') }}
            </div>
        {% endif %}

        {# Slot for custom content #}
        {{ caller() if caller else '' }}
    </header>
{% endmacro %}
```

### 3. Layering via Theme Chain (Swizzling)

Because Bengal resolves imports via the theme chain, layering is native:

1.  **Base Theme** defines `partials/components/share-widget.html`.
2.  **Child Theme** creates `partials/components/share-widget.html` to add a new "Share to Mastodon" button.
3.  **Result**: The `page_hero` (and footer, etc.) automatically use the *new* widget.

---

## Proposed Component Library

### Phase 1: Core Components

| Component | Type | Props | Description |
|-----------|------|-------|-------------|
| `page_hero` | Organism | `page`, `show_share`, `preset` | The main hero wrapper. Composes title, meta, widget. |
| `share_widget` | Molecule | `page`, `class_prefix` | **NEW**: The complex AI share dropdown. Reusable! |
| `hero_title` | Atom | `title`, `tag`, `class_prefix` | Renders the title. |
| `hero_meta` | Atom | `page`, `show_date`, `class_prefix` | Renders metadata line. |
| `toc` | Molecule | `page`, `collapsible`, `max_depth` | Table of contents. |

---

## Directory Structure

```
partials/
├── components/
│   ├── page-hero.html          # Organism (The Controller)
│   ├── share-widget.html       # Molecule (Reusable logic)
│   ├── toc.html
│   └── atoms/                  # Overridable Atoms
│       ├── hero-title.html
│       ├── hero-meta.html
│       └── hero-breadcrumbs.html
```

---

## Benefits

1.  **Reusability**: The `share_widget` can now be used in the footer or sidebar, not just the hero.
2.  **Surgical Overrides**: Change the `hero_title` markup without touching the complex `share_widget` logic.
3.  **Safe Upgrades**: Themers who override atoms still receive updates/fixes to the molecules they didn't touch.
4.  **Consistency**: Use the same `page_hero` macro across Doc, API, and Blog layouts with different props.

---

## Risks & Mitigations (Gotchas)

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Context Trap** | Macros don't see global context. | **Rule**: Always pass explicit arguments (e.g., pass `page` object). |
| **CSS Prefixing** | Reused widgets might break layout. | **Rule**: Atoms must accept `class_prefix` prop to adapt BEM classes. |
| **Name Collisions** | Overriding files requires matching macro names. | **Doc**: Explicitly document required macro names for overrides. |

---

## Migration Path

### Step 1: Extract Components
- [ ] **Extract** the "Share with AI" logic from `page-hero-magazine.html` into `components/share-widget.html`.
- [ ] **Extract** title/meta logic into `atoms/`.

### Step 2: Update Templates
- [ ] Create `components/page-hero.html` that imports and uses `share_widget`.
- [ ] Update `doc/single.html` to use the new macro.

### Step 3: Cleanup
- [ ] Remove legacy `page-hero-*.html` files once migrated.
