---
title: Layout Directives
description: Reference for layout directives (cards, tabs, dropdown, grid)
weight: 12
tags: [reference, directives, layout, cards, tabs]
keywords: [cards, tabs, dropdown, grid, layout, directives]
---

# Layout Directives

Layout directives organize content into structured components like card grids, tabs, and collapsible sections.

## Key Terms

Card Grid
:   A container directive (`{cards}`) that creates a responsive grid of card components. Supports flexible column layouts and responsive breakpoints.

Card
:   An individual card component (`{card}`) within a card grid. Can include icons, links, images, colors, and footer content.

Tab Set
:   A container directive (`{tab-set}`) that groups multiple tab items together. Provides tabbed navigation for organizing related content.

Tab Item
:   An individual tab (`{tab-item}`) within a tab set. Contains content for one tab panel.

Dropdown
:   A collapsible section directive (`{dropdown}`) that can be expanded or collapsed. Useful for optional or advanced content to reduce cognitive load.

Grid
:   A Sphinx-Design compatibility directive (`{grid}`) that converts to card grids internally. Prefer `{cards}` for new content.

## Cards

Create responsive card grids for navigation, feature highlights, or content organization.

### Card Grid (`{cards}`)

Container for multiple cards with responsive column layout.

**Important**: Container directives like `{cards}` require **4 fences minimum** (`::::`). Use higher fence counts (5, 6, etc.) for deeper nesting (e.g., admonitions within cards, tabs within cards).

**Syntax**:

```markdown
::::{cards}
:columns: 3
:gap: medium
:style: default
:variant: navigation

:::{card} Card Title
:icon: book
:link: /docs/
:color: blue
:image: /hero.jpg
:footer: Updated 2025

Card content with **markdown** support.
:::
::::
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
:link: /docs/
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
- `:color:` - Color: `blue`, `green`, `red`, `yellow`, `orange`, `purple`, `gray`, `pink`, `indigo`
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

**Basic Card Grid**:

```markdown
::::{cards}
:columns: 3

:::{card} Getting Started
:icon: rocket
:link: /docs/getting-started/

Learn the basics
:::

:::{card} API Reference
:icon: code
:link: /api/

Complete API docs
:::

:::{card} Guides
:icon: book
:link: /docs/guides/

Step-by-step guides
:::
::::
```

**Responsive Columns**:

```markdown
::::{cards}
:columns: 1-2-3
:gap: large

:::{card} Card 1
Content
:::

:::{card} Card 2
Content
:::
::::
```

**Cards with Nested Admonitions**:

For nested directives like admonitions within cards, use 5 fences for the container:

````markdown
:::::{cards}
:columns: 2

::::{card} Important Card
:::{warning}
This feature requires special setup.
:::
::::

::::{card} Regular Card
Standard content here.
::::
:::::
````

:::{tip} Count the Fences
The container uses 5 fences (`:::::`), cards use 4 fences (`::::`), and the nested admonition uses 3 colons (`:::`). Each nesting level requires incrementing the fence count.
:::

**Auto-Pull from Linked Pages**:

Use `:pull:` to automatically fetch metadata from linked pages, reducing content duplication:

```markdown
::::{cards}
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
:link: /docs/contributor/
:pull: description

Custom content overrides pulled description.
:::
::::
```

The `:pull:` option supports:
- `title` - Page title from frontmatter
- `description` - Page description from frontmatter
- `icon` - Icon from frontmatter
- `image` - Image from frontmatter
- `date` - Page date
- `tags` - Page tags

:::{tip} Reference Targets
Use `id:ref-name` syntax to reference pages by their frontmatter `id` field instead of path. This makes links stable even if you reorganize content.
:::

**Layout Variants**:

Use `:layout:` for different card arrangements:

```markdown
::::{cards}
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
::::
```

Layout options:
- `default` - Vertical card (image top, content below)
- `horizontal` - Image left, content right
- `portrait` - Tall aspect ratio (2:3), great for app screenshots or TCG-style cards
- `compact` - Reduced padding for dense reference lists

**Portrait Cards (TCG/Phone Style)**:

```markdown
::::{cards}
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
::::
```

## Tabs

Create tabbed content sections for organizing related content.

### Tab Set (`{tab-set}`)

Container for tab items.

**Important**: Container directives like `{tab-set}` require **4 fences minimum** (`::::`). Use higher fence counts (5, 6, etc.) for deeper nesting (e.g., admonitions within tabs, steps within tabs).

**Syntax**:

````markdown
::::{tab-set}
:sync: my-key

:::{tab-item} Tab Title
:selected:

Tab content with **markdown** support.
:::

:::{tab-item} Another Tab
More content
:::
::::
````

**Options**:

- `:sync:` - Sync key for multiple tab-sets (same key = synchronized selection)
- `:id:` - Tab set ID

### Tab Item (`{tab-item}`)

Individual tab within a tab-set.

**Syntax**:

````markdown
:::{tab-item} Tab Title
:selected:

Tab content
:::
````

**Options**:

- `:selected:` - Mark this tab as initially selected (no value needed)

### Legacy Tabs (`{tabs}`)

Backward-compatible tabs syntax.

**Syntax**:

````markdown
:::{tabs}
:id: my-tabs

### Tab: First Tab

Content in first tab.

### Tab: Second Tab

Content in second tab.
:::
````

**Note**: Prefer `{tab-set}` / `{tab-item}` for new content.

### Examples

**Basic Tabs**:

````markdown
::::{tab-set}

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
::::
````

**Synchronized Tabs**:

````markdown
::::{tab-set}
:sync: code-example

:::{tab-item} Python
Python code
:::
::::

::::{tab-set}
:sync: code-example

:::{tab-item} Python
Same Python code (synced)
:::
::::
````

**Tabs with Nested Admonitions**:

For nested directives like admonitions within tabs, use 5 fences for the container:

````markdown
:::::{tab-set}

::::{tab-item} Setup
:::{warning}
Make sure to backup your data first!
:::

Setup instructions here.
::::

::::{tab-item} Usage
Regular usage content.
::::
:::::
````

:::{tip} Count the Fences!!!
The container uses 5 fences (`:::::`), tab items use 4 fences (`::::`), and the nested admonition uses 3 colons (`:::`). Each nesting level requires incrementing the fence count.
:::

## Dropdown

Collapsible sections for optional or advanced content.

**Syntax**:

`````markdown
::::{dropdown} Title
:open: true

Content with **markdown** support.

:::{note}
Nested directives work!
:::
::::
`````

**Options**:

- `:open:` - Open by default: `true`, `false` (default)

**Alias**: `{details}` works the same as `{dropdown}`.

### Examples

**Collapsed by Default**:

````markdown
:::{dropdown} Advanced Options
Click to expand advanced configuration options.
:::
````

**Open by Default**:

````markdown
:::{dropdown} Quick Reference
:open: true

Common commands and shortcuts.
:::
````

## Grid (Sphinx-Design Compatibility)

Compatibility layer for Sphinx-Design grid syntax.

:::{tip}
Container directives like `{grid}` require **4 fences minimum** (`::::`). Use higher fence counts for deeper nesting.
:::

**Syntax**:

```markdown
::::{grid} 1 2 2 2
:gutter: 1

:::{grid-item-card} Title
:link: /docs/

Content
:::
::::
```

:::{note}
Prefer `{cards}` / `{card}` for new content. Grid directives convert to cards internally.
:::

## Best Practices

1. **Card Grids**: Use for navigation, feature highlights, or content organization
2. **Tabs**: Use for related content that doesn't need to be visible simultaneously
3. **Dropdowns**: Use for optional or advanced content to reduce cognitive load
4. **Responsive Design**: Use responsive column syntax (`1-2-3`) for mobile-friendly layouts

## Related

- [Admonitions](/docs/reference/directives/admonitions/) - Callout boxes
- [Formatting Directives](/docs/reference/directives/formatting/) - Badges, buttons, steps
