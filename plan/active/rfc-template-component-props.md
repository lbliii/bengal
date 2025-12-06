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
2.  **Atomic Layering**: Decompose complex components into reusable, overridable parts.

**Key Insight**: By decomposing large partials (like `page-hero`) into smaller "atoms" and "molecules" (like `share_widget`), we allow themers to customize specific parts via the theme chain without rewriting the entire component.

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
2.  **Rigidity**: A themer cannot change the date format without copying the entire 150-line file, including the complex share logic.
3.  **Duplication**: Similar logic is repeated across `editorial` and `magazine`.

---

## The Solution: Atomic Components & Layering

### 1. Mental Model: Atomic Design

We apply **Atomic Design** principles to Jinja macros:

*   **Atoms**: Basic building blocks (e.g., `hero_title`, `hero_meta`).
*   **Molecules**: Functional units composed of atoms (e.g., `share_widget` - the complex AI dropdown).
*   **Organisms**: Complex sections composed of molecules/atoms (e.g., `page_hero`).

### 2. Props Convention

Every component accepts typed props and supports content injection:

```jinja2
{# partials/components/page-hero.html #}

{% from 'partials/components/share-widget.html' import share_widget with context %}
{% from 'partials/components/atoms/hero-title.html' import hero_title with context %}

{% macro page_hero(
    show_share=true,
    title_tag='h1',
    extra_classes="",
    **overrides
) %}
    <header class="page-hero {{ extra_classes }}">

        {{ hero_title(tag=title_tag) }}

        {% if show_share %}
            {# Reusing the complex share logic as a component #}
            <div class="page-hero__actions">
                {{ share_widget(context='hero') }}
            </div>
        {% endif %}

        {# Slot for custom content #}
        {{ caller() if caller else '' }}
    </header>
{% endmacro %}
```

### 3. Layering via Theme Chain

Because Bengal resolves imports via the theme chain, layering is native:

1.  **Base Theme** defines `partials/components/share-widget.html`.
2.  **Child Theme** creates `partials/components/share-widget.html` to add a new "Share to Mastodon" button.
3.  **Result**: The `page_hero` (and footer, etc.) automatically use the *new* widget.

---

## Proposed Component Library

### Phase 1: Core Components

| Component | Type | Props | Description |
|-----------|------|-------|-------------|
| `page_hero` | Organism | `show_share`, `preset` | The main hero wrapper. Composes title, meta, widget. |
| `share_widget` | Molecule | `url`, `title`, `orientation` | **NEW**: The complex AI share dropdown. Reusable! |
| `hero_title` | Atom | `title`, `tag` | Renders the title. |
| `hero_meta` | Atom | `show_date`, `show_time` | Renders metadata line. |
| `toc` | Molecule | `collapsible`, `max_depth` | Table of contents. |

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

## Benefits for Themers

1.  **Reusability**: The `share_widget` can now be used in the footer or sidebar, not just the hero.
2.  **Surgical Overrides**: Change the `hero_title` markup without touching the complex `share_widget` logic.
3.  **Composition**: Build new layouts by composing existing atoms/molecules.

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
