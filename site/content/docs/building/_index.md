---
title: Building
description: Build configuration, CLI usage, and deployment
weight: 30
cascade:
  type: doc
---

# Build & Deploy

Configure, build, optimize, and deploy your Bengal site.

## What Do You Need?

:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::

## Build Pipeline

```mermaid
flowchart LR
    subgraph Input
        A[Content]
        B[Config]
        C[Theme]
    end

    subgraph Build
        D[Discovery]
        E[Rendering]
        F[Post-Process]
    end

    subgraph Output
        G[public/]
    end

    A --> D
    B --> D
    C --> E
    D --> E
    E --> F
    F --> G
```

## Quick Reference

| I want to... | Go to... |
|--------------|----------|
| Configure my site | [Configuration](./configuration/) |
| Build for production | [Commands](./commands/) |
| Speed up builds | [Performance](./performance/) |
| Deploy my site | [Deployment](./deployment/) |

:::{tip}
**Quick start**: Run `bengal build` for production, `bengal serve` for development. Add `--environment production` for production builds with optimizations.
:::
