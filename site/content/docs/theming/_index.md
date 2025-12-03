---
title: Theming
description: Templates, assets, and visual customization
weight: 25
cascade:
  type: doc
---

# Design & Theming

Control how your site looks with Jinja2 templates, CSS/JS assets, and theme packages.

## What Do You Need?

::::{cards}
:columns: 2
:gap: medium

:::{card} 🧩 Templates
:link: ./templating/
:color: blue

Jinja2 layouts, inheritance, partials, and the complete template API reference.
:::

:::{card} 🎨 Assets
:link: ./assets/
:color: green

CSS, JavaScript, images, and fonts. Processing, optimization, and fingerprinting.
:::

:::{card} 📦 Themes
:link: ./themes/
:color: purple

Use existing themes, customize without forking, or create your own from scratch.
:::

:::{card} 🍳 Recipes
:link: ./recipes/
:color: orange

Copy-paste patterns: list recent posts, group by category, filter by tags, and more.
:::
::::

## How Theming Works

```mermaid
flowchart TB
    subgraph Input
        A[Content Pages]
        B[Theme Templates]
        C[Assets CSS/JS]
    end
    
    subgraph "Template Engine"
        D[Select Layout]
        E[Render Jinja2]
        F[Process Assets]
    end
    
    subgraph Output
        G[HTML Pages]
        H[Optimized Assets]
    end
    
    A --> D
    B --> D
    D --> E
    C --> F
    E --> G
    F --> H
```

## Customization Levels

| Level | Effort | What You Can Change |
|-------|--------|---------------------|
| **CSS Variables** | Low | Colors, fonts, spacing via `--var` overrides |
| **Template Overrides** | Medium | Copy and modify specific templates |
| **Custom Theme** | High | Full control over all templates and assets |

:::{tip}
**Quick wins**: Start with [CSS Variables](./themes/customization/) to change colors and fonts without touching templates. Graduate to [Template Overrides](./templating/overrides/) when you need structural changes.
:::
