---
title: Content
description: Author, organize, and validate your documentation
weight: 20
cascade:
  type: doc
---

# The Content System

Bengal turns your Markdown files into a structured, validated documentation site.

## What Do You Need?

::::{cards}
:columns: 2
:gap: medium

:::{card}
:link: ./organization/
:pull: title, description
:color: green
:::

:::{card}
:link: ./authoring/
:pull: title, description
:color: blue
:::

:::{card}
:link: ./collections/
:pull: title, description
:color: purple
:::

:::{card}
:link: ./sources/
:pull: title, description
:color: orange
:::

:::{card}
:link: ./reuse/
:pull: title, description
:color: teal
:::
::::

## How Content Flows

```mermaid
flowchart LR
    subgraph Sources
        A[Local .md files]
        B[GitHub repos]
        C[Notion/APIs]
    end
    
    subgraph Processing
        D[Discovery]
        E[Schema Validation]
        F[Markdown Rendering]
    end
    
    subgraph Output
        G[HTML Pages]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
```

:::{tip}
**New to Bengal content?** Start with [Organization](./organization/) to understand how files become pages, then explore [Authoring](./authoring/) for writing syntax.
:::
