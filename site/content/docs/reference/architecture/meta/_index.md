---
title: Meta & Operations
description: Performance, testing, and project structure
weight: 50
cascade:
  type: doc
icon: tag
---
# Meta & Operations

Operational details, standards, and project meta-information.

## Project Quality

```mermaid
flowchart LR
    subgraph Standards
        A[Testing]
        B[Performance]
        C[Organization]
    end

    subgraph Extensibility
        D[Extension Points]
        E[Plugin Hooks]
    end

    A --> Quality[Quality Assurance]
    B --> Quality
    C --> Maintainability[Maintainability]
    D --> Customization[Customization]
    E --> Customization
```

## Coverage

| Area | Coverage | Approach |
|------|----------|----------|
| **Testing** | Unit + Integration | pytest, fixture-based |
| **Performance** | Benchmarked | Build time, memory, incremental |
| **Organization** | Documented | Clear module boundaries |

## Extension Points

Bengal supports customization at multiple levels:

| Level | Mechanism | Use Case |
|-------|-----------|----------|
| **Content** | Custom loaders | New content sources |
| **Validation** | Custom validators | Project-specific rules |
| **Rendering** | Custom shortcodes | Rich content components |
| **Post-process** | Custom processors | Output transformations |

:::{seealso}
- [Extension Points](extension-points/) — Hook documentation
- [Testing](testing/) — Test patterns and fixtures
:::
