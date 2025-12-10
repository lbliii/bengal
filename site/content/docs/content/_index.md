---
title: Content
description: Author, organize, and validate your documentation
weight: 20
cascade:
  type: doc
icon: file-text
---
# The Content System

Bengal turns your Markdown files into a structured, validated documentation site.

## What Do You Need?

:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::

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

**Larger sites?** Check out [Analysis](./analysis/) to optimize internal linking and [Validation](./validation/) for automated quality checks.
:::
