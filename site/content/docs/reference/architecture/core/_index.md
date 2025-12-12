---
title: Core Architecture
nav_title: Core
description: Data models, build coordination, and core principles
weight: 10
cascade:
  type: doc
icon: bengal-rosette
---
# Core Architecture

The brain of Bengal — foundational data models and build coordination.

## Data Model Overview

```mermaid
graph TB
    subgraph "Core Objects"
        Site[Site]
        Page[Page]
        Section[Section]
        Asset[Asset]
    end

    Site --> Section
    Site --> Page
    Site --> Asset
    Section --> Page
    Section --> Section
    Page --> Asset
```

## Key Components

| Component | Responsibility | Module |
|-----------|----------------|--------|
| **Site** | Central container, holds all content | `bengal/core/site.py` |
| **Page** | Single content page with metadata | `bengal/core/page/` |
| **Section** | Directory container, holds children | `bengal/core/section.py` |
| **Asset** | Static file with processing metadata | `bengal/core/asset/` |

## Design Principles

- **No God Objects**: Each class has single responsibility
- **Passive Core**: Data models don't perform I/O
- **Composition over Inheritance**: BuildContext passes services
- **Immutable Where Possible**: Minimize side effects

:::{seealso}
- [Design Principles](../design-principles/) — Full architectural guidelines
- [Orchestration](orchestration/) — How builds are coordinated
:::
