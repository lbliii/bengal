---
title: Extending
description: Autodoc, analysis, validation, and architecture
weight: 35
cascade:
  type: doc
props:
  icon: starburst
---
# Extend Bengal

Power features for documentation teams: auto-generate API docs, analyze site structure, validate content, and contribute to Bengal itself.

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
