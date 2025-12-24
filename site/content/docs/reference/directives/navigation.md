---
title: Navigation Directives
nav_title: Navigation
description: Reference for navigation directives (child-cards, breadcrumbs, siblings,
  prev-next, related)
weight: 15
tags:
- reference
- directives
- navigation
- cards
keywords:
- child-cards
- breadcrumbs
- siblings
- prev-next
- related
- navigation
- directives
---

# Navigation Directives

Navigation directives automatically generate navigation elements from your site's object tree. They read directly from page and section metadata, eliminating manual content duplication.

## Key Terms

:::{glossary}
:tags: navigation
:::

## Child Cards

Automatically generate a card grid from child sections and pages. This is the recommended approach for section index pages.

### Syntax

```markdown
:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::
```

### Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `:columns:` | `1`, `2`, `3`, `4`, `auto` | `2` | Number of columns in the grid |
| `:include:` | `all`, `sections`, `pages` | `all` | What to include in the cards |
| `:fields:` | Comma-separated list | `title, description` | Metadata fields to display |
| `:gap:` | `small`, `medium`, `large` | `medium` | Gap between cards |
| `:layout:` | `default`, `horizontal`, `compact` | `default` | Card layout style |

### Available Fields

- `title` - Page/section title from frontmatter
- `description` - Description from frontmatter
- `icon` - Icon from frontmatter (falls back to folder/file SVG icons)
- `date` - Publication date
- `tags` - Tag list
- `estimated_time` - Reading time estimate
- `difficulty` - Difficulty level

### Examples

:::{example-label} Basic Child Cards
:::

```markdown
:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::
```

:::{example-label} Include All Children
:::

```markdown
:::{child-cards}
:columns: 3
:include: all
:fields: title, description
:::
```

:::{example-label} Pages Only
:::

```markdown
:::{child-cards}
:include: pages
:fields: title, description, date
:layout: compact
:::
```

### Best Practices

1. **Use for section index pages** - Replace manual card lists with `child-cards`
2. **Add icons in frontmatter** - Each child page/section can have `icon: name` in frontmatter
3. **Add card_color in frontmatter** - Use `card_color: blue` for colored cards
4. **Falls back to SVG icons** - When no icon is specified, sections get folder icons and pages get file icons

## Breadcrumbs

Generate hierarchical breadcrumb navigation showing the page's location in the site.

### Syntax

```markdown
:::{breadcrumbs}
:separator: ›
:show-home: true
:home-text: Home
:home-url: /
:::
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `:separator:` | `›` | Separator character between items |
| `:show-home:` | `true` | Whether to show home link |
| `:home-text:` | `Home` | Text for home link |
| `:home-url:` | `/` | URL for home link |

### Example Output

```html
<nav class="breadcrumbs" aria-label="Breadcrumb">
  <a class="breadcrumb-item" href="/">Home</a>
  <span class="breadcrumb-separator">›</span>
  <a class="breadcrumb-item" href="/docs/">Docs</a>
  <span class="breadcrumb-separator">›</span>
  <span class="breadcrumb-item breadcrumb-current">Current Page</span>
</nav>
```

## Siblings

List sibling pages (pages in the same section as the current page).

### Syntax

```markdown
:::{siblings}
:limit: 10
:exclude-current: true
:show-description: false
:::
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `:limit:` | `0` (no limit) | Maximum number of siblings to show |
| `:exclude-current:` | `true` | Whether to exclude the current page |
| `:show-description:` | `false` | Whether to show page descriptions |

### Example Output

```html
<div class="siblings">
  <ul class="siblings-list">
    <li>
      <a href="/docs/theming/assets/">Assets</a>
      <span class="sibling-description">Managing static assets</span>
    </li>
    <li>
      <a href="/docs/theming/themes/">Themes</a>
    </li>
  </ul>
</div>
```

## Prev/Next Navigation

Generate previous/next links for sequential navigation within a section.

### Syntax

```markdown
:::{prev-next}
:show-title: true
:show-section: false
:::
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `:show-title:` | `true` | Show page titles in links |
| `:show-section:` | `false` | Show section names (reserved for future use) |

### Example Output

```html
<nav class="prev-next">
  <a class="prev-next-link prev-link" href="/docs/theming/templating/">
    <span class="prev-next-label">← Previous</span>
    <span class="prev-next-title">Templating</span>
  </a>
  <a class="prev-next-link next-link" href="/docs/theming/themes/">
    <span class="prev-next-label">Next →</span>
    <span class="prev-next-title">Themes</span>
  </a>
</nav>
```

## Related Pages

List pages that share tags with the current page.

### Syntax

```markdown
:::{related}
:limit: 5
:title: Related Articles
:show-tags: true
:::
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `:limit:` | `5` | Maximum number of related pages to show |
| `:title:` | `Related Articles` | Section title |
| `:show-tags:` | `false` | Whether to show matching tags |

### Example Output

```html
<aside class="related">
  <h3 class="related-title">Related Articles</h3>
  <ul class="related-list">
    <li>
      <a href="/docs/tutorials/theming/">Theming Tutorial</a>
      <span class="related-tags">theming, css, customization</span>
    </li>
    <li>
      <a href="/docs/theming/assets/">Custom CSS Guide</a>
    </li>
  </ul>
</aside>
```

## How It Works

Navigation directives access Bengal's object tree directly:

```mermaid
flowchart LR
    subgraph "Object Tree"
        A[Site] --> B[Section]
        B --> C[Page]
        B --> D[Subsection]
        C --> E[metadata]
    end

    subgraph "Directives"
        F[child-cards] -.-> B
        G[breadcrumbs] -.-> C
        H[siblings] -.-> B
        I[prev-next] -.-> C
        J[related] -.-> E
    end
```

This means:
- **No manual updates needed** - Cards update automatically when you add/remove pages
- **Single source of truth** - Metadata comes from frontmatter, not duplicated in cards
- **O(1) lookups** - Direct object access, no index lookups required

## Frontmatter for Navigation

To get the best results, add these fields to your pages' frontmatter:

```yaml
---
title: My Page
description: A helpful description for cards
icon: book           # Icon name (book, code, rocket, etc.)
card_color: blue     # Card color (blue, green, purple, orange, etc.)
weight: 10           # Sort order (lower = first)
tags: [guide, python]  # For related pages
---
```

## Related

- [Layout Directives](/docs/reference/directives/layout/) - Manual cards and tabs
- [Content Organization](/docs/content/organization/) - How sections and pages work
