---
title: Extending
description: Autodoc, analysis, validation, and architecture
weight: 35
cascade:
  type: doc
---

# Extend Bengal

Power features for documentation teams: auto-generate API docs, analyze site structure, validate content, and contribute to Bengal itself.

## What Do You Need?

::::{cards}
:columns: 2
:gap: medium

:::{card} 📚 Autodoc
:link: ./autodoc/
:color: blue

Generate documentation from Python docstrings, CLI commands, and OpenAPI specs.
:::

:::{card} 🔬 Analysis
:link: ./analysis/
:color: green

Graph analysis, PageRank, link suggestions, and navigation optimization.
:::

:::{card} ✅ Validation
:link: ./validation/
:color: purple

Health checks, broken link detection, auto-fix, and custom validators.
:::

:::{card} 🏗️ Architecture
:link: ./architecture/
:color: orange

For contributors: Bengal's internals, object model, and extension points.
:::
::::

## Extension Points

```mermaid
flowchart TB
    subgraph "Your Code"
        A[Custom Validators]
        B[Content Loaders]
        C[Post-Processors]
    end
    
    subgraph "Bengal Pipeline"
        D[Discovery] --> E[Validation]
        E --> F[Rendering]
        F --> G[Post-Process]
    end
    
    A -.->|hooks into| E
    B -.->|feeds| D
    C -.->|extends| G
```

:::{note}
**Most users don't need this section.** These are power features for documentation teams with specific automation needs. Start with [Content](../content/) and [Theming](../theming/) for standard documentation.
:::
