---
title: Core Architecture
nav_title: Core
description: Data models and build coordination
weight: 10
cascade:
  type: doc
icon: bengal-rosette
---

# Core Architecture

Foundational data models and build coordination for Bengal's static site generation.

| Component | Responsibility | Module |
|-----------|----------------|--------|
| **Site** | Central container, holds all content | `bengal/core/site/` |
| **Page** | Single content page with metadata | `bengal/core/page/` |
| **Section** | Directory container, holds children | `bengal/core/section/` |
| **Asset** | Static file with processing metadata | `bengal/core/asset/` |

## Design Principles

- **No God Objects**: Each class has single responsibility (Site uses 7 focused mixins)
- **Passive Core**: Core models (PageCore, Section) are data-only; Site and Asset provide I/O convenience APIs that orchestrators coordinate
- **Composition over Inheritance**: BuildContext passes services between build phases
- **Immutable PageCore**: PageCore uses `frozen=True` for thread-safety and cache integrity (Python 3.14t compatible)

## In This Section

| Topic | Description |
|-------|-------------|
| [Cache](cache.md) | Build cache system with Zstandard compression |
| [Content Types](content-types.md) | Strategy pattern for type-specific behavior |
| [Data Flow](data-flow.md) | How data moves through the build pipeline |
| [Object Model](object-model.md) | Core data structures and relationships |
| [Orchestration](orchestration.md) | Build phase coordination |
| [Pipeline](pipeline.md) | Rendering pipeline architecture |

:::{seealso}
[Design Principles](../design-principles.md) — Full architectural guidelines
:::
