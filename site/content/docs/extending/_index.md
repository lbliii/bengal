---
title: Extending
description: Autodoc, architecture, and Bengal internals
weight: 35
cascade:
  type: doc
icon: starburst
---
# Extend Bengal

Power features for documentation teams: auto-generate API docs and understand Bengal's architecture to contribute or customize.

## What Do You Need?

:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::

## Extension Points

```mermaid
flowchart TB
    subgraph "Your Code"
        A[Python Modules]
        B[Content Loaders]
        C[Post-Processors]
    end

    subgraph "Bengal Pipeline"
        D[Discovery] --> E[Processing]
        E --> F[Rendering]
        F --> G[Post-Process]
    end

    A -.->|autodoc generates| F
    B -.->|feeds| D
    C -.->|extends| G
```

:::{note}
**Most users don't need this section.** These are power features for documentation teams with specific automation needs. Start with [Content](../content/) and [Theming](../theming/) for standard documentation.
:::
