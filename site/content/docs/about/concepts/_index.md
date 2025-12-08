---
title: Core Concepts
description: Foundational concepts for understanding Bengal
weight: 30
props:
  icon: star
---
# Core Concepts

Understand how Bengal organizes content, processes files, and generates sites.

## The Build Model

```mermaid
flowchart LR
    subgraph Input
        A[Content .md]
        B[Templates .html]
        C[Assets CSS/JS]
    end

    subgraph Process
        D[Parse]
        E[Render]
        F[Optimize]
    end

    subgraph Output
        G[public/]
    end

    A --> D
    B --> E
    C --> F
    D --> E --> F --> G
```

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **Page** | A single content file (`.md`) → single HTML output |
| **Section** | A directory with `_index.md` → list page with children |
| **Bundle** | A directory with `index.md` → page with co-located assets |
| **Template** | Jinja2 HTML that wraps your content |
| **Asset** | CSS, JS, images — processed and optimized |

## Mental Model

::::{tab-set}
:::{tab-item} Files → Pages
Your file structure becomes your URL structure:

```
content/blog/hello.md → /blog/hello/
content/docs/_index.md → /docs/
```
:::

:::{tab-item} Templates → Layouts
Templates wrap content in HTML:

```
page.content + single.html → final HTML
```
:::

:::{tab-item} Assets → Output
Static files are copied and optionally processed:

```
static/css/main.css → public/css/main.a1b2c3.css
```
:::
::::

:::{tip}
**Start simple**: Most sites only need pages and a theme. Add sections when you need grouping, bundles when you need co-located assets.
:::
