# RFC: Auto-Generated Cards from Children

> **Status**: Draft  
> **Created**: 2025-01-03  
> **Problem**: Index pages require manual card definitions that duplicate child page frontmatter

---

## Problem Statement

Current index pages require manually defining cards with hardcoded titles and descriptions:

```markdown
::::{cards}
:::{card} 📁 Organize Content
:link: ./organization/
:color: green
Understand pages, sections, bundles...  ← DUPLICATES organization/_index.md description
:::
::::
```

This creates:
1. **Maintenance burden** - Changes to child frontmatter don't propagate
2. **Drift risk** - Descriptions go out of sync over time
3. **Boilerplate** - Every index page repeats the same pattern

## Proposed Solution

### Option A: `source: children` on Cards Grid (Recommended)

Add a `source` option to the cards directive:

```markdown
:::{cards}
:source: children
:columns: 2
:gap: medium
:::
```

This would:
1. Automatically iterate over `subsections` and `posts` from template context
2. Pull `title`, `description`, `icon`, `color` from each child's frontmatter
3. Generate card HTML for each child

**Frontmatter for children:**

```yaml
# organization/_index.md
---
title: Content Organization
description: Pages, sections, and bundles explained
icon: folder          # Optional - for card icon
card_color: green     # Optional - for card color
weight: 10            # For ordering
---
```

**Filtering options:**

```markdown
:::{cards}
:source: children
:filter: subsections   # Only subsections, not pages
:limit: 4              # Max 4 cards
:exclude: experimental # Exclude by slug
:::
```

### Option B: New `children-cards` Directive

A dedicated directive:

```markdown
:::{children-cards}
:columns: 2
:style: navigation
:::
```

Simpler but less flexible than enhancing existing cards.

### Option C: Jinja2 Loop (No Directive Change)

Use Jinja2 directly in markdown:

```markdown
::::{cards}
:columns: 2
{% for child in subsections %}
:::{card} {{ child.title }}
:link: {{ child.url }}
:pull: description
:::
{% endfor %}
::::
```

**Pros**: Works today  
**Cons**: Mixes Jinja2 and MyST syntax (awkward)

---

## Recommendation: Option A

Enhance the existing cards directive with `source: children`.

### Implementation Plan

1. **Parse `source` option** in `CardsDirective.parse()`
2. **Access template context** during rendering (need renderer access to `posts`/`subsections`)
3. **Generate card tokens** for each child
4. **Support filtering** via `:filter:`, `:limit:`, `:exclude:`

### API Design

```markdown
# Full auto-generation
:::{cards}
:source: children
:::

# With customization
:::{cards}
:source: children
:columns: 2
:filter: subsections
:sort: weight
:::

# Hybrid (some auto, some manual)
:::{cards}
:source: children
:exclude: experimental

:::{card} 🆕 Custom Card
:link: /custom/
Manual card mixed with auto-generated
:::
:::
```

### Frontmatter Contract

Children can specify card appearance via frontmatter:

| Field | Purpose | Example |
|-------|---------|---------|
| `title` | Card title | "Content Organization" |
| `description` | Card body | "How pages are structured" |
| `icon` | Card icon | "folder" |
| `card_color` | Card color | "blue", "green", etc. |
| `card_image` | Card header image | "/images/hero.jpg" |
| `weight` | Sort order | 10, 20, 30 |
| `hidden` | Exclude from cards | true |

---

## Migration Path

1. **Phase 1**: Implement `source: children` (new feature)
2. **Phase 2**: Update index pages to use new syntax
3. **Phase 3**: Remove hardcoded card definitions

### Before (Manual)

```markdown
::::{cards}
:::{card} 📁 Organize Content
:link: ./organization/
:color: green
Understand pages, sections, bundles...
:::
:::{card} ✍️ Write Content
:link: ./authoring/
:color: blue
Markdown, directives, and shortcodes...
:::
::::
```

### After (Auto-Generated)

```markdown
:::{cards}
:source: children
:columns: 2
:::
```

With children defining their own appearance in frontmatter:

```yaml
# organization/_index.md
---
title: Content Organization
description: Understand pages, sections, bundles, and how your folder structure becomes your site
icon: folder
card_color: green
---
```

---

## Open Questions

1. **Icon mapping**: Should we auto-map icons from category/type?
2. **Color assignment**: Auto-assign colors based on position/category?
3. **Hybrid mode**: How to mix auto and manual cards cleanly?
4. **Performance**: Does accessing template context from directive add overhead?

---

## Alternatives Considered

### Alternative: Template Macro

Create a `child_cards` macro in Jinja2:

```jinja
{{ child_cards(subsections, columns=2) }}
```

**Pros**: Pure Jinja2, works in any template  
**Cons**: Can't use in markdown content, requires template knowledge

### Alternative: Shortcode

```markdown
{{< child-cards columns="2" filter="subsections" >}}
```

**Pros**: Familiar syntax for Hugo users  
**Cons**: Shortcodes have different semantics than directives

---

## Success Criteria

1. ✅ Index pages can render child cards with zero manual duplication
2. ✅ Changes to child frontmatter automatically reflected
3. ✅ Filtering and sorting supported
4. ✅ Hybrid mode (auto + manual) works
5. ✅ No performance regression for pages not using feature
