---
title: Layout Directives
nav_title: Layout
description: Reference for layout directives (cards, tabs, dropdown, grid)
weight: 12
tags:
- reference
- directives
- layout
- cards
- tabs
keywords:
- cards
- tabs
- dropdown
- grid
- layout
- directives
---

# Layout Directives

Layout directives organize content into structured components like card grids, tabs, and collapsible sections.

## Key Terms

:::{glossary}
:tags: layout
:::

## Cards

Create responsive card grids for navigation, feature highlights, or content organization.

### Card Grid (`{cards}`)

Container for multiple cards with responsive column layout. Use `:::{/cards}` to close.

**Syntax**:

```markdown
:::{cards}
:columns: 3
:gap: medium
:style: default
:variant: navigation

:::{card} Card Title
:icon: book
:link: docs/getting-started
:color: blue
:image: /hero.jpg
:footer: Updated 2025

Card content with **markdown** support.
:::

:::{/cards}
```

**Options**:

- `:columns:` - Column layout:
  - `auto` (default) - Auto-fit based on card width
  - `2`, `3`, `4` - Fixed columns
  - `1-2-3` - Responsive (mobile-tablet-desktop)
  - `1-2-3-4` - Responsive with wide breakpoint
- `:gap:` - Gap between cards: `small`, `medium` (default), `large`
- `:style:` - Card style: `default`, `minimal`, `bordered`
- `:variant:` - Variant: `navigation` (default), `info`, `concept`
- `:layout:` - Card layout: `default`, `horizontal`, `portrait`, `compact`

### Individual Card (`{card}`)

Single card within a cards container.

**Syntax**:

```markdown
:::{card} Card Title
:icon: book
:link: docs/getting-started
:color: blue
:image: /hero.jpg
:footer: Footer text

Card content with **markdown** support.

+++
Footer content (alternative to :footer: option)
:::
```

**Options**:

- `:icon:` - Icon name (e.g., `book`, `code`, `rocket`)
- `:link:` - Card link URL (path, slug, or `id:ref-target`)
- `:color:` - Color: `blue`, `green`, `red`, `yellow`, `orange`, `purple`, `gray`, `pink`, `indigo`, `teal`, `cyan`, `violet`
- `:image:` - Header image URL
- `:footer:` - Footer text (or use `+++` separator)
- `:pull:` - Auto-fetch fields from linked page: `title`, `description`, `icon`, `image`, `date`, `tags`
- `:layout:` - Override grid layout: `horizontal`, `portrait`, `compact`

**Footer Separator**:

```markdown
:::{card} Title
Body content
+++
Footer content
:::
```

### Examples

:::{example-label} Basic Card Grid
:::

```markdown
:::{cards}
:columns: 3

:::{card} Getting Started
:icon: rocket
:link: docs/get-started

Learn the basics
:::

:::{card} API Reference
:icon: code
:link: docs/reference/api

Complete API docs
:::

:::{card} Tutorials
:icon: book
:link: docs/tutorials

Step-by-step tutorials
:::

:::{/cards}
```

:::{example-label} Responsive Columns
:::

```markdown
:::{cards}
:columns: 1-2-3
:gap: large

:::{card} Card 1
Content
:::

:::{card} Card 2
Content
:::

:::{/cards}
```

:::{example-label} Cards with Nested Admonitions
:::

Named closers eliminate fence-counting for complex nesting:

````markdown
:::{cards}
:columns: 2

:::{card} Important Card
:::{warning}
This feature requires special setup.
:::
:::{/card}

:::{card} Regular Card
Standard content here.
:::{/card}

:::{/cards}
````

:::{tip} Named Closers
Use `:::{/name}` to explicitly close any container directive, eliminating the need to count colons.
:::

:::{example-label} Auto-Pull from Linked Pages
:::

Use `:pull:` to automatically fetch metadata from linked pages, reducing content duplication:

```markdown
:::{cards}
:columns: 3

:::{card}
:link: docs/getting-started/writer-quickstart
:pull: title, description
:::

:::{card}
:link: id:themer-qs
:pull: title, description, icon
:::

:::{card} Custom Title
:link: docs/get-started/quickstart-contributor
:pull: description

Custom content overrides pulled description.
:::

:::{/cards}
```

The `:pull:` option supports:
- `title` - Page title from frontmatter
- `description` - Page description from frontmatter
- `icon` - Icon from frontmatter
- `image` - Image from frontmatter
- `badge` - Badge from frontmatter

:::{tip} Reference Targets
Use `id:ref-name` syntax to reference pages by their frontmatter `id` field instead of path. This makes links stable even if you reorganize content.
:::

:::{example-label} Layout Variants
:::

Use `:layout:` for different card arrangements:

```markdown
:::{cards}
:columns: 2
:layout: horizontal

:::{card} Feature One
:image: /images/feature1.png

Image on left, content on right.
:::

:::{card} Feature Two
:image: /images/feature2.png

Great for feature showcases.
:::

:::{/cards}
```

Layout options:
- `default` - Vertical card (image top, content below)
- `horizontal` - Image left, content right
- `portrait` - Tall aspect ratio (2:3), great for app screenshots or TCG-style cards
- `compact` - Reduced padding for dense reference lists

:::{example-label} Portrait Cards (TCG/Phone Style)
:::

```markdown
:::{cards}
:columns: 3
:layout: portrait

:::{card} App Screenshot
:image: /images/app-home.png

Home screen of our mobile app.
:::

:::{card} Dashboard
:image: /images/app-dashboard.png

Analytics dashboard view.
:::

:::{/cards}
```

## Tabs

Create tabbed content sections for organizing related content.

### Tab Set (`{tab-set}`)

Container for tab items. Use `:::{/tab-set}` to close.

**Aliases**: `{tabs}`

**Syntax**:

````markdown
:::{tab-set}
:sync: my-key

:::{tab-item} Tab Title
:selected:

Tab content with **markdown** support.
:::

:::{tab-item} Another Tab
More content
:::

:::{/tab-set}
````

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:sync:` | — | Sync key for synchronizing tabs across multiple tab-sets |
| `:id:` | auto-generated | Tab set ID for targeting |

### Tab Item (`{tab-item}`)

Individual tab within a tab-set.

**Aliases**: `{tab}`

**Syntax**:

````markdown
:::{tab-item} Tab Title
:selected:
:icon: python
:badge: Recommended

Tab content
:::
````

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:selected:` | `false` | Mark this tab as initially selected |
| `:icon:` | — | Icon name to display next to the tab label |
| `:badge:` | — | Badge text (e.g., "New", "Beta", "Pro") |
| `:disabled:` | `false` | Mark tab as disabled/unavailable |

### Examples

:::{example-label} Basic Tabs
:::

````markdown
:::{tab-set}

:::{tab-item} Python
```python
print("Hello")
```
:::

:::{tab-item} JavaScript
```javascript
console.log("Hello");
```
:::

:::{/tab-set}
````

:::{example-label} Synchronized Tabs
:::

````markdown
:::{tab-set}
:sync: code-example

:::{tab-item} Python
Python code
:::

:::{/tab-set}

:::{tab-set}
:sync: code-example

:::{tab-item} Python
Same Python code (synced)
:::

:::{/tab-set}
````

:::{example-label} Tabs with Icons and Badges
:::

````markdown
:::{tab-set}

:::{tab-item} Python
:icon: python
:badge: Recommended
:selected:

Python code here.
:::

:::{tab-item} JavaScript
:icon: javascript

JavaScript code here.
:::

:::{tab-item} Ruby
:disabled:

Ruby support coming soon.
:::

:::{/tab-set}
````

:::{example-label} Tabs with Nested Admonitions
:::

Named closers eliminate fence-counting for complex nesting:

````markdown
:::{tab-set}

:::{tab-item} Setup
:::{warning}
Make sure to backup your data first!
:::

Setup instructions here.
:::{/tab-item}

:::{tab-item} Usage
Regular usage content.
:::{/tab-item}

:::{/tab-set}
````

:::{tip} Named Closers
Use `:::{/name}` to explicitly close any container directive, eliminating the need to count colons.
:::

## Dropdown

Collapsible sections for optional or advanced content. Renders as HTML5 `<details>`/`<summary>` elements for native browser support without JavaScript.

**Aliases**: `{details}`

**Syntax**:

````markdown
:::{dropdown} Title
:open: true
:icon: info
:description: Additional context about what is inside

Content with **markdown** support.

:::{note}
Nested directives work!
:::
:::
````

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:open:` | `false` | Open by default |
| `:icon:` | — | Icon name to display next to title |
| `:badge:` | — | Badge text (e.g., "New", "Advanced") |
| `:color:` | — | Color variant: `success`, `warning`, `danger`, `info`, `minimal` |
| `:description:` | — | Secondary text below the title to elaborate on content |
| `:class:` | — | Additional CSS classes |

### Examples

:::{example-label} Collapsed by Default
:::

````markdown
:::{dropdown} Advanced Options
:icon: settings

Click to expand advanced configuration options.
:::
````

:::{example-label} Open by Default
:::

````markdown
:::{dropdown} Quick Reference
:icon: info
:open: true

Common commands and shortcuts.
:::
````

:::{example-label} With Description
:::

````markdown
:::{dropdown} API Authentication
:icon: lock
:description: Learn about OAuth 2.0, API keys, and JWT tokens

Detailed authentication documentation here.
:::
````

:::{example-label} With Badge and Color
:::

````markdown
:::{dropdown} New Features
:icon: star
:badge: New
:color: success

Check out the latest features!
:::
````

:::{example-label} Warning Dropdown
:::

````markdown
:::{dropdown} Breaking Changes
:icon: alert
:color: warning
:badge: v2.0

Review breaking changes before upgrading.
:::
````

## Grid (Sphinx-Design Compatibility)

:::{deprecated}
Grid directives are deprecated. Use `{cards}` / `{card}` for all new content.
:::

Legacy compatibility layer for Sphinx-Design grid syntax. Grid directives are parsed and converted to cards internally.

**Syntax**:

```markdown
:::{grid} 1 2 2 2
:gutter: 1

:::{grid-item-card} Title
:link: docs/getting-started

Content
:::

:::{/grid}
```

**Migration**: Replace `{grid}` with `{cards}` and `{grid-item-card}` with `{card}`:

```markdown
:::{cards}
:columns: 1-2-2-2
:gap: small

:::{card} Title
:link: docs/getting-started

Content
:::

:::{/cards}
```

## Best Practices

1. **Card Grids**: Use for navigation, feature highlights, or content organization
2. **Tabs**: Use for related content that doesn't need to be visible simultaneously
3. **Dropdowns**: Use for optional or advanced content to reduce cognitive load
4. **Responsive Design**: Use responsive column syntax (`1-2-3`) for mobile-friendly layouts

## Auto-Generated Cards

For section index pages, consider using `{child-cards}` instead of manual cards. It automatically generates cards from child sections and pages:

```markdown
:::{child-cards}
:columns: 2
:gap: medium
:layout: default
:include: sections
:fields: title, description, icon
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:columns:` | `auto` | Column layout (same as `{cards}`) |
| `:gap:` | `medium` | Gap between cards: `small`, `medium`, `large` |
| `:layout:` | `default` | Card layout: `default`, `horizontal`, `portrait`, `compact` |
| `:include:` | `all` | What to include: `sections`, `pages`, `all` |
| `:fields:` | `title` | Fields to pull: `title`, `description`, `icon` |

See [Navigation Directives](/docs/reference/directives/navigation/) for full documentation.

## Related

- [Navigation Directives](/docs/reference/directives/navigation/) - Auto-generated cards, breadcrumbs, siblings
- [Admonitions](/docs/reference/directives/admonitions/) - Callout boxes
- [Formatting Directives](/docs/reference/directives/formatting/) - Badges, buttons, steps
