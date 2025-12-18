---
title: Rendering Pipeline
nav_title: Rendering
description: How Bengal transforms Markdown to HTML
weight: 20
cascade:
  type: doc
icon: arrow-clockwise
---
# Rendering Pipeline

How Bengal transforms source content into final output.

## Pipeline Overview

```mermaid
flowchart LR
    subgraph Discovery
        A[Find Content]
        B[Parse Frontmatter]
    end

    subgraph Rendering
        C[Select Template]
        D[Parse Markdown]
        E[Render Jinja2]
    end

    subgraph "Post-Process"
        F[Generate Sitemap]
        G[Validate Links]
        H[Optimize Assets]
    end

    A --> B --> C --> D --> E --> F --> G --> H
```

## Stage Responsibilities

| Stage | What it does | Key modules |
|-------|--------------|-------------|
| **Discovery** | Find `.md` files, parse frontmatter | `bengal/discovery/` |
| **Rendering** | Template selection, Markdown → HTML | `bengal/rendering/` |
| **Post-Process** | Sitemap, RSS, link validation | `bengal/postprocess/` |

## Template Resolution

```mermaid
flowchart TD
    A[Page needs template] --> B{Has explicit layout?}
    B -->|Yes| C[Use specified template]
    B -->|No| D{Match by content type?}
    D -->|Yes| E[Use type template]
    D -->|No| F[Use default single.html]
```

:::{note}
The rendering pipeline is **lazy** — templates are compiled on first use and cached. Markdown is parsed only when content is accessed.
:::
